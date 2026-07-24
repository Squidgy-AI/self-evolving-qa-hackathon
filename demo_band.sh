#!/bin/bash
# One-command BAND room demo. Runs a real evolution-loop cycle as live agent
# handoffs in the BAND room. Open the room on screen first:
#   https://app.band.ai/chat/989029da-3bd2-421f-92cb-fed2464bbe73
#
# Usage:  ./demo_band.sh ["your question"]
set -e
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:$PATH"
set -a; . ./.env; set +a
export ANSWERER=local
export TARGET_REPO="${TARGET_REPO:-$HOME/Git/fastapi}"
export BAND_ROOM_ID="${BAND_ROOM_ID:-989029da-3bd2-421f-92cb-fed2464bbe73}"
export BAND_PACE="${BAND_PACE:-2.5}"

Q="${1:-How are WebSocket dependencies resolved differently from HTTP ones?}"
exec ./.venv-engine/bin/python agents/band_room.py "$Q"
