import ccxt
import logging
import config
import os
from logging.handlers import RotatingFileHandler

# ==============================
# 📝 Настройка логирования
# ==============================

# Определяем путь к директории логов в зависимости от окружения (Docker или локально)
if os.getenv("DOCKER_ENV"):
    log_directory = "/app/logs"  # Путь внутри Docker-контейнера
else:
    log_directory = "logs"  # Путь для локального запуска

# Создаем директорию для логов, если она не существует
os.makedirs(log_directory, exist_ok=True)
log_file_path = os.path.join(log_directory, "trading.log")

# Настраиваем ротацию лог-файлов: 5 файлов по 2 МБ каждый
file_handler = RotatingFileHandler(log_file_path, maxBytes=2_000_000, backupCount=5)
# Настраиваем вывод логов в консоль
console_handler = logging.StreamHandler()

# Создаем и настраиваем логгер
logger = logging.getLogger("trading")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Добавляем обработчики в логгер
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("🔄 Инициализация бирж...")

# ==============================
# 🔌 Инициализация бирж
# ==============================

# Словарь для хранения активных экземпляров бирж
exchanges = {}

# Инициализация Bybit, если заданы API-ключи
if config.BYBIT_API_KEY and config.BYBIT_API_SECRET:
    logger.info("🔄 Настройка Bybit API...")
    try:
        exchanges['bybit'] = ccxt.bybit({
            'apiKey': config.BYBIT_API_KEY,
            'secret': config.BYBIT_API_SECRET
        })
        logger.info("✅ Bybit успешно инициализирован!")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации Bybit: {e}")

# Инициализация Binance, если заданы API-ключи
if config.BINANCE_API_KEY and config.BINANCE_API_SECRET:
    logger.info("🔄 Настройка Binance API...")
    try:
        exchange = ccxt.binance({
            'apiKey': config.BINANCE_API_KEY,
            'secret': config.BINANCE_API_SECRET,
            'options': {
                'defaultType': 'future',  # Устанавливаем фьючерсы как тип по умолчанию
            },
            'enableRateLimit': True,  # Включаем автоматическое управление лимитами запросов
        })

        # Проверяем, нужно ли включить демо-режим для Binance
        if os.getenv('USE_DEMO_TRADING', 'false').lower() == 'true':
            logger.info("🎛️ Включение режима Демо-торговли для Binance...")
            exchange.enable_demo_trading(True)
        
        exchanges['binance'] = exchange
        logger.info("✅ Binance Futures успешно инициализирован!")

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации Binance Futures: {e}")

# Логируем итоговое состояние инициализации бирж
if exchanges:
    logger.info(f"🎉 Загруженные биржи: {list(exchanges.keys())}")
else:
    logger.error("❌ Ни одна биржа не загружена! Проверьте API-ключи и конфигурацию.")

# ==============================
# 🚀 Функции торговой логики
# ==============================

def get_positions():
    """
    Получает список всех открытых позиций с каждой инициализированной биржи.

    Собирает данные по активным позициям (где количество контрактов больше нуля)
    и форматирует их в стандартизированный словарь.

    Returns:
        dict: Словарь, где ключи — названия бирж, а значения — списки словарей,
              каждый из которых представляет открытую позицию.
              Пример: {'binance': [{'symbol': 'BTC/USDT', 'side': 'long', ...}]}
              Возвращает пустой словарь, если биржи не загружены.
    
    Raises:
        ccxt.base.errors.RequestTimeout: Если запрос к бирже превышает тайм-аут.
        ccxt.base.errors.AuthenticationError: Если API-ключи недействительны.
        ccxt.base.errors.NetworkError: При проблемах с сетевым подключением.
    """
    logger.info("📊 Запрос открытых позиций...")
    positions_data = {}

    if not exchanges:
        logger.error("❌ Биржи не загружены! Проверьте API-ключи и конфигурацию.")
        return positions_data

    for exchange_name, exchange in exchanges.items():
        positions_data[exchange_name] = []
        try:
            all_positions = exchange.fetch_positions()
            for pos in all_positions:
                # Фильтруем только активные позиции
                if pos.get('contracts', 0) > 0:
                    positions_data[exchange_name].append({
                        "symbol": pos.get('symbol', 'N/A'),
                        "side": pos.get('side', 'N/A'),
                        "contracts": pos.get('contracts', 0),
                        "notional": pos.get('notional', 0.0),
                        "entry_price": pos.get('entryPrice', 0.0),
                        "liquidation_price": pos.get('liquidationPrice', None),
                        "margin_ratio": pos.get('marginRatio', None),
                        "leverage": pos.get('leverage', None),
                        "unrealized_pnl": pos.get('unrealizedPnl', 0.0),
                        "exchange": exchange_name
                    })
        except Exception as e:
            logger.error(f"❌ [get_positions] Ошибка получения позиций для {exchange_name}: {e}")

    logger.info(f"📊 Итоговые данные по позициям: {positions_data}")
    return positions_data


