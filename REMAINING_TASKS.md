# Remaining Tasks - Evolution Loop Hackathon

**Last Updated**: July 24, 2026 - 15:45 PDT
**Deadline**: 16:30 PDT (45 minutes remaining)
**Status**: ✅ All code complete, only setup tasks remaining

---

## ✅ COMPLETED (All Coding Done)

### Code & Implementation (100% Complete)
- ✅ 4 BAND agents (@Grader, @Researcher, @Verifier, @Publisher) - `agents/`
- ✅ Guild AI cron trigger - `guild.yml`
- ✅ Render deployment config - `render.yaml`
- ✅ All integration clients (Gemini, Pioneer, Senso, Actian, Replay, BAND) - `clients/`
- ✅ Evolution loop engine - `engine/loop.py`
- ✅ Dashboard - `dashboard/app.py`
- ✅ Setup automation - `quick_setup.sh`, `launch_agents.sh`
- ✅ Documentation - SETH.md, STATUS.md, LOCAL_TEST_RESULTS.md, etc.

### Testing
- ✅ Local test passed - system runs successfully
- ✅ All 8 questions graded
- ✅ DeepWiki connection verified
- ✅ Fallback system validated
- ✅ FastAPI repo cloned for citation validation

### Repository
- ✅ All changes pushed to GitHub
- ✅ Branch: `engine/evolution-loop`
- ✅ Latest commit: 5eea964
- ✅ GitHub: https://github.com/Squidgy-AI/self-evolving-qa-hackathon

---

## 🔴 CRITICAL PATH (Must Do Before Demo)

### 1. Get Gemini API Key ⏱️ 1 minute
**Priority**: CRITICAL - Unblocks grading
**URL**: https://aistudio.google.com/app/apikey

**Steps**:
1. Click "Create API key"
2. Copy the key
3. Add to `.env`: `GEMINI_API_KEY=your_key_here`

**Unlocks**:
- ✓ Independent grading with Gemini judge
- ✓ Proper grounded/partial/miss scoring
- ✓ Citation validity checking

**Current Status**: ❌ Not set (using heuristic fallback)

---

### 2. Get Pioneer API Key ⏱️ 5 minutes
**Priority**: CRITICAL - Unblocks research & feedback loop
**URL**: https://agent.pioneer.ai

**Steps**:
1. Sign up / log in
2. Go to Billing → Get Pro
3. Use promo code: `HACKATHONSF0724`
4. Copy API key
5. Add to `.env`: `PIONEER_API_KEY=your_key_here`

**Unlocks**:
- ✓ Research via Pioneer-routed models
- ✓ Feedback loop for Hermes retraining
- ✓ Automatic model improvement
- ✓ The core "self-evolution" feature

**Current Status**: ❌ Not set (research fails)

---

### 3. Test Full Cycle ⏱️ 2 minutes
**Priority**: CRITICAL - Verify everything works
**Command**: `python3 -m engine.loop`

**Steps**:
```bash
cd ~/CascadeProjects/SelfBuildingAgent/self-evolving-qa-hackathon
python3 -m engine.loop
```

**Expected Output**:
```
=== cycle over 8 questions ===
  [grounded] How does the dependency injection cache key work...
  [grounded] How does FastAPI decide whether a route handler runs...
  ...
  + promoted: How does the dependency injection cache key work
  + promoted: How does FastAPI decide whether a route handler runs
=== score 0.38 -> 0.75 | pass 3/8 -> 6/8, 2 promoted, 1 rejected ===
```

**Verify**:
- [ ] No errors in console
- [ ] `data/runs.jsonl` created with cycle data
- [ ] `data/canon/*.md` files created (promoted docs)
- [ ] Score improved (before → after)

**Current Status**: ⚠️ Tested with fallbacks, needs API keys for full test

---

### 4. Deploy Dashboard to Render ⏱️ 5 minutes
**Priority**: CRITICAL - Required for Devpost submission
**URL**: https://dashboard.render.com/blueprints

**Steps**:
1. Go to Render dashboard
2. Click "New Blueprint Instance"
3. Connect GitHub repo: `Squidgy-AI/self-evolving-qa-hackathon`
4. Select branch: `engine/evolution-loop`
5. Render reads `render.yaml` and auto-deploys
6. Wait ~3 minutes for deployment
7. Copy the public URL

