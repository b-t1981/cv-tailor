# CV Tailor - demarrage fiable (backend + frontend + redirection port 3030)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "=== CV Tailor ===" -ForegroundColor Cyan
Write-Host ""

# Arreter les anciennes instances uvicorn/node
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*uvicorn*app.main*" -or $_.CommandLine -like "*redirect-3030.js*" } |
    ForEach-Object {
        if ($_.ProcessId -and $_.ProcessId -ne 0) {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }

# Liberer les ports si occupes par une ancienne instance
foreach ($port in 3000, 3030, 8001) {
    Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object {
            if ($_ -and $_ -ne 0) {
                Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
            }
        }
}

# Backend
$Backend = Join-Path $Root "backend"
if (-not (Test-Path (Join-Path $Backend ".env"))) {
    Copy-Item (Join-Path $Backend ".env.example") (Join-Path $Backend ".env")
}

Write-Host "Demarrage backend (port 8001)..." -ForegroundColor Yellow
Start-Process -FilePath "$Backend\venv\Scripts\uvicorn.exe" `
    -ArgumentList "app.main:app", "--host", "127.0.0.1", "--port", "8001" `
    -WorkingDirectory $Backend `
    -WindowStyle Hidden

Start-Sleep -Seconds 2

# Frontend
$Frontend = Join-Path $Root "frontend"
Set-Location $Frontend

if (-not (Test-Path ".env.local")) {
    Copy-Item ".env.local.example" ".env.local"
}

if (-not (Test-Path ".next\BUILD_ID")) {
    Write-Host "Build frontend (premiere fois, ~30s)..." -ForegroundColor Yellow
    npm run build
}

Write-Host "Demarrage frontend (port 3000)..." -ForegroundColor Yellow
Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm run start" `
    -WorkingDirectory $Frontend `
    -WindowStyle Hidden

Start-Sleep -Seconds 3

# Redirection 3030 -> 3000 (si vous tapez le mauvais port)
Write-Host "Redirection port 3030 -> 3000..." -ForegroundColor Yellow
Start-Process -FilePath "node.exe" `
    -ArgumentList (Join-Path $Root "scripts\redirect-3030.js") `
    -WorkingDirectory $Root `
    -WindowStyle Hidden

Start-Sleep -Seconds 2

# Verification
$feOk = $false
$beOk = $false
try {
    $feOk = (Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200
} catch { }
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/health" -TimeoutSec 5
    $beOk = $health.status -eq "ok"
} catch { }

Write-Host ""
if ($feOk -and $beOk) {
    Write-Host "Application prete !" -ForegroundColor Green
} else {
    Write-Host "Demarrage en cours..." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "  URL principale : http://localhost:3000" -ForegroundColor Green
Write-Host "  URL alternative: http://localhost:3030  (redirige vers 3000)" -ForegroundColor Green
Write-Host "  API backend    : http://localhost:8001" -ForegroundColor Green
Write-Host ""
Write-Host "Laissez cette fenetre ouverte. Ctrl+C pour arreter." -ForegroundColor Gray
Write-Host ""

# Garder le script actif et ouvrir le navigateur
Start-Process "http://localhost:3000"

try {
    while ($true) { Start-Sleep -Seconds 60 }
} finally {
    Write-Host "Arret des services..." -ForegroundColor Yellow
    foreach ($port in 3000, 3030, 8001) {
        Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique |
            ForEach-Object {
                if ($_ -and $_ -ne 0) {
                    Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
                }
            }
    }
}
