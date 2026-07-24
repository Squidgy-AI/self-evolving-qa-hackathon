"""
Replay QA (loop-qa.replay.io) client — hackathon glue for autonomous QA.
Explores a running app, writes its own Playwright tests, and files
root-caused bug reports w/ suggested fixes. Wraps the REST API per the live
OpenAPI spec fetched directly from loop-qa.replay.io/api/v1/openapi.json
(2026-07-24) — authoritative for every endpoint/body below.
# VERIFY: spec's `servers` block says "https://qa.replay.io", conflicting with
# the fact the spec itself loads fine from loop-qa.replay.io. Defaulting to the
# host proven reachable; override via REPLAY_API_BASE_URL if that's wrong.
CREDITS: free tier = 25/month. `budget` (POST /projects) is the real cost
control — spec says "~10 = smoke test, 20-50 = thorough, 50+ = broad", defaults
to 20 when omitted (~80% of a month's quota in one scan). create_project()
refuses to spend anything unless dry_run=False is passed explicitly.
Auth: `Authorization: Bearer lqa_...` (dashboard -> Settings -> API Keys).
"""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any

import httpx

logger = logging.getLogger("replay_qa")
logging.basicConfig(level=logging.INFO, format="%(levelname)s replay_qa: %(message)s")

DEFAULT_BASE_URL = "https://loop-qa.replay.io/api/v1"
DEFAULT_SCAN_BUDGET = 20  # API default when `budget` is omitted, per the OpenAPI spec

class ReplayQAError(RuntimeError):
    pass

