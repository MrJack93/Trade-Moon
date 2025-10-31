# -*- coding: utf-8 -*-

# =============================================================================
# ОБРАБОТЧИК ТОРГОВЫХ СИГНАЛОВ (SIGNAL HANDLER)
# =============================================================================
#
# Этот модуль является ядром торговой логики. Он отвечает за:
# 1. Инициализацию подключений к биржам (Bybit, Binance) с использованием
#    API-ключей из конфигурационного файла.
# 2. Обработку входящих торговых сигналов, полученных из webhook_receiver
#    или email_reader.
# 3. Валидацию данных сигнала (проверку обязательных полей).
# 4. Создание и отправку ордеров на соответствующую биржу.
#
# =============================================================================

import os
import logging
from logging.handlers import RotatingFileHandler
import config
import ccxt


# --- Настройка логирования ---
# (Аналогично другим модулям, настраивает вывод логов в файл и консоль)
if os.getenv("DOCKER_ENV"):
    log_directory = "/app/logs"
else:
    log_directory = "logs"
os.makedirs(log_directory, exist_ok=True)
log_file_path = os.path.join(log_directory, "trading.log")
file_handler = RotatingFileHandler(log_file_path, maxBytes=2_000_000, backupCount=5)
console_handler = logging.StreamHandler()

logger = logging.getLogger("trading")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("🎉 Обработчик торговых сигналов инициализирован!")


# --- Инициализация бирж ---
# Создаем словарь для хранения активных экземпляров бирж.
exchanges = {}

# Инициализация Bybit, если в конфиге есть API-ключи.
if config.BYBIT_API_KEY and config.BYBIT_API_SECRET:
    exchanges['bybit'] = ccxt.bybit({
        'apiKey': config.BYBIT_API_KEY,
        'secret': config.BYBIT_API_SECRET,
        'enableRateLimit': True, # Включает встроенную защиту от превышения лимитов запросов.
    })

# Инициализация Binance Futures, если в конфиге есть API-ключи.
if config.BINANCE_API_KEY and config.BINANCE_API_SECRET:
    exchange = ccxt.binance({
        'apiKey': config.BINANCE_API_KEY,
        'secret': config.BINANCE_API_SECRET,
        'options': {
            'defaultType': 'future', # Указываем, что будем работать с фьючерсами.
        },
        'enableRateLimit': True,
    })
    # Если включен демо-режим, активируем его для Binance.
    if os.getenv('USE_DEMO_TRADING', 'false').lower() == 'true':
        exchange.enable_demo_trading(True)
    exchanges['binance'] = exchange

def process_signal(data):
    """
    Основная функция для обработки входящего торгового сигнала.
    """
    try:
        # --- Валидация данных сигнала ---
        required_fields = ["EXCHANGE", "SYMBOL", "SIDE", "ORDER_TYPE", "QUANTITY"]
        for field in required_fields:
            if field not in data:
                logger.error(f"❌ Отсутствует обязательное поле: {field}")
                return

        # Приводим названия к единому формату (нижний регистр).
        exchange_name = data["EXCHANGE"].lower()
        symbol = data["SYMBOL"]
        side = data["SIDE"].lower()
        order_type = data["ORDER_TYPE"].lower()
        
        try:
            quantity = float(data["QUANTITY"])
        except ValueError:
            logger.error("❌ Неверное значение QUANTITY: должно быть числом.")
            return

        # Проверяем корректность стороны ордера.
        if side not in ["buy", "sell"]:
            logger.error(f"❌ Неверное значение SIDE: {side}. Должно быть 'buy' или 'sell'.")
            return

        # Для лимитных ордеров дополнительно проверяем наличие цены.
        if order_type == "limit":
            if "PRICE" not in data:
                logger.error("❌ Отсутствует обязательное поле 'PRICE' для лимитного ордера.")
                return
            try:
                price = float(data["PRICE"])
            except ValueError:
                logger.error("❌ Неверное значение PRICE: должно быть числом.")
                return

        # --- Исполнение ордера ---
        exchange = exchanges.get(exchange_name)
        if not exchange:
            logger.error(f"Биржа '{exchange_name}' не настроена или не поддерживается.")
            return

        logger.info(f"Размещение ордера на {exchange_name}: {data}")
        if order_type == "limit":
            order = exchange.create_order(symbol, order_type, side, quantity, price)
        elif order_type == "market":
            order = exchange.create_order(symbol, order_type, side, quantity)
        else:
            logger.error(f"❌ Неподдерживаемый тип ордера: {order_type}")
            return

        logger.info(f"✅ Ордер успешно размещен: {order}")
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке сигнала: {e}")
