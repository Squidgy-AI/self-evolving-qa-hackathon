# Soma — start here

Written 12:55 PDT, updated 14:45. Submission is **16:30 PDT on Devpost**. Read this
top to bottom once, then start at "Your tasks".

> ### CHANGED at 14:45 — the demo target is now `fastapi/fastapi`, not Squidgy code
>
> **Do not point anything at `squidgy-deepwiki-api.onrender.com` in the repo, the
> demo video, or the Devpost entry.** That service has **no authentication** and
> indexes our **private** repos — `/auth/status` returns `{"auth_required": false}`
> and it will answer questions about `squidgy_updated_backend` to anyone who knows
> the hostname. Publishing that URL would advertise it to a room full of engineers.
> (Worth flagging to whoever owns that Render service — it's a live exposure
> independent of this hackathon.)
>
> The loop now runs against a **local clone of the public `fastapi/fastapi` repo**.
> This is also just better for judging: they can open the cited file and verify it
> themselves. Verified working — 10/10 citations resolve to real lines.
>
> `git clone --depth 1 https://github.com/fastapi/fastapi.git ~/Git/fastapi`

---

## What we're building

An agent that **improves a live production Q&A system without anyone touching it**.

The system is **squidgy-deepwiki** (`https://concierge-deepwiki.onrender.com`) — the
RAG service that answers questions about our real repos (`squidgy_updated_backend`,
`squidgy_updated_ui`, `N8N-Workflows`, `squidgy-docs-hub`, `squidgy_marketing`).

The loop, once per cycle:

```
ask deepwiki a question
  -> grade the answer                      (Gemini, an independent judge)
  -> if it's a miss:
       recall a fix we already found       (Actian vector memory — free, no research)
       else research the repo              (Pioneer-routed model)
       write a doc with file:line citations
       VERIFY  - every citation must resolve to a real line
               - re-ask; the score must actually improve
       promote -> publish to Senso, remember it worked
       reject  -> bin it, remember it didn't
  -> post every miss to Pioneer /feedback  (their model retrains on our corrections)
  -> append the cycle to data/runs.jsonl   (the dashboard chart)
```

**Two rules make this defensible rather than a hallucination amplifier**, and judges
will ask about both:

1. A citation that doesn't resolve to a real file and line = automatic rejection.
2. No measured improvement = no promotion. Ever.

Your Tom & Jerry work is not wasted — the BAND plumbing is the hard part and it's
done. The four roles below are that same wiring, renamed.

---

## Current state

**Working and pushed** (branch `engine/evolution-loop`):

| Thing | Where | Status |
|---|---|---|
| The loop | `engine/loop.py` | Runs end to end. Validated: promoted 1 real doc, correctly rejected 1. |
| Data model | `engine/models.py` | `CycleResult` is the JSONL line the dashboard reads |
| Dashboard | `dashboard/app.py` | Verified 200 on all routes, survives bad data, no dead links |
| Pioneer | `clients/pioneer_client.py` | Built off their live `openapi.json` |
| Senso | `clients/senso_client.py` | Base URL + auth dug out of their quickstart repo source |
| Actian | `clients/memory_client.py` | Qdrant-compatible, needs the docker container |
| Replay | `clients/replay_client.py` | Built off their live `openapi.json`. **Credit-guarded** |
| Gemini judge | `clients/judge.py` | Independent grader |
| Fallbacks | `clients/local_answerer.py`, `clients/claude_cli.py` | So the demo survives an outage |

**Not done — this is the gap:**

- Nothing has a real API key yet, so every sponsor path is running on fallbacks.
- BAND agents are still Tom and Jerry.
- No Guild trigger, so "no manual intervention" isn't yet demonstrable.
- Dashboard isn't deployed to a public URL, so Replay can't scan it.

---

## Your tasks

### 1. Rename the BAND agents to the four loop roles  *(highest value — it's the demo)*

Each role calls exactly one function. Nothing else about the loop needs to be
understood to wire this up.

```python
from engine.loop import grade, research, verify, promote, run_cycle
```

| Agent | Calls | Does |
|---|---|---|
| `@Grader` | `grade(question) -> Grade` | asks deepwiki, scores the answer |
| `@Researcher` | `research(gap) -> Canon` | recalls a past fix, else derives a new doc |
| `@Verifier` | `verify(canon, before) -> Verification` | checks citations, re-asks, measures |
| `@Publisher` | `promote(canon, verification) -> PromoteResult` | publishes or bins it |

