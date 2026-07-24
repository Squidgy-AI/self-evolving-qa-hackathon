# Squidgy DeepWiki Analysis

**Repository**: https://github.com/Squidgy-AI/squidgy-deepwiki
**Original Fork**: https://github.com/AsyncFuncAI/deepwiki-open

This is Squidgy's internal documentation engine - a significantly more relevant reference for our QA hackathon project than codebase-concierge.

---

## Project Overview

**Squidgy DeepWiki** auto-generates comprehensive documentation wikis from GitHub repositories with:
1. Architecture overviews with source citations
2. Mermaid diagrams (architecture + data flow)
3. Navigable wiki structure
4. RAG-based "Ask" interface over the codebase

### Core Value Proposition
Transforms code repositories into searchable, AI-powered documentation with Q&A capabilities.

---

## Architecture

```
GitHub Repo → Clone → Analyze → Generate Embeddings
                                        ↓
                              Store in Vector DB (~/.adalflow)
                                        ↓
User Question → RAG Retrieval → LLM Generation → Streaming Response
                                        ↓
                              Wiki Pages + Mermaid Diagrams
```

### Tech Stack

**Frontend**:
- Next.js (TypeScript)
- Real-time WebSocket streaming
- Wiki visualization

**Backend** (FastAPI):
- **api.py** (main API, ~1,200+ lines)
- **data_pipeline.py** (repo analysis, embeddings)
- **rag.py** (Retrieval Augmented Generation)
- **simple_chat.py** (streaming chat interface)
- **websocket_wiki.py** (wiki generation WebSocket)