def get_pending_orders():
    """
    Получает список всех отложенных (открытых) ордеров с каждой биржи.

    Returns:
        dict: Словарь, где ключи — названия бирж, а значения — списки
              открытых ордеров, полученные от ccxt.
              Возвращает пустой словарь, если биржи не загружены.

    Raises:
        ccxt.base.errors.RequestTimeout: Если запрос к бирже превышает тайм-аут.
        ccxt.base.errors.AuthenticationError: Если API-ключи недействительны.
        ccxt.base.errors.NetworkError: При проблемах с сетевым подключением.
    """
    logger.info("📋 Запрос отложенных ордеров...")
    pending_orders = {}

    if not exchanges:
        logger.error("❌ Биржи не загружены! Проверьте API-ключи и конфигурацию.")
        return pending_orders

    for exchange_name, exchange in exchanges.items():
        try:
            # fetch_open_orders возвращает список ордеров в формате ccxt
            orders = exchange.fetch_open_orders()
            pending_orders[exchange_name] = orders
        except Exception as e:
            logger.error(f"❌ [get_pending_orders] Ошибка получения ордеров для {exchange_name}: {e}")

    return pending_orders


def execute_order(exchange_name, symbol, side, order_type, quantity, price=None):
    """
    Размещает торговый ордер на указанной бирже.

    Поддерживает рыночные (market) и лимитные (limit) ордера.

    Args:
        exchange_name (str): Название биржи (например, 'binance').
        symbol (str): Торговый символ (например, 'BTC/USDT').
        side (str): Направление ордера ('buy' или 'sell').
        order_type (str): Тип ордера ('market' или 'limit').
        quantity (float): Количество для покупки или продажи.
        price (float, optional): Цена для лимитного ордера. Defaults to None.

    Returns:
        dict: Результат операции.
              В случае успеха: {'status': 'success', 'order': {...}}.
              В случае ошибки: {'status': 'error', 'message': '...'}.
    
    Raises:
        ccxt.base.errors.InvalidOrder: Если параметры ордера некорректны.
        ccxt.base.errors.InsufficientFunds: Если на балансе недостаточно средств.
        Exception: Любые другие ошибки, которые могут возникнуть при взаимодействии с API.
    """
    logger.info(f"📌 Исполнение ордера на {exchange_name}: {side} {quantity} {symbol} ({order_type}) по цене {price if price else 'рыночной'}")

    if exchange_name not in exchanges:
        logger.error(f"❌ Биржа {exchange_name} недоступна.")
        return {"status": "error", "message": f"Биржа {exchange_name} не найдена."}

    exchange = exchanges[exchange_name]

    try:
        if order_type == "market":
            order = exchange.create_market_order(symbol, side, quantity)
        elif order_type == "limit" and price:
            order = exchange.create_limit_order(symbol, side, quantity, price)
        else:
            # Обработка невалидного типа ордера или отсутствия цены для лимитного
            logger.error(f"❌ Неверный тип ордера: {order_type} или не указана цена.")
            return {"status": "error", "message": "Неверный тип ордера или не указана цена для лимитного ордера"}

        logger.info(f"✅ Ордер успешно размещен: {order}")
        return {"status": "success", "order": order}

    except Exception as e:
        logger.error(f"❌ Ошибка исполнения ордера на {exchange_name}: {e}")
        return {"status": "error", "message": str(e)}


def close_position(exchange_name, symbol):
    """
    Закрывает открытую позицию по указанному символу на бирже.

    Определяет текущую сторону позиции (long/short) и создает
    встречный рыночный ордер для ее закрытия.

    Args:
        exchange_name (str): Название биржи.
        symbol (str): Торговый символ позиции для закрытия.

    Returns:
        dict: Результат операции.
              В случае успеха: {'status': 'success', 'order': {...}}.
              В случае ошибки: {'status': 'error', 'message': '...'}.
    
    Raises:
        ccxt.base.errors.InvalidOrder: Если параметры ордера некорректны.
        ccxt.base.errors.InsufficientFunds: Если на балансе недостаточно средств.
    """
    logger.info(f"❌ Закрытие позиции по {symbol} на {exchange_name}...")

    if exchange_name not in exchanges:
        logger.error(f"❌ Биржа {exchange_name} недоступна.")
        return {"status": "error", "message": f"Биржа {exchange_name} не найдена."}

    exchange = exchanges[exchange_name]

    try:
        positions = get_positions().get(exchange_name, [])
        for pos in positions:
            if pos["symbol"] == symbol:
                # Определяем сторону для закрытия: 'sell' для long, 'buy' для short
                side = "sell" if (pos["side"] == "buy" or pos["side"] == "long") else "buy"
                order = exchange.create_market_order(symbol, side, pos["contracts"])
                logger.info(f"✅ Позиция закрыта: {order}")
                return {"status": "success", "order": order}

        logger.warning(f"⚠ Не найдено открытой позиции для {symbol}.")
        return {"status": "error", "message": "Открытая позиция не найдена."}

    except Exception as e:
        logger.error(f"❌ Ошибка закрытия позиции: {e}")
        return {"status": "error", "message": str(e)}


