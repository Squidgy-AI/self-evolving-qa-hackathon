"""Client for Concierge — the live production codebase-Q&A service we evolve.

Concierge exposes a channel-agnostic reasoning core at POST /skill/ask which returns
a cited answer. We drive it from outside: ask -> grade -> improve its knowledge base
-> ask again. We never need database access, only this endpoint.

Env:
    CONCIERGE_URL   default https://<your-qa-service-host>
    SKILL_API_KEY   bearer token for /skill/ask
    ADMIN_PASSWORD  optional fallback (endpoint also accepts HTTP Basic)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import httpx

DEFAULT_URL = "https://<your-qa-service-host>"
TIMEOUT = 90.0

# Concierge hedges in recognisable ways when it doesn't know. Cheap pre-filter so we
# don't spend a judge call on an obvious miss.
HEDGE = re.compile(
    r"(i (?:don't|do not|couldn't|could not) (?:have|find|see|know)"
    r"|not (?:in the )?indexed"
    r"|no (?:relevant )?(?:results|information|documentation) (?:found|available)"
    r"|unable to (?:find|locate|determine)"
    r"|insufficient (?:context|information))",
    re.IGNORECASE,
)


class ConciergeError(RuntimeError):
    pass


@dataclass
class Answer:
    question: str
    text: str
    sources: list[str]
    mode: str
    cache_hit: bool
    raw: dict

    @property
    def looks_hedged(self) -> bool:
        return bool(HEDGE.search(self.text)) or not self.sources


class ConciergeClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.getenv("CONCIERGE_URL") or DEFAULT_URL).rstrip("/")
        self.api_key = api_key or os.getenv("SKILL_API_KEY") or ""
        self.admin_password = os.getenv("ADMIN_PASSWORD") or ""

    def _auth(self) -> tuple[dict, tuple[str, str] | None]:
        headers = {"Content-Type": "application/json"}
        basic = None
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.admin_password:
            basic = ("admin", self.admin_password)
        return headers, basic

    def ask(self, question: str, mode: str | None = None) -> Answer:
        """Ask Concierge. Returns the answer plus whatever sources it cited."""
        headers, basic = self._auth()
        payload: dict = {"question": question}
        if mode:
            payload["mode"] = mode

        try:
            r = httpx.post(
                f"{self.base_url}/skill/ask",
                json=payload,
                headers=headers,
                auth=basic,
                timeout=TIMEOUT,
            )
        except httpx.HTTPError as e:
            raise ConciergeError(f"could not reach {self.base_url}: {e}") from e

        if r.status_code == 401:
            raise ConciergeError(
                "401 from /skill/ask — set SKILL_API_KEY (or ADMIN_PASSWORD) in .env"
            )
        if r.status_code >= 400:
            raise ConciergeError(f"{r.status_code} from /skill/ask: {r.text[:400]}")

        d = r.json()
        text = d.get("answer_md") or _strip_html(d.get("answer_html", "")) or ""
        sources = d.get("sources") or []
        if sources and isinstance(sources[0], dict):
            sources = [s.get("path") or s.get("file") or str(s) for s in sources]

        return Answer(
            question=question,
            text=text,
            sources=[str(s) for s in sources],
            mode=d.get("mode", "eng"),
            cache_hit=bool(d.get("cache_hit")),
            raw=d,
        )

    def healthy(self) -> bool:
        try:
            r = httpx.get(f"{self.base_url}/healthz", timeout=15.0)
            return r.status_code < 500
        except httpx.HTTPError:
            return False


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", " ", s or "").strip()


def smoke() -> None:
    c = ConciergeClient()
    print(f"[..] base_url = {c.base_url}")
    print(f"[{'OK' if c.healthy() else '??'}] reachable")
    try:
        a = c.ask("How does the Q&A cache decide a cache hit?")
        print(f"[OK] answered in {len(a.text)} chars, {len(a.sources)} sources, hedged={a.looks_hedged}")
    except ConciergeError as e:
        print(f"[FAIL] {e}")


if __name__ == "__main__":
    smoke()
