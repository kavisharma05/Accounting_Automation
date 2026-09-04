#Requires -Version 5.1
<#
.SYNOPSIS
  Bootstrap Railway project for accounting-automation.

.PREREQUISITES
  1. Railway CLI installed: npm install -g @railway/cli
  2. Logged in: railway login
  3. GitHub connected to Railway (for --repo deploy)

.USAGE
  .\scripts\railway_setup.ps1
#>

$ErrorActionPreference = "Stop"
$ProjectName = "accounting-automation"
$Repo = "kavisharma05/Accounting_Automation"

Write-Host "Checking Railway login..." -ForegroundColor Cyan
$whoami = railway whoami 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Not logged in. Run: railway login" -ForegroundColor Red
    exit 1
}
Write-Host "Logged in as: $whoami" -ForegroundColor Green

if (-not (Test-Path ".railway")) {
    Write-Host "Creating Railway project '$ProjectName'..." -ForegroundColor Cyan
    railway init --name $ProjectName
}

Write-Host "Adding PostgreSQL..." -ForegroundColor Cyan
railway add --database postgres

Write-Host "Adding Redis..." -ForegroundColor Cyan
railway add --database redis

Write-Host "Adding API service from GitHub..." -ForegroundColor Cyan
railway add --repo $Repo --service api

Write-Host "Adding Worker service from GitHub..." -ForegroundColor Cyan
railway add --repo $Repo --service worker

$secret = python -c "import secrets; print(secrets.token_hex(32))"

Write-Host "Setting API environment variables..." -ForegroundColor Cyan
$apiVars = @{
    "DATABASE_URL" = '${{Postgres.DATABASE_URL}}'
    "REDIS_URL"    = '${{Redis.REDIS_URL}}'
    "SECRET_KEY"   = $secret
    "ENVIRONMENT"  = "staging"
    "RUN_MIGRATIONS" = "true"
    "SERVE_FRONTEND" = "true"
    "MESSAGING_PROVIDER" = "mock"
    "DOCUMENT_PROVIDER" = "mock"
    "STORAGE_PROVIDER" = "local"
    "LOCAL_STORAGE_PATH" = "/tmp/documents"
    "GSP_PROVIDER" = "mock"
}
foreach ($kv in $apiVars.GetEnumerator()) {
    railway variable set "$($kv.Key)=$($kv.Value)" --service api --skip-deploys
}

Write-Host "Setting Worker environment variables..." -ForegroundColor Cyan
$workerVars = @{
    "DATABASE_URL" = '${{Postgres.DATABASE_URL}}'
    "REDIS_URL"    = '${{Redis.REDIS_URL}}'
    "SECRET_KEY"   = $secret
    "ENVIRONMENT"  = "staging"
    "MESSAGING_PROVIDER" = "mock"
    "DOCUMENT_PROVIDER" = "mock"
    "STORAGE_PROVIDER" = "local"
    "LOCAL_STORAGE_PATH" = "/tmp/documents"
}
foreach ($kv in $workerVars.GetEnumerator()) {
    railway variable set "$($kv.Key)=$($kv.Value)" --service worker --skip-deploys
}

Write-Host ""
Write-Host "=== Manual steps in Railway dashboard ===" -ForegroundColor Yellow
Write-Host "1. Worker service -> Settings -> Deploy -> Start Command:"
Write-Host "     python -m app.workers.runner"
Write-Host "2. API service -> Settings -> Networking -> Generate Domain"
Write-Host "3. API service -> Variables -> set CORS_ORIGINS to your public URL"
Write-Host "4. After first deploy, seed pilot org:"
Write-Host "     railway run --service api python scripts/seed_pilot_org.py"
Write-Host ""
Write-Host "Open dashboard: railway open" -ForegroundColor Cyan
