# VPN для мобильного интернета (белые списки)

Пошаговая инструкция: цепочка из двух серверов для работы на МТС, Мегафон, Билайн, Tele2 в режиме белых списков.

## Как это работает

```
Телефон ──VLESS+Reality──► Мост (РФ, «белый» IP) ──xHTTP──► Выход (EU) ──► Интернет
         SNI: ya.ru              IP в белом списке              VDSina NL
```

Мобильный оператор видит только соединение с разрешённым российским IP (Яндекс, VK и т.д.). Зарубежный сервер для оператора **невидим** — с ним говорит только мост.

| Роль | Где | Цена | Задача |
|------|-----|------|--------|
| **Выход (Exit)** | Нидерланды (VDSina) | ~150 ₽/мес | Выход в интернет |
| **Мост (Bridge)** | Яндекс Облако или VPS в РФ | 75–500 ₽/мес | «Белый» IP для телефона |

**Бюджет ~300 ₽:** VDSina 150 ₽ + дешёвый VPS-мост в РФ ~100–150 ₽ (нужно проверить IP).  
**Надёжнее:** VDSina 150 ₽ + Яндекс Облако ~400–500 ₽/мес.

---

## Часть 1. Выходной сервер (Европа)

### 1.1 Аренда

1. Зайдите на [vdsina.ru](https://vdsina.ru)
2. **Стандартный VPS** → локация **Амстердам**
3. ОС: **Ubuntu 22.04**
4. Оплата: ~150 ₽/мес

Запишите **IP выхода**: `EU_IP`

### 1.2 Установка Xray

```bash
# С Windows (PowerShell), скопируйте скрипт на сервер:
scp C:\Users\QWERTY_\Projects\telegram-vpn-bot\scripts\install_exit_node.sh root@EU_IP:/root/

ssh root@EU_IP
bash /root/install_exit_node.sh
```

Скрипт выведет и сохранит в `/root/exit-node.env`:

- `EXIT_UUID`
- `EXIT_PUBLIC_KEY` / `EXIT_PRIVATE_KEY`
- `EXIT_SHORT_ID`
- `EXIT_SNI` (по умолчанию `www.microsoft.com`)

**Сохраните эти значения** — они нужны для моста и клиентов.

### 1.3 Проверка

```bash
systemctl status xray
ss -tlnp | grep 443
```

---

## Часть 2. Мост в России

Два варианта — выберите один.

### Вариант A: Яндекс Облако (надёжнее для мобильного)

IP Яндекса почти всегда в белых списках.

#### 2A.1 Регистрация

1. [console.cloud.yandex.ru](https://console.cloud.yandex.ru) — аккаунт Yandex
2. Создайте **каталог** (folder)
3. Привяжите карту (списания посекундные)

#### 2A.2 Виртуальная машина

1. **Compute Cloud** → **Виртуальные машины** → **Создать**
2. Параметры:
   - Зона: `ru-central1-a` (или b/c)
   - Платформа: Intel Broadwell
   - **Прерываемая (preemptible)** — дешевле (~400–500 ₽/мес при 24/7)
   - 2 vCPU, 2 ГБ RAM (минимум 1/1 для теста)
   - Диск 10 ГБ
   - ОС: **Ubuntu 22.04 LTS**
   - Публичный IP: **автоматически**
3. Создать

Запишите **IP моста**: `BRIDGE_IP`

#### 2A.3 Firewall

В Yandex Cloud → **Группы безопасности** → разрешить **входящий TCP 443** с `0.0.0.0/0`.

#### 2A.4 Установка моста

На своём ПК подставьте данные с выходного сервера:

```bash
scp scripts/install_bridge_ru.sh root@BRIDGE_IP:/root/
ssh root@BRIDGE_IP

export EU_IP="1.2.3.4"              # IP VDSina
export EU_UUID="..."                # EXIT_UUID
export EU_PUBLIC_KEY="..."          # EXIT_PUBLIC_KEY
export EU_SHORT_ID="..."            # EXIT_SHORT_ID
export EU_SNI="www.microsoft.com"   # EXIT_SNI
export BRIDGE_SNI="ya.ru"           # маска для мобильного (Яндекс в белом списке)

bash install_bridge_ru.sh
```

Скрипт выведет **клиентские данные** для телефона.

---

### Вариант B: Дешёвый VPS в РФ (~100–150 ₽)

Подходит, если бюджет ограничен. **Не все IP «белые»** — обязательно проверьте.

Провайдеры: 4VPS, SprintHost, VDSina Москва, Timeweb MSK.

#### 2B.1 Проверка «белого» IP

1. Арендуйте VPS, получите IP
2. На сервере поднимите временный HTTPS на 443:

```bash
apt update && apt install -y nginx
echo "ok" > /var/www/html/index.html
# временно nginx на 443 — или certbot для теста
```

3. **С мобильного интернета (4G, не Wi‑Fi!)** откройте `https://BRIDGE_IP`
4. Если страница открылась — IP **белый**, можно ставить мост
5. Если таймаут — удалите VPS, возьмите другой IP/провайдера

Или используйте скрипт `scripts/check_white_ip.sh` (см. ниже).

#### 2B.2 Установка

Те же шаги, что в **2A.4**, с `BRIDGE_SNI=ya.ru` или `vk.com` (если IP VK Cloud).

---

## Часть 3. Подключение телефона

### 3.1 Приложения

| Платформа | Приложение |
|-----------|------------|
| Android | [Hiddify](https://play.google.com/store/apps/details?id=app.hiddify.com), v2rayNG |
| iOS | Shadowrocket, Streisand, V2Box |

Версия Xray в клиенте должна быть **актуальной** (25.x+). На iOS лучше Shadowrocket.

### 3.2 Импорт конфига

После установки моста на сервере:

```bash
ssh root@BRIDGE_IP
cat /root/client-link.txt
```

Скопируйте ссылку `vless://...` в приложение (**Импорт из буфера** / **+**).

Либо сгенерируйте на ПК:

```bash
cd telegram-vpn-bot
.venv\Scripts\python.exe scripts/generate_mobile_client.py
```

(скрипт спросит IP моста и ключи)

### 3.3 Проверка

1. Отключите Wi‑Fi, включите **только мобильный интернет**
2. Включите VPN в приложении
3. Откройте [2ip.ru](https://2ip.ru) — должен показать страну **Нидерланды** (или локацию EU VPS)
4. Проверьте YouTube, Telegram, заблокированные сайты

---

## Часть 4. Добавление в Telegram-бот

В админ-панели добавьте **мост** как основной сервер для пользователей:

1. http://localhost:8080/admin/servers
2. **Host** = `BRIDGE_IP` (не EU!)
3. **Public Key / Short ID** = с моста (`/root/bridge-node.env`)
4. **SNI** = `ya.ru`

Пользователи получают ключ на **мост** — цепочка до EU прозрачна.

---

## Часть 5. Устранение неполадок

| Симптом | Решение |
|---------|---------|
| На Wi‑Fi работает, на 4G нет | IP моста не в белом списке → смените VPS или Yandex Cloud |
| Подключается, но нет интернета | Проверьте мост → EU: `journalctl -u xray -f` на обоих серверах |
| Обрывы через 1–2 мин | Смените xHTTP mode: `packet-up` → `stream-one` в конфиге моста |
| Медленно | Нормально для цепочки; мост ближе к вам = лучше пинг |
| iOS вылетает | Shadowrocket, отключите тяжёлые Geo-файлы в клиенте |

### Логи

```bash
# На мосте
journalctl -u xray -n 50 --no-pager

# На выходе
journalctl -u xray -n 50 --no-pager
```

### Проверка цепочки с моста

```bash
ssh root@BRIDGE_IP
curl -x socks5h://127.0.0.1:10808 https://ifconfig.me
# должен вернуть EU_IP
```

(если настроен локальный тестовый outbound)

---

## Безопасность

- Не публикуйте UUID и private keys
- Меняйте UUID при утечке конфига
- Мост в РФ теоретически виден регулятору — не храните логи с трафиком
- Используйте в рамках законодательства вашей страны

---

## Схема файлов проекта

```
scripts/
  install_exit_node.sh   # EU сервер (выход)
  install_bridge_ru.sh   # RU мост (белый IP)
  check_white_ip.sh      # проверка IP с телефона
  generate_mobile_client.py
```

## Порядок действий (кратко)

1. VDSina Амстердам → `install_exit_node.sh` → сохранить ключи
2. Yandex Cloud VM (или белый RU VPS) → `install_bridge_ru.sh` с ключами EU
3. Импорт `client-link.txt` в Hiddify/Shadowrocket
4. Тест на **4G без Wi‑Fi**
5. Добавить мост в админку бота
