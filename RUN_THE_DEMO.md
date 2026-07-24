# Run the demo — everything you need

Last verified 15:58 PDT. All six sponsors live. Two demo screens, both working.

---

## 1. Links

| What | Link |
|---|---|
| **Interactive demo** (main screen) | https://sstudio.tailc6b458.ts.net/ |
| **Metrics dashboard** (the curve) | https://sstudio.tailc6b458.ts.net/dash/evolution |
| **BAND room** (second screen) | https://app.band.ai/chat/989029da-3bd2-421f-92cb-fed2464bbe73 |
| **Repo** (submit this) | https://github.com/Squidgy-AI/self-evolving-qa-hackathon |
| Branch with everything | `engine/evolution-loop` |
| Demo script (what to say) | [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) |
| Interface contract | [`CONTRACT.md`](CONTRACT.md) |

⚠️ The two `sstudio.*` URLs are served from the Mac Studio in the office. **Don't let
it sleep and don't quit Docker Desktop.** If you want independence from that machine,
deploy to Render (see §5).

---

## 2. Before you present — 60 seconds

1. Open https://sstudio.tailc6b458.ts.net/ and click **Reset demo** (top right).
   Without this, the questions are already learned and there's no before/after.
2. Open the BAND room in a second tab.
3. Have a terminal ready in the repo (only needed for the BAND screen).

---

## 3. The main demo (3 min, no slides)

Full narration is in [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md). Short version:

1. **Frame it** — "tools like DeepWiki answer questions about a codebase, but they
   never learn from their own failures. We gave it a fact-checker and a notebook."
2. **Ask** — dropdowns are pre-filled (repo `fastapi/fastapi`, first question).
   Click **Ask** → comes back **miss** in ~4s.
3. **Thumbs down** → optionally type a hint → **Teach it →**. Takes ~30s; narrate:
   *"it's grading itself with an independent model, researching the real code,
   writing a doc where every claim must cite a line that actually exists, then
   re-asking to check the doc genuinely helped."*
4. **Result** — **miss → grounded**, with the citations it verified. Judges can open
   that file on GitHub and confirm the line is real.
5. **The winning line** — *"it rejects about half the docs it writes. If a citation
   doesn't resolve or the answer doesn't measurably improve, the doc is deleted. That's
   the difference between self-improvement and an AI confidently making things up."*

**Repo/question dropdowns take arrow keys.** "Custom…" reveals a text box — that's how
you point it at any other public repo live.

---

## 4. The BAND screen (second screen, optional but strong)

With the room open, run:

```bash
cd ~/Git/self-evolving-qa-hackathon
./demo_band.sh "How are WebSocket dependencies resolved differently from HTTP ones?"
```

Four registered agents post the same real loop as live handoffs:

```
🔎 @grader     → @researcher : graded it "miss" — it can't answer this
📚 @researcher → @verifier   : drafted a doc citing 7 lines, check it
✓  @verifier   → @publisher  : 7/7 citations resolve, miss → partial. Verified.
📤 @publisher  → @grader     : published — the tool can now answer this ✅
```

Not scripted — it's the genuine `grade → research → verify → promote` functions, each
agent posting with its own key. It auto-resets so it always shows a fresh miss.

Say: *"same loop, as a team of agents collaborating in real time — you're watching them
actually do it."*

---

## 5. Optional: deploy to Render (removes the Studio dependency)

1. https://dashboard.render.com/blueprints → connect
   `Squidgy-AI/self-evolving-qa-hackathon`, branch `engine/evolution-loop`.
2. It reads `render.yaml` (already set to serve the interactive app).
3. In Render's **Environment** tab add: `GEMINI_API_KEY`, `PIONEER_API_KEY`,
   `SENSO_API_KEY`. (Actian is local-only, so recall goes quiet in the cloud —
   everything else works.)
4. Use `https://<app>.onrender.com/` as the submission URL instead.

---

## 6. Devpost submission

- **Repo:** https://github.com/Squidgy-AI/self-evolving-qa-hackathon (branch
  `engine/evolution-loop` — or merge to `main` first)
