---
description: Deploy OMNI to Railway
---

# Deploy to Railway

This workflow guides you through deploying OMNI to Railway with all necessary configurations.

## Prerequisites

- Railway account (https://railway.app)
- GitHub repository with your code
- API keys ready (OpenRouter, Kie.ai, Blotato)

## Step 1: Prepare Environment Variables

Before deploying, gather all required API keys:

```bash
# Check .env.example for all required variables
cat .env.example
```

**Required:**
- `OPENROUTER_API_KEY` - For AI model access
- `KIE_API_KEY` - For Sora 2 video generation

**Optional but recommended:**
- `BLOTATO_API_KEY` - For social media posting
- `GITHUB_TOKEN` - For self-update feature

## Step 2: Push to GitHub

```bash
# Make sure all changes are committed
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

## Step 3: Create Railway Project

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your `omni_agent` repository
5. Railway will auto-detect the configuration from `nixpacks.toml`

## Step 4: Configure Environment Variables

In Railway dashboard:

1. Go to your project → Variables tab
2. Add each variable from `.env.example`:

```
OPENROUTER_API_KEY=sk-or-v1-xxxxx
KIE_API_KEY=xxxxx
BLOTATO_API_KEY=xxxxx
SECRET_KEY=xxxxx
VIDEO_OUTPUT_DIR=/tmp/omni_videos
```

**Note:** Railway automatically provides `DATABASE_URL` for PostgreSQL

## Step 5: Add PostgreSQL Database

1. In Railway project, click "New"
2. Select "Database" → "PostgreSQL"
3. Railway will automatically set `DATABASE_URL` environment variable

## Step 6: Deploy

Railway will automatically deploy when you push to GitHub.

**Manual deployment:**
```bash
# In Railway dashboard, click "Deploy" button
```

## Step 7: Verify Deployment

### Check Health Endpoint

```bash
curl https://your-app.railway.app/health
```

Expected response:
```json
{"status": "healthy"}
```

### Check System Status

```bash
curl https://your-app.railway.app/api/status
```

### Test Animal Facts Workflow

```bash
curl -X POST https://your-app.railway.app/api/animal-facts/preview \
  -H "Content-Type: application/json" \
  -d '{"animal_id": "penguin"}'
```

## Step 8: Monitor First Execution

The Animal Facts workflow runs every 6 hours automatically.

**Check scheduler status:**
```bash
curl https://your-app.railway.app/api/scheduler/schedules
```

**View logs in Railway:**
1. Go to project → Deployments
2. Click on latest deployment
3. View logs in real-time

## Troubleshooting

### Deployment Failed

**Check build logs:**
1. Railway dashboard → Deployments → Click failed deployment
2. Look for error messages in build logs

**Common issues:**
- Missing environment variables → Add in Railway dashboard
- Python version mismatch → Check `nixpacks.toml`
- Dependency conflicts → Check `requirements.txt`

### App Crashes on Startup

**Check runtime logs:**
```bash
# In Railway dashboard, view deployment logs
```

**Common causes:**
- Missing `DATABASE_URL` → Add PostgreSQL database
- Invalid API keys → Verify in Variables tab
- Port binding issues → Railway auto-assigns PORT

### Video Generation Fails

**Check Kie.ai API key:**
```bash
# Test the API key
curl https://api.kie.ai/api/v1/jobs/createTask \
  -H "Authorization: Bearer YOUR_KIE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"sora-2-text-to-video","input":{"prompt":"test"}}'
```

**Check logs for errors:**
- Look for "Kie.ai" in Railway logs
- Verify API quota/credits

## Rollback Procedure

If deployment fails:

1. **In Railway dashboard:**
   - Go to Deployments
   - Find last working deployment
   - Click "Redeploy"

2. **Via Git:**
   ```bash
   git revert HEAD
   git push origin main
   ```

## Post-Deployment Checklist

- [ ] Health endpoint responds
- [ ] System status shows all components active
- [ ] Preview endpoint works
- [ ] Scheduler is configured (check `/api/scheduler/schedules`)
- [ ] Database is connected
- [ ] Logs show no errors
- [ ] First workflow execution succeeds

## Monitoring

**View active workflows:**
```bash
curl https://your-app.railway.app/api/workflows
```

**View scheduler logs:**
```bash
curl https://your-app.railway.app/api/scheduler/logs
```

**Check recent executions:**
- Railway dashboard → Logs
- Filter by "Animal Facts" or "workflow"

## Next Steps

After successful deployment:

1. **Test the full workflow:**
   ```bash
   curl -X POST https://your-app.railway.app/api/animal-facts/run \
     -H "Content-Type: application/json" \
     -d '{"dry_run": true, "duration": 10}'
   ```

2. **Monitor first scheduled execution** (wait 6 hours or trigger manually)

3. **Set up alerts** (optional):
   - Add email notifications
   - Configure Sentry for error tracking

4. **Scale if needed:**
   - Railway dashboard → Settings → Increase resources
