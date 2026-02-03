@"
# Quick Railway URL Finder and Tester

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "RAILWAY APP URL FINDER & TESTER" -ForegroundColor Yellow
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ""

Write-Host "Your Railway Dashboard URL:" -ForegroundColor White
Write-Host "https://railway.com/project/f748c30b-8732-480e-beb1-0fef0c89181d" -ForegroundColor Gray
Write-Host ""

Write-Host "To find your PUBLIC app URL:" -ForegroundColor Yellow
Write-Host "1. Go to the Railway dashboard link above" -ForegroundColor White
Write-Host "2. Click on your service (omni_agent)" -ForegroundColor White
Write-Host "3. Look for 'Settings' tab" -ForegroundColor White
Write-Host "4. Find 'Domains' section" -ForegroundColor White
Write-Host "5. Copy the URL (looks like: xxx.up.railway.app)" -ForegroundColor White
Write-Host ""

Write-Host "Common Railway URL patterns to try:" -ForegroundColor Yellow
$urls = @(
    "https://omni-ai-agent-production.up.railway.app",
    "https://web-production-4b50.up.railway.app",
    "https://omni-agent.up.railway.app"
)

foreach ($url in $urls) {
    Write-Host "Testing: " -NoNewline -ForegroundColor White
    Write-Host $url -ForegroundColor Cyan
    
    try {
        $response = Invoke-WebRequest -Uri "$url/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host "  ✅ FOUND! Status: $($response.StatusCode)" -ForegroundColor Green
        Write-Host "  Response: $($response.Content)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "🎉 YOUR APP URL IS: $url" -ForegroundColor Green
        Write-Host ""
        Write-Host "Now testing the workflow..." -ForegroundColor Yellow
        
        # Test the workflow
        $body = @{
            dry_run = $true
            duration = 10
        } | ConvertTo-Json
        
        Write-Host "Calling /api/animal-facts/run (this may take 2-5 minutes)..." -ForegroundColor White
        $start = Get-Date
        
        try {
            $workflowResponse = Invoke-WebRequest -Uri "$url/api/animal-facts/run" `
                -Method POST `
                -Body $body `
                -ContentType "application/json" `
                -TimeoutSec 360 `
                -UseBasicParsing `
                -ErrorAction Stop
            
            $elapsed = (Get-Date) - $start
            Write-Host ""
            Write-Host "✅ WORKFLOW COMPLETED!" -ForegroundColor Green
            Write-Host "Time taken: $($elapsed.TotalSeconds) seconds" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Response:" -ForegroundColor Yellow
            Write-Host $workflowResponse.Content -ForegroundColor Gray
            
        } catch {
            $elapsed = (Get-Date) - $start
            Write-Host ""
            Write-Host "❌ WORKFLOW FAILED/TIMEOUT" -ForegroundColor Red
            Write-Host "Time before failure: $($elapsed.TotalSeconds) seconds" -ForegroundColor Cyan
            Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        }
        
        break
    } catch {
        Write-Host "  ❌ Not found or error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "If none of these worked, please:" -ForegroundColor Yellow
Write-Host "1. Go to your Railway dashboard" -ForegroundColor White
Write-Host "2. Copy the public domain from Settings > Domains" -ForegroundColor White
Write-Host "3. Share it with me" -ForegroundColor White
"@
