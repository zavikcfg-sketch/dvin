# TVIL Booking Bot

Telegram-бот для **посуточного бронирования** с интеграцией **TVIL** (без iCal и без API TVIL).

Отдельный проект — только бронирование, без VPN.

## Возможности

- Бронирование номеров через календарь в Telegram
- Связка с объектом на TVIL (object ID + ссылка на объявление)
- Импорт занятости с TVIL (вручную или через webhook)
- Уведомления админу о закрытии дат на TVIL
- HTTP API для автоматизации

## Быстрый старт

```powershell
cd tvil-booking-bot
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\scripts\setup.ps1
```

Запуск:

```powershell
.\start-bot.ps1      # терминал 1
.\start-api.ps1      # терминал 2
```

## Docker

```bash
cd tvil-booking-bot
cp .env.example .env   # заполните BOT_TOKEN и ADMIN_IDS
docker compose up -d --build
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/admin` | Панель администратора |
| `/add_room Название \| описание \| цена` | Добавить комнату |
| `/set_tvil ID \| object_id \| ссылка` | Связать с TVIL |
| `/tvil_import ID` | Импорт занятых дат |
| `/tvil_done ID` | Отметить выгрузку на TVIL |
| `/tvil` | Инструкция |

## Структура

```
tvil-booking-bot/
├── bot/           # Telegram-бот
├── api/           # Webhook TVIL + health
├── core/          # Модели, сервисы, TVIL
├── data/          # SQLite (локально)
├── docker-compose.yml
└── Dockerfile
```

## Отличие от telegram-vpn-bot

Проект `telegram-vpn-bot` — VPN + бронирование в одном репозитории.
Папка `tvil-booking-bot` — **только ваш бот бронирования**, можно деплоить отдельно.
