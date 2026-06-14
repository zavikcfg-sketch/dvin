$envPath = Join-Path $PSScriptRoot "..\.env"
$examplePath = Join-Path $PSScriptRoot "..\.env.example"

Write-Host "=== Настройка TVIL Booking Bot ===" -ForegroundColor Cyan

if (Test-Path $envPath) {
    $overwrite = Read-Host ".env уже существует. Перезаписать? (y/N)"
    if ($overwrite -ne "y") { exit 0 }
}

Copy-Item $examplePath $envPath

$token = Read-Host "BOT_TOKEN (от @BotFather)"
if ($token) {
    (Get-Content $envPath) -replace 'BOT_TOKEN=.*', "BOT_TOKEN=$token" | Set-Content $envPath
}

$adminId = Read-Host "Ваш Telegram ID (от @userinfobot)"
if ($adminId) {
    (Get-Content $envPath) -replace 'ADMIN_IDS=.*', "ADMIN_IDS=$adminId" | Set-Content $envPath
}

$tvilSecret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
(Get-Content $envPath) -replace 'TVIL_WEBHOOK_SECRET=.*', "TVIL_WEBHOOK_SECRET=$tvilSecret" | Set-Content $envPath
Write-Host "TVIL_WEBHOOK_SECRET: $tvilSecret" -ForegroundColor Yellow

New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot "..\data") -Force | Out-Null

Write-Host "`nГотово! Файл .env создан." -ForegroundColor Green
Write-Host "Запуск бота:  .\start-bot.ps1"
Write-Host "Запуск API:   .\start-api.ps1"
