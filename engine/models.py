"""Data model shared across the loop. All JSON-serialisable via dataclasses.asdict().

CycleResult is the exact shape written one-per-line to data/runs.jsonl and read by
the dashboard. Don't rename its fields without saying so in CONTRACT.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Literal

Verdict_t = Literal["grounded", "partial", "miss"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass
class Grade:
    question: str
    answer: str
    verdict: Verdict_t
    reason: str
    citations_valid: int = 0
    citations_total: int = 0
    inference_id: str | None = None
    graded_at: str = field(default_factory=now)

    @property
    def passed(self) -> bool:
        return self.verdict == "grounded"

    def score(self) -> float:
        return {"grounded": 1.0, "partial": 0.5, "miss": 0.0}[self.verdict]


@dataclass
class Gap:
    question: str
    signature: str
    reason: str
    ask_count: int = 1


@dataclass
class Canon:
    title: str
    body_md: str
    citations: list[str]  # "path/to/file.py:123"
    source_gap: str
    generated_at: str = field(default_factory=now)
    from_memory: bool = False  # True if recalled from Actian rather than researched


@dataclass
class Verification:
    ok: bool
    citations_valid: int
    citations_total: int
    invalid: list[str]
    reason: str
    regraded: Grade | None = None
    improved: bool = False
    regressed: bool = False


@dataclass
class PromoteResult:
    promoted: bool
    reason: str
    senso_content_id: str | None = None
    published_url: str | None = None


@dataclass
class CycleResult:
    cycle: int
    started_at: str
    ended_at: str
    questions_tested: int
    passed_before: int
    passed_after: int
    gaps_found: int
    canon_written: int
    canon_promoted: int
    canon_rejected: int
    recalled_from_memory: int
    cost_usd: float = 0.0
    tokens: int = 0

    def as_json(self) -> dict:
        return asdict(self)
