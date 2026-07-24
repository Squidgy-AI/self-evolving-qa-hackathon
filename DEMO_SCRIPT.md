# 3-Minute Live Demo Script

**URL (have it open, logged in, full screen):** https://sstudio.tailc6b458.ts.net/
**Second tab:** https://sstudio.tailc6b458.ts.net/dash/evolution  (the metrics/curve)

**Before you start:** click **Reset demo** (top right). This clears learned docs so the
first question genuinely misses. Do a full dry run once, then reset again.

No slides. You drive the whole thing from the one page.

---

## The 30-second frame (say this first)

> "You've all used tools like DeepWiki — point it at a codebase, ask a question in
> plain English, get an answer with a code reference. It's great. But it has one
> ceiling: **it never learns from its own failures.** Ask it something it can't
> answer, and it shrugs — today, tomorrow, forever. It reads the code; it never
> adds to what's known about the code.
>
> We gave it a fact-checker and a notebook. Watch."

---

## Beat 1 — it fails (0:30 → 0:55)

- Repo dropdown is already `fastapi/fastapi`. Question dropdown is already the
  WebSocket one. **Just click "Ask."**
- ~4 seconds. It comes back **miss** — "I couldn't find that in the indexed codebase."

> "FastAPI — a real, popular open-source codebase, on GitHub, so you can check
> everything I'm about to show you. It just failed to answer. A normal Q&A tool
> stops here."

## Beat 2 — you teach it (0:55 → 1:45)

- Click **👎**. A note box appears.
- Type a short hint (optional but shows the human-guidance angle), e.g.
  *"look at how websocket dependencies are solved vs http"*. Click **Teach it →**.
- It takes ~30 seconds. **Narrate while it runs:**

> "It's grading its own answer with a second, independent model — so it's not marking
> its own homework. It failed. So now it goes and researches the actual code, writes
> a short doc to answer the question — and here's the important part — **every single
> claim has to cite a real line of code that actually exists.** Then it re-asks the
> question to check the doc genuinely helped. If the citations don't resolve, or the
> answer doesn't improve, the doc is **thrown away.**"

## Beat 3 — it answers, and you can verify it (1:45 → 2:20)

- Result card shows **miss → grounded**, the new doc's title, and the citation(s) it
  checked, e.g. `fastapi/routing.py:1646`.
- Scroll the new answer — it's now specific and cited.

> "Same question, seconds later — now it answers, with a code reference. It taught
> itself the missing piece. And because this is a public repo, you can open that file
> on GitHub right now and confirm the line is real. It didn't make it up."

## Beat 4 — the guardrail (the winning moment) (2:20 → 2:45)

- If a rejection showed during your run, point at it. If not, say it anyway — it
  happens roughly half the time and you can show it in Q&A with another question.

> "The thing I actually care about: it **rejects about half the docs it writes.** If a
> citation points to a line that doesn't exist, or the answer doesn't measurably get
> better, the doc is deleted, not kept. That's the difference between a system that
> *self-improves* and an AI that just hallucinates new 'facts' with confidence.
> This one can't lie to itself — unverifiable knowledge doesn't survive."

## Beat 5 — the sponsors + close (2:45 → 3:00)

- Switch to the metrics tab (or just say it): the pass-rate line climbing, docs
  written vs. rejected.

> "Under the hood: **Gemini** is the independent fact-checker, **Pioneer** does the
> research and gets told when it was wrong so its own model retrains on our
> corrections, **Senso** stores the verified docs, and **Replay QA** tested this very
> dashboard and found a bug we fixed. Five tools, one loop: a codebase tool that gets
> permanently better every time it fails — and only keeps what it can prove."

---

## If something goes wrong live

- **A question doesn't improve (stays miss/partial):** that's real and it's fine —
  *"and there's a case where the code it found wasn't enough — it correctly refused to
  claim it solved it. That honesty is the point."* Then pick the next question in the
  dropdown (they're ordered most-reliable first).
- **The learn step is slow:** keep narrating the steps (grade → research → check
  citations → re-verify). Silence is the only failure.
- **A judge opens a citation and it's slightly off-topic:** *"The guard verifies every
  cited line exists — that kills the #1 failure mode, invented file paths. Verifying
  the line is semantically the best one is the next layer."* Do not overclaim citation
  precision.
- **The Studio URL is down:** fall back to the Render URL (if deployed) or run it
  locally on the laptop: `uvicorn dashboard.live:app --port 8138` with the `.env` keys.

## If asked "is this just for FastAPI / a toy?"

> "No — type any public GitHub repo into that box and it clones and runs live. We
> demo on FastAPI because it's public so you can check us. Point it at your own
> private codebase and it's the same loop."

## The one-line pitch (for the pitch, the elevator, the Devpost blurb)

> "A codebase Q&A tool that teaches itself the answers it doesn't know — writing its
> own documentation, but only keeping what it can prove against real code."
