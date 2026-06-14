# Telegram VPN Bot (VLESS + Reality)

Telegram-бот для выдачи VPN-ключей с обходом блокировок и белых списков.
Протокол: **VLESS + Reality** — трафик маскируется под обычный HTTPS к легитимным сайтам.

## Возможности

- Telegram-бот: выдача ключей, QR-коды, статус подписки
- Пробный период и тарифные планы
- Админ-панель (веб): серверы, пользователи, статистика
- Админ-команды в боте: `/admin`, `/grant <id> <дней>`
- Генерация ссылок для Hiddify, v2rayN, Streisand

## Быстрый старт

### 1. Создайте бота

1. Напишите [@BotFather](https://t.me/BotFather) → `/newbot`
2. Скопируйте токен

### 2. Настройте проект

Требуется **Python 3.11–3.13** (на 3.14 часть пакетов пока не собирается).

```bash
cd telegram-vpn-bot
py -3.12 -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env
```

Заполните `.env`:
- `BOT_TOKEN` — токен от BotFather
- `ADMIN_IDS` — ваш Telegram ID (узнать: @userinfobot)
- `ADMIN_PASSWORD` — пароль для веб-панели

### 3. Запуск

```bash
# Терминал 1 — бот
python -m bot.main

# Терминал 2 — админ-панель
uvicorn api.main:app --host 0.0.0.0 --port 8080
```

Админ-панель: http://localhost:8080/admin/login

### 4. VPS и Xray

Нужен VPS **за пределами РФ**. Рекомендуемые провайдеры:

| Провайдер | Цена | Примечание |
|-----------|------|------------|
| [Hetzner](https://www.hetzner.com) | от €4/мес | Надёжный, EU |
| [Aeza](https://aeza.net) | от 299₽/мес | Оплата картой РФ |
| [Vultr](https://www.vultr.com) | от $5/мес | Много локаций |
| [BuyVM](https://buyvm.net) | от $3.5/мес | Анти-DMCA |

На VPS (Ubuntu 22.04+):

```bash
ssh root@YOUR_VPS_IP
bash scripts/install_xray.sh
```

Скрипт выведет `Public Key`, `Short ID`, `UUID` — добавьте сервер в админ-панель.

## Как работает обход белых списков

**Reality** маскирует VPN-трафик под обычное HTTPS-соединение к разрешённому сайту (microsoft.com, apple.com и т.д.). Для DPI и фильтров это выглядит как обычный визит на белый сайт.

### Мобильный интернет (4G / белые списки)

Одного зарубежного VPS **недостаточно** — оператор блокирует иностранные IP. Нужна **цепочка из двух серверов**:

```
Телефон → Мост (РФ, белый IP) → Выход (EU) → Интернет
```

**Полная инструкция:** [docs/MOBILE_WHITELIST.md](docs/MOBILE_WHITELIST.md)

Скрипты:
- `scripts/install_exit_node.sh` — выходной сервер (VDSina NL)
- `scripts/install_bridge_ru.sh` — мост в РФ (Яндекс Облако или белый VPS)
- `scripts/check_white_ip.sh` — проверка IP

Рекомендации (домашний Wi‑Fi):
- Используйте SNI популярных сайтов из белого списка
- Порт 443 (стандартный HTTPS)
- Fingerprint: `chrome`
- При блокировке IP — смените VPS или используйте CDN

## Структура проекта

```
telegram-vpn-bot/
├── bot/           # Telegram-бот (aiogram 3)
├── api/           # FastAPI админ-панель
├── core/          # Модели, сервисы, конфиг
├── xray/          # Генерация VLESS-ссылок
├── admin/         # HTML-шаблоны
├── scripts/       # Установка Xray на VPS
└── docker-compose.yml
```

## Docker

```bash
cp .env.example .env
# Укажите DATABASE_URL=postgresql+asyncpg://vpn:vpn_password@db:5432/vpn_bot
docker compose up -d
```

## Дальнейшее развитие

- [ ] Автоматическая синхронизация клиентов с Xray API
- [ ] Оплата через Telegram Stars / ЮKassa
- [ ] Мониторинг трафика и health-check серверов
- [ ] Резервные серверы и автопереключение
- [ ] Рассылка через бота

## Важно

Используйте сервис в соответствии с законодательством вашей страны. Автор не несёт ответственности за использование.
