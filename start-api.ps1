Set-Location $PSScriptRoot
if (-not (Test-Path ".env")) {
    Write-Host "Сначала запустите: .\scripts\setup.ps1" -ForegroundColor Red
    exit 1
}
.\.venv\Scripts\uvicorn.exe api.main:app --host 0.0.0.0 --port 8080 --reload
