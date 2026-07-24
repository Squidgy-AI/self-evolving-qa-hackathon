"""@Researcher agent — recalls fixes from memory or researches the repo."""

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

from engine.loop import research  # noqa: E402
from engine.models import Gap  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


RESEARCHER_PROMPT = """You are @Researcher, the answer finder in the Evolution Loop system.

Your role:
- When @Grader finds a miss, you find the answer
- First check Actian memory for a prior fix (free, no research needed)
- If not found, research the fastapi/fastapi repo with Pioneer routing
- Write a Canon doc with specific file:line citations
- Mention @Verifier when done

When called, you execute the research() function from engine.loop which:
1. Checks Actian vector memory for similar past fixes (similarity > 0.85)
2. If memory hit: return the recalled fix immediately
3. If miss: grep the repo for relevant files
4. Use Pioneer-routed model to write a doc with citations
5. Extract all file:line citations from the generated text

You must cite specific lines like `fastapi/routing.py:123` — never invent paths.
Only cite files shown in the context. Every claim needs a citation.

Respond with the Canon title and mention @Verifier to check the citations."""


async def main() -> None:
    """Run @Researcher agent."""
    load_dotenv()

    ws_url = os.getenv("BAND_WS_URL")
    rest_url = os.getenv("BAND_REST_URL")

    adapter = ClaudeSDKAdapter(
        custom_section=RESEARCHER_PROMPT,
        features=AdapterFeatures(emit={Emit.EXECUTION, Emit.THOUGHTS}),
    )

    config_kwargs = {"adapter": adapter}
    if ws_url:
        config_kwargs["ws_url"] = ws_url
    if rest_url:
        config_kwargs["rest_url"] = rest_url

    agent = Agent.from_config("researcher_agent", **config_kwargs)

    logger.info("@Researcher is online — finding answers via Pioneer + Actian memory...")
    logger.info("Agent ID: %s", agent.runtime.agent_id)
    logger.info("Press Ctrl+C to stop")

    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Shutting down @Researcher...")


if __name__ == "__main__":
    asyncio.run(main())
