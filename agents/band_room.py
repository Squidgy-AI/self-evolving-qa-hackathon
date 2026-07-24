"""Narrate a REAL evolution-loop cycle into a BAND room as four agent handoffs.

Each of the four registered BAND agents (grader/researcher/verifier/publisher) posts
its own stage — with its own agent key, so they appear as distinct participants —
@-mentioning the next. The messages are driven by the genuine grade/research/verify/
promote functions, not a script: what the room shows is what actually happened.

Room creation and human posting need a BAND Enterprise plan, but *agents* can post on
the free plan with their own keys. So: make a room in the app.band.ai UI, put its id
in BAND_ROOM_ID, and run this.

    BAND_ROOM_ID=989029da-... python agents/band_room.py \
        "How are WebSocket dependencies resolved differently from HTTP ones?"
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from band.client.rest import RestClient  # noqa: E402
from band_rest.types.chat_message_request import ChatMessageRequest  # noqa: E402
from band_rest.types.chat_message_request_mentions_item import (  # noqa: E402
    ChatMessageRequestMentionsItem as Mention,
)

from clients.judge import Judge  # noqa: E402
from clients.local_answerer import LocalAnswerer  # noqa: E402
from engine import loop as L  # noqa: E402
from engine.models import Gap  # noqa: E402

EMOJI = {"grader": "🔎", "researcher": "📚", "verifier": "✓", "publisher": "📤"}


def load_agents() -> dict:
    cfg = yaml.safe_load(open(Path(__file__).resolve().parents[1] / "agent_config.yaml"))
    return {name.replace("_agent", ""): {
        "id": d["agent_id"], "key": d["api_key"],
        "handle": d.get("handle", f"@everyone/{name.replace('_', '-')}"),
        "client": RestClient(api_key=d["api_key"]),
    } for name, d in cfg.items()}


def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else \
        "How are WebSocket dependencies resolved differently from HTTP ones?"
    repo = os.getenv("DEMO_REPO", "fastapi/fastapi")
    rid = os.environ["BAND_ROOM_ID"]
    A = load_agents()
    pace = float(os.getenv("BAND_PACE", "2.0"))

    def post(who: str, mention: str, text: str) -> None:
        """Post as `who`, @-mentioning `mention` (must differ — BAND forbids self-mention)."""
        a, tgt = A[who], A[mention]
        mentions = [Mention(id=tgt["id"], handle=tgt["handle"], name=f"{mention}_agent")]
        a["client"].agent_api_messages.create_agent_chat_message(
            rid, message=ChatMessageRequest(content=f"{EMOJI[who]} {text}", mentions=mentions),
        )
        print(f"{EMOJI[who]} @{who} → @{mention}: {text}")
        time.sleep(pace)

    answerer = LocalAnswerer()
    judge = Judge()

    # ---- the real loop, narrated as handoffs ----
    answerer.clear_cache()
    before = L.grade(question, answerer, judge)
    if before.verdict == "grounded":
        post("grader", "publisher", f'`{repo}`: "{question}" — already **grounded**. Nothing to fix.')
        return
    post("grader", "researcher",
         f'New question on `{repo}`:\n> "{question}"\nGraded the current answer: '
         f"**{before.verdict}** — it can't answer this. @researcher, over to you.")

    gap = Gap(question=question, signature=L._signature(question), reason=before.reason)
    canon = L.research(gap, pioneer=None, memory=None)
    if canon is None:
        post("researcher", "grader", "Searched the code — no supporting source found. "
             "Better to stay silent than guess. Aborting this one.")
        return
    cites = ", ".join(f"`{x}`" for x in canon.citations[:4]) or "(none)"
    post("researcher", "verifier",
         f"Found it. Drafted a doc citing {len(canon.citations)} line(s): {cites}.\n"
         f"@verifier — don't take my word for it, check it.")

    v = L.verify(canon, before, answerer, judge, others=[before])
    if v.ok:
        post("verifier", "publisher",
             f"{v.citations_valid}/{v.citations_total} citations resolve to real code · "
             f"answer improved **{before.verdict} → {v.regraded.verdict}**. Verified. @publisher, ship it.")
        L.promote(canon, v, senso=None, memory=None)
        post("publisher", "grader", "Published the verified doc. The tool can now answer this "
             "question — permanently. @grader, ready for the next one. ✅")
    else:
        post("verifier", "grader", f"**Rejected**: {v.reason}.\nDoc discarded — we never keep "
             "what we can't prove against real code. That's the anti-hallucination gate. "
             "@grader, no change made. ✋")

    print(f"\nRoom: https://app.band.ai/chat/{rid}")


if __name__ == "__main__":
    main()
