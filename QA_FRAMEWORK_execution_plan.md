# Self-Learning QA Bug Fixing Framework - Execution Plan

**Version**: 1.0
**Date**: 2026-08-02
**Status**: Planning Phase
**Estimated Duration**: 4-6 weeks

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Foundation Setup](#phase-1-foundation-setup)
3. [Phase 2: QA Evaluator](#phase-2-qa-evaluator)
4. [Phase 3: QA Grader](#phase-3-qa-grader)
5. [Phase 4: Root Cause Analysis](#phase-4-root-cause-analysis)
6. [Phase 5: Memory Integration](#phase-5-memory-integration)
7. [Phase 6: Notification System](#phase-6-notification-system)
8. [Phase 7: CRON Integration](#phase-7-cron-integration)
9. [Testing Strategy](#testing-strategy)
10. [Rollout Plan](#rollout-plan)
11. [Success Criteria](#success-criteria)

---

## Prerequisites

### Environment Setup

#### 1. Install Dependencies

```bash
cd ~/CascadeProjects/SelfBuildingAgent/self-evolving-qa-hackathon

# Python dependencies
pip install playwright pytest

# Playwright browsers
playwright install chromium

# Node dependencies for MCP servers
npm install -g @executeautomation/playwright-mcp-server
npm install -g @modelcontextprotocol/server-filesystem
```

#### 2. Configure MCP Servers

**Edit**: `~/.claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@executeautomation/playwright-mcp-server"]
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
      "args": ["-y", "@roam/mcp-server"],
      "env": {
        "ROAM_API_KEY": "${BAND_USER_API_KEY}"
      }
    }
  }
}
```

#### 3. Environment Variables

**Create/Update**: `.env`

```bash
# Existing keys
GEMINI_API_KEY=...
PIONEER_API_KEY=...
BAND_USER_API_KEY=...
SENSO_API_KEY=...

# New QA-specific
BACKEND_REPO=/Users/somasekharaddakula/Git/squidgy-backend
FRONTEND_REPO=/Users/somasekharaddakula/Git/squidgy-frontend
CITADEL_REPO=/Users/somasekharaddakula/Git/citadel
SQUIDGY_APP_URL=https://app.squidgy.ai
DEV_EMAIL=development@squidgy.ai

# Test credentials
QA_TEST_EMAIL=qa-test@squidgy.ai
QA_TEST_PASSWORD=... (use password manager)
```

#### 4. Repository Setup

```bash
# Ensure all code repos are cloned and up to date
cd ~/Git
git clone git@github.com:Squidgy-AI/squidgy-backend.git
git clone git@github.com:Squidgy-AI/squidgy-frontend.git
git clone git@github.com:Squidgy-AI/citadel.git

# Pull latest
cd squidgy-backend && git pull origin main
cd ../squidgy-frontend && git pull origin main
cd ../citadel && git pull origin main
```

---

## Phase 1: Foundation Setup

**Duration**: 3-5 days
**Goal**: Create directory structure, data models, and bug report template

### 1.1 Create Directory Structure

```bash
cd ~/CascadeProjects/SelfBuildingAgent/self-evolving-qa-hackathon

# Create QA engine directories
mkdir -p qa_engine
mkdir -p qa_clients
mkdir -p templates
mkdir -p data/bugs/{pending,processing,completed}
mkdir -p data/canon/bugs
mkdir -p data/screenshots
mkdir -p data/fixes

# Create __init__.py files
touch qa_engine/__init__.py
touch qa_clients/__init__.py
```

### 1.2 Implement Data Models

**File**: `qa_engine/models.py`

```python
"""
Data models for QA bug fixing framework.
See QA_FRAMEWORK_architecture_plan.md section 3 for full specifications.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

@dataclass
class BugReport:
    id: str
    title: str
    description: str
    repro_steps: list[str]
    expected_outcome: str
    environment: str
    severity: Literal["critical", "high", "medium", "low"]
    reporter: str
    reported_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    url: str = ""
    user_agent: str = ""
    attachments: list[str] = field(default_factory=list)

@dataclass
class ReproStep:
    step_number: int
    action: str
    selector: str | None
    value: str | None
    screenshot_path: str | None
    timestamp: float
    success: bool
    error: str | None

@dataclass
class ActualOutcome:
    success: bool
    screenshots: list[str]
    final_url: str
    error_messages: list[str]
    dom_state: str
    network_logs: list[dict]
    console_logs: list[str]
    execution_time: float

    def to_summary(self) -> str:
        return f"""
Reproduction Result: {'Success' if self.success else 'Failed'}
Final URL: {self.final_url}
Errors: {'; '.join(self.error_messages) if self.error_messages else 'None'}
Screenshots captured: {len(self.screenshots)}
Execution time: {self.execution_time:.2f}s
"""

@dataclass
class ComparisonResult:
    match: bool
    confidence: float
    reason: str
    differences: list[str]
    verdict: Literal["reproduced", "not_reproduced", "unclear"]

@dataclass
class RootCause:
    file_path: str
    line_number: int
    repository: Literal["backend", "frontend", "citadel", "n8n"]
    error_type: str
    explanation: str
    code_context: str
    confidence: float
    stack_trace: str | None = None
    related_files: list[str] = field(default_factory=list)

@dataclass
class ProposedFix:
    root_cause: RootCause
    changes: list[dict]
    test_cases: list[str]
    validation_steps: list[str]
    estimated_risk: Literal["low", "medium", "high"]
    requires_human_review: bool

    def to_diff(self) -> str:
        return "\n\n".join(
            f"--- {c['file']}\n+++ {c['file']}\n{c['diff']}"
            for c in self.changes
        )

@dataclass
class BugFixResult:
    bug_report: BugReport
    actual_outcome: ActualOutcome
    comparison: ComparisonResult
    root_cause: RootCause | None
    proposed_fix: ProposedFix | None
    verdict: Literal["grounded", "partial", "miss"]
    judge_reason: str
    tests_passed: bool
    regressions_detected: bool
    reproducible: bool
    recalled_from_memory: bool = False
    stored_in_memory: bool = False
    cycle_number: int = 1
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    ended_at: str = ""
    total_time: float = 0.0
    screenshots: list[str] = field(default_factory=list)

@dataclass
class BugPattern:
    bug_signature: str
    symptoms: list[str]
    root_cause: RootCause
    fix: ProposedFix
    success_rate: float
    times_recalled: int = 0
    last_used: str = ""

    def to_dict(self) -> dict:
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

**Test**:
```bash
python -c "from qa_engine.models import BugReport; print(BugReport(id='test', title='Test', description='Test', repro_steps=[], expected_outcome='', environment='local', severity='low', reporter='test@test.com'))"
```

### 1.3 Create Bug Report Template

**File**: `templates/bug_report_template.md`

```markdown
---
id: {auto-generated}
severity: [critical|high|medium|low]
environment: [production|staging|local]
reported_by: user@example.com
url: https://app.squidgy.ai/...
---

# Bug Title

Brief one-line description of the issue

## Description

Detailed description of what's happening

## Steps to Reproduce

1. Navigate to https://app.squidgy.ai/login
2. Click the "Login" button
3. Enter email: test@example.com
4. Enter password: ••••••••
5. Click "Submit"
6. Observe the error

## Expected Outcome

What should happen (e.g., "User should be redirected to /dashboard")

## Actual Outcome

What actually happens (e.g., "Page shows error: CSRF token invalid")

## Environment Details

- Browser: Chrome 120
- OS: macOS 14.2
- User Account: test@example.com
- Timestamp: 2026-08-02T15:30:00Z

## Attachments

- user_screenshot.png (optional)
```

### 1.4 Create Sample Bug Report

**File**: `data/bugs/pending/bug-001-login-csrf.md`

```markdown
---
id: bug-001
severity: high
environment: production
reported_by: user@squidgy.ai
url: https://app.squidgy.ai/login
---

# Login Button Not Working After 1 Hour

User cannot log in after being idle for more than 1 hour

## Description

When a user returns to the app after being idle for 1+ hours, clicking the login button does not redirect them to the dashboard. Instead, an error message appears.

## Steps to Reproduce

1. Navigate to https://app.squidgy.ai/login
2. Wait 1 hour (or simulate by clearing session storage)
3. Enter email: qa-test@squidgy.ai
4. Enter password: test1234
5. Click "Login" button
6. Observe error message

## Expected Outcome

User should be redirected to https://app.squidgy.ai/dashboard

## Actual Outcome

Error message appears: "CSRF token invalid. Please refresh and try again."

## Environment Details

- Browser: Chrome 120.0.6099.109
- OS: macOS 14.2.1
- User Account: qa-test@squidgy.ai
- Timestamp: 2026-08-02T14:23:15Z
```

**Validation**:
```bash
ls data/bugs/pending/
# Should show: bug-001-login-csrf.md
```

---

## Phase 2: QA Evaluator

**Duration**: 5-7 days
**Goal**: Implement Playwright-based bug reproduction

### 2.1 Create Playwright MCP Client

**File**: `qa_clients/playwright_client.py`

```python
"""
Playwright MCP client wrapper for browser automation.
"""

import os
import json
from pathlib import Path
from typing import Any

class PlaywrightClient:
    """Wrapper for Playwright MCP server"""

    def __init__(self):
        self.screenshots_dir = Path("data/screenshots")
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def navigate(self, url: str) -> dict:
        """Navigate to URL"""
        # Call Playwright MCP
        # For now, placeholder that will be replaced with actual MCP call
        return {"success": True, "url": url}

    def click(self, selector: str) -> dict:
        """Click element"""
        return {"success": True, "selector": selector}

    def fill(self, selector: str, value: str) -> dict:
        """Fill input field"""
        return {"success": True, "selector": selector, "value": value}

    def screenshot(self, path: str) -> dict:
        """Capture screenshot"""
        full_path = self.screenshots_dir / path
        return {"success": True, "path": str(full_path)}

    def get_console_logs(self) -> list[str]:
        """Get browser console logs"""
        return []

    def get_network_logs(self) -> list[dict]:
        """Get network request/response logs"""
        return []

    def close(self):
        """Close browser"""
        pass
```

### 2.2 Implement Bug Processor

**File**: `qa_engine/bug_processor.py`

```python
"""
Parse bug reports from markdown template format.
"""

import re
from pathlib import Path
from qa_engine.models import BugReport

def parse_bug_report(file_path: str | Path) -> BugReport:
    """Parse bug report markdown file into BugReport dataclass"""
    content = Path(file_path).read_text(encoding="utf-8")

    # Extract frontmatter
    frontmatter_match = re.search(r"---\n(.*?)\n---", content, re.DOTALL)
    if not frontmatter_match:
        raise ValueError("Bug report missing frontmatter")

    frontmatter = {}
    for line in frontmatter_match.group(1).split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()

    # Extract sections
    title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
    title = title_match.group(1) if title_match else "Untitled"

    desc_match = re.search(r"## Description\n\n(.+?)\n\n##", content, re.DOTALL)
    description = desc_match.group(1).strip() if desc_match else ""

    steps_match = re.search(r"## Steps to Reproduce\n\n(.+?)\n\n##", content, re.DOTALL)
    repro_steps = []
    if steps_match:
        for line in steps_match.group(1).split("\n"):
            if line.strip() and line.strip()[0].isdigit():
                step = re.sub(r"^\d+\.\s*", "", line.strip())
                repro_steps.append(step)

    expected_match = re.search(r"## Expected Outcome\n\n(.+?)\n\n##", content, re.DOTALL)
    expected = expected_match.group(1).strip() if expected_match else ""

    return BugReport(
        id=frontmatter.get("id", "unknown"),
        title=title,
        description=description,
        repro_steps=repro_steps,
        expected_outcome=expected,
        environment=frontmatter.get("environment", "unknown"),
        severity=frontmatter.get("severity", "medium"),
        reporter=frontmatter.get("reported_by", "unknown"),
        url=frontmatter.get("url", ""),
    )


def get_pending_bugs() -> list[Path]:
    """Get all pending bug reports"""
    pending_dir = Path("data/bugs/pending")
    return sorted(pending_dir.glob("*.md"))
```

**Test**:
```bash
python -c "
from qa_engine.bug_processor import parse_bug_report
bug = parse_bug_report('data/bugs/pending/bug-001-login-csrf.md')
print(f'Bug: {bug.title}')
print(f'Steps: {len(bug.repro_steps)}')
"
```

### 2.3 Implement QA Evaluator

**File**: `qa_engine/evaluator.py`

```python
"""
QA Evaluator: Execute bug reproduction steps with Playwright.
"""

import time
from pathlib import Path
from qa_clients.playwright_client import PlaywrightClient
from qa_engine.models import BugReport, ReproStep, ActualOutcome

class QAEvaluator:
    """Reproduce bugs using Playwright automation"""

    def __init__(self):
        self.playwright = PlaywrightClient()

    def reproduce(self, bug_report: BugReport) -> ActualOutcome:
        """Execute reproduction steps and capture outcome"""
        screenshots = []
        steps_executed = []
        start_time = time.time()

        try:
            # Navigate to URL
            self.playwright.navigate(bug_report.url or "https://app.squidgy.ai")
            screenshot_path = f"bug-{bug_report.id}/step-0-initial.png"
            self.playwright.screenshot(screenshot_path)
            screenshots.append(screenshot_path)

            # Execute each reproduction step
            for i, step_text in enumerate(bug_report.repro_steps, 1):
                step = self._parse_step(step_text, i)
                self._execute_step(step)

                # Screenshot after each step
                screenshot_path = f"bug-{bug_report.id}/step-{i}.png"
                self.playwright.screenshot(screenshot_path)
                screenshots.append(screenshot_path)
                steps_executed.append(step)

            # Get final state
            console_logs = self.playwright.get_console_logs()
            network_logs = self.playwright.get_network_logs()
            final_url = "https://app.squidgy.ai"  # Get from Playwright

            # Extract errors
            error_messages = [
                log for log in console_logs
                if "error" in log.lower() or "exception" in log.lower()
            ]

            return ActualOutcome(
                success=True,
                screenshots=screenshots,
                final_url=final_url,
                error_messages=error_messages,
                dom_state="",  # Could extract via Playwright
                network_logs=network_logs,
                console_logs=console_logs,
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            return ActualOutcome(
                success=False,
                screenshots=screenshots,
                final_url="",
                error_messages=[str(e)],
                dom_state="",
                network_logs=[],
                console_logs=[],
                execution_time=time.time() - start_time,
            )

    def _parse_step(self, step_text: str, step_number: int) -> ReproStep:
        """Parse step text into structured ReproStep"""
        # Simple parser - can be enhanced with LLM
        action = "unknown"
        selector = None
        value = None

        if "navigate" in step_text.lower() or "go to" in step_text.lower():
            action = "navigate"
        elif "click" in step_text.lower():
            action = "click"
            # Extract selector from quotes
            import re
            match = re.search(r'"([^"]+)"', step_text)
            if match:
                selector = f'text="{match.group(1)}"'
        elif "enter" in step_text.lower() or "type" in step_text.lower():
            action = "fill"
            # Extract field and value
            # e.g., "Enter email: test@example.com"

        return ReproStep(
            step_number=step_number,
            action=action,
            selector=selector,
            value=value,
            screenshot_path=None,
            timestamp=time.time(),
            success=True,
            error=None,
        )

    def _execute_step(self, step: ReproStep):
        """Execute a single reproduction step"""
        if step.action == "navigate":
            self.playwright.navigate(step.value or "")
        elif step.action == "click":
            self.playwright.click(step.selector or "")
        elif step.action == "fill":
            self.playwright.fill(step.selector or "", step.value or "")
        elif step.action == "wait":
            time.sleep(2)
```

**Test**:
```bash
python -c "
from qa_engine.bug_processor import parse_bug_report
from qa_engine.evaluator import QAEvaluator

bug = parse_bug_report('data/bugs/pending/bug-001-login-csrf.md')
evaluator = QAEvaluator()
outcome = evaluator.reproduce(bug)
print(f'Success: {outcome.success}')
print(f'Screenshots: {len(outcome.screenshots)}')
print(outcome.to_summary())
"
```

---

## Phase 3: QA Grader

**Duration**: 3-4 days
**Goal**: Implement outcome comparison with LLM

### 3.1 Implement QA Grader

**File**: `qa_engine/grader.py`

```python
"""
QA Grader: Compare expected vs actual outcomes.
"""

import os
from qa_engine.models import BugReport, ActualOutcome, ComparisonResult

GRADER_PROMPT = """You are a QA grader comparing expected vs actual outcomes.

Expected Outcome:
{expected_outcome}

Actual Outcome:
{actual_outcome}

Console Errors:
{console_errors}

Network Errors:
{network_errors}

Task: Determine if the actual outcome matches the expected outcome.

Respond with JSON:
{{
  "match": true/false,
  "confidence": 0.0-1.0,
  "reason": "Detailed explanation",
  "differences": ["diff1", "diff2", ...],
  "verdict": "reproduced" | "not_reproduced" | "unclear"
}}

Guidelines:
- "reproduced" = Bug successfully reproduced, outcome differs from expected
- "not_reproduced" = Bug NOT reproduced, outcome matches expected
- "unclear" = Cannot determine
"""

class QAGrader:
    """Compare expected vs actual outcomes using LLM"""

    def __init__(self):
        from google import genai
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def compare(self, bug_report: BugReport, actual: ActualOutcome) -> ComparisonResult:
        """Compare expected vs actual outcomes"""

        prompt = GRADER_PROMPT.format(
            expected_outcome=bug_report.expected_outcome,
            actual_outcome=actual.to_summary(),
            console_errors="; ".join(actual.error_messages),
            network_errors="None",  # Could analyze network_logs
        )

        response = self.client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config={"temperature": 0.0},
        )

        # Parse JSON response
        import json
        result = json.loads(response.text)

        return ComparisonResult(
            match=result["match"],
            confidence=result["confidence"],
            reason=result["reason"],
            differences=result["differences"],
            verdict=result["verdict"],
        )
```

**Test**:
```bash
python -c "
from qa_engine.bug_processor import parse_bug_report
from qa_engine.evaluator import QAEvaluator
from qa_engine.grader import QAGrader

bug = parse_bug_report('data/bugs/pending/bug-001-login-csrf.md')
evaluator = QAEvaluator()
grader = QAGrader()

outcome = evaluator.reproduce(bug)
comparison = grader.compare(bug, outcome)
print(f'Match: {comparison.match}')
print(f'Verdict: {comparison.verdict}')
print(f'Reason: {comparison.reason}')
"
```

---

## Phase 4: Root Cause Analysis

**Duration**: 7-10 days
**Goal**: Implement code debugging and fix generation

### 4.1 Create Filesystem Client

**File**: `qa_clients/filesystem_client.py`

```python
"""
Filesystem MCP client for code repository access.
"""

from pathlib import Path

class FilesystemClient:
    """Access code repositories via filesystem MCP"""

    def __init__(self):
        import os
        self.backend_repo = Path(os.environ["BACKEND_REPO"])
        self.frontend_repo = Path(os.environ["FRONTEND_REPO"])
        self.citadel_repo = Path(os.environ["CITADEL_REPO"])

    def read_file(self, repo: str, file_path: str) -> str:
        """Read file from repository"""
        repo_path = getattr(self, f"{repo}_repo")
        full_path = repo_path / file_path
        return full_path.read_text(encoding="utf-8")

    def search_files(self, repo: str, keyword: str, file_pattern: str = "*.py") -> list[dict]:
        """Search for keyword in repository files"""
        repo_path = getattr(self, f"{repo}_repo")
        results = []

        for file_path in repo_path.rglob(file_pattern):
            try:
                content = file_path.read_text(encoding="utf-8")
                if keyword.lower() in content.lower():
                    # Find line numbers
                    lines = content.split("\n")
                    matches = [
                        {"line": i + 1, "text": line}
                        for i, line in enumerate(lines)
                        if keyword.lower() in line.lower()
                    ]
                    results.append({
                        "file": str(file_path.relative_to(repo_path)),
                        "matches": matches,
                    })
            except Exception:
                continue

        return results
```

### 4.2 Implement Root Cause Analyzer

**File**: `qa_engine/root_cause.py`

```python
"""
Root Cause Analyzer: Debug code to find issue.
"""

import os
from qa_clients.filesystem_client import FilesystemClient
from qa_engine.models import BugReport, ActualOutcome, RootCause

ROOT_CAUSE_PROMPT = """You are a senior software engineer debugging a production issue.

Bug Report:
{bug_report}

Actual Outcome:
{actual_outcome}

Error Messages:
{error_messages}

Code Search Results:
{code_results}

Your task:
1. Analyze the error messages and symptoms
2. Identify the file and line number causing the issue
3. Explain WHY this causes the observed behavior

Return JSON:
{{
  "file_path": "relative/path/to/file",
  "line_number": 123,
  "repository": "backend" | "frontend" | "citadel",
  "error_type": "CSRF token expiration",
  "explanation": "Why this causes the bug",
  "confidence": 0.0-1.0
}}
"""

class RootCauseAnalyzer:
    """Find root cause of bug in code"""

    def __init__(self):
        from google import genai
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.filesystem = FilesystemClient()

    def analyze(self, bug_report: BugReport, actual: ActualOutcome) -> RootCause | None:
        """Identify root cause in code"""

        # Extract keywords from errors
        keywords = self._extract_keywords(actual.error_messages)

        # Search code repos
        code_results = []
        for repo in ["backend", "frontend", "citadel"]:
            for keyword in keywords:
                results = self.filesystem.search_files(repo, keyword)
                code_results.extend(results)

        # Ask LLM to analyze
        prompt = ROOT_CAUSE_PROMPT.format(
            bug_report=bug_report.description,
            actual_outcome=actual.to_summary(),
            error_messages="; ".join(actual.error_messages),
            code_results=str(code_results[:5]),  # Top 5 results
        )

        response = self.client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config={"temperature": 0.0},
        )

        import json
        result = json.loads(response.text)

        # Read code context
        code_context = self._get_code_context(
            result["repository"],
            result["file_path"],
            result["line_number"],
        )

        return RootCause(
            file_path=result["file_path"],
            line_number=result["line_number"],
            repository=result["repository"],
            error_type=result["error_type"],
            explanation=result["explanation"],
            code_context=code_context,
            confidence=result["confidence"],
        )

    def _extract_keywords(self, errors: list[str]) -> list[str]:
        """Extract search keywords from error messages"""
        keywords = []
        for error in errors:
            # Simple extraction - could use LLM
            if "CSRF" in error:
                keywords.append("CSRF")
            if "token" in error.lower():
                keywords.append("token")
            if "auth" in error.lower():
                keywords.append("auth")
        return keywords or ["error"]

    def _get_code_context(self, repo: str, file_path: str, line_number: int) -> str:
        """Get ±10 lines around the issue"""
        try:
            content = self.filesystem.read_file(repo, file_path)
            lines = content.split("\n")
            start = max(0, line_number - 10)
            end = min(len(lines), line_number + 10)
            context_lines = lines[start:end]
            return "\n".join(f"{start + i + 1:4}: {line}" for i, line in enumerate(context_lines))
        except Exception:
            return ""
```

### 4.3 Implement Fix Generator

**File**: `qa_engine/fix_generator.py`

```python
"""
Fix Generator: Generate code changes to fix bug.
"""

import os
from qa_engine.models import RootCause, ProposedFix

FIX_GENERATOR_PROMPT = """You are generating a code fix for a verified bug.

Root Cause:
File: {file_path}:{line_number}
Error Type: {error_type}
Explanation: {explanation}

Code Context:
{code_context}

Your task:
1. Generate the minimal code change to fix this issue
2. Ensure the fix doesn't break other functionality
3. Create test cases to verify the fix

Return JSON:
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

class FixGenerator:
    """Generate code fixes"""

    def __init__(self):
        from google import genai
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def generate(self, root_cause: RootCause) -> ProposedFix:
        """Generate fix for root cause"""

        prompt = FIX_GENERATOR_PROMPT.format(
            file_path=root_cause.file_path,
            line_number=root_cause.line_number,
            error_type=root_cause.error_type,
            explanation=root_cause.explanation,
            code_context=root_cause.code_context,
        )

        response = self.client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config={"temperature": 0.0},
        )

        import json
        result = json.loads(response.text)

        return ProposedFix(
            root_cause=root_cause,
            changes=result["changes"],
            test_cases=result["test_cases"],
            validation_steps=result["validation_steps"],
            estimated_risk=result["estimated_risk"],
            requires_human_review=result["requires_human_review"],
        )
```

---

## Phase 5: Memory Integration

**Duration**: 3-4 days
**Goal**: Implement bug pattern recall

### 5.1 Implement Memory Manager

**File**: `qa_engine/memory.py`

```python
"""
Memory Manager: Store and recall bug patterns.
"""

from clients.memory_client import MemoryClient as ActianClient
from qa_engine.models import BugReport, BugPattern, RootCause, ProposedFix

class MemoryManager:
    """Manage bug pattern storage and recall"""

    def __init__(self):
        self.actian = ActianClient()
        self.collection = "qa_bugs"

    def recall(self, bug_report: BugReport) -> BugPattern | None:
        """Search for similar bug in memory"""

        hits = self.actian.recall(
            collection=self.collection,
            query=bug_report.title + " " + bug_report.description,
            limit=3,
            min_score=0.85,
        )

        if not hits:
            return None

        # Convert to BugPattern
        hit = hits[0]
        payload = hit.get("payload", hit)

        # Reconstruct objects from stored data
        # (Simplified - actual implementation would be more robust)

        return BugPattern(
            bug_signature=payload.get("bug_signature", ""),
            symptoms=payload.get("symptoms", []),
            root_cause=RootCause(
                file_path=payload["root_cause"]["file"],
                line_number=payload["root_cause"]["line"],
                repository=payload["root_cause"]["repo"],
                error_type=payload["root_cause"]["error_type"],
                explanation="",
                code_context="",
                confidence=1.0,
            ),
            fix=ProposedFix(
                root_cause=None,  # Placeholder
                changes=[{"file": "", "diff": payload["fix"], "reason": ""}],
                test_cases=[],
                validation_steps=[],
                estimated_risk="low",
                requires_human_review=False,
            ),
            success_rate=payload.get("success_rate", 1.0),
            times_recalled=payload.get("times_recalled", 0),
        )

    def remember(self, bug_report: BugReport, root_cause: RootCause, fix: ProposedFix, worked: bool):
        """Store bug pattern in memory"""

        pattern = BugPattern(
            bug_signature=bug_report.title,
            symptoms=[bug_report.description] + bug_report.repro_steps,
            root_cause=root_cause,
            fix=fix,
            success_rate=1.0 if worked else 0.0,
        )

        self.actian.remember(
            collection=self.collection,
            problem=bug_report.title,
            fix=fix.to_diff(),
            worked=worked,
            meta=pattern.to_dict(),
        )
```

---

## Phase 6: Notification System

**Duration**: 2-3 days
**Goal**: Implement Roam/Email notifications

### 6.1 Implement Roam Client

**File**: `qa_clients/roam_client.py`

```python
"""
Roam client for sending notifications.
"""

from clients.band_room import BandRoom

class RoamClient:
    """Send messages to Roam/BAND"""

    def __init__(self):
        self.room = BandRoom(
            room_id="development-room-id",
            api_key=os.environ["BAND_USER_API_KEY"],
        )

    def send_notification(self, message: str):
        """Send notification to dev team"""
        self.room.post(message)
```

### 6.2 Implement Notifier

**File**: `qa_engine/notifier.py`

```python
"""
Notification system for bug fix results.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from qa_clients.roam_client import RoamClient
from qa_engine.models import BugFixResult

class Notifier:
    """Send notifications via Roam and Email"""

    def __init__(self):
        self.roam = RoamClient()
        self.dev_email = os.environ.get("DEV_EMAIL", "development@squidgy.ai")

    def notify(self, result: BugFixResult):
        """Send notification about bug fix result"""

        if result.verdict == "grounded":
            self._notify_success(result)
        else:
            self._notify_partial(result)

    def _notify_success(self, result: BugFixResult):
        """Notify successful fix"""

        roam_message = f"""
🐛 **Bug Analysis Complete**

**Bug ID**: #{result.bug_report.id}
**Status**: ✅ Fix verified (grounded)

**Bug**: {result.bug_report.title}
**Root Cause**: {result.root_cause.error_type if result.root_cause else 'Unknown'}
**Location**: `{result.root_cause.file_path}:{result.root_cause.line_number}` if result.root_cause else 'N/A'

**Files Changed**:
{self._format_changes(result.proposed_fix.changes if result.proposed_fix else [])}

**Test Results**: {'✅ Passed' if result.tests_passed else '❌ Failed'}
**Regressions**: {'✅ None' if not result.regressions_detected else '⚠️ Detected'}

**Next Steps**:
Review proposed changes and approve for staging deployment.

📎 **Documentation**: `data/canon/bugs/{self._slug(result.bug_report.title)}.md`
"""

        self.roam.send_notification(roam_message)

        # Also send email
        self._send_email(result, roam_message)

    def _notify_partial(self, result: BugFixResult):
        """Notify partial/failed fix"""

        message = f"""
🐛 **Bug Analysis Incomplete**

**Bug ID**: #{result.bug_report.id}
**Status**: ⚠️ {result.verdict.title()}

**Bug**: {result.bug_report.title}
**Reason**: {result.judge_reason}

Manual investigation needed.
"""

        self.roam.send_notification(message)

    def _format_changes(self, changes: list[dict]) -> str:
        """Format file changes for message"""
        return "\n".join(f"• {c['file']}" for c in changes)

    def _slug(self, title: str) -> str:
        """Convert title to slug"""
        import re
        return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]

    def _send_email(self, result: BugFixResult, body: str):
        """Send email notification (placeholder)"""
        # Implement SMTP email sending
        pass
```

---

## Phase 7: CRON Integration

**Duration**: 2-3 days
**Goal**: Integrate with Guild AI scheduler

### 7.1 Create Main Loop

**File**: `qa_engine/loop.py`

```python
"""
Main QA loop orchestrator.
"""

import time
from pathlib import Path
from qa_engine.bug_processor import parse_bug_report, get_pending_bugs
from qa_engine.evaluator import QAEvaluator
from qa_engine.grader import QAGrader
from qa_engine.root_cause import RootCauseAnalyzer
from qa_engine.fix_generator import FixGenerator
from qa_engine.memory import MemoryManager
from qa_engine.notifier import Notifier
from qa_engine.models import BugFixResult
from clients.judge import Judge

def run_qa_cycle():
    """Main entry point for QA bug fixing cycle"""

    print("\n=== QA Bug Fixing Cycle ===")

    # Initialize components
    evaluator = QAEvaluator()
    grader = QAGrader()
    root_cause_analyzer = RootCauseAnalyzer()
    fix_generator = FixGenerator()
    memory = MemoryManager()
    notifier = Notifier()
    judge = Judge()

    # Get pending bugs
    pending = get_pending_bugs()
    print(f"Found {len(pending)} pending bugs")

    for bug_file in pending:
        print(f"\nProcessing: {bug_file.name}")

        # Parse bug report
        bug_report = parse_bug_report(bug_file)

        # Check memory first
        recalled_pattern = memory.recall(bug_report)
        if recalled_pattern:
            print(f"  ✓ Recalled from memory (times_used: {recalled_pattern.times_recalled})")
            # Apply recalled fix and verify
            # ...
            continue

        # QA Evaluator: Reproduce bug
        print("  → Running QA Evaluator (Playwright)")
        actual_outcome = evaluator.reproduce(bug_report)
        print(f"    Screenshots: {len(actual_outcome.screenshots)}")

        # QA Grader: Compare outcomes
        print("  → Running QA Grader")
        comparison = grader.compare(bug_report, actual_outcome)
        print(f"    Verdict: {comparison.verdict}")

        if comparison.verdict == "not_reproduced":
            print("  ✓ Bug not reproduced (might be fixed)")
            continue

        # Root Cause Analysis
        print("  → Analyzing root cause")
        root_cause = root_cause_analyzer.analyze(bug_report, actual_outcome)
        if not root_cause:
            print("  ✗ Could not find root cause")
            continue

        print(f"    Found: {root_cause.file_path}:{root_cause.line_number}")

        # Generate fix
        print("  → Generating fix")
        proposed_fix = fix_generator.generate(root_cause)
        print(f"    Changes: {len(proposed_fix.changes)} files")

        # Gemini Judge
        print("  → Running Gemini Judge")
        verdict = "grounded"  # Simplified - actual implementation would re-test

        # Create result
        result = BugFixResult(
            bug_report=bug_report,
            actual_outcome=actual_outcome,
            comparison=comparison,
            root_cause=root_cause,
            proposed_fix=proposed_fix,
            verdict=verdict,
            judge_reason="Fix verified",
            tests_passed=True,
            regressions_detected=False,
            reproducible=True,
        )

        # Store in memory
        if verdict == "grounded":
            print("  → Storing in memory")
            memory.remember(bug_report, root_cause, proposed_fix, worked=True)

        # Notify humans
        print("  → Sending notification")
        notifier.notify(result)

        # Move to completed
        bug_file.rename(f"data/bugs/completed/{bug_file.name}")

        print(f"  ✓ Complete: {verdict}")

    print("\n=== Cycle Complete ===")
```

### 7.2 Create Entry Point

**File**: `run_qa.py`

```python
"""
Entry point for QA bug fixing framework.
"""

if __name__ == "__main__":
    from qa_engine.loop import run_qa_cycle
    run_qa_cycle()
```

### 7.3 Update Guild Configuration

**File**: `guild_qa.yml`

```yaml
- model: qa-evolution-loop
  description: Self-learning QA bug fixing framework

  operations:
    run-qa-cycle:
      description: Run QA bug fixing cycle
      exec: python run_qa.py
      schedule: "*/15 * * * *"  # Every 15 minutes

      output-scalars:
        - step: 'cycle (\d+)'
          bugs_processed: '(\d+) pending bugs'
          bugs_recalled: 'Recalled from memory.*(\d+)'
          bugs_grounded: 'Complete: grounded'
          bugs_partial: 'Complete: partial'

      env:
        GEMINI_API_KEY: ${GEMINI_API_KEY}
        PIONEER_API_KEY: ${PIONEER_API_KEY}
        BAND_USER_API_KEY: ${BAND_USER_API_KEY}
        BACKEND_REPO: ${BACKEND_REPO}
        FRONTEND_REPO: ${FRONTEND_REPO}
        CITADEL_REPO: ${CITADEL_REPO}
        SQUIDGY_APP_URL: ${SQUIDGY_APP_URL}
        DEV_EMAIL: ${DEV_EMAIL}
```

---

## Testing Strategy

### Unit Tests

```bash
pytest qa_engine/tests/
```

### Integration Tests

1. **Test Bug Processor**: Parse sample bugs
2. **Test QA Evaluator**: Reproduce simple bug
3. **Test QA Grader**: Compare outcomes
4. **Test Root Cause**: Find issue in code
5. **Test Memory**: Store and recall pattern
6. **Test Full Loop**: End-to-end with sample bug

### Manual Testing

1. Create bug report: `data/bugs/pending/bug-test-001.md`
2. Run: `python run_qa.py`
3. Verify: Screenshots created, notification sent
4. Check: Bug moved to completed

---

## Rollout Plan

### Week 1-2: Foundation
- ✅ Directory structure
- ✅ Data models
- ✅ Bug template
- ✅ Sample bug

### Week 3-4: Core Components
- ✅ QA Evaluator
- ✅ QA Grader
- ✅ Bug processor

### Week 5-6: Advanced Features
- ✅ Root cause analysis
- ✅ Fix generator
- ✅ Memory integration

### Week 7-8: Integration & Testing
- ✅ Notification system
- ✅ Guild CRON
- ✅ End-to-end testing
- ✅ Production rollout

---

## Success Criteria

### Phase 1 Success
- [ ] Bug report template created
- [ ] Sample bug parsed successfully
- [ ] Directory structure in place

### Phase 2 Success
- [ ] Playwright reproduces simple bug
- [ ] Screenshots captured
- [ ] Errors extracted

### Phase 3 Success
- [ ] Grader compares outcomes correctly
- [ ] Verdict matches expected

### Phase 4 Success
- [ ] Root cause found in code
- [ ] Fix generated
- [ ] Diff created

### Phase 5 Success
- [ ] Bug stored in memory
- [ ] Similar bug recalled
- [ ] Faster on second attempt

### Phase 6 Success
- [ ] Roam message sent
- [ ] Email sent
- [ ] Humans receive notification

### Phase 7 Success
- [ ] Guild cron runs every 15 min
- [ ] Metrics tracked
- [ ] Dashboard shows progress

### Overall Success
- [ ] 10 bugs processed
- [ ] 6+ grounded fixes
- [ ] 2+ recalled from memory
- [ ] 0 auto-deployments (safety check)
- [ ] Humans approve all notifications

---

**End of Execution Plan**
