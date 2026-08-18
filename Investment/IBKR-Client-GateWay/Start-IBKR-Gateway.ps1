<#
.SYNOPSIS
  Starts IBKR Client Portal Gateway from your install folder.

  Recommended (once): set a user environment variable so this script finds the install anywhere:
    IBKR_GATEWAY_ROOT = C:\Investment\IBKR-Client-GateWay\clientportal.gw

  Optional: add IBKR_GATEWAY_BIN if your launcher lives only under ...\bin:
    IBKR_GATEWAY_BIN = C:\Investment\IBKR-Client-GateWay\clientportal.gw\bin

  Run from anywhere after PATH tweak (optional):
    PowerShell -ExecutionPolicy Bypass -File "C:\Investment\IBKR-Client-GateWay\Start-IBKR-Gateway.ps1"
#>

param(
    [string]$GatewayRoot = $env:IBKR_GATEWAY_ROOT,
    [string]$GatewayBin = $env:IBKR_GATEWAY_BIN
)

$ErrorActionPreference = "Stop"

if (-not $GatewayRoot) {
    $candidate = Join-Path $PSScriptRoot "clientportal.gw"
    if (Test-Path $candidate) {
        $GatewayRoot = $candidate
    } else {
        $GatewayRoot = $PSScriptRoot
    }
}

if (-not $GatewayBin) {
    $GatewayBin = Join-Path $GatewayRoot "bin"
}

$launchers = @(
    (Join-Path $GatewayBin "run.bat"),
    (Join-Path $GatewayBin "Run.bat"),
    (Join-Path $GatewayBin "gateway.bat"),
    (Join-Path $GatewayBin "clientportal.gw.exe"),
    (Join-Path $GatewayRoot "run.bat"),
    (Join-Path $GatewayRoot "Run.bat"),
    (Join-Path $GatewayRoot "bin\run.bat")
)

$picked = $launchers | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $picked) {
    Write-Host "Could not find a launcher under:" -ForegroundColor Yellow
    Write-Host "  Root: $GatewayRoot"
    Write-Host "  Bin:  $GatewayBin"
    Write-Host ""
    Write-Host "Set IBKR_GATEWAY_ROOT to your clientportal.gw folder, or edit this script."
    Write-Host "Files looked for: $( $launchers -join ', ' )"
    exit 1
}

$confYaml = Join-Path $GatewayRoot "root\conf.yaml"
if (-not (Test-Path $confYaml)) {
    Write-Host "Config not found: $confYaml" -ForegroundColor Red
    exit 1
}

$runBat = Join-Path $GatewayRoot "bin\run.bat"
if (-not (Test-Path $runBat)) {
    Write-Host "run.bat not found: $runBat" -ForegroundColor Red
    exit 1
}

Write-Host "Starting: $runBat root\conf.yaml" -ForegroundColor Green
Write-Host "Working directory: $GatewayRoot"
Write-Host "After startup, open https://localhost:5000 and login." -ForegroundColor Cyan

Start-Process -FilePath $runBat -ArgumentList "root\conf.yaml" -WorkingDirectory $GatewayRoot
