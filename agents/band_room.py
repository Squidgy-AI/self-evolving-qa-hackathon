"""Stand up a BAND room and narrate a real evolution-loop cycle as agent handoffs.

Why this shape: the four role agents (grader/researcher/verifier/publisher) are
registered in BAND, but running four live Claude-SDK agents that actually drive the
loop is heavy and fragile for a 3-minute demo. Instead we run the REAL loop here and
post each stage into a shared BAND room as the corresponding agent — so judges watch
@Grader -> @Researcher -> @Verifier -> @Publisher hand off in real time, backed by
the genuine grade/research/verify/promote functions (not a scripted playback).

Usage:
    python agents/band_room.py "How are WebSocket dependencies resolved differently from HTTP ones?"

Prints the room URL to open on screen.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from band.client.rest import RestClient  # noqa: E402
from band_rest.human_api_chats.types.create_my_chat_room_request_chat import (  # noqa: E402
    CreateMyChatRoomRequestChat as RoomReq,
)
from band_rest.types.chat_message_request import ChatMessageRequest  # noqa: E402
from band_rest.types.participant_request import ParticipantRequest  # noqa: E402

from clients.judge import Judge  # noqa: E402
from clients.local_answerer import LocalAnswerer  # noqa: E402
from engine import loop as L  # noqa: E402
from engine.models import Gap  # noqa: E402

AGENTS = {  # name -> agent_id (from registration; see agent_config.yaml)
    "grader": "5ddbbcda-bfdf-40c3-ba6c-2af0f797f6c8",
    "researcher": "d2750b12-2d5c-4a3a-97e6-d8ff7d4b2224",
    "verifier": "b2be74e9-a22f-4aa7-9adc-5f5e09006294",
    "publisher": "03eadbd5-529c-4e1b-8e02-caeb2f47e493",
}
EMOJI = {"grader": "🔎", "researcher": "📚", "verifier": "✓", "publisher": "📤"}


def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else \
        "How are WebSocket dependencies resolved differently from HTTP ones?"
    repo = os.getenv("DEMO_REPO", "fastapi/fastapi")

    key = os.environ["BAND_API_KEY"]
    c = RestClient(api_key=key)

    # Creating a room via the API needs an Enterprise BAND plan (free/Pro returns
    # 403 plan_required). So: if BAND_ROOM_ID is set (a room you made in the
    # app.band.ai UI and added the four agents to), narrate into that. Otherwise try
    # to create one and fall back with a clear message.
    rid = os.getenv("BAND_ROOM_ID")
    if not rid:
        try:
            room = c.human_api_chats.create_my_chat_room(chat=RoomReq(title="Evolution Loop — live"))
            rid = room.model_dump(mode="json").get("data", {}).get("id") \
                or room.model_dump(mode="json").get("id")
            for name, aid in AGENTS.items():
                try:
                    c.human_api_participants.add_my_chat_participant(
                        rid, participant=ParticipantRequest(participant_id=aid, role="member"))
                except Exception as e:  # noqa: BLE001
                    print(f"  ! add {name}: {e}")
        except Exception as e:  # noqa: BLE001
            print("Could not create a room via API (BAND plan likely doesn't allow it):")
            print(f"  {type(e).__name__}: {str(e)[:120]}")
            print("Create a room in the app.band.ai UI, add the four agents (they're")
            print("registered — see /agents), then re-run with BAND_ROOM_ID=<room id>.")
            return
    print(f"ROOM: https://app.band.ai/chat/{rid}\n")

    def say(who: str, text: str) -> None:
        c.human_api_messages.send_my_chat_message(
            rid, message=ChatMessageRequest(content=f"{EMOJI[who]} @{who.title()}: {text}")
        )
        print(f"{EMOJI[who]} @{who.title()}: {text}")
        time.sleep(1.2)  # let the room render each handoff for the camera

    # --- run the real loop, narrating each stage as the right agent ---
    L.set_target_repo(L._basename_index.__globals__["TARGET_REPO"])  # keep current
    answerer = LocalAnswerer()
    judge = Judge()

    say("grader", f"New question on `{repo}`: \"{question}\"")
    answerer.clear_cache()
    before = L.grade(question, answerer, judge)
    say("grader", f"Graded the current answer: **{before.verdict}**. "
        + ("Handing to @Researcher." if before.verdict != "grounded" else "Already solid — nothing to do."))
    if before.verdict == "grounded":
        return

    say("researcher", "Searching the codebase for the relevant source…")
    gap = Gap(question=question, signature=L._signature(question), reason=before.reason)
    canon = L.research(gap, pioneer=None, memory=None)
    if canon is None:
        say("researcher", "Couldn't find supporting source. Aborting — better to say nothing than guess.")
        return
    say("researcher", f"Drafted a doc citing {len(canon.citations)} line(s): "
        + ", ".join(f"`{x}`" for x in canon.citations[:4]) + ". Handing to @Verifier.")

    say("verifier", "Checking every citation resolves to real code, and that the answer actually improves…")
    v = L.verify(canon, before, answerer, judge, others=[before])
    if v.ok:
        say("verifier", f"{v.citations_valid}/{v.citations_total} citations resolve, "
            f"answer improved {before.verdict} → {v.regraded.verdict}. Approved. @Publisher.")
        L.promote(canon, v, senso=None, memory=None)
        say("publisher", "Published the verified doc to the knowledge base. The tool can now answer this. ✅")
    else:
        say("verifier", f"Rejected: {v.reason}. Doc discarded — we don't keep what we can't prove. ✋")

    print(f"\nOpen the room: https://app.band.ai/chat/{rid}")


if __name__ == "__main__":
    main()
