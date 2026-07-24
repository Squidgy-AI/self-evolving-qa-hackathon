"""
Senso ("Context OS") Python client.

Senso is a programmable, version-controlled knowledge base for AI agents:
ingest raw text/docs, it indexes them, then agents run grounded search or
generate new content against that knowledge base.

Ground truth (docs.senso.ai is mostly sign-in walled; the quickstart repo's
source code was the reliable source):
  https://github.com/AI-Template-SDK/api-quickstart
  (support-hub/cli_support_hub.py, repurpose/cli_repurpose.py)
    base URL:    https://sdk.senso.ai/api/v1
    auth header: X-API-Key: <key>
    POST /content/raw  {title, text, summary} -> {"id": ...}
    GET  /content/{id}           -> {"processing_status": completed|failed|...}
    POST /search  {query, max_results} -> {"answer", "results":[
                                            {score, title, chunk_text}, ...]}
    POST /generate  {content_type, instructions, save, max_results}
                                  -> {"content_id", "generated_text"}
  Web search over docs.senso.ai/api-reference/authentication confirms the
  X-API-Key header and SENSO_API_KEY env convention. `senso engine publish`
  confirmed as a real CLI subcommand with no discoverable REST equivalent.

Install: pip install httpx
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time

import httpx

BASE_URL = "https://sdk.senso.ai/api/v1"


class SensoError(RuntimeError):
    pass


class SensoClient:
    def __init__(self, api_key: str | None = None):
        # VERIFY: quickstart repo's README uses env var SENSO_KEY; the auth
        # docs and hackathon brief say SENSO_API_KEY. Accept either.
        self.api_key = api_key or os.environ.get("SENSO_API_KEY") or os.environ.get("SENSO_KEY")
        if not self.api_key:
            raise SensoError("Set SENSO_API_KEY (or pass api_key=) to use SensoClient.")
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            timeout=60.0,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SensoClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def ingest(self, text: str, title: str, wait: bool = True, timeout_s: int = 60) -> str:
        """POST /content/raw then poll GET /content/{id} until processed.

        Ingestion is async server-side: raw content is stored immediately,
        but chunking/embedding happens in the background, tracked via
        `processing_status`. Returns the content id.
        """
        resp = self._client.post(
            "/content/raw",
            json={"title": title, "text": text, "summary": f"Imported: {title}"},
        )
        resp.raise_for_status()
        content_id = resp.json()["id"]

        if not wait:
            return content_id

        deadline = time.monotonic() + timeout_s
        poll_interval = 3  # seconds, matches the quickstart CLI examples
        status = None
        while time.monotonic() < deadline:
            r = self._client.get(f"/content/{content_id}")
            r.raise_for_status()
            status = r.json().get("processing_status")
            if status == "completed":
                return content_id
            if status == "failed":
                raise SensoError(f"Senso ingestion failed for content_id={content_id}")
            time.sleep(poll_interval)

        raise TimeoutError(
            f"Senso ingestion for content_id={content_id} did not complete within "
            f"{timeout_s}s (last status={status!r})"
        )

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """POST /search — grounded retrieval with citations.

        Returns the result chunks (score/title/chunk_text each). The
        top-level `answer` (a synthesized, cited answer) is attached as
        `_answer` on result[0] if present; ignore it if unneeded.
        """
        resp = self._client.post("/search", json={"query": query, "max_results": limit})
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if results and "answer" in data:
            results[0] = {**results[0], "_answer": data["answer"]}
        return results

    def generate(self, prompt: str, save: bool = True) -> dict:
        """POST /generate.

        VERIFY: the quickstart repo sends "instructions" (not "prompt") plus
        a required "content_type" (it used the literal "marketing asset").
        We pass a generic content_type since this client is domain-agnostic
        — confirm whether it's validated against a fixed enum.
        """
        resp = self._client.post(
            "/generate",
            json={
                "content_type": "generated content",  # VERIFY: enum vs free text
                "instructions": prompt,
                "save": save,
                "max_results": 5,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def publish(self, content_id: str) -> dict:
        """Publish content to the web so other agents/humans can discover it.

        No REST equivalent was found in the quickstart repo or reachable
        docs — only the CLI (`senso engine publish`) advertises this, so
        this shells out to it. Requires `npm install -g @senso-ai/cli`.
        VERIFY: exact `senso engine publish` args/flags and JSON output shape
        against a live CLI (`senso engine publish --help`).
        """
        cli = shutil.which("senso")
        if not cli:
            raise SensoError(
                "publish() requires the Senso CLI (`npm install -g @senso-ai/cli`); "
                "`senso` not found on PATH."
            )
        env = {**os.environ, "SENSO_API_KEY": self.api_key}
        result = subprocess.run(
            [cli, "engine", "publish", content_id, "--json"],  # VERIFY: --json flag exists
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            raise SensoError(f"`senso engine publish {content_id}` failed: {result.stderr.strip()}")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"raw_output": result.stdout.strip()}


def smoke() -> None:
    marker = "the quokka guards the hackathon snacks"
    title = "senso_client smoke test"
    text = f"This is a smoke-test document. Important fact: {marker}."

    client = SensoClient()
    try:
        print("[1/3] ingest ...", end=" ", flush=True)
        try:
            content_id = client.ingest(text, title, wait=True, timeout_s=60)
            print(f"PASS (content_id={content_id})")
        except Exception as e:
            print(f"FAIL ({e})")
            return

        print("[2/3] search ...", end=" ", flush=True)
        try:
            results = client.search(marker, limit=5)
            found = any(marker in r.get("chunk_text", "") for r in results)
            print("PASS" if found else f"FAIL (marker not in results: {results})")
        except Exception as e:
            print(f"FAIL ({e})")
            return

        print("[3/3] generate ...", end=" ", flush=True)
        try:
            gen = client.generate(f"Summarize the fact about: {marker}", save=False)
            print("PASS" if gen.get("generated_text") else f"FAIL (empty response: {gen})")
        except Exception as e:
            print(f"FAIL ({e})")
    finally:
        client.close()


if __name__ == "__main__":
    smoke()
