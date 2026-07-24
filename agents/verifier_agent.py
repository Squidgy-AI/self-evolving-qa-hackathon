"""@Verifier agent — validates citations and measures improvement."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from band import Agent
from band.adapters import ClaudeSDKAdapter
from band.core.types import AdapterFeatures, Emit

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.loop import verify  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


VERIFIER_PROMPT = """You are @Verifier, the citation validator in the Evolution Loop system.

Your role:
- Check that every citation resolves to a real file and line
- Stage the Canon doc and re-ask the question
- Measure: did the score actually improve?
- Check for regressions: did other questions get worse?
- Mention @Publisher if valid, or @Researcher if rejected

When called, you execute the verify() function from engine.loop which:
1. Validates all citations against the local fastapi/fastapi clone
2. A citation like `routing.py:123` must exist and have at least 123 lines
3. Basename matching: `routing.py` finds `fastapi/routing.py` anywhere in tree
4. Stages the Canon doc where deepwiki will read it
5. Re-asks the original question
6. Compares before/after scores (miss=0, partial=0.5, grounded=1.0)
7. Checks that other grounded answers didn't regress

The two safety rules:
1. A citation that doesn't resolve => automatic rejection
2. No measured improvement => no promotion. Ever.

Respond with valid/invalid counts and mention @Publisher if verified, else @Researcher."""


async def main() -> None:
    """Run @Verifier agent."""
    load_dotenv()

    ws_url = os.getenv("BAND_WS_URL")
    rest_url = os.getenv("BAND_REST_URL")

    adapter = ClaudeSDKAdapter(
        custom_section=VERIFIER_PROMPT,
        features=AdapterFeatures(emit={Emit.EXECUTION, Emit.THOUGHTS}),
    )

    config_kwargs = {"adapter": adapter}
    if ws_url:
        config_kwargs["ws_url"] = ws_url
    if rest_url:
        config_kwargs["rest_url"] = rest_url

    agent = Agent.from_config("verifier_agent", **config_kwargs)

    logger.info("@Verifier is online — checking citations against fastapi/fastapi clone...")
    logger.info("Agent ID: %s", agent.runtime.agent_id)
    logger.info("Press Ctrl+C to stop")

    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Shutting down @Verifier...")


if __name__ == "__main__":
    asyncio.run(main())
