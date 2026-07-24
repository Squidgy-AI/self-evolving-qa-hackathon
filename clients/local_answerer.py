"""LocalAnswerer — a local, no-network drop-in for ConciergeClient.

Retrieves context via keyword search over a local codebase checkout, injects
"canon" (promoted verified docs) at the top of the context, and calls
whichever model backend is configured (Pioneer or Gemini) to compose a cited
answer. Exists so a demo isn't blocked by Concierge being down or flaky.

Env:
    TARGET_REPO      local checkout to answer questions about
                      (default ~/Git/Squidgy/codebase-concierge)
    PIONEER_API_KEY  preferred model backend (clients.pioneer_client)
    GEMINI_API_KEY   fallback model backend (google-genai)
"""

from __future__ import annotations

import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from clients.concierge_client import Answer, ConciergeClient  # noqa: E402

TARGET_REPO = Path(os.getenv("TARGET_REPO", str(Path.home() / "Git/fastapi")))
CANON_DIR = REPO_ROOT / "data" / "canon"
# Prefix match: catches .venv-billing as well as .venv. The backend repo vendors
# ~2,500 site-packages files; without this the retriever returns Stripe internals.
SKIP_DIRS = (".git", ".venv", "venv", "node_modules", "__pycache__", "site-packages",
             ".mypy_cache", ".pytest_cache", "dist", "build", ".next")
CITATION = re.compile(r"([\w./-]+\.(?:py|ts|js|md|json|ya?ml|sh)):(\d+)")

HEDGE_TEXT = "I couldn't find that in the indexed codebase."

SYSTEM_PROMPT = (
    "You are a codebase Q&A assistant. Answer ONLY using the SOURCE below — never "
    "your own outside knowledge. Cite every factual claim inline as "
    "`path/to/file.py:123`, using paths and line numbers exactly as they appear in "
    "the SOURCE. Prefer canon (verified documentation, marked below) over raw code "
    "when both answer the question. If the SOURCE genuinely does not contain the "
    f'answer, reply with exactly: "{HEDGE_TEXT}" and nothing else.'
)

class LocalAnswerer:
    def __init__(self, target_repo: Path | str | None = None):
        self.target_repo = Path(target_repo) if target_repo else TARGET_REPO
        self._cache: dict[str, Answer] = {}

    def healthy(self) -> bool:
        return self.target_repo.is_dir()

    def clear_cache(self) -> None:
        """Drop memoised answers. The loop calls this after publishing canon —
        otherwise the re-ask returns the pre-canon answer and improvement can
        never be measured."""
        self._cache.clear()

    def ask(self, question: str, mode: str | None = None) -> Answer:
        key = _normalise(question)
        if key in self._cache:
            c = self._cache[key]
            return Answer(question=question, text=c.text, sources=c.sources,
                           mode=c.mode, cache_hit=True, raw=c.raw)

        canon_text = _load_canon()
        code_text = _retrieve(self.target_repo, question)
        context = ""
        if canon_text:
            context += "=== VERIFIED DOCUMENTATION (canon) ===\n" + canon_text + "\n\n"
        context += "=== SOURCE CODE ===\n" + (code_text or "(no matching files found)")

        text = _compose(question, context)
        sources = [f"{m.group(1)}:{m.group(2)}" for m in CITATION.finditer(text)]

        answer = Answer(
            question=question, text=text, sources=sources,
            mode=mode or "eng", cache_hit=False,
            raw={"backend": "local", "context_chars": len(context)},
        )
        self._cache[key] = answer
        return answer

def _normalise(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip().lower())

def _load_canon() -> str:
    """Canon = promoted, verified docs. This is how the system improves over
    time: future answers see what past cycles learned, at the top of context."""
    if not CANON_DIR.is_dir():
        return ""
    parts = []
    for p in sorted(CANON_DIR.glob("*.md")):
        try:
            parts.append(f"--- canon: {p.name} ---\n{p.read_text(encoding='utf-8', errors='ignore')}")
        except OSError:
            continue
    return "\n\n".join(parts)