The point of putting these in a BAND room isn't architecture — it's that judges
**watch the handoffs happen live** instead of reading log output. `@Grader` finds a
miss and @-mentions `@Researcher`, and so on round the loop. That's the money shot.

### 2. Guild cron trigger

Guild is free right now. Create a scheduled trigger that calls `run_cycle()` every
few minutes. That trigger is our *evidence* for the "acts on real-time data without
manual intervention" criterion — it's worth more than another integration.

### 3. Deploy the dashboard publicly

Render, no env vars needed:

- Build: `pip install -r dashboard/requirements.txt`
- Start: `uvicorn dashboard.app:app --host 0.0.0.0 --port $PORT`

**It must have no auth** — Replay QA has to crawl it, and the Devpost submission
asks for a working URL. Send me the URL when it's up.

---

## Accounts and keys — these need a human, I can't create them

Put everything in `.env` at the repo root (gitignored). Template is `.env.example`.

| Service | Where | Code / note |
|---|---|---|
| **Gemini** | aistudio.google.com → "Get API key" | Free, no card, 60 seconds. **Do this first** — it unblocks the judge. |
| **Pioneer** | agent.pioneer.ai → Billing → Get Pro | Promo **`HACKATHONSF0724`**. Stripe asks you to "subscribe with obligation to pay" — that's a formality, no card needed. *Cancel it after the event.* |
| **Senso** | docs.senso.ai/sign-up → /api-keys | $100 signup credit |
| **Replay** | replay.io → Settings → API Keys | Access code **`HACKATHON`** in Replay settings. Key looks like `lqa_...` |
| **BAND** | app.band.ai → Agents | Pro via **`TOKENBAND26`**. You already have agents registered — reuse those IDs. |
| **Guild** | app.guild.ai | Free tier |
| **deepwiki** | Render env of the deepwiki service, or ask Hardeep | `DEEPWIKI_API_KEY` — the `/chat/completions/stream` endpoint returns 401 without it. **Blocking for the real demo.** |

**Actian needs no account** — it's a local container:

```bash
docker run -d --name vectorai \
  -v ./local_data:/var/lib/actian-vectorai \
  -p 6573-6575:6573-6575 \
  -e ACTIAN_VECTORAI_ACCEPT_EULA=YES \
  actian/vectorai:latest
```

**Replay credit warning:** free tier is 25 credits/month and a scan costs ~10–20
(`budget` param, defaults to 20). You get roughly one good scan plus one
verification scan. `create_project()` defaults to `dry_run=True` and refuses to
spend unless explicitly told to. Don't remove that guard.

---

## Running it

```bash
git fetch && git checkout engine/evolution-loop
python3 -m venv .venv-engine && ./.venv-engine/bin/pip install -r requirements-engine.txt
cp .env.example .env        # fill in keys

./.venv-engine/bin/python -m engine.loop        # one cycle
./.venv-engine/bin/python clients/judge.py      # smoke-test any single client
uvicorn dashboard.app:app --port 8000           # dashboard at /evolution
```

Every client has a `smoke()` under `if __name__ == "__main__"` — run the file
directly to check one integration in isolation.

---

## Don't collide

| Directory | Owner |
|---|---|
| `agents/`, `app/` | you |
| `clients/`, `engine/`, `dashboard/` | me |
| `data/` | shared, gitignored |

Branch from `engine/evolution-loop`, not `main`. Full detail in `CONTRACT.md`.

---

## The demo (3 minutes, live, no slides)

1. Show the dashboard: pass rate over previous cycles, already climbing.
2. Ask deepwiki something it gets wrong. It hedges.
3. Trigger a cycle — or better, let the Guild cron fire on its own.
4. Watch the BAND room: `@Grader` calls it a miss → `@Researcher` reads the repo →
   `@Verifier` checks every citation resolves → `@Publisher` publishes to Senso.
5. Ask the same question again. Correct, cited answer.
6. Back to the dashboard — the line moved.
7. One sentence on the guard: *"it rejected two of five docs it wrote, because the
   citations didn't resolve or the score didn't improve."*

Tick **every** sponsor prize on the Devpost form or we're not considered for them.
