"""Client for squidgy-deepwiki — Squidgy's internal "Ask the codebase" RAG service.

squidgy-deepwiki is a fork of AsyncFuncAI/deepwiki-open: point it at a GitHub
repo, it clones + embeds the code, and exposes a streaming Q&A chat over the
indexed content plus a couple of retrieval/listing endpoints.

Ground truth (read directly, do not guess): local checkout at
`squidgy-deepwiki/api/{api.py,main.py,simple_chat.py,rag.py}` (repo
Squidgy-AI/squidgy-deepwiki). Key facts pulled from that source:

  POST /chat/completions/stream   (api/simple_chat.py: ChatCompletionRequest)
    Request JSON:
      {
        "repo_url": "https://github.com/<owner>/<repo>",
        "messages": [{"role": "user", "content": "<question>"}],
        "type": "github",            # repo_type; also gitlab/bitbucket
        "provider": "openrouter",    # google|openai|openrouter|ollama|bedrock|azure|dashscope
        "model": "anthropic/claude-sonnet-4.6",  # REQUIRED for provider=openrouter —
                                                  # the server does NOT fall back to a
                                                  # default model for this provider and
                                                  # returns a 400 "No models provided"
                                                  # from OpenRouter if omitted.
        "language": "en"
      }
      No branch field exists on this endpoint — RAG.prepare_retriever resolves
      whatever index already exists for the repo_url.
      Tag a message's content with the literal substring "[DEEP RESEARCH]" to
      switch the server onto its multi-iteration deep-research prompt chain
      instead of the single-shot simple-chat prompt.
    Response: `StreamingResponse(..., media_type="text/event-stream")` — but the
    generator (`response_stream()`) just `yield`s raw text fragments (e.g.
    `chunk.text` from the underlying model client). It is NOT actually
    SSE-framed (no "data: " prefix, no "event:" lines, no terminal "[DONE]")
    on the deployment tested below — confirmed by capturing a live stream and
    seeing plain prose. This client accumulates raw chunks by default and
    additionally auto-detects true SSE framing (all non-blank lines prefixed
    "data:") in case a fronting proxy ever reframes it.
    On an internal error mid-stream, the server yields a 200 OK response body
    like "\\nError with OpenRouter API: ...\\n" instead of raising — so a
    completed .ask() with an apparently-empty/short/error-looking `.text` can
    still mean the HTTP call itself succeeded.

  GET  /api/processed_projects   -> list[{name: "owner/repo", branch, has_wiki,
                                     indexed, ...}]  no auth in the source.
  GET  /api/squidgy/repos        -> GitHub org repo picker (server's own
                                     GITHUB_TOKEN; not "indexed" repos, just
                                     everything in the org — not used here).
  GET  /auth/status              -> {"auth_required": bool}   (WIKI_AUTH_MODE,
                                     for the wiki UI's own access code, not an
                                     API bearer scheme).
  GET  /health                   -> {"status": "healthy", ...}

  POST /api/retrieve_chunks      -> the ONE endpoint in this codebase that
                                     enforces a shared-secret header:
                                     `X-Concierge-Token: $CONCIERGE_SERVICE_TOKEN`
                                     (api/api.py ~line 1108-1124, hmac constant-
                                     time compare). Not used by ask() — it is a
                                     retrieval-only sibling endpoint for the
                                     separate Codebase Concierge product.

Auth mechanism / env vars used by THIS client:
  DEEPWIKI_API_KEY  — if set, sent as BOTH `Authorization: Bearer <key>` and
                       `X-Concierge-Token: <key>` on every request. Nothing in
                       api/simple_chat.py or api/api.py actually checks an
                       Authorization header for /chat/completions/stream,
                       /api/processed_projects, or /auth/status — the only
                       header-gated route found in the source is
                       /api/retrieve_chunks (CONCIERGE_SERVICE_TOKEN via
                       X-Concierge-Token, see above). We still send both forms
                       whenever a key is configured in case a fronting
                       gateway enforces its own auth in front of the FastAPI
                       app (see the IMPORTANT note below) — harmless no-op
                       against the raw FastAPI service either way.
  DEEPWIKI_URL      — base URL, default below.
  DEEPWIKI_REPO     — default repo target (constructor arg `repo` wins).
  DEEPWIKI_PROVIDER / DEEPWIKI_MODEL — override the LLM used server-side.

IMPORTANT — live-instance discrepancy found while building/verifying this
client (2026-07-24): the URL specified as the "live instance"
(https://squidgy-deepwiki-api.onrender.com) is NOT this squidgy-deepwiki FastAPI
service. Probing it directly:
  - GET /            -> 307 redirect to /login?next=%2F
  - GET /health, /auth/status, /api/processed_projects, /api/squidgy/repos,
    /api/retrieve_chunks, /docs, /openapi.json -> 404 or 307-to-/login
  - GET /mcp/sse     -> 401 {"error":"Unauthorized"} with CSP/security headers
    that don't appear anywhere in this repo's FastAPI app.
  All served with `x-render-origin-server: uvicorn`, so it IS a real FastAPI
  app on Render — just a DIFFERENT one (almost certainly the separate
  "Squidgy Concierge" MCP gateway, not squidgy-deepwiki) that happens to share
  a similar hostname.
  The REAL squidgy-deepwiki-api backend declared in this repo's render.yaml,
  https://squidgy-deepwiki-api.onrender.com, matches every route in this
  source tree exactly and was verified live and unauthenticated:
    /health -> 200, /auth/status -> {"auth_required": false},
    /api/processed_projects -> real indexed-repo list,
    /api/squidgy/repos -> real org repo list,
    /api/retrieve_chunks (no token) -> 401 {"detail":"Invalid or missing
      service token."} (as expected from the source),
    POST /chat/completions/stream (provider=openrouter, model=
      anthropic/claude-sonnet-4.6) -> a real, correct, source-cited answer.
  DEFAULT_URL below is kept at the literally-instructed
  concierge-deepwiki.onrender.com per the brief; set DEEPWIKI_URL=
  https://squidgy-deepwiki-api.onrender.com in .env to hit the service this
  client was actually written against and verified working end-to-end.

Install: pip install httpx
"""

