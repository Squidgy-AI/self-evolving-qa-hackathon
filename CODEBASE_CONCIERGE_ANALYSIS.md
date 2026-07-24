# Codebase Concierge Analysis

**Reference Project**: https://github.com/Squidgy-AI/codebase-concierge

This document analyzes the Codebase Concierge project and extracts key patterns for our Self-Learning QA Agent System.

---

## Project Overview

**Codebase Concierge** is an email-driven AI agent that answers natural-language questions about codebases. Built for the OpenClaw Hackathon (Eragon × Nozomio × AgentMail), it demonstrates how to make codebases accessible to non-engineers.

### Core Value Proposition
Makes the codebase (the truest but least readable knowledge base) queryable by anyone via email.

---

## Architecture Pattern

```
Email Question → AgentMail Webhook → FastAPI
                                        ↓
                                 Check SQLite Cache
                                        ↓
                              Nia Query (codebase search)
                                        ↓
                              Claude Composes Answer
                                        ↓
                            AgentMail Reply (threaded)
                                        ↓
                            Auto-CC Engineer (git blame)
```

### Three-Layer System
1. **Brain**: Nia API (codebase context/search)
2. **Voice**: AgentMail (programmable inbox)
3. **Memory**: SQLite cache (Q&A history with embeddings)

---

## Key Features

### 1. Multi-Mode Intelligence
| Mode | Trigger | Output Style |
|------|---------|--------------|
| `eng` | Default | Code explanations with file:line citations |
| `sales` | `[sales]` tag | Capability answers (yes/no/partial) |
| `marketing` | `[marketing]` tag | Feature angles from diffs |
| `support` | `[support]` tag | Bug vs expected behavior triage |

**Pattern**: Same reasoning core, different system prompts based on context

### 2. Memory Layer (Hackathon Theme)
```python
# Cache structure
{
  "question_embedding": [0.1, 0.2, ...],
  "answer_html": "<p>Middleware works by...</p>",
  "sources": ["src/middleware.ts:45", "docs/api.md"],
  "timestamp": "2026-07-15T10:30:00Z",
  "answered_for": "pm@company.com"
}

# Cache hit logic
if cosine_similarity(new_question, cached_question) > 0.92:
    return cached_answer + "Previously answered for {user} on {date}"
```

**Benefits**:
- 25s → <1s response time
- Saves API quota
- Demonstrates "shared memory across workflows"

### 3. Auto-CC Engineer
Uses `git blame` to identify the engineer who last touched cited code and CCs them automatically. Brilliant UX touch.

### 4. Path Validation
Rejects hallucinated file paths by verifying against indexed repos. Maintains credibility.

---

## Technical Stack

**APIs**:
- Anthropic Claude Sonnet 4.6 (reasoning)
- Nia API (codebase search, ~25s latency)
- AgentMail (email inbox/threading)

**Framework**:
- Python 3.11
- FastAPI + uvicorn
- SQLite (cache)
- httpx (API calls)
- Deployed on Render

**Code Size**: ~3,630 lines total
- `core.py`: 776 lines (reasoning engine)
- `cache.py`: 413 lines (Q&A memory)
- `admin.py`: 818 lines (management UI)
- `main.py`: 398 lines (FastAPI routes)

---

## Integration Pattern

### Clean API Wrapper Example
```python
async def nia_query(question: str) -> dict:
    """Query indexed codebases. Returns {content, sources, follow_up_questions}."""
    payload = {
        "mode": "query",
        "messages": [{"role": "user", "content": question}],
        "repositories": get_active_repos(),
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        headers = {
            "Authorization": f"Bearer {NIA_API_KEY}",
            "Content-Type": "application/json",
        }
        resp = await client.post(NIA_BASE + "/chat", headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()
```

**Key Principles**:
- Clean function signatures
- Type hints
- Error handling with `raise_for_status()`
- Async/await for I/O
- Environment-based config

---

## Applicable Patterns for Our QA System

### 1. Memory/Cache Strategy

**Codebase Concierge**: SQLite cache with cosine similarity search
```python
def check_cache(question: str) -> tuple[bool, str, list]:
    embedding = embed(question)
    if similarity(embedding, cached_embedding) > 0.92:
        return (True, cached_answer, sources)
    return (False, "", [])
```

