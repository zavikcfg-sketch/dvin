Set-Location $PSScriptRoot
if (-not (Test-Path ".env")) {
    Write-Host "Сначала запустите: .\scripts\setup.ps1" -ForegroundColor Red
    exit 1
}
.\.venv\Scripts\python.exe -m bot.main
