# Self-Evolving QA Agent System

**Built for the Self-Evolving Agents Hackathon (July 24, 2026)**

A multi-agent system combining Band.ai orchestration, RL-powered learning, and grader-evaluator frameworks to create a self-improving QA testing system.

## 🎯 Project Overview

This project demonstrates a self-learning QA agent system that:
- Executes automated tests using Playwright/Browserbase
- Evaluates test quality using LLM-as-judge methodology
- Learns from feedback using reinforcement learning principles
- Evolves testing strategy over time through multi-agent collaboration

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   GUILD AI CONTROL PLANE                 │
│  • Tracks agent performance and experiments              │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                  BAND AI AGENT PLATFORM                  │
├─────────────────────────────────────────────────────────┤
│  QA Agent ──→ Grader Agent ──→ Learning Agent           │
└─────────────────────────────────────────────────────────┘
                           ↓
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │Browserbase│ │Guild AI  │  │Actian DB │
        │  Replay  │  │Tracking  │  │ Vector   │
        └──────────┘  └──────────┘  └──────────┘
```

## 🛠️ Technology Stack

### Partner Technologies (Hackathon Sponsors)
1. **Band AI** - Multi-agent communication and orchestration
2. **Guild AI** - Agent control plane and experiment tracking
3. **Actian VectorAI DB** - Vector database for pattern storage
4. **Browserbase Replay** - Session recording and playback

### Core Technologies
- Python 3.12
- Band SDK with Claude SDK adapter
- Claude Sonnet 4.6
- Playwright for browser automation
- Vector embeddings for pattern matching

## 🚀 Current Status: Tom & Jerry Demo

Currently implemented: **Tom & Jerry multi-agent demo** on Band.ai

### Active Agents

**Tom (The Cat)** - Agent ID: `0fd36fc9-96da-41b6-bf5c-d120bf697709`
- Persistent and theatrical personality
- Uses platform tools to find and invite Jerry
- Employs various persuasion tactics

**Jerry (The Mouse)** - Agent ID: `6ababca3-2958-4ded-9468-717068b8022f`
- Clever and cautious personality
- Lives safely in his hole
- Evaluates Tom's offers and stays safe

### Try It Out

1. Visit [Band.ai](https://app.band.ai)
2. Start a new chat
3. Add Tom (`@dmacproject123/tom`)
4. Send: `@dmacproject123/tom catch jerry`
5. Watch the agents interact!

## 📦 Installation

```bash
# Clone repository
git clone https://github.com/Squidgy-AI/self-evolving-qa-hackathon.git
cd self-evolving-qa-hackathon

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run agents
uv run python tom_agent.py
uv run python jerry_agent.py
```

## 🎓 Next Steps: Full QA System

The complete self-learning QA system will include:

### Agent Roles
1. **QA Agent** - Executes tests with Browserbase recording
2. **Grader Agent** - Evaluates tests using LLM-as-judge
3. **Learning Agent** - RL-powered strategy optimization

### Learning Mechanism
- Grader scores tests on multiple dimensions (bug detection, coverage, efficiency)
- Learning Agent uses rewards to prioritize high-value tests
- Vector similarity search finds related test patterns
- System evolves strategy over time through exploration/exploitation

### Integration Features
- **Band AI**: Multi-agent orchestration
- **Guild AI**: Experiment tracking and performance monitoring
- **Actian VectorAI**: Pattern storage and similarity search
- **Browserbase**: Session recording and replay analysis

## 📊 Self-Learning Flow

```
1. QA Agent runs test (based on Learning Agent strategy)
2. Browserbase records session
3. Grader evaluates test quality
4. Grader sends reward score to Learning Agent
5. Learning Agent queries Actian for similar past tests
6. Learning Agent updates strategy in Guild AI
7. Next iteration: improved test selection
```

## 🏆 Hackathon Alignment

This project demonstrates:
- ✅ Self-evolving agent behavior
- ✅ Multi-agent collaboration
- ✅ Integration with 4 hackathon partners
- ✅ Practical QA use case
- ✅ RL-powered learning
- ✅ Grader-evaluator pattern

## 📝 License

MIT License - Built for the Self-Evolving Agents Hackathon 2026

## 🤝 Contributing

This is a hackathon project. Feel free to fork and experiment!

## 📧 Contact

Built by the Squidgy AI team for the Band.ai Self-Evolving Agents Hackathon.

---

**Status**: 🟢 Active Development
**Hackathon**: Self-Evolving Agents Hackathon - July 24, 2026
**Organization**: Squidgy-AI
