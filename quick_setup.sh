#!/bin/bash
# Quick Setup Script for Evolution Loop Demo
# Run this to get everything ready in ~10 minutes

set -e

echo "=================================="
echo "Evolution Loop - Quick Setup"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}✗ .env not found!${NC}"
    echo "Creating .env from template..."
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Edit .env and add your API keys!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ .env file found${NC}"
echo ""

# Step 1: Clone fastapi/fastapi repo
echo "Step 1/5: Clone fastapi/fastapi repo for citation validation"
FASTAPI_PATH=~/Git/fastapi
if [ -d "$FASTAPI_PATH" ]; then
    echo -e "${GREEN}✓ FastAPI repo already cloned at $FASTAPI_PATH${NC}"
else
    echo "Cloning fastapi/fastapi..."
    mkdir -p ~/Git
    git clone --depth 1 https://github.com/fastapi/fastapi.git $FASTAPI_PATH
    echo -e "${GREEN}✓ Cloned fastapi/fastapi${NC}"
fi
echo ""

# Step 2: Install Python dependencies
echo "Step 2/5: Install Python dependencies"
if command -v uv &> /dev/null; then
    echo "Using uv for faster installation..."
    uv pip install -r requirements-engine.txt
else
    echo "Using pip..."
    pip install -r requirements-engine.txt
fi
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Step 3: Start Actian Vector DB
echo "Step 3/5: Start Actian Vector DB"
if docker ps | grep -q vectorai; then
    echo -e "${GREEN}✓ Actian Vector already running${NC}"
else
    echo "Starting Actian Vector container..."
    docker run -d --name vectorai \
        -v ./local_data:/var/lib/actian-vectorai \
        -p 6573-6575:6573-6575 \
        -e ACTIAN_VECTORAI_ACCEPT_EULA=YES \
        actian/vectorai:latest

    echo "Waiting for Actian to be ready..."
    sleep 5
    echo -e "${GREEN}✓ Actian Vector started${NC}"
fi
echo ""

# Step 4: Validate API keys
echo "Step 4/5: Validate API keys"
source .env

API_KEYS_FOUND=0
API_KEYS_NEEDED=0

check_key() {
    local name=$1
    local value=$2
    local required=$3

    if [ -n "$value" ]; then
        echo -e "${GREEN}✓ $name${NC}"
        ((API_KEYS_FOUND++))
    else
        if [ "$required" = "required" ]; then
            echo -e "${RED}✗ $name (REQUIRED)${NC}"
        else
            echo -e "${YELLOW}⊘ $name (optional)${NC}"
        fi
        ((API_KEYS_NEEDED++))
    fi
}

check_key "GEMINI_API_KEY" "$GEMINI_API_KEY" "required"
check_key "PIONEER_API_KEY" "$PIONEER_API_KEY" "required"
check_key "REPLAY_API_KEY" "$REPLAY_API_KEY" "optional"
check_key "SENSO_API_KEY" "$SENSO_API_KEY" "optional"
check_key "BAND_USER_API_KEY" "$BAND_USER_API_KEY" "required"

echo ""

# Step 5: Test one cycle
echo "Step 5/5: Test one evolution cycle"
if [ -n "$GEMINI_API_KEY" ] && [ -n "$PIONEER_API_KEY" ]; then
    echo "Running test cycle..."
    python -m engine.loop
    echo ""
    echo -e "${GREEN}✓ Test cycle complete!${NC}"
else
    echo -e "${YELLOW}⊘ Skipping test cycle (missing required API keys)${NC}"
    echo ""
    echo "Get API keys:"
    echo "  1. Gemini (60 sec): https://aistudio.google.com/app/apikey"
    echo "  2. Pioneer (5 min): https://agent.pioneer.ai (code: HACKATHONSF0724)"
    echo ""
    echo "Then run: python -m engine.loop"
fi

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "  1. Launch BAND agents: ./launch_agents.sh"
echo "  2. Start Guild AI: pip install guild && guild serve"
echo "  3. Deploy dashboard: See DEPLOY_DASHBOARD.md"
echo ""
echo "Hackathon ready! 🚀"
