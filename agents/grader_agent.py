"""@Grader agent — asks deepwiki and scores the answer."""

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

from engine.loop import grade  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


GRADER_PROMPT = """You are @Grader, the quality evaluator in the Evolution Loop system.

Your role:
- Ask deepwiki a question
- Score the answer using Gemini as an independent judge
- Return a Grade with verdict: grounded/partial/miss
- Mention @Researcher if you find a miss

When called, you execute the grade() function from engine.loop which:
1. Asks the Concierge (deepwiki) the question
2. Validates citations (file:line format)
3. Uses Gemini judge to score: grounded/partial/miss
4. Detects hedging ("I'm not sure", "it might be")

A "miss" means the answer is wrong, hedged, or lacks valid citations.
A "grounded" answer has specific file:line citations that resolve to real code.
A "partial" answer has truth but is incomplete or vague.

Respond concisely with the verdict and reason, then @-mention @Researcher for any miss."""


async def main() -> None:
    """Run @Grader agent."""
    load_dotenv()

    ws_url = os.getenv("BAND_WS_URL")
    rest_url = os.getenv("BAND_REST_URL")

    adapter = ClaudeSDKAdapter(
        custom_section=GRADER_PROMPT,
        features=AdapterFeatures(emit={Emit.EXECUTION, Emit.THOUGHTS}),
    )

    config_kwargs = {"adapter": adapter}
    if ws_url:
        config_kwargs["ws_url"] = ws_url
    if rest_url:
        config_kwargs["rest_url"] = rest_url

    agent = Agent.from_config("grader_agent", **config_kwargs)

    logger.info("@Grader is online — evaluating answers with Gemini judge...")
    logger.info("Agent ID: %s", agent.runtime.agent_id)
    logger.info("Press Ctrl+C to stop")

    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Shutting down @Grader...")


if __name__ == "__main__":
    asyncio.run(main())
