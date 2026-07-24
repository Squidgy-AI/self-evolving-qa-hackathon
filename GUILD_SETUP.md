# Guild AI Setup Guide

Guild AI provides automated scheduling and metrics tracking for the Evolution Loop.

## Quick Start

### 1. Install Guild AI

```bash
pip install guild
```

### 2. Initialize Guild

```bash
guild init
```

This creates a `.guild` directory for storing run data and metrics.

### 3. Run One Cycle Manually

```bash
guild run evolution-loop
```

Guild will:
- Install dependencies from `requirements-engine.txt`
- Load environment variables from `.env`
- Run `python -m engine.loop`
- Track metrics (score_before, score_after, promoted, rejected, recalled)

### 4. Start the Scheduler (for automated runs)

```bash
guild serve
```

This starts Guild's scheduler on `http://localhost:6060`. The `scheduled-cycle` operation will run automatically every 5 minutes.

**For the demo**: This proves "no manual intervention" — the system evolves itself.

## Viewing Metrics

### Local Dashboard

```bash
guild view
```

Opens a web UI at `http://localhost:6060` showing:
- Pass rate over time (score_before → score_after)
- Number of docs promoted vs rejected
- Memory recalls (free vs research)
- Cost per cycle (if tracking tokens)

### Compare Runs

```bash
guild compare
```

Shows a table of all runs with key metrics.

### Tensorboard Integration

```bash
guild tensorboard
```

Visualizes metrics as line charts over time.

## Configuration (guild.yml)

### Operations

1. **run-cycle**: Manual trigger for testing
   - Runs `engine.loop` main
   - Tracks all metrics from console output
   - Uses flags for custom question sets

2. **scheduled-cycle**: Automated cron trigger
   - Runs every 5 minutes (`*/5 * * * *`)
   - Proof of "no manual intervention"
   - Same metrics as manual runs

### Metrics Tracked

Extracted via regex from console output:

```python
score_before: 'score (\S+) ->'
score_after: '-> (\S+)'
passed_before: 'pass (\d+)/'
passed_after: '/ -> (\d+)/'
promoted: '(\d+) promoted'
rejected: '(\d+) rejected'
recalled: '(\d+) recalled'
```

Example output:
```
=== score 0.38 -> 0.75 | pass 3/8 -> 6/8, 2 promoted, 1 rejected, 1 recalled ===
```

Guild extracts: `score_before=0.38`, `score_after=0.75`, `passed_after=6`, `promoted=2`, etc.

## For the Hackathon Demo

### Show Automated Evolution

1. Start Guild scheduler:
   ```bash
   guild serve
   ```

2. Open dashboard: `http://localhost:6060`

3. Let it run for 15-30 minutes before the demo

4. Show judges the metrics chart: pass rate climbing without manual intervention

### Manual Trigger During Demo

If you want to trigger a cycle during the live demo:

```bash
guild run evolution-loop
```

This runs immediately and judges can watch the console output + BAND room simultaneously.

## Environment Variables

Guild loads from `.env` automatically. Required keys:

```bash
GEMINI_API_KEY=...          # For grading
PIONEER_API_KEY=...         # For research
SENSO_API_KEY=...           # For publishing
DEEPWIKI_API_KEY=...        # For querying Concierge
ACTIAN_VECTOR_URL=...       # Default: http://localhost:6333
TARGET_REPO=...             # Default: ~/Git/fastapi
```

## Troubleshooting

### "No module named 'guild'"

```bash
pip install guild
```

### "No runs found"

Run at least one cycle first:
```bash
guild run evolution-loop
```

### "Schedule not running"

Make sure `guild serve` is running in the background:
```bash
guild serve &
```

### "Metrics not showing up"

Check that console output matches the regex patterns in `guild.yml`:

```bash
python -m engine.loop | grep "score"
```

Should output: `=== score 0.38 -> 0.75 | ...`

## Deployment (Optional)

To deploy Guild to a server for continuous evolution:

```bash
# On server
git clone <repo>
cd self-evolving-qa-hackathon
git checkout engine/evolution-loop
pip install -r requirements-engine.txt
pip install guild

# Copy .env with API keys
cp .env.example .env
# Edit .env

# Start scheduler as background service
nohup guild serve > guild.log 2>&1 &
```

Guild will run cycles every 5 minutes indefinitely.

---

**For Hackathon Judges**: The `scheduled-cycle` operation in `guild.yml` is the proof that the system acts on real-time data without manual intervention. Every 5 minutes, it grades deepwiki, finds gaps, researches fixes, verifies citations, and publishes — all automatically.
