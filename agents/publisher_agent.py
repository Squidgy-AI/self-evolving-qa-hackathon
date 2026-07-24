"""@Publisher agent — publishes verified docs to Senso and remembers outcomes."""

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

from engine.loop import promote  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


PUBLISHER_PROMPT = """You are @Publisher, the knowledge publisher in the Evolution Loop system.

Your role:
- If @Verifier confirms the Canon is valid, publish it to Senso
- Store the outcome in Actian memory (worked=True or worked=False)
- Only publish if verification passed — never promote unverified docs
- Report the Senso URL or rejection reason

When called, you execute the promote() function from engine.loop which:
1. Checks verification.ok — if False, reject immediately
2. If verified: ingest the Canon into Senso via /ingest endpoint
3. Publish to the web via /publish so it's discoverable by ChatGPT/Perplexity
4. Remember in Actian memory with worked=True
5. If rejected: remember with worked=False (so we don't retry the same fix)

The memory prevents wasted research:
- Next time we see this gap, we recall the fix if it worked
- Or skip it immediately if we already tried and it failed

Respond with the Senso URL if published, or the rejection reason."""


async def main() -> None:
    """Run @Publisher agent."""
    load_dotenv()

    ws_url = os.getenv("BAND_WS_URL")
    rest_url = os.getenv("BAND_REST_URL")

    adapter = ClaudeSDKAdapter(
        custom_section=PUBLISHER_PROMPT,
        features=AdapterFeatures(emit={Emit.EXECUTION, Emit.THOUGHTS}),
    )

    config_kwargs = {"adapter": adapter}
    if ws_url:
        config_kwargs["ws_url"] = ws_url
    if rest_url:
        config_kwargs["rest_url"] = rest_url

    agent = Agent.from_config("publisher_agent", **config_kwargs)

    logger.info("@Publisher is online — publishing verified docs to Senso + Actian memory...")
    logger.info("Agent ID: %s", agent.runtime.agent_id)
    logger.info("Press Ctrl+C to stop")

    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Shutting down @Publisher...")


if __name__ == "__main__":
    asyncio.run(main())
