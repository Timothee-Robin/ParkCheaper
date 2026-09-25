# ==============================================================================
# PayByPhone Buyer - Automated Build Script (Frontend, Standalone EXE & MSI)
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " PAYBYPHONE BUYER - BUILD SUITE (EXE & MSI)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Build React Frontend
Write-Host "`n[*] Step 1/4: Building Frontend React App (Vite)..." -ForegroundColor Yellow
Push-Location frontend
try {
    npm run build
} finally {
    Pop-Location
}
if (!(Test-Path "frontend\dist\index.html")) {
    Write-Error "Frontend build failed: frontend\dist\index.html not found."
}
Write-Host "[+] Frontend built successfully!" -ForegroundColor Green

# 2. Build Standalone Executable with PyInstaller
Write-Host "`n[*] Step 2/4: Building Standalone Executable (PyInstaller)..." -ForegroundColor Yellow
pyinstaller --noconfirm PaybyPhoneBuyer.spec
if (!(Test-Path "dist\PaybyPhoneBuyer.exe")) {
    Write-Error "PyInstaller build failed: dist\PaybyPhoneBuyer.exe not found."
}
$exeSizeMb = [math]::Round((Get-Item "dist\PaybyPhoneBuyer.exe").Length / 1MB, 2)
Write-Host "[+] Standalone executable built: dist\PaybyPhoneBuyer.exe ($exeSizeMb MB)" -ForegroundColor Green

# 3. Locate or Setup WiX Toolset for MSI building
Write-Host "`n[*] Step 3/4: Locating WiX Toolset for MSI generation..." -ForegroundColor Yellow

$wixCandidates = @(
    "candle.exe",
    "C:\Program Files (x86)\WiX Toolset v3.11\bin\candle.exe",
    "C:\Program Files (x86)\WiX Toolset v3.14\bin\candle.exe",
    "$PSScriptRoot\.tools\wix\candle.exe"
)

$candlePath = $null
foreach ($cand in $wixCandidates) {
    if (Get-Command $cand -ErrorAction SilentlyContinue) {
        $candlePath = (Get-Command $cand).Source
        break
    } elseif (Test-Path $cand) {
        $candlePath = $cand
        break
    }
}

if (-not $candlePath) {
    Write-Host "[*] WiX Toolset not found in PATH. Downloading portable WiX binaries..." -ForegroundColor Cyan
    $toolsDir = Join-Path $PSScriptRoot ".tools\wix"
    New-Item -ItemType Directory -Force -Path $toolsDir | Out-Null
    $zipPath = Join-Path $toolsDir "wix311-binaries.zip"
    $wixUrl = "https://github.com/wixtoolset/wix3/releases/download/wix3112rtm/wix311-binaries.zip"
    
    try {
        Write-Host "    Downloading from $wixUrl..." -ForegroundColor DarkGray
        curl.exe -L -s $wixUrl -o $zipPath
        Expand-Archive -Path $zipPath -DestinationPath $toolsDir -Force
        Remove-Item $zipPath -Force
        $candlePath = Join-Path $toolsDir "candle.exe"
        Write-Host "[+] Portable WiX Toolset ready at $toolsDir" -ForegroundColor Green
    } catch {
        Write-Warning "Could not download WiX binaries: $_"
        Write-Warning "The standalone executable (dist\PaybyPhoneBuyer.exe) is ready. To compile the MSI locally, install WiX Toolset or run via GitHub Actions."
    }
}

if ($candlePath -and (Test-Path $candlePath)) {
    $wixBinDir = Split-Path $candlePath -Parent
    $lightPath = Join-Path $wixBinDir "light.exe"

    Write-Host "[*] Step 4/4: Compiling Windows MSI Installer..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path "build" | Out-Null

    & $candlePath -arch x64 -ext WixUIExtension -out "build\PaybyPhoneBuyer.wixobj" "installer\PaybyPhoneBuyer.wxs"
    & $lightPath -ext WixUIExtension -out "dist\PaybyPhoneBuyer.msi" "build\PaybyPhoneBuyer.wixobj"

    if (Test-Path "dist\PaybyPhoneBuyer.msi") {
        $msiSizeMb = [math]::Round((Get-Item "dist\PaybyPhoneBuyer.msi").Length / 1MB, 2)
        Write-Host "[+] Windows MSI Installer created: dist\PaybyPhoneBuyer.msi ($msiSizeMb MB)" -ForegroundColor Green
    }
}

# 4. Generate Checksums
$checksumFiles = @()
foreach ($f in @("dist\PaybyPhoneBuyer.exe", "dist\PaybyPhoneBuyer-cli.exe", "dist\PaybyPhoneBuyer.msi")) {
    if (Test-Path $f) { $checksumFiles += $f }
}
if ($checksumFiles.Count -gt 0) {
    Get-FileHash $checksumFiles -Algorithm SHA256 |
        ForEach-Object { "$($_.Hash)  $(Split-Path $_.Path -Leaf)" } |
        Set-Content "dist\SHA256SUMS.txt"
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " BUILD COMPLETED SUCCESSFULLY" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Get-ChildItem dist | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
