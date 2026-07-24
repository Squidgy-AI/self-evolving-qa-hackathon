#!/bin/bash
# Launch all 4 Evolution Loop agents in the background
# For the hackathon demo — judges watch them collaborate in the BAND room

set -e

echo "🚀 Launching Evolution Loop agents..."
echo ""

# Activate venv if it exists
if [ -d ".venv-engine" ]; then
    source .venv-engine/bin/activate
fi

# Launch each agent in the background
echo "Starting @Grader..."
python agents/grader_agent.py > logs/grader.log 2>&1 &
GRADER_PID=$!
echo "  PID: $GRADER_PID"

echo "Starting @Researcher..."
python agents/researcher_agent.py > logs/researcher.log 2>&1 &
RESEARCHER_PID=$!
echo "  PID: $RESEARCHER_PID"

echo "Starting @Verifier..."
python agents/verifier_agent.py > logs/verifier.log 2>&1 &
VERIFIER_PID=$!
echo "  PID: $VERIFIER_PID"

echo "Starting @Publisher..."
python agents/publisher_agent.py > logs/publisher.log 2>&1 &
PUBLISHER_PID=$!
echo "  PID: $PUBLISHER_PID"

echo ""
echo "✅ All agents running!"
echo ""
echo "Watch them collaborate at: https://app.band.ai/rooms/evolution-loop"
echo ""
echo "To stop all agents:"
echo "  kill $GRADER_PID $RESEARCHER_PID $VERIFIER_PID $PUBLISHER_PID"
echo ""
echo "Logs:"
echo "  tail -f logs/grader.log"
echo "  tail -f logs/researcher.log"
echo "  tail -f logs/verifier.log"
echo "  tail -f logs/publisher.log"
echo ""

# Save PIDs to file for easy cleanup
echo "$GRADER_PID $RESEARCHER_PID $VERIFIER_PID $PUBLISHER_PID" > .agent_pids

echo "Agents are live. Press Ctrl+C to monitor, or run 'cat .agent_pids | xargs kill' to stop all."