class ReplayQA:
    """Thin sync client over the Replay QA REST API."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or os.environ.get("REPLAY_API_KEY")
        if not self.api_key:
            raise ReplayQAError(
                "No API key. Pass api_key=... or set REPLAY_API_KEY "
                "(dashboard -> Settings -> API Keys; starts with 'lqa_')."
            )
        self.base_url = (base_url or os.environ.get("REPLAY_API_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=30.0,
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        resp = self._client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            raise ReplayQAError(f"{method} {path} -> {resp.status_code}: {resp.text[:500]}")
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    # ---------------------------------------------------------------- projects

    def list_projects(self, status: str = "all", page: int = 1, page_size: int = 20) -> list[dict]:
        """GET /projects. Read-only — never spends credits."""
        data = self._request("GET", "/projects", params={"status": status, "page": page, "page_size": page_size})
        if isinstance(data, list):
            return data
        return data.get("projects") or data.get("data") or []

    def create_project(
        self,
        target_url: str,
        description: str | None = None,
        dry_run: bool = True,
        budget: float | None = None,
        name: str | None = None,
    ) -> str:
        """POST /projects — starts an autonomous exploration of target_url.
        CREDIT GUARD (hard requirement): dry_run defaults True; then NO request
        is sent, only the payload is logged, and a "dryrun-..." id is returned.
        Pass dry_run=False explicitly to spend credits (see module docstring)."""
        payload: dict[str, Any] = {"name": name or f"hackathon-scan-{int(time.time())}", "target_url": target_url}
        if description:
            payload["instructions"] = description
        if budget is not None:
            payload["budget"] = budget
        est_cost = payload.get("budget", DEFAULT_SCAN_BUDGET)

        if dry_run:
            logger.warning(
                "[DRY RUN] would spend ~%s credits scanning %s. NO request sent. "
                "Call with dry_run=False to run it. Payload: %s", est_cost, target_url, payload,
            )
            return f"dryrun-{int(time.time())}"

        logger.warning(
            "SPENDING CREDITS: creating a REAL scan of %s (~%s credits, free tier = "
            "25/month total, non-refundable). Pass budget= to cap lower.", target_url, est_cost,
        )
        data = self._request("POST", "/projects", json=payload)
        project_id = data.get("id") or data.get("project_id") or data.get("exploration_id")
        if not project_id:
            raise ReplayQAError(f"create_project: no id in response: {data}")
        logger.info("Created project %s (dashboard: %s)", project_id, data.get("url"))
        return project_id

    def status(self, project_id: str) -> dict:
        """GET /projects/{id}/status — counts of explorations, journeys, test runs, bugs."""
        if project_id.startswith("dryrun-"):
            return {"project_id": project_id, "status": "dry_run", "note": "no project was actually created"}
        return self._request("GET", f"/projects/{project_id}/status")

    def wait_for_results(self, project_id: str, timeout_s: int = 900, poll_s: int = 15) -> dict:
        # VERIFY: /status has no formal response schema (prose only), so there's no
        # guaranteed "finished" boolean; we treat `finished_at` or a status/state of
        # finished/completed/done/idle as done. Spec DOES document a
        # `finished_webhook_url` (event: "qa.finished") — prefer that over polling.
        if project_id.startswith("dryrun-"):
            return self.status(project_id)
        deadline = time.monotonic() + timeout_s
        last: dict = {}
        while time.monotonic() < deadline:
            last = self.status(project_id)
            state = str(last.get("status") or last.get("state") or "").lower()
            if last.get("finished_at") or state in ("finished", "completed", "done", "idle"):
                return last
            logger.info("project %s status: %s (next poll in %ss)", project_id, last, poll_s)
            time.sleep(poll_s)
        logger.warning("wait_for_results: timed out after %ss on project %s", timeout_s, project_id)
        return last

    # ------------------------------------------------------------------- bugs

    def bugs(self, project_id: str, status: str | None = None) -> list[dict]:
        # Normalised to: [{id, title, root_cause, suggested_fix, confidence, url}]
        # VERIFY: spec has no response schema for bug objects (prose only). Field
        # names ARE documented on the webhook_url payload (POST /projects): body,
        # referrer, callback_url, bug_id, title, severity, description,
        # reproduction_steps, expected_behavior, actual_behavior,
        # replay_recording_id, analysis, polish_category. No documented
        # confidence/suggested_fix field anywhere — we probe likely aliases and
        # fall back to None; confirm against a live response before relying on them.
        if project_id.startswith("dryrun-"):
            return []
        params: dict[str, Any] = {"page_size": 100}
        if status:
            params["status"] = status
        data = self._request("GET", f"/projects/{project_id}/bugs", params=params)
        raw_bugs = data if isinstance(data, list) else (data.get("bugs") or data.get("data") or [])
        out = []
        for b in raw_bugs:
            rec_id = b.get("replay_recording_id")
            out.append({
                "id": b.get("id") or b.get("bug_id"),
                "title": b.get("title"),
                "root_cause": b.get("root_cause") or b.get("analysis") or b.get("root_cause_analysis"),
                "suggested_fix": b.get("suggested_fix") or b.get("fix") or b.get("recommended_fix"),
                "confidence": b.get("confidence", b.get("confidence_score")),
                "url": b.get("url") or (f"https://app.replay.io/recording/{rec_id}" if rec_id else None),
                "_raw": b,  # severity/description/repro steps, used by to_agent_prompt
            })
        return out

    def mark_fixed(self, bug_id: str) -> dict:
        """PATCH /bugs/{bug_id} status=fixed. Per the spec this auto-retries the
        affected journey to confirm the fix — cheap re-verification, not a rescan."""
        return self._request("PATCH", f"/bugs/{bug_id}", json={"status": "fixed"})

    # ---------------------------------------------------------------- reporting

    def to_agent_prompt(self, bugs: list[dict]) -> str:
        """Render normalised bug reports as one markdown prompt for a coding agent."""
        if not bugs:
            return "# Replay QA report\n\nNo open bugs found. Nothing to fix.\n"

        lines = [
            f"# Replay QA report — {len(bugs)} bug(s) to fix", "",
            "Replay QA autonomously explored this app, reproduced each bug below against "
            "a real Playwright run, and traced it to its root cause via time-travel "
            "debugging. Apply the fix each analysis points to, then call "
            "`ReplayQA().mark_fixed(bug_id)` so Replay re-verifies it.", "",
        ]
        for i, b in enumerate(bugs, 1):
            raw = b.get("_raw", {})
            lines.append(f"## {i}. {b.get('title') or '(untitled bug)'}  `id={b.get('id')}`")
            meta = [f"severity: {raw['severity']}"] if raw.get("severity") else []
            if b.get("confidence") is not None:
                meta.append(f"confidence: {b['confidence']}")
            if meta:
                lines.append("**" + " | ".join(meta) + "**")
            if b.get("url"):
                lines.append(f"Recording: {b['url']}")
            for label, key in (
                ("Description", "description"), ("Expected", "expected_behavior"), ("Actual", "actual_behavior"),
            ):
                if raw.get(key):
                    lines.append(f"**{label}:** {raw[key]}")
            steps = raw.get("reproduction_steps")
            if steps:
                steps = steps if isinstance(steps, list) else [steps]
                lines.append("**Reproduction steps:** " + "; ".join(f"{j}. {s}" for j, s in enumerate(steps, 1)))
            if b.get("root_cause"):
                lines.append(f"**Root cause (Replay's analysis):** {b['root_cause']}")
            if b.get("suggested_fix"):
                lines.append(f"**Suggested fix:** {b['suggested_fix']}")
            lines.append("\n---\n")

        lines.append(
            "When done, call `ReplayQA().mark_fixed(bug_id)` for each fixed bug id "
            "above so Replay QA re-verifies it against the app."
        )
        return "\n".join(lines)

def smoke() -> bool:
    """Verify auth and list existing projects WITHOUT creating a scan. Never burns credits."""
    try:
        client = ReplayQA()
        projects = client.list_projects()
        print(f"PASS: authenticated against {client.base_url}, {len(projects)} existing project(s) visible.")
        for p in projects[:5]:
            print(f"  - {p.get('id') or p.get('project_id')}: {p.get('name')} ({p.get('target_url')})")
        return True
    except Exception as exc:  # noqa: BLE001 - smoke test just needs PASS/FAIL
        print(f"FAIL: {exc}")
        return False

if __name__ == "__main__":
    sys.exit(0 if smoke() else 1)

# Claude Code MCP setup for Replay's time-travel MCP server ("universal mode" —
# every tool takes a recordingId). Add to .claude/mcp_config.json (or pass via
# `claude --mcp-config`). Source: replay.io blog "How to set up Replay MCP with
# Claude Code in under 10 minutes":
#
# {"mcpServers": {"replay": {"type": "http", "url": "https://dispatch.replay.io/nut/mcp",
#   "headers": {"Authorization": "YOUR_API_KEY"}}}}