def _retrieve(target_repo: Path, question: str, max_files: int = 6, span: int = 40) -> str:
    if not target_repo.is_dir():
        return ""
    terms = re.findall(r"[a-zA-Z_]{3,}", question.lower())[:8]
    if not terms:
        return ""
    scored: list[tuple[int, Path]] = []
    for p in target_repo.rglob("*.py"):
        if any(part.startswith(SKIP_DIRS) for part in p.parts):
            continue
        try:
            body = p.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        hits = sum(body.count(t) for t in terms)
        if not hits:
            continue
        # Raw hit counts just elect the biggest file. fastapi/applications.py is
        # thousands of lines of Doc(...) prose that mentions "dependency" and
        # "cache" constantly, so it buried dependencies/utils.py where the logic
        # actually lives. Normalise by length, and reward files whose PATH matches
        # the question — a question about dependencies wants dependencies/*.
        rel_l = str(p).lower()
        distinct = sum(1 for t in terms if t in body)          # breadth beats repetition
        path_bonus = 1 + 0.75 * sum(1 for t in terms if t in rel_l)
        score = (hits ** 0.5) * distinct * path_bonus / (1 + len(body) / 60000)
        scored.append((score, p))
    scored.sort(reverse=True, key=lambda x: x[0])

    chunks = []
    for _, p in scored[:max_files]:
        rel = p.relative_to(target_repo)
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        best, best_hits, step = 0, -1, max(span // 2, 1)
        for i in range(0, max(1, len(lines) - span) + 1, step):
            hits = sum(" ".join(lines[i:i + span]).lower().count(t) for t in terms)
            if hits > best_hits:
                best, best_hits = i, hits
        numbered = "\n".join(
            f"{rel}:{i + 1}: {l}" for i, l in enumerate(lines[best:best + span], start=best)
        )
        chunks.append(f"--- {rel} (lines {best + 1}-{min(best + span, len(lines))}) ---\n{numbered}")
    return "\n\n".join(chunks)[:24000]

def _compose(question: str, context: str) -> str:
    user_msg = f"{context}\n\nQUESTION: {question}"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    # Prefer Pioneer, but a paywalled/erroring Pioneer must not kill the run — fall
    # through to Gemini. (Pioneer 403s with card_required until the promo is applied.)
    if os.getenv("PIONEER_API_KEY"):
        from clients.pioneer_client import PioneerClient
        client = PioneerClient()
        try:
            text, _ = client.chat(messages)
            return text
        except Exception as e:  # noqa: BLE001
            print(f"    ! pioneer compose failed ({type(e).__name__}); falling back to Gemini")
        finally:
            client.close()

    if os.getenv("GEMINI_API_KEY"):
        from google import genai
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        resp = client.models.generate_content(
            model=os.getenv("JUDGE_MODEL", "gemini-2.5-flash"),
            contents=f"{SYSTEM_PROMPT}\n\n{user_msg}",
        )
        return resp.text or ""

    # Dev stopgap so the loop is runnable before sponsor keys land. Never reached
    # once PIONEER_API_KEY or GEMINI_API_KEY is set.
    from clients import claude_cli
    if claude_cli.available():
        text, _ = claude_cli.chat(messages)
        return text

    raise RuntimeError("No model backend configured — set PIONEER_API_KEY or GEMINI_API_KEY.")

def get_answerer():
    """Pick the Q&A backend, best first:

      1. DeepWikiClient  — the live production RAG over the real Squidgy repos.
                           No auth needed. This is what we're actually evolving.
      2. ConciergeClient — the older service, kept as a fallback.
      3. LocalAnswerer   — offline last resort so a demo is never blocked.

    Each candidate gets a cheap health probe then one real ask() bounded to ~25s,
    so a hung service can't hang the caller. Prints which was chosen and why.
    """
    # ANSWERER=local forces the local backend. Needed because deepwiki's index is
    # scoped to a repo — pointing it at an unindexed one silently answers from the
    # wrong codebase, which grades every question a miss.
    forced = os.getenv("ANSWERER", "").strip().lower()
    if forced == "local":
        print("[get_answerer] ANSWERER=local; using LocalAnswerer")
        return LocalAnswerer()

    try:
        from clients.deepwiki_client import DeepWikiClient

        dw = DeepWikiClient()
        if dw.healthy():
            # Probe with something concrete — a vague question makes any RAG hedge,
            # and a hedge here is not evidence the service is down.
            a = _bounded_ask(dw, "What web framework does this backend use?", 40.0)
            if a is not None and a.text.strip():
                print(f"[get_answerer] using DeepWikiClient ({dw.base_url})")
                return dw
            print("[get_answerer] deepwiki reachable but did not answer; trying next")
        else:
            print("[get_answerer] deepwiki not healthy; trying next")
    except Exception as e:  # noqa: BLE001
        print(f"[get_answerer] deepwiki unavailable ({type(e).__name__}: {e}); trying next")

    concierge = ConciergeClient()
    try:
        r = httpx.get(f"{concierge.base_url}/healthz", timeout=5.0)
        if r.status_code >= 500:
            print(f"[get_answerer] {concierge.base_url}/healthz -> {r.status_code}; using LocalAnswerer")
            return LocalAnswerer()
    except httpx.HTTPError as e:
        print(f"[get_answerer] {concierge.base_url}/healthz unreachable ({e}); using LocalAnswerer")
        return LocalAnswerer()

    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(concierge.ask, "sanity check: are you answering questions?")
    try:
        future.result(timeout=25.0)
    except FutureTimeoutError:
        print("[get_answerer] Concierge ask() exceeded 25s; using LocalAnswerer")
        pool.shutdown(wait=False)
        return LocalAnswerer()
    except Exception as e:  # noqa: BLE001
        print(f"[get_answerer] Concierge ask() failed ({e}); using LocalAnswerer")
        pool.shutdown(wait=False)
        return LocalAnswerer()

    pool.shutdown(wait=False)
    print(f"[get_answerer] Concierge is healthy and answering at {concierge.base_url}; using ConciergeClient")
    return concierge


def _bounded_ask(client, question: str, timeout_s: float):
    """One ask() with a hard wall-clock bound. Returns the Answer, or None on
    timeout/error. The worker thread is abandoned rather than joined so a hung
    backend can never block the caller."""
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(client.ask, question).result(timeout=timeout_s)
    except Exception:  # noqa: BLE001 - timeout or transport, both mean "try next"
        return None
    finally:
        pool.shutdown(wait=False)


def smoke() -> None:
    la = LocalAnswerer()
    print(f"[..] target_repo = {la.target_repo}")
    print(f"[{'OK' if la.healthy() else '??'}] target repo present")

    canon = _load_canon()
    print(f"[{'OK' if CANON_DIR.is_dir() else '--'}] canon dir={CANON_DIR} loaded={len(canon)} chars")

    good_q = "How does the Q&A cache decide a cache hit?"
    bad_q = "What is the airspeed velocity of an unladen swallow?"

    ctx = _retrieve(la.target_repo, good_q)
    print(f"[{'OK' if ctx else '??'}] retrieval returned {len(ctx)} chars for: {good_q!r}")

    if not (os.getenv("PIONEER_API_KEY") or os.getenv("GEMINI_API_KEY")):
        print("[SKIP] no PIONEER_API_KEY / GEMINI_API_KEY set — verified retrieval + canon "
              "injection only, did not verify generation. Set one of those env vars to "
              "run the full smoke test.")
        return

    try:
        a1 = la.ask(good_q)
        a2 = la.ask(bad_q)
        a2_repeat = la.ask(bad_q)
        assert a2.looks_hedged, f"expected unanswerable question to be hedged, got: {a2.text[:200]!r}"
        print(f"PASS: answerable q -> {len(a1.sources)} sources, hedged={a1.looks_hedged}; "
              f"unanswerable q hedged correctly; cache_hit on repeat={a2_repeat.cache_hit}")
    except AssertionError as e:
        print(f"FAIL: {e}")
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {type(e).__name__}: {e}")

if __name__ == "__main__":
    smoke()
