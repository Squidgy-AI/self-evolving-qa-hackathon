# Self-Learning QA Bug Fixing Framework - Overview

## Concept

Extend the existing Q&A Evolution Loop framework to automatically debug, fix, and learn from bugs reported on app.squidgy.ai.

---

## Architecture Flow

```
Bug Report + Repro Steps + Expected Outcome
  ↓
CHECK MEMORY FIRST (Self-Learning!)
  ├─ Similar bug fixed before?
  │    ↓ YES
  │    Recall: Root cause + Fix + Screenshots
  │    Apply fix → Test → Report → Done! (FREE, instant)
  │
  └─ NO similar bug found
       ↓
┌─────────────────────────────────────────┐
│  INTERNAL LOOP (QA Evaluator + Grader)  │
│                                         │
│  1. QA Evaluator (Playwright MCP)       │
│     - Follow repro steps automatically  │
│     - Capture screenshot per action     │
│     - Store in temp/bug-{id}/           │
│     - Get actual outcome                │
│                                         │
│  2. QA Grader (Prompt-Driven)           │
│     - Compare: Expected vs Actual       │
│     - Match? → BREAK loop               │
│     - No match? → Continue              │
│                                         │
│  3. Root Cause Analysis                 │
│     - Debug via repos:                  │
│       • Backend code repo               │
│       • Frontend code repo              │
│       • Citadel (or n8n)                │
│     - Prompt-driven code analysis       │
│     - Identify file:line of issue       │
│                                         │
│  4. Suggest Fix                         │
│     - Generate code changes             │
│     - Create test cases                 │
│                                         │
│  5. Apply Fix (in test env)             │
│     - Apply suggested changes           │
│                                         │
│  6. Re-run QA Evaluator                 │
│     - Test the fix with Playwright      │
│     - Capture new screenshots           │
│     - Get new actual outcome            │
│                                         │
│  REPEAT until Expected = Actual         │
└─────────────────────────────────────────┘
  ↓ (Loop satisfied, break)

Gemini Judge:
  - Grades the final solution
  - Three grades: grounded / partial / miss
  - Validates quality of fix

  ↓
Verify:
  - Re-run all tests
  - Check for regressions on other features
  - Validate screenshots match expected outcome
  - Ensure fix is reproducible

  ↓
Promote/Reject:

  ├─ GROUNDED → PROMOTE
  │    ├─ Store in Memory (Actian/Vector DB)
  │    │   • Bug pattern (error message, symptoms)
  │    │   • Root cause (file:line)
  │    │   • Fix (code changes/diff)
  │    │   • Screenshots (before/after)
  │    │   • Repro steps
  │    │
  │    ├─ Document in data/canon/bugs/*.md
  │    │   • Full bug report
  │    │   • Root cause analysis
  │    │   • Solution with citations
  │    │   • Test coverage
  │    │
  │    ├─ Post feedback to Pioneer
  │    │   • Model learns debugging patterns
  │    │
  │    └─ NOTIFY HUMANS (NO AUTO-DEPLOY!)
  │         └─ Send Roam Message to dev team (@all)
  │
  │              Message: [Auto-QA] Bug Fixed: {bug_title}
  │
  │              Bug Report: #{id}
  │              Root Cause: {cause} ({file}:{line})
  │              Fix Verified: ✅ Grounded
  │
  │              Proposed Changes:
  │              - {file}:{lines} (+ diff)
  │              - {test_file} (new test added)
  │
  │              Screenshots:
  │              - Before: [temp/bug-{id}/before.png]
  │              - After: [temp/bug-{id}/after.png]
  │
  │              Test Results: All passed
  │              Regressions: None detected
  │
  │              Suggested Action: Review and deploy to staging
  │
  │              Documentation: data/canon/bugs/{slug}.md
  │
  └─ PARTIAL/MISS → REJECT
       ├─ Store as failed attempt (don't retry same approach)
       │
       └─ Send notification:
            "Bug analysis incomplete. Manual investigation needed."
            + Attach partial analysis + screenshots
```

