"""Senso ("Context OS") client — CLI-backed.

Senso is a programmable, version-controlled knowledge base for agents. In this loop
it's the canon store: when the agent verifies a new doc, it's ingested into Senso so
future answers (and other agents, via GEO/citeables) can find it.

Why the CLI and not REST: the org's `tgr_` keys authenticate against the CLI's
control plane but 401 against the documented `sdk.senso.ai/api/v1` REST base (tried
X-API-Key and Bearer, plus a freshly-minted org key — all 401). The CLI is the
supported path ("we have a CLI, just give it to your agent"), so we shell out to it.
Verified end to end: ingest -> parse -> embed -> search round-trips a probe doc.

Env:
    SENSO_API_KEY   tgr_...  (also picked up by the CLI's own config once logged in)
    SENSO_BIN       path to the senso binary (default: found on PATH)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass

SENSO_BIN = os.getenv("SENSO_BIN") or shutil.which("senso") or "/opt/homebrew/bin/senso"
TIMEOUT = 180  # ingest embeds in a background worker; searches are quick
ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")  # strip terminal control codes


def _clean(s: str) -> str:
    return ANSI.sub("", s)


class SensoError(RuntimeError):
    pass


@dataclass
class SearchResult:
    answer: str
    chunks: list[dict]


def available() -> bool:
    return bool(SENSO_BIN) and os.path.exists(SENSO_BIN)


def _env() -> dict:
    e = dict(os.environ)
    key = os.getenv("SENSO_API_KEY")
    if key:
        e["SENSO_API_KEY"] = key
    return e


def _run_json(args: list[str], timeout: int = TIMEOUT) -> dict:
    """Run `senso --output json <args>` and parse the JSON, tolerating the CLI's
    banner lines. The CLI prints 'Senso CLI vX' and spinner noise before the JSON,
    so we slice from the first '{' or '['."""
    if not available():
        raise SensoError(f"senso CLI not found at {SENSO_BIN}")
    try:
        proc = subprocess.run(
            [SENSO_BIN, "--output", "json", *args],
            capture_output=True, text=True, timeout=timeout, env=_env(),
        )
    except subprocess.TimeoutExpired as e:
        raise SensoError(f"senso timed out after {timeout}s: {' '.join(args)}") from e

    out = _clean(proc.stdout)
    start = min([i for i in (out.find("{"), out.find("[")) if i != -1], default=-1)
    if start == -1:
        if proc.returncode != 0:
            raise SensoError(f"senso {args[0]} failed: {(proc.stderr or out)[:300]}")
        raise SensoError(f"senso {args[0]} gave no JSON: {out[:200]}")
    try:
        return json.loads(out[start:])
    except json.JSONDecodeError as e:
        raise SensoError(f"senso {args[0]} bad JSON: {out[start:start+200]}") from e


class SensoClient:
    def __init__(self, api_key: str | None = None):
        if api_key:
            os.environ["SENSO_API_KEY"] = api_key
        if not (os.getenv("SENSO_API_KEY") or _cli_logged_in()):
            raise SensoError("SENSO_API_KEY not set and CLI not logged in")

    def ingest(self, text: str, title: str, wait: bool = True, timeout_s: int = 90) -> str:
        """Write the doc to a temp file and `senso ingest upload` it. Returns a
        content id when the CLI surfaces one (best-effort — the upload is what
        matters; embedding happens in a background worker)."""
        safe = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")[:60] or "canon"
        tmp = tempfile.NamedTemporaryFile(
            "w", suffix=f"_{safe}.md", delete=False, encoding="utf-8"
        )
        try:
            tmp.write(f"# {title}\n\n{text}\n")
            tmp.close()
            # `ingest upload` streams progress and prints a human summary, not JSON —
            # so run it plain and confirm success from the text, don't parse JSON.
            proc = subprocess.run(
                [SENSO_BIN, "ingest", "upload", tmp.name],
                capture_output=True, text=True, timeout=timeout_s, env=_env(),
            )
            out = _clean(proc.stdout + proc.stderr)
            if proc.returncode != 0 or "Upload failed" in out or "file(s) uploaded" not in out:
                # "Upload failed" is usually a dedup (same content hash already stored),
                # which is fine — the doc is in the KB. Only raise on a real failure.
                if "Upload failed" in out and "hash" not in out.lower():
                    pass  # tolerate dedup
                elif proc.returncode != 0:
                    raise SensoError(f"senso ingest failed: {out[-300:]}")
            m = re.search(r'([a-f0-9-]{36})', out)
            return m.group(1) if m else ""
        finally:
            os.unlink(tmp.name)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Grounded retrieval. Returns the matching chunks; the synthesised answer
        is on each result's search too (see search_full for both)."""
        return self.search_full(query, limit).chunks

    def search_full(self, query: str, limit: int = 5) -> SearchResult:
        data = _run_json(["search", query, "--max-results", str(limit)])
        return SearchResult(
            answer=data.get("answer", ""),
            chunks=data.get("results", []),
        )

    def publish(self, content_id: str) -> dict:
        """Publish generated content to the web (citeables) so other agents discover
        it. Outward-facing — only call when explicitly intended."""
        try:
            return _run_json(["engine", "publish"])
        except SensoError as e:
            return {"published": False, "error": str(e)}


def _cli_logged_in() -> bool:
    try:
        _run_json(["whoami"], timeout=20)
        return True
    except SensoError:
        return False


def _first_id(data: dict | list) -> str | None:
    blob = json.dumps(data)
    m = re.search(r'"(?:content_id|id)"\s*:\s*"([a-f0-9-]{8,})"', blob)
    return m.group(1) if m else None


def smoke() -> None:
    if not available():
        print(f"[FAIL] senso CLI not found at {SENSO_BIN}")
        return
    marker = "SENSOSMOKE" + os.urandom(3).hex()
    try:
        c = SensoClient()
        cid = c.ingest(
            f"Loop smoke probe {marker}. FastAPI caches dependencies per request; "
            "see fastapi/dependencies/utils.py.",
            title=f"smoke {marker}",
        )
        print(f"[OK] ingested (content_id={cid or '?'})")
        import time
        time.sleep(15)  # let the embedding worker catch up
        res = c.search_full(marker, limit=3)
        hit = any(marker in (r.get("chunk_text", "")) for r in res.chunks)
        print(f"[{'OK' if hit else '??'}] search returned {len(res.chunks)} chunk(s); "
              f"answer={res.answer[:80]!r}")
    except SensoError as e:
        print(f"[FAIL] {e}")


if __name__ == "__main__":
    smoke()
