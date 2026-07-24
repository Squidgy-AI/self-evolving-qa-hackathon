"""Independent judge — Gemini.

Deliberately a different model family from the one that produced the answer, so the
student isn't marking its own homework. Free tier, no card. Env: GEMINI_API_KEY.

Grades an answer as grounded / partial / miss with a one-line reason, using
structured output so the verdict is always parseable.
"""

from __future__ import annotations

import json
import os

MODEL = os.getenv("JUDGE_MODEL", "gemini-2.5-flash")

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["grounded", "partial", "miss"]},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
}

RUBRIC = """You are grading an answer produced by a codebase question-answering system.

grounded — answers the question AND cites specific code that supports it.
partial  — partially answers, or answers without adequate citation, or hedges.
miss     — fails to answer, says it cannot find the information, or is off-topic.

Be strict. An confident-sounding answer with no citations is 'partial' at best.
An answer that says it couldn't find anything is 'miss'.
Give a one-sentence reason naming the specific deficiency."""


class JudgeError(RuntimeError):
    pass


class Judge:
    def __init__(self, api_key: str | None = None, model: str = MODEL):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        self._client = None
        if not self.api_key:
            raise JudgeError("GEMINI_API_KEY not set — get one free at aistudio.google.com")

    def _lazy(self):
        if self._client is None:
            try:
                from google import genai  # type: ignore
            except ImportError as e:
                raise JudgeError("pip install google-genai") from e
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def grade(self, question: str, answer: str, sources: list[str]) -> tuple[str, str]:
        """Returns (verdict, reason)."""
        client = self._lazy()
        prompt = (
            f"{RUBRIC}\n\n"
            f"QUESTION:\n{question}\n\n"
            f"ANSWER:\n{answer[:6000]}\n\n"
            f"CITED SOURCES ({len(sources)}):\n" + ("\n".join(sources[:40]) or "(none)")
        )
        try:
            resp = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": SCHEMA,
                },
            )
            data = json.loads(resp.text)
            return data["verdict"], data["reason"]
        except Exception as e:  # noqa: BLE001 - judge must never break the loop
            # Fail soft: an unavailable judge shouldn't halt a cycle, but it must not
            # silently pass either. Treat as 'partial' and say why.
            return "partial", f"judge unavailable ({type(e).__name__}: {e})"


def smoke() -> None:
    try:
        j = Judge()
    except JudgeError as e:
        print(f"[FAIL] {e}")
        return
    v, r = j.grade(
        "How does middleware chain in this framework?",
        "It uses onion-style composition, see src/compose.ts:41 where dispatch recurses.",
        ["src/compose.ts:41"],
    )
    print(f"[OK] grounded-case -> {v}: {r}")
    v2, r2 = j.grade("How does auth work?", "I couldn't find any information about that.", [])
    print(f"[{'OK' if v2 == 'miss' else 'FAIL'}] miss-case -> {v2}: {r2}")


if __name__ == "__main__":
    smoke()
