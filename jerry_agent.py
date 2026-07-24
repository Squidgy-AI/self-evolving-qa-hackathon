"""Jerry agent (claude_sdk)."""

from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv

from characters import generate_jerry_prompt
from band import Agent
from band.adapters import ClaudeSDKAdapter
from band.core.types import AdapterFeatures, Emit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Run Jerry the mouse agent."""
    load_dotenv()

    ws_url = os.getenv("BAND_WS_URL")
    rest_url = os.getenv("BAND_REST_URL")

    adapter = ClaudeSDKAdapter(
        custom_section=generate_jerry_prompt("Jerry"),
        features=AdapterFeatures(emit={Emit.EXECUTION, Emit.THOUGHTS}),
    )

    config_kwargs = {"adapter": adapter}
    if ws_url:
        config_kwargs["ws_url"] = ws_url
    if rest_url:
        config_kwargs["rest_url"] = rest_url

    agent = Agent.from_config("jerry_agent", **config_kwargs)

    logger.info("Jerry is cozy in his hole, watching for Tom...")
    logger.info("Agent ID: %s", agent.runtime.agent_id)
    logger.info("Press Ctrl+C to stop")

    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
