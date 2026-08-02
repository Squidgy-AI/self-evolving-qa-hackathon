# Self-Learning QA Bug Fixing Framework - Deep Architecture Plan

**Version**: 1.0
**Date**: 2026-08-02
**Status**: Planning Phase

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Components](#architecture-components)
3. [Data Models](#data-models)
4. [Prompt Engineering](#prompt-engineering)
5. [MCP Configuration](#mcp-configuration)
6. [File Structure](#file-structure)
7. [Integration Points](#integration-points)
8. [Memory & Learning](#memory--learning)
9. [Notification System](#notification-system)
10. [Security & Safety](#security--safety)
11. [Performance Considerations](#performance-considerations)
12. [Monitoring & Observability](#monitoring--observability)

---

## 1. System Overview

### 1.1 Purpose

Extend the existing self-evolving Q&A framework to automatically:
- Reproduce bugs reported on app.squidgy.ai
- Capture visual evidence (screenshots)
- Analyze root causes via code repository access
- Propose verified fixes
- Learn from successful bug patterns
- Notify human developers for review

### 1.2 Design Principles

1. **No Auto-Deploy**: Human approval required before any code changes
2. **Local Execution**: Runs on developer machine with local MCP servers
3. **Prompt-Driven**: All logic driven by LLM prompts for flexibility
4. **Self-Learning**: Memory-based recall of similar bug patterns
5. **Safe Testing**: Isolated test environment, no production access
6. **Audit Trail**: Full screenshot + log history for every bug

### 1.3 Key Differences from Q&A System

| Aspect | Q&A System | QA Bug System |
|--------|------------|---------------|
| Input | Question (text) | Bug report + repro steps |
| Tool | DeepWiki (RAG) | Playwright (browser automation) |
| Output | Answer (text) | Fix (code changes) |
| Verification | Citation validation | Screenshot + regression tests |
| Safety | Can't break anything | **Must not auto-deploy** |
| Execution | Cloud/server | **Local machine** |

---

## 2. Architecture Components

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Bug Tracker                              │
│  (Linear, Jira, GitHub Issues, or Manual Entry)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Bug Report Processor                        │
│  - Parse bug template                                           │
│  - Extract: title, repro steps, expected outcome                │
│  - Assign bug ID                                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Memory Checker                             │
│  - Embed bug description (Gemini embeddings)                    │
│  - Search Actian VectorAI for similar bugs                      │
│  - If found (score > 0.85): Recall fix → Skip to Verify         │
│  - If not found: Continue to QA Loop                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    QA EVALUATOR + GRADER LOOP                   │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ QA Evaluator (Playwright MCP)                             │ │
│  │                                                           │ │
│  │  1. Launch browser (Chrome headless)                      │ │
│  │  2. Navigate to app.squidgy.ai                            │ │
│  │  3. Follow repro steps sequentially:                      │ │
│  │     - Step 1: "Click login button"                        │ │
│  │       → playwright.click('button[data-test="login"]')     │ │
│  │       → screenshot → temp/bug-{id}/step-1.png             │ │
│  │     - Step 2: "Enter credentials"                         │ │
│  │       → playwright.fill('input[name="email"]', ...)       │ │
│  │       → screenshot → temp/bug-{id}/step-2.png             │ │
│  │     - Step N: Final state                                 │ │
│  │       → screenshot → temp/bug-{id}/step-N-actual.png      │ │
│  │  4. Extract actual outcome:                               │ │
│  │     - DOM state, error messages, network logs             │ │
│  │  5. Return: ActualOutcome + screenshots                   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                             │                                   │
│                             ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ QA Grader (Prompt-Driven LLM)                             │ │
│  │                                                           │ │
│  │  Input:                                                   │ │
│  │    - Expected outcome (from bug report)                   │ │
│  │    - Actual outcome (from Playwright)                     │ │
│  │    - Screenshots (base64 encoded)                         │ │
│  │                                                           │ │
│  │  Prompt:                                                  │ │
│  │    "Compare expected vs actual. Do they match?"           │ │
│  │                                                           │ │
│  │  Output:                                                  │ │
│  │    - match: true/false                                    │ │
│  │    - reason: "Error message differs" / "UI matches"       │ │
│  │    - confidence: 0.0-1.0                                  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                             │                                   │
│                             ▼                                   │
│                      ┌──────────────┐                           │
│                      │ Match?       │                           │
│                      └──────┬───────┘                           │
│                             │                                   │
│              ┌──────────────┴──────────────┐                    │
│              │ YES                         │ NO                 │
│              ▼                             ▼                    │
│         BREAK LOOP                  ┌──────────────────────┐    │
│                                     │ Root Cause Analysis  │    │
│                                     │                      │    │
│                                     │ - Read error logs    │    │
│                                     │ - Analyze screenshots│    │
│                                     │ - Debug code repos   │    │
│                                     │ - Identify file:line │    │
│                                     │ - Suggest fix        │    │
│                                     └──────────┬───────────┘    │
│                                                │                │
│                                                ▼                │
│                                     ┌──────────────────────┐    │
│                                     │ Apply Fix (Test Env) │    │
│                                     │                      │    │
│                                     │ - Modify code files  │    │
│                                     │ - Create test cases  │    │
│                                     └──────────┬───────────┘    │
│                                                │                │
│                                                ▼                │
│                                         LOOP BACK TO             │
│                                         QA EVALUATOR             │
│                                         (Re-test fix)            │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Gemini Judge                              │
│  - Grades overall solution quality                              │
│  - Three verdicts: grounded / partial / miss                    │
│  - Evaluates: correctness, completeness, test coverage          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Verification                             │
│  - Re-run all existing tests (pytest/jest)                      │
│  - Check for regressions on other features                      │
│  - Validate screenshots match expected outcome                  │
│  - Ensure fix is reproducible (run 3x)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Promote / Reject                            │
│                                                                 │
│  IF grounded:                                                   │
│    ├─ Store in Memory (Actian)                                 │
│    ├─ Document in data/canon/bugs/{slug}.md                    │
│    ├─ Post feedback to Pioneer                                 │
│    └─ Send notification (Roam/Email)                           │
│                                                                 │
│  IF partial/miss:                                               │
│    ├─ Store as failed attempt                                  │
│    └─ Notify: "Manual investigation needed"                    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Core Components

#### 2.2.1 Bug Report Processor
**Location**: `qa_engine/bug_processor.py`

**Responsibilities**:
- Parse bug report template
- Extract structured data
- Validate required fields
- Assign unique bug ID

**Input**: Raw bug report (Markdown/JSON)
**Output**: `BugReport` dataclass

#### 2.2.2 QA Evaluator
**Location**: `qa_engine/evaluator.py`

**Responsibilities**:
- Control Playwright via MCP
- Execute reproduction steps
- Capture screenshots
- Extract actual outcomes
- Handle browser automation errors

**Dependencies**:
- Playwright MCP server (local)
- Chrome/Chromium browser

#### 2.2.3 QA Grader
**Location**: `qa_engine/grader.py`

**Responsibilities**:
- Compare expected vs actual outcomes
- Analyze screenshots with vision model
- Determine if bug is reproduced
- Provide reasoning for decision

**Prompt-Driven**: Uses LLM (Gemini/Claude) with vision

#### 2.2.4 Root Cause Analyzer
**Location**: `qa_engine/root_cause.py`

**Responsibilities**:
- Analyze error logs
- Search code repositories (backend/frontend/citadel)
- Identify file:line of issue
- Understand code context
- Suggest fix with explanation

**Code Access**:
```python
BACKEND_REPO = Path.home() / "Git/squidgy-backend"
FRONTEND_REPO = Path.home() / "Git/squidgy-frontend"
CITADEL_REPO = Path.home() / "Git/citadel"
```

#### 2.2.5 Fix Generator
**Location**: `qa_engine/fix_generator.py`

**Responsibilities**:
- Generate code changes based on root cause
- Create test cases for the fix
- Validate syntax/linting
- Generate diff for review

**Output**: `ProposedFix` with code diffs

#### 2.2.6 Memory Manager
**Location**: `qa_engine/memory.py`

**Responsibilities**:
- Embed bug descriptions
- Store/recall successful fixes
- Track bug patterns
- Prevent duplicate work

**Storage**: Actian VectorAI (reuses existing setup)

---

## 3. Data Models

### 3.1 Core Data Structures

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

@dataclass
class BugReport:
    """Parsed bug report from template"""
    id: str                        # bug-123
    title: str                     # "Login button not working"
    description: str               # Full description
    repro_steps: list[str]         # ["Click login", "Enter email", ...]
    expected_outcome: str          # "User should be logged in"
    environment: str               # "Production / Staging / Local"
    severity: Literal["critical", "high", "medium", "low"]
    reporter: str                  # email address
    reported_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Metadata
    url: str = ""                  # URL where bug occurs
    user_agent: str = ""           # Browser info
    attachments: list[str] = field(default_factory=list)  # User screenshots


@dataclass
class ReproStep:
    """Single step in reproduction sequence"""
    step_number: int
    action: str                    # "Click button", "Fill form", "Wait"
    selector: str | None           # CSS selector or None
    value: str | None              # Input value or None
    screenshot_path: str | None    # Path to screenshot after this step
    timestamp: float               # Execution time
    success: bool                  # Step completed successfully
    error: str | None              # Error message if failed


@dataclass
class ActualOutcome:
    """What actually happened during reproduction"""
    success: bool                  # Reproduction successful
    screenshots: list[str]         # Paths to all screenshots
    final_url: str                 # URL after all steps
    error_messages: list[str]      # JS errors, network errors, etc.
    dom_state: str                 # Final DOM snapshot
    network_logs: list[dict]       # Network requests/responses
    console_logs: list[str]        # Browser console output
    execution_time: float          # Total time in seconds

    def to_summary(self) -> str:
        """Human-readable summary for LLM"""
        return f"""
Reproduction Result: {'Success' if self.success else 'Failed'}
Final URL: {self.final_url}
Errors: {'; '.join(self.error_messages) if self.error_messages else 'None'}
Screenshots captured: {len(self.screenshots)}
Execution time: {self.execution_time:.2f}s
"""


@dataclass
class ComparisonResult:
    """QA Grader output: expected vs actual"""
    match: bool                    # Do they match?
    confidence: float              # 0.0-1.0
    reason: str                    # Explanation
    differences: list[str]         # List of specific differences
    verdict: Literal["reproduced", "not_reproduced", "unclear"]


@dataclass
class RootCause:
    """Identified root cause of bug"""
    file_path: str                 # relative/to/repo/file.py
    line_number: int               # Line where issue occurs
    repository: Literal["backend", "frontend", "citadel", "n8n"]
    error_type: str                # "TypeError", "CSRF token", etc.
    explanation: str               # Why this causes the bug
    code_context: str              # ±10 lines around the issue
    confidence: float              # 0.0-1.0

    # Supporting evidence
    stack_trace: str | None = None
    related_files: list[str] = field(default_factory=list)


@dataclass
class ProposedFix:
    """Suggested code changes"""
    root_cause: RootCause
    changes: list[dict]            # [{"file": "...", "diff": "...", "reason": "..."}]
    test_cases: list[str]          # New test code
    validation_steps: list[str]    # How to verify fix works
    estimated_risk: Literal["low", "medium", "high"]
    requires_human_review: bool

    def to_diff(self) -> str:
        """Generate unified diff for email"""
        return "\n\n".join(
            f"--- {c['file']}\n+++ {c['file']}\n{c['diff']}"
            for c in self.changes
        )


@dataclass
class BugFixResult:
    """Final result of entire QA process"""
    bug_report: BugReport
    actual_outcome: ActualOutcome
    comparison: ComparisonResult
    root_cause: RootCause | None
    proposed_fix: ProposedFix | None

    # Gemini Judge verdict
    verdict: Literal["grounded", "partial", "miss"]
    judge_reason: str

    # Verification
    tests_passed: bool
    regressions_detected: bool
    reproducible: bool             # Fix works consistently

    # Memory
    recalled_from_memory: bool = False
    stored_in_memory: bool = False

    # Metadata
    cycle_number: int = 1
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    ended_at: str = ""
    total_time: float = 0.0
    screenshots: list[str] = field(default_factory=list)


@dataclass
class BugPattern:
    """Stored in memory for future recall"""
    bug_signature: str             # Embedding-friendly description
    symptoms: list[str]            # Error messages, UI issues
    root_cause: RootCause
    fix: ProposedFix
    success_rate: float            # How often this fix works
    times_recalled: int = 0
    last_used: str = ""

    def to_dict(self) -> dict:
        """For Actian VectorAI storage"""
        return {
            "bug_signature": self.bug_signature,
            "symptoms": self.symptoms,
            "root_cause": {
                "file": self.root_cause.file_path,
                "line": self.root_cause.line_number,
                "repo": self.root_cause.repository,
                "error_type": self.root_cause.error_type,
            },
            "fix": self.fix.to_diff(),
            "success_rate": self.success_rate,
        }
```

### 3.2 Bug Report Template

**Location**: `templates/bug_report_template.md`

```markdown
---
id: {auto-generated}
severity: [critical|high|medium|low]
environment: [production|staging|local]
reported_by: user@example.com
---

# Bug Title

Brief one-line description

## Description

Detailed description of the issue

## Steps to Reproduce

1. Step one (e.g., "Navigate to https://app.squidgy.ai/login")
2. Step two (e.g., "Click the login button")
3. Step three (e.g., "Enter email: test@example.com")
4. Step N (e.g., "Observe the error")

## Expected Outcome

What should happen (e.g., "User should be redirected to dashboard")

## Actual Outcome

What actually happens (e.g., "Page shows 'CSRF token invalid'")

## Environment Details

- Browser: Chrome 120
- OS: macOS 14.2
- User Account: test@example.com
- Timestamp: 2026-08-02T15:30:00Z

## Attachments

- screenshot1.png
- network_log.har
```

---

## 4. Prompt Engineering

### 4.1 QA Evaluator Prompts

#### 4.1.1 Playwright Step Executor

```python
EVALUATOR_PROMPT = """You are a QA automation engineer using Playwright to reproduce a bug.

Bug Report:
{bug_report}

Your task:
1. Navigate to {url}
2. Execute each reproduction step using Playwright commands
3. Capture a screenshot after each step
4. Extract the actual outcome

Reproduction Steps:
{repro_steps}

For each step, generate the appropriate Playwright command:
- Navigation: await page.goto('url')
- Click: await page.click('selector')
- Fill input: await page.fill('selector', 'value')
- Wait: await page.waitForTimeout(ms)
- Screenshot: await page.screenshot({{ path: 'path.png' }})

After all steps, extract:
- Final URL
- Any error messages (console, network, DOM)
- Final DOM state

Return a structured report of what happened.
"""
```

#### 4.1.2 Screenshot Analysis

```python
SCREENSHOT_ANALYSIS_PROMPT = """You are analyzing screenshots from a bug reproduction attempt.

Expected Outcome:
{expected_outcome}

Screenshots (in order):
{screenshot_descriptions}

Analyze these screenshots and determine:
1. Does the final state match the expected outcome?
2. What specific differences do you see?
3. What error messages or UI issues are visible?

Provide a detailed comparison.
"""
```

### 4.2 QA Grader Prompts

#### 4.2.1 Outcome Comparison

```python
GRADER_PROMPT = """You are a QA grader comparing expected vs actual outcomes.

Expected Outcome:
{expected_outcome}

Actual Outcome:
{actual_outcome}

Screenshots:
{screenshots}

Console Errors:
{console_errors}

Network Errors:
{network_errors}

Task: Determine if the actual outcome matches the expected outcome.

Respond with:
{{
  "match": true/false,
  "confidence": 0.0-1.0,
  "reason": "Detailed explanation",
  "differences": ["diff1", "diff2", ...],
  "verdict": "reproduced" | "not_reproduced" | "unclear"
}}

Guidelines:
- "reproduced" = Bug successfully reproduced, outcome differs from expected
- "not_reproduced" = Bug NOT reproduced, outcome matches expected (bug might be fixed)
- "unclear" = Cannot determine (ambiguous, need more info)
"""
```

### 4.3 Root Cause Analysis Prompts

#### 4.3.1 Code Debugger

```python
ROOT_CAUSE_PROMPT = """You are a senior software engineer debugging a production issue.

Bug Report:
{bug_report}

Actual Outcome:
{actual_outcome}

Error Messages:
{error_messages}

Available Code Repositories:
- Backend: {backend_repo_path}
- Frontend: {frontend_repo_path}
- Citadel: {citadel_repo_path}

Your task:
1. Analyze the error messages and symptoms
2. Search the relevant code repositories
3. Identify the file and line number causing the issue
4. Explain WHY this causes the observed behavior

Think step-by-step:
- What type of error is this? (Network, Logic, Data, UI, etc.)
- Which repository is most likely responsible?
- What keywords should we search for?
- What are the most common causes of this error type?

Return:
{{
  "file_path": "relative/path/to/file",
  "line_number": 123,
  "repository": "backend" | "frontend" | "citadel",
  "error_type": "CSRF token expiration",
  "explanation": "Why this causes the bug",
  "code_context": "±10 lines around the issue",
  "confidence": 0.0-1.0
}}
"""
```

#### 4.3.2 Fix Generator

```python
FIX_GENERATOR_PROMPT = """You are generating a code fix for a verified bug.

Root Cause:
{root_cause}

File: {file_path}:{line_number}
Error Type: {error_type}
Explanation: {explanation}

Code Context:
{code_context}

Your task:
1. Generate the minimal code change to fix this issue
2. Ensure the fix doesn't break other functionality
3. Create test cases to verify the fix
4. Explain the reasoning

Return:
{{
  "changes": [
    {{
      "file": "path/to/file",
      "diff": "unified diff format",
      "reason": "Why this change fixes the issue"
    }}
  ],
  "test_cases": ["test code 1", "test code 2"],
  "validation_steps": ["How to verify this works"],
  "estimated_risk": "low" | "medium" | "high",
  "requires_human_review": true/false
}}
"""
```

### 4.4 Gemini Judge Prompt

```python
JUDGE_PROMPT = """You are grading the quality of a bug fix solution.

Bug Report:
{bug_report}

Proposed Fix:
{proposed_fix}

Test Results:
{test_results}

Verification:
- Tests passed: {tests_passed}
- Regressions detected: {regressions_detected}
- Reproducible: {reproducible}

Grade this solution as:
- "grounded": Fix is correct, complete, well-tested, no regressions
- "partial": Fix addresses the issue but incomplete/risky/needs refinement
- "miss": Fix doesn't work or causes more issues

Respond with:
{{
  "verdict": "grounded" | "partial" | "miss",
  "reason": "Detailed explanation of your assessment",
  "confidence": 0.0-1.0,
  "suggestions": ["Improvement 1", "Improvement 2", ...]
}}
"""
```

---

## 5. MCP Configuration

### 5.1 Claude Desktop Config

**Location**: `~/.claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": [
        "-y",
        "@executeautomation/playwright-mcp-server"
      ]
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/somasekharaddakula/Git/squidgy-backend",
        "/Users/somasekharaddakula/Git/squidgy-frontend",
        "/Users/somasekharaddakula/Git/citadel"
      ]
    },
    "roam": {
      "command": "npx",
      "args": [
        "-y",
        "@roam/mcp-server"
      ],
      "env": {
        "ROAM_API_KEY": "${BAND_USER_API_KEY}"
      }
    }
  }
}
```

### 5.2 Playwright MCP Server

**Installation**:
```bash
npm install -g @executeautomation/playwright-mcp-server
playwright install chromium
```

**Capabilities**:
- `playwright_navigate`: Go to URL
- `playwright_click`: Click element
- `playwright_fill`: Fill input
- `playwright_screenshot`: Capture screenshot
- `playwright_evaluate`: Execute JS
- `playwright_waitForSelector`: Wait for element

### 5.3 Filesystem MCP Server

**Purpose**: Read code repositories for root cause analysis

**Usage**:
```python
# Via MCP client
filesystem.read_file("/Users/.../squidgy-backend/app/auth/middleware.py")
filesystem.search_files("CSRF", repo="/Users/.../squidgy-backend")
```

---

## 6. File Structure

```
self-evolving-qa-hackathon/
├── qa_engine/                    # New QA framework code
│   ├── __init__.py
│   ├── bug_processor.py          # Parse bug reports
│   ├── evaluator.py              # QA Evaluator (Playwright)
│   ├── grader.py                 # QA Grader (comparison)
│   ├── root_cause.py             # Root cause analyzer
│   ├── fix_generator.py          # Generate fixes
│   ├── memory.py                 # Memory/recall manager
│   ├── notifier.py               # Roam/Email notifications
│   ├── loop.py                   # Main QA loop orchestrator
│   └── models.py                 # Data models (above)
│
├── qa_clients/                   # Client wrappers
│   ├── playwright_client.py      # Playwright MCP wrapper
│   ├── filesystem_client.py      # Code repo access
│   └── roam_client.py            # Roam messaging
│
├── templates/
│   └── bug_report_template.md   # Standard bug report format
│
├── data/
│   ├── bugs/                     # Bug reports (input)
│   │   ├── pending/              # New bugs to process
│   │   ├── processing/           # Currently being worked on
│   │   └── completed/            # Finished bugs
│   │
│   ├── canon/
│   │   └── bugs/                 # Verified fixes (documentation)
│   │       ├── bug-123-login-csrf-token.md
│   │       └── bug-456-api-timeout.md
│   │
│   ├── screenshots/              # Organized by bug ID
│   │   ├── bug-123/
│   │   │   ├── step-1.png
│   │   │   ├── step-2.png
│   │   │   └── final.png
│   │   └── bug-456/
│   │       └── ...
│   │
│   ├── fixes/                    # Proposed fixes (diffs)
│   │   ├── bug-123.diff
│   │   └── bug-456.diff
│   │
│   └── qa_runs.jsonl             # QA cycle results (like runs.jsonl)
│
├── guild_qa.yml                  # Guild AI config for QA cron
│
├── run_qa.py                     # Main entry point
│
└── .env                          # API keys + repo paths
```

---

## 7. Integration Points

### 7.1 Integration with Existing Evolution Loop

```python
# Shared components
from clients.judge import Judge             # Reuse Gemini judge
from clients.memory_client import MemoryClient  # Reuse Actian
from clients.pioneer_client import PioneerClient  # Reuse Pioneer

# New QA-specific components
from qa_clients.playwright_client import PlaywrightClient
from qa_clients.filesystem_client import FilesystemClient
from qa_clients.roam_client import RoamClient
```

### 7.2 Shared Memory Storage

**Same Actian VectorAI instance**, different collections:
- `qa_questions`: Q&A evolution loop (existing)
- `qa_bugs`: Bug fixing loop (new)

```python
memory = MemoryClient()

# Store bug pattern
memory.remember(
    collection="qa_bugs",
    problem=bug_report.title,
    fix=proposed_fix.to_diff(),
    worked=(verdict == "grounded"),
    meta={
        "symptoms": bug_report.description,
        "root_cause": f"{root_cause.file_path}:{root_cause.line_number}",
        "error_type": root_cause.error_type,
        "screenshots": result.screenshots,
    }
)

# Recall similar bug
hits = memory.recall(
    collection="qa_bugs",
    query=bug_report.title,
    limit=3,
    min_score=0.85
)
```

### 7.3 Shared Guild AI Scheduler

**Extend existing `guild.yml`**:

```yaml
- model: evolution-loop
  operations:
    run-qa-cycle:
      description: Run QA bug fixing cycle
      exec: python run_qa.py
      schedule: "*/15 * * * *"  # Every 15 minutes

      output-scalars:
        - step: 'qa_cycle (\d+)'
          bugs_processed: '(\d+) bugs processed'
          fixes_grounded: '(\d+) grounded'
          fixes_partial: '(\d+) partial'
          recalled: '(\d+) recalled'

      env:
        # Existing keys
        TARGET_REPO: ${TARGET_REPO}
        GEMINI_API_KEY: ${GEMINI_API_KEY}
        PIONEER_API_KEY: ${PIONEER_API_KEY}

        # New QA-specific
        BACKEND_REPO: ${BACKEND_REPO}
        FRONTEND_REPO: ${FRONTEND_REPO}
        CITADEL_REPO: ${CITADEL_REPO}
        SQUIDGY_APP_URL: https://app.squidgy.ai
        DEV_EMAIL: development@squidgy.ai
```

---

## 8. Memory & Learning

### 8.1 Bug Pattern Storage

**What to store**:
```python
{
  "bug_id": "bug-123",
  "signature": "Login button CSRF token expiration",
  "symptoms": [
    "Button clickable but no redirect",
    "Error: CSRF token invalid",
    "Occurs after 1 hour idle"
  ],
  "root_cause": {
    "file": "app/auth/middleware.py",
    "line": 156,
    "repo": "backend",
    "type": "CSRF token expiration"
  },
  "fix": {
    "diff": "... code diff ...",
    "test": "... test code ..."
  },
  "success_rate": 1.0,
  "times_recalled": 0,
  "embedding": [0.123, 0.456, ...]  # 768-dim vector
}
```

### 8.2 Recall Strategy

**Matching algorithm**:
1. Embed new bug description → 768-dim vector
2. Cosine similarity search in Actian
3. Threshold: 0.85 (same as Q&A system)
4. If match found:
   - Return stored fix
   - Increment `times_recalled`
   - Skip research

**Example**:
```python
# New bug: "Login not working after session timeout"
# Embedding: [0.125, 0.458, ...]

# Search returns:
# Bug-123: "Login button CSRF token expiration" (similarity: 0.92)
# → RECALL! Apply same fix pattern

# New bug: "Signup form CSS broken"
# Embedding: [0.789, 0.234, ...]

# Search returns:
# No matches > 0.85
# → RESEARCH from scratch
```

### 8.3 Learning Metrics

Track over time:
```python
{
  "cycle": 1,
  "bugs_processed": 10,
  "recalled_from_memory": 0,  # First cycle, no memory yet
  "fixes_grounded": 6,
  "fixes_partial": 3,
  "fixes_miss": 1,
  "avg_time_per_bug": 180.0,  # 3 minutes
}

{
  "cycle": 5,
  "bugs_processed": 10,
  "recalled_from_memory": 4,  # Learning!
  "fixes_grounded": 8,
  "fixes_partial": 2,
  "fixes_miss": 0,
  "avg_time_per_bug": 90.0,   # Faster! (recalls are instant)
}
```

---

## 9. Notification System

### 9.1 Roam Message Format (with @all tagging)

```python
def send_roam_notification(result: BugFixResult):
    message = f"""
@all 🐛 **Bug Analysis Complete**

**Bug ID**: #{result.bug_report.id}
**Status**: {verdict_emoji(result.verdict)} {result.verdict.title()}

**Bug**: {result.bug_report.title}
**Root Cause**: {result.root_cause.error_type}
**Location**: `{result.root_cause.file_path}:{result.root_cause.line_number}`

**Fix Summary**:
{result.proposed_fix.changes[0]['reason']}

**Files Changed**:
{format_changes(result.proposed_fix.changes)}

**Test Results**: {'✅ Passed' if result.tests_passed else '❌ Failed'}
**Regressions**: {'✅ None' if not result.regressions_detected else '⚠️ Detected'}

**Next Steps**:
Review proposed changes and approve for staging deployment.

📎 **Documentation**: `data/canon/bugs/{slug(result.bug_report.title)}.md`
📸 **Screenshots**: {len(result.screenshots)} captured
"""

    roam_client.post_message(
        room_id=os.environ.get("ROAM_ROOM_ID", "development-room-id"),
        message=message
    )
```

**Note**: The `@all` tag at the beginning ensures all team members are notified in the Roam room.

---

## 10. Security & Safety

### 10.1 Code Execution Isolation

**Principle**: Never execute untrusted code

1. **Read-only code access**: Only read repos, never write
2. **Test environment**: Apply fixes in isolated Docker container
3. **No auto-deploy**: Human approval required
4. **Sandboxed browser**: Playwright runs in headless mode, no access to local files

### 10.2 Credential Management

```python
# .env file (gitignored)
GEMINI_API_KEY=...
PIONEER_API_KEY=...
BAND_USER_API_KEY=...
SQUIDGY_APP_URL=https://app.squidgy.ai
ROAM_ROOM_ID=development-room-id  # Roam room for notifications

# For app access (if needed)
TEST_USER_EMAIL=qa-test@squidgy.ai
TEST_USER_PASSWORD=... (use password manager, not .env)
```

### 10.3 Screenshot Privacy

**Concern**: Screenshots may contain user data

**Solution**:
1. Use dedicated test account
2. Blur sensitive data before storing
3. Auto-delete screenshots after 7 days
4. Don't upload to public storage

---

## 11. Performance Considerations

### 11.1 Execution Time Budget

| Phase | Target Time | Max Time |
|-------|-------------|----------|
| Bug parsing | 1s | 5s |
| Memory check | 2s | 10s |
| QA Evaluation (Playwright) | 30s | 120s |
| Root cause analysis | 20s | 60s |
| Fix generation | 15s | 45s |
| Verification | 30s | 120s |
| **Total per bug** | **~2 min** | **~6 min** |

### 11.2 Concurrency

**Limit**: 1 bug at a time (local Playwright can't handle multiple browsers)

**Future optimization**: Use browser context pool

### 11.3 Memory Usage

- Playwright browser: ~200MB
- Screenshots (10 per bug): ~5MB
- LLM context: ~50MB
- **Total**: ~250MB per bug

---

## 12. Monitoring & Observability

### 12.1 Metrics to Track

```python
{
  "qa_cycle": 1,
  "bugs_processed": 10,
  "bugs_recalled": 2,
  "bugs_grounded": 6,
  "bugs_partial": 3,
  "bugs_miss": 1,
  "avg_time": 120.0,
  "screenshot_count": 45,
  "memory_hit_rate": 0.2,
  "playwright_success_rate": 0.9,
}
```

### 12.2 Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('qa_loop.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('qa_engine')

# Usage
logger.info(f"Processing bug {bug_id}")
logger.debug(f"Playwright step: {step}")
logger.warning(f"Screenshot failed: {error}")
logger.error(f"Root cause analysis failed: {error}")
```

### 12.3 Guild AI Dashboard

**Metrics visible at `http://localhost:6060`**:
- Bugs processed per cycle
- Grounded/partial/miss ratio
- Memory recall rate
- Average time per bug
- Screenshot count
- Error rate

---

## 13. Next Steps

See `QA_FRAMEWORK_execution_plan.md` for implementation roadmap.

---

**End of Architecture Plan**
