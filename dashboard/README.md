# Evolution Dashboard

A small, self-contained FastAPI dashboard visualising a self-evolving agent's
improvement across cycles. Reads `data/runs.jsonl` (one JSON line per cycle)
and renders stat tiles, two hand-rolled inline-SVG line charts (pass rate up,
cost-per-resolved down), and a cycle history table. Dark theme, no
authentication, no CDN dependencies — safe for an automated QA crawler and
readable from across a room on a projector.

## Run locally

```bash
pip install -r dashboard/requirements.txt
uvicorn dashboard.app:app --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000/evolution (or http://localhost:8000/, which
redirects there).

It also runs directly with `python dashboard/app.py` (reads `$PORT`, defaults
to 8000) — useful for platforms that just execute the file.

If `data/runs.jsonl` does not exist yet, the app seeds it with 3–4 demo cycles
on first run so the dashboard is never blank during a demo. Once your agent
starts appending real cycles to `data/runs.jsonl`, the seed rows are simply
more history at the front of the same file — delete them from the file if you
don't want them.

## Deploy on Render

- **Build command:** `pip install -r dashboard/requirements.txt`
- **Start command:** `uvicorn dashboard.app:app --host 0.0.0.0 --port $PORT`
- **Environment variables:** none required.

## Endpoints

| Path | Returns |
|---|---|
| `GET /` | Redirects to `/evolution` |
| `GET /evolution` | The dashboard page (auto-refreshes every 5s) |
| `GET /api/cycles` | The parsed contents of `data/runs.jsonl` as JSON |
| `GET /healthz` | `{"ok": true}` |
