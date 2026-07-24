# Interface Contract

Two people are building this in parallel. **Stay inside your own directories.**

| Directory | Owner | Contents |
|---|---|---|
| `agents/` | Soma | BAND role agents (renamed from tom/jerry), Guild trigger config |
| `app/` | Soma | anything he needs for BAND/Guild wiring |
| `clients/` | Jeff | Pioneer, Senso, Actian, Replay, Concierge, Gemini judge |
| `engine/` | Jeff | the evolution loop + data model |
| `dashboard/` | Jeff | public `/evolution` page (Replay QA target) |
| `data/` | shared, gitignored | `runs.jsonl` — one cycle per line |

Never edit a directory you don't own. If you need something from the other side, it goes through the interfaces below.

---

## What the system does

An agent improves **Concierge** (a live production codebase-Q&A service) without human intervention:

```
ask Concierge a question  ->  grade the answer  ->  if it's a miss:
    recall a prior fix from memory  ->  else research the repo
    -> write canon with file:line citations  -> verify citations resolve
    -> re-ask  -> promote only if the score improved and nothing regressed
    -> remember what worked
```

Each pass through that is one **cycle**. Cycles are appended to `data/runs.jsonl`.

---

## The four BAND roles map to four engine calls

Soma's agents don't need to know how any of this works. Each role calls exactly one function.

```python
from engine.loop import grade, research, verify, promote, run_cycle
```

| BAND agent | Calls | Returns |
|---|---|---|
| `@Grader` | `grade(question: str) -> Grade` | verdict + why |
| `@Researcher` | `research(gap: Gap) -> Canon` | proposed doc + citations |
| `@Verifier` | `verify(canon: Canon) -> Verdict` | do the citations resolve, did the score improve |
| `@Publisher` | `promote(canon: Canon, verdict: Verdict) -> PromoteResult` | published or discarded |

And for the Guild cron trigger, one headless entrypoint that does the whole thing:

```python
run_cycle(questions: list[str] | None = None) -> CycleResult
```

`run_cycle()` with no arguments uses the golden question set. It is safe to call repeatedly.

---

## Data model (`engine/models.py`)

All dataclasses, all JSON-serialisable via `asdict()`.

```python
Grade      (question, answer, verdict: "grounded"|"partial"|"miss",
            reason, citations_valid, citations_total, inference_id, graded_at)

Gap        (question, signature, reason, ask_count)

Canon      (title, body_md, citations: list[str], source_gap, generated_at)
           # citations are "path/to/file.py:123" and MUST resolve to real lines

Verdict    (ok: bool, citations_valid, citations_total, invalid: list[str],
            regraded: Grade | None, reason)

PromoteResult (promoted: bool, senso_content_id, published_url, reason)

CycleResult (cycle, started_at, ended_at, questions_tested,
             passed_before, passed_after, gaps_found, canon_written,
             canon_promoted, canon_rejected, recalled_from_memory,
             cost_usd, tokens)
```

`CycleResult` is exactly the JSONL line the dashboard reads. Do not change its field
names without telling the other person — the dashboard parses it positionally by key.

---

## Environment

One `.env` at the repo root. Never commit it — `.env` is gitignored.

```
# ours
CONCIERGE_URL=https://concierge.squidgy.net
SKILL_API_KEY=

# sponsors
PIONEER_API_KEY=          # agent.pioneer.ai -> Billing -> Get Pro -> code HACKATHONSF0724
SENSO_API_KEY=            # docs.senso.ai/sign-up -> /api-keys  ($100 credit)
GEMINI_API_KEY=           # aistudio.google.com, free
REPLAY_API_KEY=           # replay.io settings, access code HACKATHON  (lqa_...)
BAND_REST_URL=https://app.band.ai/
BAND_WS_URL=wss://app.band.ai/api/v1/socket/websocket
BAND_API_KEY=             # per-agent, from app.band.ai/agents  (Pro code TOKENBAND26)
```

Actian runs locally, no key:

```bash
docker run -d --name vectorai \
  -v ./local_data:/var/lib/actian-vectorai \
  -p 6573-6575:6573-6575 \
  -e ACTIAN_VECTORAI_ACCEPT_EULA=YES \
  actian/vectorai:latest
```

---

## Rules that matter

1. **Citations must resolve.** A canon doc whose `file:line` doesn't exist is rejected, always. This is the guard against the agent poisoning its own knowledge base, and judges will ask about it.
2. **Promotion is gated on measured improvement.** Re-ask after writing; promote only if that question now scores better AND the rest of the golden set didn't regress. No score, no promotion.
3. **Never scan with Replay casually.** Free tier is 25 credits/month and one app scan costs ~20. `ReplayQA.create_project()` defaults to `dry_run=True` and refuses to spend unless explicitly told otherwise.
4. **Every graded miss posts to Pioneer feedback.** That's what makes their model improve on our traffic — it's half the pitch.
5. **The dashboard has no auth.** It's the Replay target and the submission URL.
