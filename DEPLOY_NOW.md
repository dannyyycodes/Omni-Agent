# Quick Deployment Guide

Since Railway CLI requires login and browser access is unavailable, here's how to deploy manually:

## Option 1: Deploy via Railway Dashboard (Recommended)

1. **Open Railway Dashboard:**
   - Go to: https://railway.app/dashboard
   - Login with your credentials

2. **Find Your Project:**
   - Look for "omni-ai-agent" or "omni_agent" project
   - Click to open it

3. **Trigger Deployment:**
   - Railway should auto-deploy from the latest GitHub push
   - If not, click "Deploy" or "Redeploy" button
   - Wait for build to complete (~3-5 minutes)

4. **Check Deployment Status:**
   - Go to "Deployments" tab
   - Watch build logs in real-time
   - Look for "Build successful" message

5. **Configure Environment Variables (if not set):**
   - Go to "Variables" tab
   - Add these required variables:
     ```
     OPENROUTER_API_KEY=sk-or-v1-xxxxx
     KIE_API_KEY=xxxxx
     SECRET_KEY=xxxxx
     VIDEO_OUTPUT_DIR=/tmp/omni_videos
     ```

6. **Test the Deployment:**
   - Once deployed, get your app URL (e.g., https://omni-ai-agent-production.up.railway.app)
   - Test health endpoint:
     ```bash
     curl https://YOUR-APP-URL.railway.app/health
     ```
   - Test workflow preview:
     ```bash
     curl -X POST https://YOUR-APP-URL.railway.app/api/animal-facts/preview \
       -H "Content-Type: application/json" \
       -d '{"animal_id": "penguin"}'
     ```

## Option 2: Test Locally First

Before deploying, test locally to identify the timeout issue:

```bash
# Set environment variables
$env:OPENROUTER_API_KEY="sk-or-v1-xxxxx"
$env:KIE_API_KEY="xxxxx"

# Run the diagnostic test
python test_workflow_timeout.py
```

This will:
- Check all environment variables
- Run the full workflow in dry-run mode
- Show detailed timing information
- Identify exactly where timeouts occur

## Option 3: Railway CLI (After Login)

If you want to use CLI:

```bash
# Login to Railway
railway login

# Link to project
railway link

# Deploy
railway up

# View logs
railway logs
```

## Testing the Timeout Issue

Once deployed (or running locally), test with:

```bash
# Dry run (generates video, doesn't post)
curl -X POST https://YOUR-APP-URL/api/animal-facts/run \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true, "duration": 10}'
```

Watch for:
- How long it takes to start video generation
- How long the polling loop runs
- Whether it times out at 300 seconds (5 minutes)
- Any specific error messages

## Expected Behavior

**Normal flow:**
1. Animal selection: ~2-5 seconds
2. Fact generation: ~3-10 seconds
3. Sora prompt creation: <1 second
4. Kie.ai video start: ~5-10 seconds
5. **Polling for completion: 2-5 minutes** ⬅️ This is where timeout likely occurs
6. Video download: ~10-30 seconds
7. FFmpeg composition: ~10-20 seconds

**Total expected time:** 3-7 minutes

## Timeout Configuration

Current settings in `nixpacks.toml`:
```toml
[start]
cmd = "gunicorn app:app --workers 2 --timeout 600 --keep-alive 600"
```

This gives 600 seconds (10 minutes) for requests, which should be enough.

## Next Steps

1. Deploy to Railway via dashboard
2. Get the app URL
3. Run the test command above
4. Share the results/logs so we can see exactly where it's timing out