---

## What Gets Sent to Humans

### Via Roam Message (using existing Roam MCP):

```
@all 🐛 Bug Analysis Complete

**Status**: ✅ Fix verified (grounded)

**Bug**: Login button not responding after 1 hour
**Root Cause**: CSRF token expiration in middleware
**Fix**: Added token refresh logic

**Files Changed**:
• app/auth/middleware.py:156-160
• tests/auth/test_csrf.py (new)

**Test Results**: ✅ All passed
**Regressions**: ✅ None

**Next Steps**:
Review changes and approve for staging deployment

📎 Full report: /data/canon/bugs/login-button-csrf-token.md
📸 Screenshots: {count} captured
```

---

## Human Decision Points

1. **Review** the analysis and proposed fix
2. **Approve** or reject the changes
3. **Deploy** manually if approved
4. **Feedback** if fix needs adjustments

**No automatic code changes to production!**

---

## Self-Learning Mechanisms

### 1. Memory Recall
```
Next bug: "Login button not working"
  ↓
Check Memory:
  → Found similar bug from 2 weeks ago
  → Root cause: CSRF token expired
  → Fix: Refresh token on page load
  → Apply same fix
  → Test → Works!
  → 0 research needed, instant fix
```

### 2. Pattern Learning
```
After 10 bugs fixed:
  • 5 were "CSRF token issues" → Common pattern
  • 3 were "API timeout" → Check this first
  • 2 were "CSS z-index" → Known issue

Next bug:
  → Check most common patterns first
  → Faster root cause identification
```

### 3. Continuous Improvement
```
Cycle 1: Bug X → Research 10 files → Fix in 5 min
Cycle 5: Same bug Y → Recall from memory → Fix in 30 sec
Cycle 10: Playwright learned common flows → Fewer screenshots needed
```

---

## Key Features

### 1. Runs Locally
- QA Framework executes on local machine
- Uses local Playwright MCP server
- Access to local code repositories
- Secure environment for testing

### 2. Prompt-Driven
- QA Evaluator: LLM-guided browser automation
- QA Grader: LLM-based outcome comparison
- Root Cause Analysis: LLM debugs code with context

### 3. CRON Automated
- Scheduled bug checks (Guild AI)
- Monitors bug tracker
- Auto-processes new bugs
- Sends reports when done

### 4. Safe & Human-Supervised
- No automatic deployments
- Human review required
- Notification before any changes
- Full audit trail with screenshots

---

## Parallel to Q&A System

| **Q&A System** | **QA Bug System** |
|----------------|-------------------|
| Question | Bug Report |
| DeepWiki Answer | QA Evaluator (Playwright) |
| Gemini Judge | Gemini Judge |
| Research (grep repo) | Root Cause Analysis (debug repos) |
| Write Doc | Write Fix + Documentation |
| Verify (citations) | Verify (screenshots + regression tests) |
| Promote (Senso) | Promote (Notify humans) |
| Memory Recall | Memory Recall (bug patterns) |
| Pioneer Feedback | Pioneer Feedback (model learns debugging) |

---

## Expected Outcomes

### Cycle 1 (First 10 bugs):
- 10 bugs reported
- 10 root causes found
- 6 fixes verified (grounded)
- 4 partial solutions (need human help)
- 6 stored in memory

### Cycle 5 (After 50 bugs):
- 10 bugs reported
- 4 recalled from memory (instant fix)
- 6 new bugs debugged
- 8 fixes verified (learning from patterns)
- 2 partial solutions

### Cycle 10 (After 100 bugs):
- 10 bugs reported
- 7 recalled from memory
- 3 new bugs debugged
- 9 fixes verified (system is expert now)
- 1 partial solution

**Result**: System learns common bug patterns and fixes them faster over time.
