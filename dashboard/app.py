"""
Self-Evolving QA — Evolution Dashboard

A small, self-contained FastAPI app that visualises a self-evolving agent's
improvement across cycles. Reads newline-delimited JSON from data/runs.jsonl
(one line per cycle) and renders stat tiles, two hand-rolled inline-SVG line
charts, and a cycle table.

Design goals (see task brief):
- Never 500. Missing/empty/malformed data all degrade to a clean empty state.
- Seed data/runs.jsonl with demo rows on first run ONLY (file doesn't exist).
- No authentication -- publicly scannable by an automated QA crawler.
- Pure stdlib + fastapi + uvicorn + jinja2. No CDN, no JS chart libraries.
- Runs via `uvicorn dashboard.app:app` and via `python dashboard/app.py`,
  reading the port from $PORT (default 8000).
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# ---------------------------------------------------------------------------
# Paths — resolved from this file's location, independent of the process's
# current working directory, so both `uvicorn dashboard.app:app` (run from
# the project root) and `python dashboard/app.py` (run from anywhere) land
# on the same data/ and templates/ directories.
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_FILE = DATA_DIR / "runs.jsonl"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="Self-Evolving QA — Evolution Dashboard")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ---------------------------------------------------------------------------
# Demo seed data — written to data/runs.jsonl only if that file does not
# exist yet, so a fresh checkout / fresh deploy never shows a blank page
# during a demo. An existing file (even an empty or malformed one) is left
# alone; that case is handled by the empty-state render path instead.
# ---------------------------------------------------------------------------
DEMO_ROWS: list[dict[str, Any]] = [
    {"cycle": 1, "started_at": "2026-07-24T12:00:00Z", "ended_at": "2026-07-24T12:04:32Z",
     "questions_tested": 10, "passed_before": 3, "passed_after": 5,
     "gaps_found": 7, "canon_written": 7, "canon_promoted": 2, "canon_rejected": 5,
     "recalled_from_memory": 0, "cost_usd": 0.241, "tokens": 52300},
    {"cycle": 2, "started_at": "2026-07-24T12:10:00Z", "ended_at": "2026-07-24T12:13:48Z",
     "questions_tested": 10, "passed_before": 5, "passed_after": 7,
     "gaps_found": 5, "canon_written": 5, "canon_promoted": 3, "canon_rejected": 2,
     "recalled_from_memory": 1, "cost_usd": 0.198, "tokens": 44100},
    {"cycle": 3, "started_at": "2026-07-24T12:20:00Z", "ended_at": "2026-07-24T12:23:31Z",
     "questions_tested": 10, "passed_before": 7, "passed_after": 8,
     "gaps_found": 4, "canon_written": 4, "canon_promoted": 3, "canon_rejected": 1,
     "recalled_from_memory": 2, "cost_usd": 0.156, "tokens": 36800},
    {"cycle": 4, "started_at": "2026-07-24T12:30:00Z", "ended_at": "2026-07-24T12:34:10Z",
     "questions_tested": 10, "passed_before": 8, "passed_after": 9,
     "gaps_found": 3, "canon_written": 3, "canon_promoted": 3, "canon_rejected": 0,
     "recalled_from_memory": 2, "cost_usd": 0.112, "tokens": 27500},
]


def _ensure_seed_data() -> None:
    """Write demo rows to data/runs.jsonl on first run only.

    Never raises -- if the filesystem is read-only or anything else goes
    wrong, we simply fall through to the empty-state render instead of
    crashing the app.
    """
    try:
        if DATA_FILE.exists():
            return
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with DATA_FILE.open("w", encoding="utf-8") as f:
            for row in DEMO_ROWS:
                f.write(json.dumps(row) + "\n")
    except OSError:
        pass


def load_cycles() -> list[dict[str, Any]]:
    """Parse data/runs.jsonl into a list of dicts, skipping malformed lines.

    Never raises: missing file, empty file, and bad JSON all just yield
    fewer (or zero) rows rather than an exception.
    """
    cycles: list[dict[str, Any]] = []
    try:
        if not DATA_FILE.exists():
            return cycles
        with DATA_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if isinstance(row, dict) and "cycle" in row:
                    cycles.append(row)
    except OSError:
        return []
    cycles.sort(key=lambda r: _num(r.get("cycle")) or 0)
    return cycles


def _num(value: Any, default: float = 0.0) -> float:
    """Coerce a value to float, tolerating None/strings/junk."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_div(numer: float, denom: float, default: float = 0.0) -> float:
    if not denom:
        return default
    return numer / denom


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _fmt_usd(x: float) -> str:
    return f"${x:,.3f}"