- **Working URL:** https://sstudio.tailc6b458.ts.net/
- **Video:** 3 min, screen recording of §3 (+ §4 if you have time)
- **Tick every sponsor prize** or you're not considered for them.

**One-liner:** *"A codebase Q&A tool that teaches itself the answers it doesn't know —
writing its own documentation, but only keeping what it can prove against real code."*

**Sponsors and what each actually does:**

| Sponsor | Role in the loop |
|---|---|
| **Gemini** (DeepMind) | Independent judge — grades every answer grounded/partial/miss. Deliberately a different model family from the answerer, so it isn't marking its own homework. |
| **Pioneer** (Fastino) | Researches the gap; every graded failure posts to `/inferences/{id}/feedback` so their model retrains on our corrections. |
| **Senso** | Canon store — verified docs are ingested, embedded and searchable. |
| **Actian VectorAI** | Experience memory. **Proven:** cycle 1 researched a gap; cycle 2 (doc deleted, memory kept) recalled the prior fix with zero research. |
| **Replay QA** | Scanned this dashboard, found a real accessibility bug (missing `<main>`), we fixed it and marked it resolved. |
| **BAND** | Four agents collaborating in a room as visible handoffs. |

---

## 7. Honest answers to likely judge questions

**"Is the improvement real or just a caching trick?"**
Real, and we tested exactly this. Grading is always a fresh ask + judge against the
docs currently on disk — no cached grades. An independent re-grade against the
persisted canon reproduced **0.88 vs a 0.38 baseline**. (We *found and fixed* a bug
where cached grades made the curve look like it climbed while the canon dir was empty.
Worth telling — it's the kind of thing most demos never check.)

**"How do you stop it poisoning its own knowledge base?"**
Two gates. Every cited `file:line` must exist in the repo, or the doc is rejected. And
the answer must measurably improve without regressing others. Roughly half the docs it
writes get thrown away.

**"Is the citation the *right* line?"**
Existence is verified — that kills the #1 failure mode, invented file paths. Verifying
semantic relevance is the next layer. **Don't overclaim this.**

**"Does it watch the repo and update itself automatically?"**
Not yet. It runs on trigger (a question, or a Guild cron). Next step is a git webhook
so a push re-validates every doc whose cited lines moved.

**"Only works on FastAPI?"**
No — type any public GitHub repo into the box and it clones and runs. FastAPI is the
demo because it's public, so judges can verify the citations themselves.

---

## 8. If something breaks live

| Problem | Fix |
|---|---|
| A question doesn't improve | That's real and fine — *"it correctly refused to claim it solved that."* Pick the next question (ordered most-reliable first). |
| Learn step feels slow (~30s) | Keep narrating the stages. Silence is the only failure. |
| `sstudio` URL down | Studio asleep. Use the Render URL, or run locally: `uvicorn dashboard.live:app --port 8138` with `.env` present. |
| Recall stops working | Docker died. `docker start vectorai`. The loop still runs without it. |
| BAND posts fail | Skip that screen — the main demo is self-sufficient. |

---

## 9. ⚠️ Security — do this after the event

**Two live keys were committed to this public repo earlier today** (in Soma's handover
docs) and remain in git history at commits `3c2056a` and `ed3f288`:

- a **Replay** API key (`lqa_…`)
- a **BAND** user key (`band_u_…`)

They're redacted in the current files, but history is public. **Treat both as
compromised and rotate them.**

Also, independent of this hackathon: **the internal deepwiki host has no
authentication** (`/auth/status` returns `{"auth_required": false}`) and will answer
questions about private repos to anyone who knows the hostname. It was referenced in
this public repo — now scrubbed — but **the endpoint itself should be locked down.**
Worth telling whoever owns that Render service.

Other cleanup: cancel the Pioneer Pro subscription; delete the FastAPI docs this demo
wrote into the company Senso KB (`senso content list` → delete); revoke the spare
Senso key `hackathon-loop`.