**Result**: `https://<app-name>.onrender.com/evolution`

**Verify**:
- [ ] Dashboard loads in browser
- [ ] `/health` endpoint returns `{"status": "ok"}`
- [ ] `/evolution` shows charts and cycle table
- [ ] No auth required (publicly accessible)

**Current Status**: ❌ Not deployed (config ready)

---

### 5. Rehearse Demo ⏱️ 10 minutes
**Priority**: CRITICAL - Must be smooth for judges

**Demo Script** (3 minutes):
```
[0:00-0:30] Problem
- Show DeepWiki giving vague answer
- "Sometimes misses details"

[0:30-1:30] Evolution Loop
- Run: python3 -m engine.loop
- Show console or BAND room
- @Grader finds miss → @Researcher generates doc → @Verifier validates → @Publisher publishes

[1:30-2:15] Proof
- Show data/runs.jsonl: score improved
- Dashboard: pass rate climbing
- Re-ask question: now grounded with citations

[2:15-2:45] Safety
- Point to rejected doc (citations didn't resolve)
- Show engine/loop.py line 309: validate_citations()
- "No improvement = no promotion"

[2:45-3:00] Automation
- Guild cron: runs every 5 min
- Pioneer feedback: retrains model
- "No manual intervention"
```

**Practice**:
- [ ] Time the demo (must be under 3 minutes)
- [ ] Prepare for Q&A
- [ ] Know the code (especially `engine/loop.py`)
- [ ] Have backup video ready

**Current Status**: ❌ Not rehearsed

---

## 🟡 OPTIONAL (Nice to Have)

### 6. Get Senso API Key ⏱️ 5 minutes
**Priority**: OPTIONAL - System works without it
**URL**: https://docs.senso.ai/sign-up

**Benefits**:
- Publishes verified docs to web
- Makes content discoverable by ChatGPT/Perplexity
- Shows external action criterion

**Fallback**: Docs stored locally in `data/canon/` (still works for demo)

**Current Status**: ❌ Not set (using local-only fallback)

---

### 7. Register BAND Agents ⏱️ 10 minutes
**Priority**: OPTIONAL - Demo works without it
**URL**: https://app.band.ai

**Steps**:
1. Go to app.band.ai
2. Create room: "Evolution Loop"
3. Register 4 agents or reuse Tom/Jerry agent IDs
4. Update agent config files if needed
5. Run: `./launch_agents.sh`

**Benefits**:
- Judges watch agents collaborate live
- @-mentions show workflow visually
- Better demo experience

**Fallback**: Show console output instead (still demonstrates system)

**Current Status**: ❌ Not registered

---

### 8. Install Guild AI ⏱️ 5 minutes
**Priority**: OPTIONAL - Shows automation
**Command**: `pip install guild && guild init`

**Steps**:
```bash
pip install guild
guild init
guild serve  # Starts scheduler
```

**Benefits**:
- Dashboard at http://localhost:6060
- Automated 5-min cycles
- Metrics tracking over time
- Proof of "no manual intervention"

**Fallback**: Manual runs still work (`python3 -m engine.loop`)

**Current Status**: ❌ Not installed

---

### 9. Start Actian Vector Database ⏱️ 2 minutes
**Priority**: OPTIONAL - Memory disabled without it
**Command**: Docker run

**Steps**:
```bash
docker run -d --name vectorai \
  -p 6573-6575:6573-6575 \
  -e ACTIAN_VECTORAI_ACCEPT_EULA=YES \
  actian/vectorai:latest
```

**Benefits**:
- Memory recall (reuse past fixes)
- Reduces research costs
- Shows persistent memory criterion

**Fallback**: System works without memory, just no recall optimization

**Current Status**: ❌ Not running

---

## ⏰ Time Budget (45 minutes remaining)

### Minimum Viable Demo (13 minutes)
```
✓ Get Gemini API key           1 min
✓ Get Pioneer API key          5 min
✓ Test full cycle              2 min
✓ Deploy dashboard             5 min
─────────────────────────────────────
Total:                        13 min
Buffer:                       32 min ← Plenty of time!
```

