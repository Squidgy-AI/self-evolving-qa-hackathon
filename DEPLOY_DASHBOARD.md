# Dashboard Deployment Guide

The Evolution Dashboard visualizes the self-evolving system's improvement over time.

**Requirements for Hackathon:**
- Must be publicly accessible (no auth) for Replay QA scanning
- Working URL required for Devpost submission
- Judges can follow along during live demo

## Option 1: Render (Recommended - Free Tier)

### Automatic Deployment via Blueprint

1. **Push to GitHub** (already done)
   ```bash
   git push origin engine/evolution-loop
   ```

2. **Connect to Render**
   - Go to https://dashboard.render.com/blueprints
   - Click "New Blueprint Instance"
   - Connect your GitHub account
   - Select `Squidgy-AI/self-evolving-qa-hackathon`
   - Select branch: `engine/evolution-loop`
   - Render reads `render.yaml` and auto-deploys

3. **Get the URL**
   - Dashboard will be at: `https://<app-name>.onrender.com/evolution`
   - Health check: `https://<app-name>.onrender.com/health`

### Manual Deployment (if blueprint doesn't work)

1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Connect GitHub repo
4. Configure:
   - **Name**: `evolution-dashboard`
   - **Region**: Oregon (fastest free tier)
   - **Branch**: `engine/evolution-loop`
   - **Build Command**: `pip install -r dashboard/requirements.txt`
   - **Start Command**: `uvicorn dashboard.app:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
5. Click "Create Web Service"

## Option 2: Vercel (Alternative)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd dashboard/
vercel --prod
```

## Option 3: Railway

```bash
# Install Railway CLI
npm i -g @railway/cli

# Deploy
railway login
railway init
railway up
```

## Testing Deployment

Once deployed, verify these endpoints work:

### 1. Health Check
```bash
curl https://your-app.onrender.com/health
```
Expected: `{"status": "ok"}`

### 2. Dashboard
```bash
curl https://your-app.onrender.com/evolution
```
Expected: HTML page with charts and cycle table

### 3. API Endpoint
```bash
curl https://your-app.onrender.com/api/cycles
```
Expected: JSON array of cycle data

## For the Demo

### Before Demo Starts
1. Seed with demo data (automatic on first deploy)
2. Run 2-3 real cycles to show live data:
   ```bash
   python -m engine.loop
   ```
3. Data syncs to dashboard automatically (reads `data/runs.jsonl`)

### During Demo
- Open dashboard URL in browser
- Show "pass rate climbing" chart to judges
- Trigger a cycle: `python -m engine.loop`
- Refresh dashboard to show new data point

### Replay QA Integration
Once deployed, trigger Replay scan:
```python
from clients.replay_client import ReplayClient

replay = ReplayClient()
scan = replay.create_project(
    url="https://your-app.onrender.com/evolution",
    dry_run=False  # Actually spend credits
)
```

Replay will crawl all routes and root-cause any bugs found.

## Troubleshooting

### "Application failed to respond"
Check logs in Render dashboard. Common issues:
- PORT env var not set (Render sets this automatically)
- Missing `data/` directory (app creates this on first run)

### "Empty dashboard"
- Dashboard seeds with demo data on first run
- If empty, run a cycle: `python -m engine.loop`
- Or manually create `data/runs.jsonl` with sample data

### "Build failed"
- Verify `dashboard/requirements.txt` exists
- Check Python version (should be 3.11)
- Build command: `pip install -r dashboard/requirements.txt`

## Environment Variables

Dashboard doesn't need any environment variables — it's read-only, just renders `data/runs.jsonl`.

## Cost

**Render Free Tier:**
- 750 hours/month free
- App sleeps after 15 min of inactivity
- Cold start: ~30 seconds
- Perfect for demo + Devpost submission

**For Production:**
- Upgrade to Starter plan ($7/month) for always-on
- Or use Guild AI self-hosted dashboard instead

---

**Next Steps After Deployment:**
1. Save the URL: `https://your-app.onrender.com/evolution`
2. Add to Devpost submission
3. Test Replay QA scan
4. Practice demo flow (open dashboard → trigger cycle → show improvement)