**LLM Providers** (Multi-provider support):
- OpenRouter (Squidgy's choice) - anthropic/claude-sonnet-4-6
- OpenAI
- Google Gemini
- AWS Bedrock
- Ollama (local)

**Embeddings**:
- openai/text-embedding-3-small (256-dim) via OpenRouter

---

## Key Features Relevant to QA System

### 1. **RAG Implementation** (api/rag.py)
```python
# Retrieval Augmented Generation pattern
def retrieve_relevant_code(query: str, repo_path: str):
    # 1. Embed query
    query_embedding = embed(query)

    # 2. Vector similarity search
    relevant_files = vector_db.search(query_embedding, top_k=5)

    # 3. Return context for LLM
    return relevant_files

def generate_answer(query: str, context: List[str]):
    # 4. LLM generates answer from context
    response = llm.generate(
        prompt=f"Context: {context}\n\nQuestion: {query}"
    )
    return response
```

**For Our QA System**: Use same pattern to find relevant test files/patterns

### 2. **Multi-Provider Configuration** (api/config/)
```json
// api/config/generator.json
{
  "providers": [
    {
      "id": "openrouter",
      "name": "OpenRouter",
      "models": [
        {
          "id": "anthropic/claude-sonnet-4-6",
          "name": "Claude Sonnet 4.6"
        }
      ]
    }
  ]
}
```

**Clean Pattern**: JSON-based config, environment variable overrides

### 3. **Streaming Responses** (api/simple_chat.py)
```python
async def stream_response(messages, repo_url):
    """Stream LLM responses in real-time"""
    async for chunk in llm.stream(messages):
        yield chunk
```

**For Our QA System**: Stream test execution progress, grader feedback

### 4. **Local Vector Storage** (~/.adalflow)
```
~/.adalflow/
├── repos/              # Cloned repositories
├── databases/          # Vector embeddings
└── wikicache/          # Generated wiki caches
```

**For Our QA System**: Store test pattern embeddings locally before moving to Actian

### 5. **Wiki Generation Pipeline** (api/websocket_wiki.py)
```python
# Multi-step generation process
async def generate_wiki(repo_url, provider, model):
    # 1. Clone repo
    repo_path = clone_repository(repo_url)

    # 2. Analyze structure
    structure = analyze_codebase(repo_path)

    # 3. Generate embeddings
    embeddings = create_embeddings(structure)

    # 4. Generate wiki pages
    pages = await generate_pages(structure, llm)

    # 5. Create Mermaid diagrams
    diagrams = generate_architecture_diagrams(structure)

    return WikiStructure(pages, diagrams)
```

**For Our QA System**: Multi-step test generation and learning pipeline

---

## Integration Patterns Applicable to Hackathon

### 1. **Configuration Management**
```python
# api/config.py
class Config:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")

    @classmethod
    def validate(cls):
        """Validate all required env vars"""
        required = ["OPENROUTER_API_KEY", "OPENAI_API_KEY"]
        missing = [k for k in required if not getattr(cls, k)]
        if missing:
            raise ValueError(f"Missing: {missing}")
```

**For Our QA System**: Validate Band AI, Guild AI, Actian, Browserbase keys

### 2. **Provider Abstraction Pattern**
```python
# api/openrouter_client.py
class OpenRouterClient:
    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            headers={"Authorization": f"Bearer {api_key}"}
        )

    async def generate(self, messages, model="anthropic/claude-sonnet-4-6"):
        response = await self.client.post("/chat/completions", json={
            "model": model,
            "messages": messages,
            "stream": True
        })
        return response
```

**For Our QA System**: Create similar wrappers for:
- `GuildClient` - experiment tracking
- `ActianClient` - vector storage
- `BrowserbaseClient` - session recording
- `BandClient` - agent messaging

### 3. **Webhook Pattern** (api/webhook.py)
```python
# GitHub webhook handling
@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None)
):
    # Verify signature
    verify_github_signature(request, x_hub_signature_256)

    # Process event
    payload = await request.json()
    if payload["action"] == "push":
        # Re-index repository
        await reindex_repository(payload["repository"]["url"])

    return {"status": "ok"}
```

**For Our QA System**: Band AI webhooks for agent communication

### 4. **Data Pipeline Pattern** (api/data_pipeline.py)
```python
async def process_repository(repo_url: str, branch: str = "main"):
    """
    Complete repository processing pipeline
    """
    # 1. Clone
    repo_path = await clone_repo(repo_url, branch)

    # 2. Extract files
    files = extract_code_files(repo_path)

    # 3. Create embeddings
    embeddings = await create_embeddings_batch(files)

    # 4. Store in vector DB
    await store_embeddings(embeddings)

    # 5. Build metadata
    metadata = build_repo_metadata(repo_path, files)

    return {
        "repo_path": repo_path,
        "file_count": len(files),
        "embedding_count": len(embeddings),
        "metadata": metadata
    }
```

**For Our QA System**: Test execution pipeline
```python
async def execute_test_iteration(test_spec):
    # 1. Start recording (Browserbase)
    session_id = await replay.start_recording(test_spec.name)

    # 2. Run test (QA Agent)
    result = await run_test(test_spec)

    # 3. Get replay (Browserbase)
    replay_url = await replay.get_replay_url(session_id)

    # 4. Grade test (Grader Agent)
    score = await grade_test(result, replay_url)

    # 5. Store pattern (Actian)
    await actian.store_pattern(test_spec, score)

    # 6. Log to Guild
    await guild.log_metrics(score, session_id)

    return TestResult(score, replay_url)
```

---

## Storage Architecture

### Local-First with Cloud Sync Potential
```
~/.adalflow/
├── repos/
│   └── {owner}__{repo}__{branch}/
│       └── [cloned repository]
├── databases/
│   └── {owner}__{repo}__{branch}/
│       ├── embeddings.index  # FAISS/Chroma index
│       └── metadata.json
└── wikicache/
    └── {owner}__{repo}__{branch}__{language}.json
        ├── wiki_structure
        ├── generated_pages
        └── provider/model metadata
```

**For Our QA System**:
```
~/.qa-learning/
├── test_specs/
│   └── {project}/
│       └── *.yaml
├── patterns/               # Local before Actian
│   └── {project}/
│       ├── embeddings.db
│       └── rewards.json
└── recordings/
    └── {test_id}/
        └── browserbase_session_id.txt
```

---

## Multi-Provider LLM Strategy

**DeepWiki's Approach**:
1. JSON config files define available providers
2. Environment variables hold API keys
3. Runtime selection via API request
4. Fallback chain if primary fails

```python
# From api/config.py
def get_llm_client(provider: str, model: str):
    clients = {
        "openrouter": OpenRouterClient,
        "openai": OpenAIClient,
        "google": GoogleClient,
        "bedrock": BedrockClient,
        "ollama": OllamaClient
    }

    ClientClass = clients.get(provider)
    if not ClientClass:
        raise ValueError(f"Unknown provider: {provider}")

    return ClientClass(model=model)
```

**For Our QA System**: Use Claude via Band AI SDK (already decided)

---

## API Design Patterns

### 1. **Streaming Endpoints**
```python
@app.post("/chat/completions/stream")
async def stream_chat(request: ChatRequest):
    """Stream responses as they're generated"""
    async def generate():
        async for chunk in llm.stream(request.messages):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

### 2. **Cache Management**
```python
@app.get("/wiki/cache/{owner}/{repo}/{branch}")
async def get_wiki_cache(owner: str, repo: str, branch: str):
    """Retrieve cached wiki"""
    cache_file = get_cache_path(owner, repo, branch)
    if cache_file.exists():
        return JSONResponse(json.load(cache_file.open()))
    raise HTTPException(404, "Cache not found")
```

### 3. **Health Checks**
```python
@app.get("/health")
async def health_check():
    """Verify all services are operational"""
    checks = {
        "api": True,
        "vector_db": await check_vector_db(),
        "llm_provider": await check_llm(),
        "embeddings": await check_embeddings()
    }

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return JSONResponse(checks, status_code=status_code)
```

---

## How This Relates to Our QA Hackathon Project

### Direct Applicability

| DeepWiki Feature | Our QA System Equivalent |
|------------------|--------------------------|
| **Repository Analysis** | Test suite analysis |
| **RAG Q&A** | Test pattern similarity search |
| **Embeddings Storage** | Actian VectorAI (test patterns) |
| **Wiki Generation** | Test report generation |
| **Streaming Responses** | Real-time test execution updates |
| **Multi-Provider LLM** | Multi-agent (QA, Grader, Learning) |
| **Local Storage** | Guild AI + Actian persistence |
| **WebSocket Updates** | Band AI agent messaging |

### Architecture Mapping

**DeepWiki**:
```
User Question → Embed → Vector Search → LLM → Streaming Response
```

**Our QA System**:
```
Test Trigger → Embed Test Spec → Find Similar → Run/Learn → Stream Results
```

### Code Patterns to Borrow

1. **Configuration Management** (JSON configs + env vars)
2. **Provider Abstraction** (Clean client classes)
3. **Streaming Implementation** (FastAPI StreamingResponse)
4. **Pipeline Architecture** (Multi-step async workflows)
5. **Cache Management** (Local-first with metadata)
6. **Health Checks** (Validate all integrations)

---

## Key Insights for Implementation

### 1. **Start Simple, Then Scale**
DeepWiki began as a simple Q&A tool, added wiki generation later:
- ✅ MVP: RAG Q&A over one repo
- ✅ v2: Wiki generation
- ✅ v3: Multi-provider support
- ✅ v4: Webhook auto-reindexing

**Our QA System**:
- ✅ MVP: Single QA agent with Band AI
- ✅ v2: Add Grader agent
- ✅ v3: Add Learning agent with Actian
- ✅ v4: Add Guild tracking + Browserbase replay

### 2. **Local-First Development**
DeepWiki stores everything locally (~/.adalflow), making dev/test easy:
- No cloud dependencies during development
- Fast iteration
- Easy debugging
- Cloud deploy is straightforward (Render)

**Our QA System**: Same approach
- Local Actian for development
- Local test pattern storage
- Cloud Actian for production

### 3. **Provider Abstraction**
DeepWiki supports 5+ LLM providers via clean abstraction:
```python
class BaseProvider:
    async def generate(self, messages): ...
    async def stream(self, messages): ...
    async def embed(self, text): ...
```

**Our QA System**: Similar abstraction for tools
```python
class BaseIntegration:
    async def initialize(self): ...
    async def call(self, *args): ...
    async def validate(self): ...
```

### 4. **Webhook-Driven Automation**
DeepWiki auto-reindexes repos on GitHub pushes:
- Registers webhook on repo
- Receives push events
- Triggers background reindexing

**Our QA System**: Band AI webhooks for agent triggers
- Agent receives message
- Triggers test execution
- Returns results via Band

---

## Recommended Project Structure

Based on DeepWiki's clean architecture:

```
qa-learning-system/
├── api/
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Centralized configuration
│   ├── agents/
│   │   ├── qa_agent.py
│   │   ├── grader_agent.py
│   │   └── learning_agent.py
│   ├── integrations/
│   │   ├── base.py                # BaseIntegration class
│   │   ├── band_client.py
│   │   ├── guild_client.py
│   │   ├── actian_client.py
│   │   └── replay_client.py
│   ├── pipeline.py                # Test execution pipeline
│   ├── rag.py                     # Pattern similarity search
│   ├── webhook.py                 # Band AI webhooks
│   └── config/
│       ├── agents.json
│       ├── grading_rubric.json
│       └── test_specs.json
├── src/                           # Next.js frontend (if needed)
├── tests/
├── .env.example
├── docker-compose.yml
├── render.yaml
└── README.md
```

---

## Action Items for Hackathon

### Phase 1: Foundation (Inspired by DeepWiki)
1. ✅ Create config.py with API key validation
2. ✅ Build BaseIntegration abstract class
3. ✅ Implement 4 integration clients (Band, Guild, Actian, Browserbase)
4. ✅ Add health check endpoint

### Phase 2: Core Pipeline
1. ✅ QA Agent test execution
2. ✅ Grader Agent evaluation
3. ✅ Learning Agent RL strategy
4. ✅ Pattern storage in Actian

### Phase 3: RAG Implementation
1. ✅ Test spec embedding
2. ✅ Similarity search in Actian
3. ✅ Cache-first test selection

### Phase 4: Streaming & Real-time
1. ✅ Band AI webhook handler
2. ✅ Streaming test progress
3. ✅ Real-time grader feedback

### Phase 5: Demo Prep
1. ✅ Pre-generate test patterns
2. ✅ Record demo video
3. ✅ Deploy to Render
4. ✅ Prepare Q&A

---

## Conclusion

**Squidgy DeepWiki** is an excellent architectural reference because it already implements many patterns we need:

- ✅ RAG-based retrieval (test pattern search)
- ✅ Multi-provider LLM (multi-agent)
- ✅ Embedding storage (Actian equivalent)
- ✅ Streaming responses (real-time updates)
- ✅ Pipeline architecture (test execution flow)
- ✅ Clean abstractions (integration wrappers)
- ✅ Local-first development
- ✅ Production deployment (Render)

**Key Takeaway**: Follow DeepWiki's clean architecture patterns:
1. Provider abstraction for integrations
2. JSON-based configuration
3. Pipeline-driven workflows
4. Local-first storage
5. Streaming interfaces
6. Health validation

This gives us a proven, production-ready architecture to build on.

---

## References

- **Squidgy DeepWiki**: https://github.com/Squidgy-AI/squidgy-deepwiki
- **Original DeepWiki**: https://github.com/AsyncFuncAI/deepwiki-open
- **Tech Stack**: FastAPI + Next.js + OpenRouter + Vector DB
- **Deployment**: Render (Blueprint deployment)

---

*Analysis completed: 2026-07-24*
*For: Self-Evolving Agents Hackathon*
*By: Squidgy AI Team*