### Optimal Demo (33 minutes)
```
✓ Get Gemini API key           1 min
✓ Get Pioneer API key          5 min
✓ Test full cycle              2 min
✓ Deploy dashboard             5 min
✓ Rehearse demo               10 min
✓ Get Senso API key            5 min
✓ Register BAND agents        10 min (optional)
✓ Install Guild AI             5 min (optional)
─────────────────────────────────────
Total:                        33 min
Buffer:                       12 min
```

---

## 📋 Pre-Demo Checklist

**Before Submission (30 min)**:
- [ ] Gemini API key added to `.env`
- [ ] Pioneer API key added to `.env`
- [ ] Full cycle tested successfully
- [ ] Dashboard deployed to Render
- [ ] Public dashboard URL saved
- [ ] Demo rehearsed (under 3 minutes)
- [ ] Backup video recorded

**Optional (if time)**:
- [ ] Senso API key added
- [ ] BAND agents registered
- [ ] Guild AI installed and running
- [ ] Actian Vector database started

**Devpost Submission**:
- [ ] Title: "Self-Evolving QA Agent"
- [ ] Description: From STATUS.md
- [ ] Video: 3-min demo
- [ ] GitHub: https://github.com/Squidgy-AI/self-evolving-qa-hackathon
- [ ] Dashboard URL: From Render deployment
- [ ] Check ALL 6 sponsor boxes

---

## 🚨 Common Issues & Solutions

### Issue: "GEMINI_API_KEY not found"
```bash
# Solution: Add to .env and source it
echo 'GEMINI_API_KEY=your_key' >> .env
source .env
```

### Issue: "Pioneer API returns 401"
```bash
# Solution: Verify Pro plan is active
# Check: https://agent.pioneer.ai/billing
# Regenerate key if needed
```

### Issue: "Dashboard shows empty"
```bash
# Solution: Run at least one cycle first
python3 -m engine.loop
# Dashboard reads from data/runs.jsonl
```

### Issue: "Research still failing"
```bash
# Solution: Verify Pioneer API key is set
echo $PIONEER_API_KEY  # Should print the key
# If empty, add to .env and source it
```

---

## 📊 Success Criteria

### Must Have (Critical Path)
- [x] Code complete and pushed ✓
- [ ] Gemini API key configured
- [ ] Pioneer API key configured
- [ ] One successful full cycle
- [ ] Dashboard deployed publicly
- [ ] Demo rehearsed

### Nice to Have (Optional)
- [ ] Senso API key (web publishing)
- [ ] BAND agents (live collaboration)
- [ ] Guild AI (automated runs)
- [ ] Actian Vector (memory recall)

### Proof for Judges
- [ ] Console output showing evolution cycle
- [ ] `data/runs.jsonl` with improving scores
- [ ] Dashboard chart showing pass rate climbing
- [ ] Rejected doc proving safety guardrails
- [ ] Code walkthrough of `engine/loop.py`

---

## 🎯 Next Actions (In Order)

1. **NOW** (1 min): Get Gemini API key
2. **NEXT** (5 min): Get Pioneer API key
3. **THEN** (2 min): Test full cycle
4. **AFTER** (5 min): Deploy dashboard
5. **FINALLY** (10 min): Rehearse demo

**Total**: 23 minutes
**Remaining**: 22 minutes of buffer

---

## ✅ Confidence Level

**Code Quality**: 🟢 Excellent - All tasks complete, tested locally
**Time Remaining**: 🟢 Plenty - 2x the time needed
**Risk Level**: 🟢 Low - Only setup tasks, no more coding
**Demo Readiness**: 🟡 Pending - Needs API keys + rehearsal

**Overall**: 🟢 **READY TO GO** - Just execute the remaining tasks!

---

## 📞 Quick Reference

**GitHub**: https://github.com/Squidgy-AI/self-evolving-qa-hackathon/tree/engine/evolution-loop

**Key Files**:
- `SETH.md` - Complete handover for Seth
- `STATUS.md` - Project status
- `LOCAL_TEST_RESULTS.md` - Test validation
- `.env` - Environment variables (add keys here)

**Commands**:
```bash
# Test cycle
python3 -m engine.loop

# Launch agents (if registered)
./launch_agents.sh

# Start Guild AI (if installed)
guild serve

# Check dashboard locally
uvicorn dashboard.app:app --port 8000
```

---

**Last Updated**: July 24, 2026 - 15:45 PDT
**Next Update**: After API keys are configured
**Owner**: Seth (with Soma's code)