**Our QA System**: Actian VectorAI for test patterns
```python
def find_similar_tests(test_embedding, min_reward=10):
    """Find similar high-reward test patterns"""
    results = actian.search(
        query_vector=test_embedding,
        limit=5,
        filter={"reward": {"$gte": min_reward}}
    )
    return results
```

### 2. Multi-Mode Architecture

**Codebase Concierge**: Mode detection from email context
```python
def detect_mode(sender: str, subject: str) -> str:
    if "[sales]" in subject.lower():
        return "sales"
    if sender.endswith("@partner.com"):
        return "sales"
    return "eng"  # default

prompts = {
    "eng": "You explain code to non-engineers...",
    "sales": "Answer capability questions yes/no/partial...",
}
```

**Our QA System**: Three specialized agents
- QA Agent: Executes tests
- Grader Agent: Evaluates quality (LLM-as-judge)
- Learning Agent: Optimizes strategy (RL)

**Same Pattern**: Single brain (reasoning), multiple voices (system prompts)

### 3. Integration Wrapper Pattern

**Project Structure**:
```
qa-learning-system/
├── core.py                    # Reasoning engine (like Concierge)
├── integrations/
│   ├── guild_client.py        # Guild AI wrapper (like nia_query)
│   ├── actian_client.py       # Actian wrapper
│   ├── replay_client.py       # Browserbase wrapper
│   └── band_client.py         # Band AI wrapper
├── agents/
│   ├── qa_agent.py
│   ├── grader_agent.py
│   └── learning_agent.py
├── cache.py                   # Pattern storage (like Concierge's cache)
├── main.py                    # FastAPI / Band AI webhooks
└── setup_page.py              # Setup wizard (API key validation)
```

### 4. Setup Wizard Pattern

**Codebase Concierge**: `/setup` endpoint walks through:
1. ✅ Verify API keys
2. ✅ Index repos in Nia
3. ✅ Register AgentMail webhook
4. ✅ Set admin password
5. ✅ Add first user

**Our QA System**: Similar onboarding flow
1. ✅ Verify 4 API keys (Band, Guild, Actian, Browserbase)
2. ✅ Register agents on Band AI
3. ✅ Initialize Actian collections
4. ✅ Test Browserbase recording
5. ✅ Start Guild AI tracking

### 5. Cache-First Strategy

**Implementation**:
```python
async def run_test_iteration(test_spec):
    # 1. Check cache for similar patterns
    test_embedding = embed(test_spec)
    similar = actian.find_similar_tests(test_embedding, min_reward=15)

    if similar and similar[0].reward > 15:
        # High-reward pattern found - exploit
        logger.info(f"Re-running proven test pattern (reward: {similar[0].reward})")
        return run_test(similar[0].test_spec)
    else:
        # No strong pattern - explore
        logger.info("Exploring new test area")
        return generate_new_test()
```

**Benefits**:
- Skip expensive test generation for known patterns
- Balance exploration/exploitation
- Demonstrate learning over time

---

## Code Quality Observations

### Strengths
- ✅ Clean separation of concerns (core.py is channel-agnostic)
- ✅ Comprehensive error handling
- ✅ Security-first (HTML sanitization, API key cleaning)
- ✅ Production-ready (Render deployment, persistent disk)
- ✅ Well-documented (README + CLAUDE.md build plan)

### Architecture Decisions
- **Single-file core**: 776 lines, manageable
- **FastAPI async**: Natural for I/O-bound operations
- **SQLite**: Simple, no external DB needed
- **Stateless webhooks**: Thread state in AgentMail

---

## Hackathon Alignment (OpenClaw)

**OpenClaw Thesis**: AI agents that live in messaging platforms you already use

**Codebase Concierge Alignment**:
- ✅ Lives in messaging (email)
- ✅ Acts in the world (sends replies, CCs engineers)
- ✅ Makes inaccessible knowledge accessible
- ✅ Skills-extensible (mode system = OpenClaw skills)

