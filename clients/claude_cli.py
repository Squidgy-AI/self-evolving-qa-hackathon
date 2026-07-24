"""Last-resort model backend: the local Claude CLI.

Purpose is development velocity, not the submission. It lets the loop run end-to-end
before sponsor keys are in hand, so the logic can be validated early instead of at
16:00. Once PIONEER_API_KEY / GEMINI_API_KEY exist, those take priority automatically
and this is never reached — the sponsor models are what earn tool-use credit.

Matches PioneerClient.chat()'s signature so it's a drop-in.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess

CLAUDE_BIN = os.getenv("CLAUDE_BIN") or shutil.which("claude") or "/opt/homebrew/bin/claude"
TIMEOUT = int(os.getenv("CLAUDE_CLI_TIMEOUT", "180"))


class ClaudeCLIError(RuntimeError):
    pass


def available() -> bool:
    return bool(CLAUDE_BIN) and os.path.exists(CLAUDE_BIN)


def _run(prompt: str, timeout: int = TIMEOUT) -> str:
    if not available():
        raise ClaudeCLIError(f"claude CLI not found at {CLAUDE_BIN}")
    try:
        # stdin MUST be closed — `claude -p` hangs forever on an open stdin that
        # never reaches EOF (this bit us in production scheduled jobs before).
        proc = subprocess.run(
            [CLAUDE_BIN, "-p", prompt],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise ClaudeCLIError(f"claude CLI timed out after {timeout}s") from e
    if proc.returncode != 0:
        raise ClaudeCLIError(f"claude CLI exit {proc.returncode}: {proc.stderr[:400]}")
    return proc.stdout.strip()


def chat(messages: list[dict], **_kw) -> tuple[str, None]:
    """Mirrors PioneerClient.chat(). Returns (text, inference_id=None).

    No inference id, so nothing is posted to Pioneer's feedback endpoint on this
    path — another reason it's a stopgap rather than the real backend.
    """
    prompt = "\n\n".join(m.get("content", "") for m in messages if m.get("content"))
    return _run(prompt), None


def judge(question: str, answer: str, sources: list[str], rubric: str) -> tuple[str, str]:
    """Structured grading fallback. Returns (verdict, reason)."""
    prompt = (
        f"{rubric}\n\n"
        f"QUESTION:\n{question}\n\n"
        f"ANSWER:\n{answer[:6000]}\n\n"
        f"CITED SOURCES ({len(sources)}):\n" + ("\n".join(sources[:40]) or "(none)") + "\n\n"
        'Reply with ONLY a JSON object, no prose, no code fence: '
        '{"verdict": "grounded|partial|miss", "reason": "one sentence"}'
    )
    raw = _run(prompt)
    text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        d = json.loads(text)
        v = d["verdict"]
        if v not in {"grounded", "partial", "miss"}:
            raise ValueError(f"bad verdict {v!r}")
        return v, d.get("reason", "")
    except Exception as e:  # noqa: BLE001
        return "partial", f"unparseable judge output ({e}): {text[:160]}"


def smoke() -> None:
    print(f"[..] binary: {CLAUDE_BIN} (exists={available()})")
    try:
        txt, _ = chat([{"role": "user", "content": "Reply with exactly: LOOP_OK"}])
        print(f"[{'OK' if 'LOOP_OK' in txt else 'FAIL'}] chat -> {txt[:60]!r}")
    except ClaudeCLIError as e:
        print(f"[FAIL] chat: {e}")
        return
    v, r = judge(
        "How does auth work?",
        "I couldn't find that in the indexed codebase.",
        [],
        "grounded=answers with citations; partial=weak; miss=cannot answer.",
    )
    print(f"[{'OK' if v == 'miss' else 'FAIL'}] judge miss-case -> {v}: {r[:80]}")


if __name__ == "__main__":
    smoke()