from __future__ import annotations

import os
import re

import httpx

from clients.concierge_client import Answer

DEFAULT_URL = "https://squidgy-deepwiki-api.onrender.com"  # see IMPORTANT note above
DEFAULT_REPO = "https://github.com/Squidgy-AI/squidgy_updated_backend"
DEFAULT_PROVIDER = "openrouter"
DEFAULT_MODEL = "anthropic/claude-sonnet-4.6"
TIMEOUT = 120.0  # Render free/standard instances can cold-start; never infinite

# Same convention as the sibling clients: pull "path:line" citations out of
# the answer's prose.
# Line number OPTIONAL — deepwiki cites bare paths ("routes/foo.py") far more often
# than "foo.py:123". Kept in sync with engine/loop.py CITATION.
SOURCE_RE = re.compile(
    r"([\w./-]+\.(?:py|ts|tsx|js|jsx|md|json|ya?ml|sh|sql))(?::(\d+))?"
)


class DeepWikiError(RuntimeError):
    pass


class DeepWikiClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        repo: str | None = None,
    ):
        self.base_url = (base_url or os.getenv("DEEPWIKI_URL") or DEFAULT_URL).rstrip("/")
        self.api_key = api_key or os.getenv("DEEPWIKI_API_KEY") or ""
        self.repo = repo or os.getenv("DEEPWIKI_REPO") or DEFAULT_REPO
        self.provider = os.getenv("DEEPWIKI_PROVIDER") or DEFAULT_PROVIDER
        self.model = os.getenv("DEEPWIKI_MODEL") or DEFAULT_MODEL
        self._cache: dict[tuple[str, str | None], Answer] = {}

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-Concierge-Token"] = self.api_key
        return headers

    def ask(self, question: str, mode: str | None = None) -> Answer:
        """Ask squidgy-deepwiki. Streams /chat/completions/stream to completion.

        `mode` has no native equivalent in this API's request schema. As a
        useful mapping: any mode containing "deep" (e.g. "deep_research")
        tags the query with the server's own "[DEEP RESEARCH]" trigger
        (api/simple_chat.py), switching it onto the multi-iteration research
        prompt chain. Any other mode value is otherwise ignored (recorded on
        the returned Answer only).
        """
        cache_key = (question, mode)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return Answer(
                question=cached.question,
                text=cached.text,
                sources=cached.sources,
                mode=cached.mode,
                cache_hit=True,
                raw=cached.raw,
            )

        # Left alone, deepwiki answers correctly but tersely and without file:line
        # references ("FastAPI." for a framework question). The whole loop is graded
        # on groundedness, so ask it to show its work. This is a request to the
        # production system, not a change to it.
        query = (
            f"{question}\n\n"
            "Answer using the indexed source. Cite every factual claim inline as "
            "`path/to/file.py:123` with real paths and line numbers from this repo. "
            "If the source does not contain the answer, say so plainly rather than "
            "guessing."
        )
        if mode and "deep" in mode.lower():
            query = f"[DEEP RESEARCH] {query}"

        payload = {
            "repo_url": self.repo,
            "messages": [{"role": "user", "content": query}],
            "type": "github",
            "provider": self.provider,
            "model": self.model,
            "language": "en",
        }

        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/chat/completions/stream",
                json=payload,
                headers=self._headers(),
                timeout=TIMEOUT,
            ) as r:
                if r.status_code == 401:
                    r.read()
                    raise DeepWikiError(
                        "401 from /chat/completions/stream — set DEEPWIKI_API_KEY "
                        "(or api_key=) in .env"
                    )
                if r.status_code >= 400:
                    r.read()
                    raise DeepWikiError(
                        f"{r.status_code} from /chat/completions/stream: {r.text[:400]}"
                    )
                raw_stream = "".join(r.iter_text())
        except httpx.HTTPError as e:
            raise DeepWikiError(f"could not reach {self.base_url}: {e}") from e

        text = _extract_stream_text(raw_stream)
        sources = _extract_sources(text)

        answer = Answer(
            question=question,
            text=text,
            sources=sources,
            mode=mode or "default",
            cache_hit=False,
            raw={
                "repo": self.repo,
                "provider": self.provider,
                "model": self.model,
                "raw_stream": raw_stream,
            },
        )
        self._cache[cache_key] = answer
        return answer

    def healthy(self) -> bool:
        try:
            r = httpx.get(f"{self.base_url}/health", timeout=15.0)
            return r.status_code < 500
        except httpx.HTTPError:
            return False

    def clear_cache(self) -> None:
        """Clear the in-process ask() memo dict so the next identical question
        is genuinely re-sent instead of served from the local cache."""
        self._cache.clear()

    def repos(self) -> list[str]:
        """Which repos are indexed, per GET /api/processed_projects."""
        try:
            r = httpx.get(
                f"{self.base_url}/api/processed_projects",
                headers=self._headers(),
                timeout=30.0,
            )
        except httpx.HTTPError as e:
            raise DeepWikiError(f"could not reach {self.base_url}: {e}") from e

        if r.status_code == 401:
            raise DeepWikiError(
                "401 from /api/processed_projects — set DEEPWIKI_API_KEY "
                "(or api_key=) in .env"
            )
        if r.status_code >= 400:
            raise DeepWikiError(
                f"{r.status_code} from /api/processed_projects: {r.text[:400]}"
            )

        entries = r.json() or []
        names = sorted({e.get("name") for e in entries if e.get("name")})
        return names