**Our QA System Alignment** (Self-Evolving Agents Hackathon):
- ✅ Self-evolving (RL-powered learning)
- ✅ Multi-agent collaboration (Band AI)
- ✅ Shared memory (Actian + Guild tracking)
- ✅ 4-partner integration depth

---

## Demo Script Learnings

**Codebase Concierge 3-min Demo**:
1. **Hook** (20s): Thesis statement
2. **Live action** (35s): Send real email, show reply
3. **Thread context** (20s): Follow-up preserved
4. **Memory moment** (25s): Duplicate question returns instantly
5. **Differentiator** (20s): Auto-CC engineer
6. **Architecture** (35s): Brain + Voice + Memory
7. **Q&A prep**: Anticipate "why not X?" questions

**Our QA System Demo** (should follow same pattern):
1. **Hook**: Self-evolving QA with RL + grader-evaluator
2. **Live test**: QA Agent runs test, Browserbase records
3. **Grader analysis**: Watches replay, scores quality
4. **Learning**: Learning Agent adapts strategy
5. **Iteration 2**: Better test selection due to learning
6. **Architecture**: Band + Guild + Actian + Browserbase
7. **Proof**: Show Guild dashboard with learning curve

---

## Key Takeaways for Implementation

### 1. Keep Architecture Simple
- Single reasoning core per agent
- Clear integration wrappers
- Stateless where possible
- ~4,000 lines total budget

### 2. Cache-First Everything
- Check Actian before expensive operations
- Store ALL results with embeddings
- Demonstrate learning via cache hits

### 3. Integration Pattern
```python
class ToolClient:
    """Base pattern for all integrations"""

    def __init__(self):
        self.api_key = os.getenv("TOOL_API_KEY")
        self.client = httpx.AsyncClient()

    async def call_api(self, endpoint, payload):
        """Clean async API call with error handling"""
        try:
            resp = await self.client.post(
                f"{self.base_url}/{endpoint}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=60.0
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"API call failed: {e}")
            raise
```

### 4. Setup Wizard First
Build `/setup` endpoint BEFORE building features:
- Validates all API keys work
- Tests each integration
- Creates initial data
- Reduces debugging pain later

### 5. Demo-Driven Development
- Build for the 3-minute demo
- Every feature must be demo-able
- Cache the "memory moment" before demo
- Have backup video

---

## Action Items for Our Project

### Phase 1: Foundation (Like Concierge's core.py)
1. ✅ Create integration wrappers
2. ✅ Build setup wizard
3. ✅ Test each API independently

### Phase 2: Core Reasoning (Like Concierge's answer_codebase_question)
1. ✅ QA Agent test execution
2. ✅ Grader Agent evaluation logic
3. ✅ Learning Agent RL strategy

### Phase 3: Memory Layer (Like Concierge's cache.py)
1. ✅ Actian pattern storage
2. ✅ Similarity search
3. ✅ Cache-first test selection

### Phase 4: Integration (Like Concierge's main.py)
1. ✅ Band AI webhooks
2. ✅ Guild AI tracking
3. ✅ Browserbase recording

### Phase 5: Demo Prep (Like Concierge's demo.py)
1. ✅ Rehearse 3-min demo
2. ✅ Pre-warm cache
3. ✅ Record backup video
4. ✅ Prepare Q&A responses

---

## Conclusion

**Codebase Concierge** proves that a well-architected hackathon project can be:
- Production-ready (~3,600 lines)
- Multi-agent capable (modes)
- Memory-enabled (cache)
- Integration-deep (3 APIs)
- Demo-ready (3-min script)

**Our QA System** follows the same principles:
- Clean architecture
- Integration depth (4 partners)
- Memory layer (Actian)
- Self-evolving behavior (RL)
- Clear demo narrative

**Success Pattern**: Simple core + clean integrations + compelling demo = winning hackathon project

---

## References

- Codebase Concierge: https://github.com/Squidgy-AI/codebase-concierge
- OpenClaw Hackathon: Eragon × Nozomio × AgentMail
- Build Time: Single-day hackathon
- Result: Production-ready email agent with memory

---

*Analysis completed: 2026-07-24*
*For: Self-Evolving Agents Hackathon*
*By: Squidgy AI Team*
