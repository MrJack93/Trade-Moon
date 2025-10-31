# -*- coding: utf-8 -*-

# =============================================================================
# ПРИЕМНИК ВЕБ-ХУКОВ (WEBHOOK RECEIVER)
# =============================================================================
#
# Этот модуль представляет собой простое Flask-приложение, предназначенное
# для приема входящих HTTP POST-запросов (веб-хуков), например, от TradingView.
#
# Основные задачи:
# 1. Прослушивание эндпоинта `/webhook`.
# 2. Валидация входящих данных (проверка наличия JSON и корректности PIN-кода).
# 3. Передача валидных данных (торгового сигнала) в `signal_handler`
#    для дальнейшей обработки.
#
# =============================================================================

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify
import json
import config
from signal_handler import process_signal

# --- Настройка логирования ---
# (Аналогично другим модулям, настраивает вывод логов в файл и консоль)
if os.getenv("DOCKER_ENV"):
    log_directory = "/app/logs"
else:
    log_directory = "logs"
os.makedirs(log_directory, exist_ok=True)
log_file_path = os.path.join(log_directory, "webhook.log")
file_handler = RotatingFileHandler(log_file_path, maxBytes=2_000_000, backupCount=5)
console_handler = logging.StreamHandler()

logger = logging.getLogger("webhook")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("🎉 Приемник веб-хуков инициализирован!")

# --- Инициализация Flask-приложения ---
app = Flask(__name__)

# --- Основной маршрут для приема веб-хуков ---
@app.route("/webhook", methods=["POST"])
def trade_signal():
    """
    Обрабатывает входящие POST-запросы на эндпоинт /webhook.
    """
    try:
        # Получаем JSON-данные из тела запроса.
        data = request.json
        if data is None:
            logger.warning("Получен пустой JSON-запрос.")
            return jsonify({"error": "No JSON data"}), 400

        # --- Валидация PIN-кода ---
        # Если в конфигурации задан WEBHOOK_PIN, проверяем его совпадение
        # с PIN-кодом, пришедшим в запросе. Это базовый механизм защиты.
        incoming_pin = data.get("PIN", "")
        if config.WEBHOOK_PIN and incoming_pin != config.WEBHOOK_PIN:
            logger.warning("Получен неверный PIN-код для веб-хука.")
            return jsonify({"error": "Invalid pin"}), 403 # 403 Forbidden - доступ запрещен.

        logger.info(f"Получены данные от веб-хука: {data}")
        # Если все проверки пройдены, передаем данные в обработчик сигналов.
        process_signal(data)

        # Возвращаем успешный ответ.
        return jsonify({"status": "ok"}), 200
    except json.JSONDecodeError:
        logger.error("Получен некорректный JSON в теле веб-хука.")
        return jsonify({"error": "Malformed JSON"}), 400 # 400 Bad Request - некорректный запрос.
    except Exception as e:
        logger.error(f"Ошибка при обработке веб-хука: {e}")
        return jsonify({"error": str(e)}), 500 # 500 Internal Server Error - внутренняя ошибка сервера.
