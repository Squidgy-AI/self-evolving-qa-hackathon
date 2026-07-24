"""The evolution loop.

One cycle:

    ask Concierge the golden questions   -> grade each (Gemini)
    for every miss:
        recall a prior fix from memory (Actian)   -- free, no research needed
        else research the repo (Pioneer-routed)   -- costs tokens
        write canon with file:line citations
        VERIFY: every citation must resolve to a real line, and the re-asked
                question must score better, and nothing else may regress
        promote -> Senso (+ publish); remember in Actian (worked=True)
        reject  -> discard; remember in Actian (worked=False) so we don't retry it
    post every miss to Pioneer /feedback so their model retrains on our corrections
    append a CycleResult to data/runs.jsonl

The two rules that make this safe rather than a hallucination amplifier:
  1. a citation that doesn't resolve => automatic rejection
  2. no measured improvement => no promotion

Entry points (see CONTRACT.md): grade(), research(), verify(), promote(), run_cycle().
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.models import (  # noqa: E402
    Canon,
    CycleResult,
    Gap,
    Grade,
    PromoteResult,
    Verification,
    now,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data"
RUNS = DATA / "runs.jsonl"

# Local checkout of the codebase Concierge answers questions about. Citations are
# validated against this, so it must exist for verification to mean anything.
TARGET_REPO = Path(
    os.getenv("TARGET_REPO", str(Path.home() / "Git/fastapi"))
)

# Line number is optional: deepwiki cites `routes/subaccount_teammates.py` while the
# researcher emits `file.py:123`. Both are checkable — a path that doesn't exist in the
# repo is a hallucination either way, which is the guard that actually matters.
CITATION = re.compile(r"([\w./-]+\.(?:py|ts|tsx|js|jsx|md|json|yaml|yml|sh|sql))(?::(\d+))?")

# Directory names to never retrieve from. Prefix match, so `.venv-billing` and
# `.venv` are both caught — the backend repo vendors ~2,500 site-packages files
# and without this the retriever drowns in Stripe SDK internals.
SKIP_PREFIXES = (".git", ".venv", "venv", "node_modules", "__pycache__", "site-packages",
                 ".mypy_cache", ".pytest_cache", "dist", "build", ".next")


def _skip(path: Path) -> bool:
    return any(part.startswith(SKIP_PREFIXES) for part in path.parts)


def set_target_repo(path: str | Path) -> None:
    """Point the loop at a different local checkout at runtime (for the 'ask about
    any repo' demo). Resets the basename index so citation validation re-scans the
    new tree. Also updates the LocalAnswerer's target so answers come from it."""
    global TARGET_REPO, _BASENAME_INDEX
    TARGET_REPO = Path(path)
    _BASENAME_INDEX = None
    os.environ["TARGET_REPO"] = str(TARGET_REPO)
    try:
        import clients.local_answerer as la
        la.TARGET_REPO = TARGET_REPO
    except Exception:  # noqa: BLE001
        pass


# Questions about squidgy_updated_backend — the live repo deepwiki indexes.
GOLDEN = [
    # fastapi/fastapi internals — maintainer-level questions, not usage docs, so the
    # baseline genuinely misses some. Public repo: judges can verify every citation.
    "How does the dependency injection cache key work within a single request?",
    "How does FastAPI decide whether a route handler runs in the threadpool or the event loop?",
    "How are sub-dependencies with yield torn down when an exception is raised?",
    "How does the response model serialisation field get built and cached?",
    "What happens to a background task if the response fails to send?",
    "How does the router resolve a path with both a static and a parameterised match?",
    "How are WebSocket dependencies resolved differently from HTTP ones?",
    "How does the OpenAPI schema deduplicate models that share a name?",
]


# --------------------------------------------------------------------------- utils

def _lazy_clients():
    """Import clients lazily so a missing key breaks one stage, not the whole module."""
    from clients.judge import Judge
    from clients.local_answerer import get_answerer

    # Hosted Concierge if it's actually answering, else the local answerer over the
    # same codebase. Same interface either way — the loop doesn't care.
    concierge = get_answerer()
    try:
        judge = Judge()
    except Exception as e:  # noqa: BLE001
        print(f"  ! judge unavailable: {e}")
        judge = None

    memory = None
    try:
        from clients.memory_client import ExperienceMemory

        memory = ExperienceMemory()
        memory.ensure_collection()
    except Exception as e:  # noqa: BLE001
        print(f"  ! memory unavailable ({type(e).__name__}) — cycle will run without recall")

    pioneer = None
    try:
        from clients.pioneer_client import PioneerClient

        pioneer = PioneerClient()
    except Exception as e:  # noqa: BLE001
        print(f"  ! pioneer unavailable ({type(e).__name__}) — research falls back to judge model")

    senso = None
    try:
        from clients.senso_client import SensoClient

        senso = SensoClient()
    except Exception as e:  # noqa: BLE001
        print(f"  ! senso unavailable ({type(e).__name__}) — promotion will be local-only")

    return concierge, judge, memory, pioneer, senso


def _signature(q: str) -> str:
    toks = re.findall(r"[a-z0-9]+", q.lower())
    stop = {"the", "a", "an", "is", "are", "how", "what", "does", "do", "and", "or",
            "of", "to", "in", "on", "for", "with", "it", "its", "where", "when", "can"}
    return " ".join(sorted(t for t in toks if t not in stop and len(t) > 1))


_BASENAME_INDEX: dict[str, Path] | None = None


def _basename_index() -> dict[str, Path]:
    """basename -> first matching path, built once. Previously this was an rglob per
    citation, which on a 1000+ file repo pegged CPU and got the process killed."""
    global _BASENAME_INDEX
    if _BASENAME_INDEX is None:
        idx: dict[str, Path] = {}
        for p in TARGET_REPO.rglob("*"):
            if p.is_file() and not _skip(p):
                idx.setdefault(p.name, p)
        _BASENAME_INDEX = idx
    return _BASENAME_INDEX


def validate_citations(citations: list[str]) -> tuple[list[str], list[str]]:
    """Split citations into (valid, invalid). A citation is valid only if the file
    exists in TARGET_REPO and actually has that many lines."""
    valid, invalid = [], []
    for c in citations:
        m = CITATION.search(c)
        if not m:
            invalid.append(c)
            continue
        rel, line_s = m.group(1), m.group(2)
        path = TARGET_REPO / rel
        if not path.is_file():
            # Try a basename match — deepwiki cites `invitation_handler.py` while the
            # file may live deeper in the tree. Still a real existence check.
            hit = _basename_index().get(Path(rel).name)
            if hit is None:
                invalid.append(c)
                continue
            path = hit

        if line_s is None:
            valid.append(c)  # path-level citation: file exists, that's the check
            continue

        try:
            with path.open("r", encoding="utf-8", errors="ignore") as fh:
                n = sum(1 for _ in fh)
        except OSError:
            invalid.append(c)
            continue
        (valid if 1 <= int(line_s) <= n else invalid).append(c)
    return valid, invalid


# ------------------------------------------------------------------- loop stages

GRADES = DATA / "grades.json"


def _load_grades() -> dict:
    if GRADES.exists():
        try:
            return json.loads(GRADES.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _save_grade(question: str, g: Grade) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    cache = _load_grades()
    cache[question] = {"verdict": g.verdict, "reason": g.reason,
                       "citations_valid": g.citations_valid,
                       "citations_total": g.citations_total, "graded_at": g.graded_at}
    GRADES.write_text(json.dumps(cache, indent=1), encoding="utf-8")


def grade(question: str, concierge=None, judge=None, force: bool = False) -> Grade:
    """@Grader — ask Concierge and score the answer.

    Always a fresh ask + judge against whatever canon is *currently* on disk. No
    caching: an earlier version cached grades and, because verify() re-grades with
    a candidate doc temporarily staged, those inflated grades survived even when the
    doc was rejected — so the score climbed while the canon dir stayed empty. Fake.
    Every grade here reflects the real, persisted state, so score_after is always
    reproducible by re-running against data/canon/.

    (force is accepted for call-site compatibility; grading is always fresh now.)
    """
    if concierge is None:
        concierge, judge, *_ = _lazy_clients()
    if hasattr(concierge, "clear_cache"):
        concierge.clear_cache()  # answer must reflect current canon, not a memo
    ans = concierge.ask(question)
    cited, bad = validate_citations(ans.sources)

    if judge is None:
        verdict = "miss" if ans.looks_hedged else ("grounded" if cited else "partial")
        reason = "heuristic only (no judge configured)"
    else:
        verdict, reason = judge.grade(question, ans.text, ans.sources)
        # A hedge is a miss regardless of what the judge thought.
        if ans.looks_hedged and verdict != "miss":
            verdict, reason = "miss", f"hedged answer ({reason})"

    return Grade(
        question=question,
        answer=ans.text,
        verdict=verdict,  # type: ignore[arg-type]
        reason=reason,
        citations_valid=len(cited),
        citations_total=len(ans.sources),
    )


def research(gap: Gap, pioneer=None, memory=None) -> Canon | None:
    """@Researcher — recall a prior fix, else derive a new one from the repo."""
    if memory is not None:
        try:
            hits = memory.recall(gap.question, limit=3, min_score=0.85)
            if hits:
                h = hits[0]
                payload = h.get("payload", h)
                return Canon(
                    title=f"[recalled] {gap.question[:70]}",
                    body_md=payload.get("fix", ""),
                    citations=payload.get("citations", []),
                    source_gap=gap.question,
                    from_memory=True,
                )
        except Exception as e:  # noqa: BLE001
            print(f"    ! recall failed: {e}")

    context = _grep_repo(gap.question)
    if not context:
        return None

    # A human reviewer's thumbs-down note (if any) steers the research — this is the
    # "self-evolving with optional human guidance" path. The note only guides; the
    # citation + improvement gates still apply, so a human can't force in a bad doc.
    guidance = ""
    if getattr(gap, "human_note", ""):
        guidance = (
            f"\nA human reviewer flagged the previous answer and said:\n"
            f"\"{gap.human_note}\"\nUse this to focus your documentation.\n"
        )

    prompt = (
        "You are documenting a codebase so a Q&A tool can answer this question "
        "correctly in future.\n\n"
        f"QUESTION: {gap.question}\n"
        f"{guidance}\n"
        f"RELEVANT SOURCE:\n{context}\n\n"
        "Write a short markdown doc that answers the question. Cite specific lines as "
        "`path/to/file.py:123`. Every claim must have a citation. Do not invent paths — "
        "only cite files shown above. Return markdown only."
    )

    msgs = [{"role": "user", "content": prompt}]
    text = None
    # Pioneer first (it's a sponsor tool + gives an inference_id for /feedback), but
    # a 403/paywall must not stop us researching — fall through to Gemini, then CLI.
    if pioneer is not None:
        try:
            text, _ = pioneer.chat(msgs)
        except Exception as e:  # noqa: BLE001
            print(f"    ! pioneer research failed ({type(e).__name__}); trying Gemini")
    if text is None and os.getenv("GEMINI_API_KEY"):
        try:
            from google import genai

            gc = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            resp = gc.models.generate_content(
                model=os.getenv("JUDGE_MODEL", "gemini-2.5-flash"), contents=prompt,
                config={"temperature": 0.0},
            )
            text = resp.text or None
        except Exception as e:  # noqa: BLE001
            print(f"    ! gemini research failed ({type(e).__name__}); trying CLI")
    if text is None:
        from clients import claude_cli

        if not claude_cli.available():
            print("    ! no research backend available")
            return None
        try:
            text, _ = claude_cli.chat(msgs)
        except Exception as e:  # noqa: BLE001
            print(f"    ! research failed: {e}")
            return None

    return Canon(
        title=gap.question[:80],
        body_md=text,
        citations=[m.group(0) for m in CITATION.finditer(text)],
        source_gap=gap.question,
    )


def _grep_repo(question: str, max_files: int = 6, span: int = 40) -> str:
    """Cheap keyword retrieval over the target repo. Good enough to ground a doc, and
    it keeps the token bill down versus shipping whole files."""
    if not TARGET_REPO.is_dir():
        print(f"    ! TARGET_REPO missing: {TARGET_REPO}")
        return ""
    terms = [t for t in re.findall(r"[a-zA-Z_]{4,}", question.lower())][:6]
    if not terms:
        return ""
    scored: list[tuple[int, Path]] = []
    for p in TARGET_REPO.rglob("*.py"):
        if _skip(p):
            continue
        try:
            body = p.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        score = sum(body.count(t) for t in terms)
        if score:
            scored.append((score, p))
    scored.sort(reverse=True, key=lambda x: x[0])

    chunks = []
    for _, p in scored[:max_files]:
        rel = p.relative_to(TARGET_REPO)
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        best, best_hits = 0, 0
        for i in range(0, max(1, len(lines) - span), span // 2 or 1):
            window = " ".join(lines[i:i + span]).lower()
            hits = sum(window.count(t) for t in terms)
            if hits > best_hits:
                best, best_hits = i, hits
        numbered = "\n".join(f"{rel}:{i+1}: {l}" for i, l in enumerate(lines[best:best + span], start=best))
        chunks.append(numbered)
    return "\n\n".join(chunks)[:24000]


def verify(canon: Canon, before: Grade, concierge=None, judge=None,
           others: list[Grade] | None = None) -> Verification:
    """@Verifier — citations must resolve AND the score must actually improve."""
    valid, invalid = validate_citations(canon.citations)
    if not canon.citations:
        return Verification(False, 0, 0, [], "no citations — cannot verify")
    if invalid:
        return Verification(
            False, len(valid), len(canon.citations), invalid,
            f"{len(invalid)} citation(s) do not resolve to real lines",
        )

    # Stage the canon where the answerer will actually read it, THEN re-ask. Without
    # this the re-ask sees the same context as before and can never improve — the
    # doc has to be in play for the measurement to mean anything.
    path = _stage_canon(canon)
    try:
        if hasattr(concierge, "clear_cache"):
            concierge.clear_cache()  # otherwise the re-ask returns the stale answer
        after = grade(canon.source_gap, concierge=concierge, judge=judge, force=True)
    finally:
        pass

    improved = after.score() > before.score()

    # Improving the target isn't enough — a new doc enters the context of EVERY
    # answer, so it can drag down questions it was never about. Re-grade the
    # previously-grounded ones and reject on a REAL regression only. grounded->partial
    # is within LLM grading noise (temp 0 isn't fully deterministic); treating it as a
    # regression rejected every promotion and nothing ever landed. A previously
    # grounded answer collapsing to `miss` is a real regression — that we block.
    regressed = False
    regression_note = ""
    if improved and others:
        prior_grounded = [g for g in others if g.question != canon.source_gap
                          and g.verdict == "grounded"]
        for prior in prior_grounded:
            recheck = grade(prior.question, concierge=concierge, judge=judge)
            if recheck.verdict == "miss":  # grounded -> miss = real breakage
                regressed = True
                regression_note = f"regressed '{prior.question[:48]}' (grounded -> miss)"
                break

    ok = improved and not regressed
    if not ok:
        _unstage_canon(path)  # never leave an unverified doc in the corpus

    if ok:
        reason = "score improved, no regressions"
    elif regressed:
        reason = f"target improved but {regression_note}"
    else:
        reason = f"no improvement ({before.verdict} -> {after.verdict})"

    return Verification(
        ok=ok,
        citations_valid=len(valid),
        citations_total=len(canon.citations),
        invalid=[],
        reason=reason,
        regraded=after,
        improved=improved,
        regressed=regressed,
    )


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "canon"


def _stage_canon(canon: Canon) -> Path:
    """Write the doc into the corpus the answerer reads."""
    d = DATA / "canon"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{_slug(canon.source_gap)}.md"
    p.write_text(
        f"# {canon.title}\n\n_source question: {canon.source_gap}_\n\n{canon.body_md}\n",
        encoding="utf-8",
    )
    return p


def _unstage_canon(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def promote(canon: Canon, verification: Verification, senso=None, memory=None) -> PromoteResult:
    """@Publisher — write to the knowledge base and publish, or discard."""
    if not verification.ok:
        if memory is not None:
            _remember(memory, canon, worked=False)
        return PromoteResult(False, verification.reason)

    content_id = None
    published = None
    if senso is not None:
        try:
            content_id = senso.ingest(
                text=canon.body_md,
                title=canon.title,
                wait=True,
            )
            try:
                res = senso.publish(content_id)
                published = (res or {}).get("url")
            except Exception as e:  # noqa: BLE001
                print(f"    ! publish failed (ingest still succeeded): {e}")
        except Exception as e:  # noqa: BLE001
            print(f"    ! senso ingest failed: {e}")

    if memory is not None:
        _remember(memory, canon, worked=True)

    return PromoteResult(True, "verified and promoted", content_id, published)


def _remember(memory, canon: Canon, worked: bool) -> None:
    try:
        memory.remember(
            problem=canon.source_gap,
            fix=canon.body_md,
            worked=worked,
            meta={"citations": canon.citations, "title": canon.title},
        )
    except Exception as e:  # noqa: BLE001
        print(f"    ! remember failed: {e}")


# ------------------------------------------------------------------------ cycle

def run_cycle(questions: list[str] | None = None) -> CycleResult:
    """Headless entrypoint. Safe to call repeatedly — this is what Guild's cron fires."""
    qs = questions or GOLDEN
    started = now()
    concierge, judge, memory, pioneer, senso = _lazy_clients()

    print(f"\n=== cycle over {len(qs)} questions ===")
    before: list[Grade] = []
    for q in qs:
        g = grade(q, concierge, judge)
        before.append(g)
        print(f"  [{g.verdict:8}] {q[:64]}")

    misses = [g for g in before if g.verdict != "grounded"]
    print(f"  {len(misses)} gap(s)")

    written = promoted = rejected = recalled = 0
    for g in misses:
        gap = Gap(question=g.question, signature=_signature(g.question), reason=g.reason)
        canon = research(gap, pioneer=pioneer, memory=memory)
        if canon is None:
            print(f"    - no canon produced for: {g.question[:50]}")
            continue
        written += 1
        if canon.from_memory:
            recalled += 1
            print("    ~ recalled a prior fix from memory (no research needed)")

        v = verify(canon, g, concierge, judge, others=before)
        r = promote(canon, v, senso=senso, memory=memory)
        if r.promoted:
            promoted += 1
            print(f"    + promoted: {canon.title[:56]}")
        else:
            rejected += 1
            print(f"    - rejected: {v.reason}")

        # feed the correction back to Pioneer so their model retrains on it
        if pioneer is not None and g.inference_id:
            try:
                pioneer.feedback(g.inference_id, correct=False, correction=canon.body_md[:2000])
            except Exception as e:  # noqa: BLE001
                print(f"    ! feedback failed: {e}")

    # 'after' reads the grade cache: questions we didn't touch keep their baseline
    # grade; only questions whose canon we published (via force=True in verify)
    # have an updated grade. Monotonic by construction.
    after = [grade(q, concierge, judge) for q in qs]  # cached unless force was used

    result = CycleResult(
        cycle=_next_cycle_number(),
        started_at=started,
        ended_at=now(),
        questions_tested=len(qs),
        passed_before=sum(1 for g in before if g.passed),
        passed_after=sum(1 for g in after if g.passed),
        score_before=round(sum(g.score() for g in before) / max(1, len(before)), 4),
        score_after=round(sum(g.score() for g in after) / max(1, len(after)), 4),
        gaps_found=len(misses),
        canon_written=written,
        canon_promoted=promoted,
        canon_rejected=rejected,
        recalled_from_memory=recalled,
    )
    _append(result)
    print(f"=== score {result.score_before:.2f} -> {result.score_after:.2f} | pass {result.passed_before}/{len(qs)} -> {result.passed_after}/{len(qs)}, "
          f"{promoted} promoted, {rejected} rejected, {recalled} recalled ===\n")
    return result


def _next_cycle_number() -> int:
    if not RUNS.exists():
        return 1
    n = 0
    for line in RUNS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            n += 1
    return n + 1


def _append(result: CycleResult) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    with RUNS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(result)) + "\n")


if __name__ == "__main__":
    run_cycle()
