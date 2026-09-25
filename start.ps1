# Script de lancement rapide de PayByPhone Buyer (Backend + Frontend)
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   PayByPhone Smart Buyer - Lancement     " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$backend = Start-Process python -ArgumentList "-m uvicorn server.app:app --port 8000 --reload" -PassThru -NoNewWindow
Write-Host "[+] Backend démarré sur http://localhost:8000 (PID: $($backend.Id))" -ForegroundColor Green

Set-Location "$PSScriptRoot\frontend"
Write-Host "[+] Lancement du frontend React sur http://localhost:5173..." -ForegroundColor Green
npm run dev
