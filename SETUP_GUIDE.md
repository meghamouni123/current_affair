# CA Portal — Setup Guide
## Architecture
- **GitHub Actions** → ML pipeline (fetch + classify + summarize → Supabase)
- **Render** → Light server (DB reads only → frontend)

## Step 1: Supabase
1. Create project at https://supabase.com
2. Copy connection string: `postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres`

## Step 2: GitHub
Add secrets (Settings → Secrets → Actions):
- `DATABASE_URL` = your Supabase URL
- `NEWSDATA_API_KEY` = optional

Workflow file: `.github/workflows/daily_pipeline.yml`
Runs: 5:30 AM IST + 12:30 PM IST daily. Manual trigger available.

## Step 3: Render
1. New Web Service → connect GitHub repo
2. Root Directory: `.` (repo root, since render_server.py is at root)
3. Build: `pip install -r requirements-render.txt`
4. Start: `python render_server.py`
5. Add env var: `DATABASE_URL`
6. Health check: `/api/health`

## ⚠️ Security
Delete `backend/server.py` and `backend/scheduler.py` — these are the old heavy server files, no longer needed on Render.