def _extract_stream_text(raw: str) -> str:
    """Accumulate a /chat/completions/stream body into plain text.

    Handles two shapes: (1) the raw-chunk passthrough actually observed live
    (return unchanged so whitespace/newlines in the answer survive), and
    (2) proper SSE framing (every non-blank line prefixed "data:"), in case a
    fronting proxy ever reframes the stream that way.
    """
    stripped = raw.strip()
    if not stripped:
        return ""

    lines = [line for line in stripped.split("\n") if line.strip()]
    if lines and all(line.startswith("data:") for line in lines):
        parts = []
        for line in lines:
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                break
            parts.append(data)
        return "".join(parts)

    return raw


def _extract_sources(text: str) -> list[str]:
    sources: list[str] = []
    for m in SOURCE_RE.finditer(text):
        s = f"{m.group(1)}:{m.group(2)}" if m.group(2) else m.group(1)
        if s not in sources:
            sources.append(s)
    return sources


def smoke() -> None:
    c = DeepWikiClient()
    print(f"[..] base_url = {c.base_url}")
    print(f"[..] repo     = {c.repo}")
    print(f"[..] provider/model = {c.provider} / {c.model}")

    print(f"[{'OK' if c.healthy() else 'FAIL'}] /health reachable")

    try:
        r = httpx.get(f"{c.base_url}/api/processed_projects", headers=c._headers(), timeout=30.0)
        if r.status_code == 200:
            print(f"[OK] /api/processed_projects -> {len(r.json())} entries")
        else:
            print(f"[{'??' if r.status_code == 401 else 'FAIL'}] /api/processed_projects -> {r.status_code}: {r.text[:200]}")
    except httpx.HTTPError as e:
        print(f"[FAIL] /api/processed_projects -> {e}")

    try:
        r = httpx.get(f"{c.base_url}/auth/status", timeout=15.0)
        print(f"[{'OK' if r.status_code == 200 else 'FAIL'}] /auth/status -> {r.status_code}: {r.text[:200]}")
    except httpx.HTTPError as e:
        print(f"[FAIL] /auth/status -> {e}")

    try:
        repos = c.repos()
        print(f"[OK] repos() -> {len(repos)} indexed repos: {repos[:5]}{'...' if len(repos) > 5 else ''}")
    except DeepWikiError as e:
        print(f"[{'??' if '401' in str(e) else 'FAIL'}] repos() -> {e}")

    print("[..] ask() ... (can take up to 120s on a cold Render instance)")
    try:
        a = c.ask("What does this repository do? Answer in one sentence and cite a file.")
        print(f"[OK] ask() -> {len(a.text)} chars, {len(a.sources)} sources, hedged={a.looks_hedged}")
        print(f"     text: {a.text[:300]!r}")
    except DeepWikiError as e:
        msg = str(e)
        level = "??" if ("401" in msg or "403" in msg) else "FAIL"
        print(f"[{level}] ask() -> {msg}")
        if level == "??":
            print("     -> a human must supply a working DEEPWIKI_API_KEY / correct DEEPWIKI_URL (see module docstring).")

    c.clear_cache()
    print("[OK] clear_cache()")


if __name__ == "__main__":
    smoke()