def close_all_positions():
    """
    Закрывает все открытые позиции на всех инициализированных биржах.

    Итерирует по всем биржам, получает список позиций и закрывает каждую из них.

    Returns:
        dict: Словарь с результатами закрытия для каждой позиции.
              Ключ - символ, значение - результат от `close_position`.
    """
    logger.info("❌ Закрытие всех открытых позиций...")

    results = {}
    all_positions = get_positions()
    for exchange_name, positions in all_positions.items():
        for pos in positions:
            # Вызываем функцию закрытия для каждой найденной позиции
            result = close_position(exchange_name, pos["symbol"])
            results[f"{exchange_name}_{pos['symbol']}"] = result

    logger.info(f"✅ Все позиции закрыты: {results}")
    return results


def cancel_order(exchange_name, order_id, symbol):
    """
    Отменяет конкретный отложенный ордер по его ID и символу.

    Args:
        exchange_name (str): Название биржи.
        order_id (str): Уникальный идентификатор ордера.
        symbol (str): Торговый символ ордера (некоторые биржи требуют его).

    Returns:
        dict: Результат операции.
              В случае успеха: {'status': 'success', 'order': {...}}.
              В случае ошибки: {'status': 'error', 'message': '...'}.
    
    Raises:
        ccxt.base.errors.OrderNotFound: Если ордер с таким ID не найден.
        ccxt.base.errors.InvalidOrder: Если ордер уже исполнен или отменен.
    """
    logger.info(f"🚫 Отмена ордера {order_id} на {exchange_name}...")

    if exchange_name not in exchanges:
        logger.error(f"❌ Биржа {exchange_name} недоступна.")
        return {"status": "error", "message": f"Биржа {exchange_name} не найдена."}

    exchange = exchanges[exchange_name]

    try:
        result = exchange.cancel_order(order_id, symbol)
        logger.info(f"✅ Ордер {order_id} успешно отменен.")
        return {"status": "success", "order": result}
    except Exception as e:
        logger.error(f"❌ Ошибка отмены ордера {order_id}: {e}")
        return {"status": "error", "message": str(e)}


def calculate_summary_stats():
    """
    Рассчитывает и возвращает сводную статистику по портфелю.

    Собирает данные о балансе, PnL и использованной марже со всех бирж.
    Предполагается, что базовой валютой для расчетов является USDT.

    Returns:
        dict: Словарь со сводной статистикой, включающий:
              - 'portfolio_value' (float): Общая стоимость портфеля в USDT.
              - 'total_pnl' (float): Суммарный нереализованный PnL.
              - 'margin_used' (float): Суммарная использованная маржа.
              Возвращает словарь с нулевыми значениями, если биржи не загружены.
              
    Raises:
        ccxt.base.errors.RequestTimeout: Если запрос к бирже превышает тайм-аут.
        ccxt.base.errors.AuthenticationError: Если API-ключи недействительны.
    """
    logger.info("📊 Расчет сводной статистики...")
    summary_stats = {
        "portfolio_value": 0.0,
        "total_pnl": 0.0,
        "margin_used": 0.0,
    }

    if not exchanges:
        logger.error("❌ Биржи не загружены! Невозможно рассчитать статистику.")
        return summary_stats

    all_positions = get_positions()

    for exchange_name, exchange in exchanges.items():
        try:
            # Получаем полный баланс аккаунта
            account_balance = exchange.fetch_balance()
            positions = all_positions.get(exchange_name, [])

            # Суммируем общую стоимость портфеля (предполагая USDT)
            summary_stats["portfolio_value"] += account_balance.get('USDT', {}).get('total', 0.0)

            # Рассчитываем PnL и использованную маржу на основе позиций
            for pos in positions:
                summary_stats["total_pnl"] += pos.get('unrealized_pnl', 0.0)
                # Расчет использованной маржи = стоимость позиции * маржинальное соотношение
                margin_ratio = pos.get('marginRatio')
                if margin_ratio is not None:
                     summary_stats["margin_used"] += pos.get('notional', 0.0) * margin_ratio

        except Exception as e:
            logger.error(f"❌ Ошибка получения баланса или позиций для {exchange_name}: {e}")

    logger.info(f"📊 Сводная статистика рассчитана: {summary_stats}")
    return summary_stats