def _fmt_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "--"
    seconds = int(round(seconds))
    m, s = divmod(max(0, seconds), 60)
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def _parse_ts(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def enrich(cycles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute display-ready derived fields for each cycle row, on a copy."""
    out: list[dict[str, Any]] = []
    for raw in cycles:
        row = dict(raw)
        qt = _num(row.get("questions_tested"))
        pa = _num(row.get("passed_after"))
        pb = _num(row.get("passed_before"))
        gaps = _num(row.get("gaps_found"))
        recalled = _num(row.get("recalled_from_memory"))
        cost = _num(row.get("cost_usd"))
        promoted = _num(row.get("canon_promoted"))
        rejected = _num(row.get("canon_rejected"))
        resolved = max(0.0, pa - pb)

        row["_pass_rate_after"] = _safe_div(pa, qt)
        row["_pass_rate_before"] = _safe_div(pb, qt)
        row["_resolved"] = resolved
        row["_cost_per_resolved"] = _safe_div(cost, max(1.0, resolved))
        row["_memory_reuse_rate"] = _safe_div(recalled, max(1.0, gaps))

        start = _parse_ts(row.get("started_at"))
        end = _parse_ts(row.get("ended_at"))
        duration = (end - start).total_seconds() if (start and end) else None

        row["_cycle_disp"] = int(_num(row.get("cycle")))
        row["_pass_rate_after_disp"] = _fmt_pct(row["_pass_rate_after"])
        row["_cost_disp"] = _fmt_usd(cost)
        row["_cost_per_resolved_disp"] = _fmt_usd(row["_cost_per_resolved"])
        row["_duration_disp"] = _fmt_duration(duration)
        row["_gaps_disp"] = int(gaps)
        row["_promoted_disp"] = int(promoted)
        row["_rejected_disp"] = int(rejected)
        row["_recalled_disp"] = int(recalled)
        out.append(row)
    return out


def compute_stats(enriched: list[dict[str, Any]]) -> dict[str, str]:
    """Four headline stat-tile values, derived from the latest cycle
    (except total canon promoted, which sums across every cycle)."""
    if not enriched:
        return {
            "pass_rate": "--",
            "canon_promoted": "--",
            "cost_per_resolved": "--",
            "memory_reuse": "--",
        }
    latest = enriched[-1]
    total_promoted = sum(int(_num(r.get("canon_promoted"))) for r in enriched)
    return {
        "pass_rate": latest["_pass_rate_after_disp"],
        "canon_promoted": str(total_promoted),
        "cost_per_resolved": latest["_cost_per_resolved_disp"],
        "memory_reuse": _fmt_pct(latest["_memory_reuse_rate"]),
    }


# ---------------------------------------------------------------------------
# Hand-rolled inline SVG line chart — no chart library, no CDN.
# Mark spec follows the dataviz skill: 2px line, ~10% opacity area wash,
# >=8px end markers with a surface-color ring, hairline recessive gridlines,
# a single direct label at the endpoint (never one per point).
# ---------------------------------------------------------------------------
def build_line_svg(
    points: list[tuple[float, float]],
    *,
    color: str,
    fmt,
    width: int = 640,
    height: int = 220,
) -> str:
    if not points:
        return ""

    pad_l, pad_r, pad_t, pad_b = 46, 20, 18, 30
    surface = "#151513"
    grid = "#2c2c2a"
    axis_ink = "#383835"
    muted = "#898781"

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_min, x_max = min(xs), max(xs)
    y_min_data, y_max_data = min(ys), max(ys)
    y_min = min(0.0, y_min_data)
    span = (y_max_data - y_min) or 1.0
    y_max = y_max_data + span * 0.18
    if y_max <= y_min:
        y_max = y_min + 1.0

    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    def sx(x: float) -> float:
        if x_max == x_min:
            return pad_l + plot_w / 2
        return pad_l + (x - x_min) / (x_max - x_min) * plot_w

    def sy(y: float) -> float:
        return pad_t + (1 - (y - y_min) / (y_max - y_min)) * plot_h

    coords = [(sx(x), sy(y)) for x, y in points]
    baseline_y = pad_t + plot_h

    line_d = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in coords)
    area_d = (
        f"M {coords[0][0]:.1f} {baseline_y:.1f} "
        + " L ".join(f"{px:.1f} {py:.1f}" for px, py in coords)
        + f" L {coords[-1][0]:.1f} {baseline_y:.1f} Z"
    )

    parts: list[str] = []
    parts.append(
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'role="img" aria-label="Line chart" preserveAspectRatio="xMidYMid meet">'
    )

    # Hairline horizontal gridlines + y-axis tick labels (rounded values).
    n_ticks = 4
    for i in range(n_ticks):
        val = y_min + (y_max - y_min) * i / (n_ticks - 1)
        y = sy(val)
        parts.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - pad_r}" y2="{y:.1f}" '
            f'stroke="{grid}" stroke-width="1" />'
        )
        parts.append(
            f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-size="11" fill="{muted}" font-family="system-ui, -apple-system, '
            f'\'Segoe UI\', sans-serif">{fmt(val)}</text>'
        )

    # Baseline / axis.
    parts.append(
        f'<line x1="{pad_l}" y1="{baseline_y:.1f}" x2="{width - pad_r}" y2="{baseline_y:.1f}" '
        f'stroke="{axis_ink}" stroke-width="1" />'
    )

    # X-axis cycle labels (all of them -- cycle counts are small).
    for (x_val, _y_val), (px, _py) in zip(points, coords):
        parts.append(
            f'<text x="{px:.1f}" y="{height - 8}" text-anchor="middle" '
            f'font-size="11" fill="{muted}" font-family="system-ui, -apple-system, '
            f'\'Segoe UI\', sans-serif">{int(x_val)}</text>'
        )

    # Area wash (~10% opacity), then the 2px line.
    parts.append(f'<path d="{area_d}" fill="{color}" opacity="0.10" stroke="none" />')
    parts.append(
        f'<path d="{line_d}" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linejoin="round" stroke-linecap="round" />'
    )

    # End-dot markers (>=8px) with a 2px surface ring; every point gets a
    # marker, but only the final point gets a text value (label selectively).
    for i, (px, py) in enumerate(coords):
        r = 5 if i == len(coords) - 1 else 4
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r}" fill="{color}" '
                      f'stroke="{surface}" stroke-width="2" />')

    last_x, last_y = coords[-1]
    last_val = points[-1][1]
    label_anchor = "end" if last_x > width * 0.75 else "start"
    label_dx = -10 if label_anchor == "end" else 10
    parts.append(
        f'<text x="{last_x + label_dx:.1f}" y="{last_y - 10:.1f}" text-anchor="{label_anchor}" '
        f'font-size="13" font-weight="600" fill="#ffffff" font-family="system-ui, -apple-system, '
        f'\'Segoe UI\', sans-serif">{fmt(last_val)}</text>'
    )

    parts.append("</svg>")
    return "".join(parts)


def build_charts(enriched: list[dict[str, Any]]) -> tuple[str, str]:
    if not enriched:
        return "", ""
    pass_points = [(r["_cycle_disp"], r["_pass_rate_after"] * 100.0) for r in enriched]
    cost_points = [(r["_cycle_disp"], r["_cost_per_resolved"]) for r in enriched]
    chart_pass = build_line_svg(
        pass_points, color="#3987e5", fmt=lambda v: f"{v:.0f}%"
    )
    chart_cost = build_line_svg(
        cost_points, color="#d95926", fmt=lambda v: f"${v:.2f}"
    )
    return chart_pass, chart_cost


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/evolution")


@app.get("/evolution", response_class=None)
def evolution(request: Request):
    _ensure_seed_data()
    raw_cycles = load_cycles()
    enriched = enrich(raw_cycles)
    stats = compute_stats(enriched)
    chart_pass_svg, chart_cost_svg = build_charts(enriched)
    context = {
        "request": request,
        "has_data": bool(enriched),
        "cycles": list(reversed(enriched)),  # newest first in the table
        "stats": stats,
        "chart_pass_svg": chart_pass_svg,
        "chart_cost_svg": chart_cost_svg,
        "cycle_count": len(enriched),
        "refresh_seconds": 5,
    }
    return templates.TemplateResponse("evolution.html", context)


@app.get("/api/cycles")
def api_cycles() -> JSONResponse:
    _ensure_seed_data()
    cycles = load_cycles()
    return JSONResponse(content=cycles)


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
