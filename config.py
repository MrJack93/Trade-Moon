# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
from datetime import timedelta

# =============================================================================
# ФАЙЛ КОНФИГУРАЦИИ (config.py)
# =============================================================================
#
# Этот файл отвечает за загрузку и предоставление всех конфигурационных
# переменных для приложения. Он считывает значения из файла `.env`
# и устанавливает значения по умолчанию, если переменные не определены.
#
# =============================================================================


# --- Загрузка переменных окружения ---
# `load_dotenv()` загружает переменные из файла .env в окружение сессии.
# Это позволяет получать доступ к конфигурации через `os.getenv()`.
load_dotenv()


# --- Настройки панели управления (Dashboard) ---

# IP-адрес, на котором будет доступна панель управления.
# "0.0.0.0" означает, что она будет доступна со всех сетевых интерфейсов.
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")

# Порт, на котором будет работать панель управления.
# Значение по умолчанию: 5000.
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))

# Пароль для доступа к панели управления.
# Загружается из переменной окружения.
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")


# --- Настройки сессии Flask ---

# Секретный ключ для Flask, используемый для подписи данных сессии.
# Важен для безопасности.
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "hardcoded-default-key")

# Время жизни сессии в часах.
SESSION_LIFETIME_HOURS = float(os.getenv("SESSION_LIFETIME_HOURS", "12"))

# Объект `timedelta` для Flask, определяющий длительность постоянной сессии.
SESSION_PERMANENT_LIFETIME = timedelta(hours=SESSION_LIFETIME_HOURS)


# --- Настройки Webhook ---

# IP-адрес для прослушивания входящих webhook-запросов.
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")

# Порт для прослушивания webhook-запросов.
# Значение по умолчанию: 5005.
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "5005"))

# PIN-код для верификации входящих webhook-запросов.
WEBHOOK_PIN = os.getenv("WEBHOOK_PIN", "")


# --- Учетные данные бирж ---

# Ключ API для Bybit.
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
# Секретный ключ API для Bybit.
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")

# Ключ API для Binance.
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
# Секретный ключ API для Binance.
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")


# --- Активные биржи ---
# Список бирж, которые будут использоваться в приложении.
# Задается в `.env` в виде строки через запятую, например: "bybit,binance".
# Приводится к нижнему регистру для унификации.
EXCHANGES = os.getenv("EXCHANGES", "bybit,binance").lower()


# --- Режим получения сигналов ---
# Определяет источник торговых сигналов.
# Возможные значения: "webhook", "email" или "both".
# Значение по умолчанию: "webhook".
MODE = os.getenv("MODE", "webhook").lower()


# --- Настройки почты (IMAP) ---

# Адрес IMAP-сервера для подключения к почтовому ящику.
IMAP_SERVER = os.getenv("IMAP_SERVER", "")

# Порт IMAP-сервера.
IMAP_PORT = int(os.getenv("IMAP_PORT", "993")) # 993 - стандартный порт для IMAP c SSL

# Email-адрес для проверки писем.
IMAP_EMAIL = os.getenv("IMAP_EMAIL", "")

# Пароль от email-адреса (или пароль приложения).
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", "")

# Флаг, указывающий, использовать ли SSL-шифрование при подключении.
# Преобразует строковые значения "true", "1", "yes" в булево `True`.
IMAP_USE_SSL = os.getenv("IMAP_USE_SSL", "true").lower() in ["true", "1", "yes"]

# Интервал в секундах для проверки новых писем в почтовом ящике.
IMAP_CHECK_INTERVAL = int(os.getenv("IMAP_CHECK_INTERVAL", "15"))
