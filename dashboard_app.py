# -*- coding: utf-8 -*-

# =============================================================================
# ВЕБ-ПРИЛОЖЕНИЕ ПАНЕЛИ УПРАВЛЕНИЯ (DASHBOARD)
# =============================================================================
#
# Этот файл содержит веб-приложение на Flask, которое предоставляет
# пользовательский интерфейс для мониторинга и управления торговым ботом.
#
# Основные функции:
# - Аутентификация пользователя.
# - Отображение открытых позиций и отложенных ордеров.
# - Предоставление API-эндпоинтов для получения данных в реальном времени.
# - Возможность закрывать позиции и отменять ордера через интерфейс.
# - Просмотр логов приложения.
#
# =============================================================================


# --- Импорты ---
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from datetime import timedelta
import os
import bcrypt

# Импорт конфигурационных переменных и основной бизнес-логики.
import config
from bot_logic import (
    calculate_summary_stats,
    execute_order,
    get_positions,
    get_pending_orders,
    close_position,
    close_all_positions,
    cancel_order
)

# --- Настройка логирования ---
# Определение директории для лог-файлов в зависимости от окружения (Docker или локально).
if os.getenv("DOCKER_ENV"):
    log_directory = "/app/logs"  # Путь внутри Docker-контейнера.
else:
    log_directory = "logs"      # Путь для локального запуска.
os.makedirs(log_directory, exist_ok=True) # Создает директорию, если она не существует.

# Настройка ротации лог-файлов: один файл до 2MB, хранится до 5 старых копий.
log_file_path = os.path.join(log_directory, "dashboard.log")
file_handler = RotatingFileHandler(log_file_path, maxBytes=2_000_000, backupCount=5)
# Настройка вывода логов в консоль.
console_handler = logging.StreamHandler()

# Создание и конфигурация логгера для панели управления.
logger = logging.getLogger("dashboard")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
# Добавление обработчиков (в файл и в консоль) к логгеру.
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("🎉 Панель управления инициализирована!")


# --- Инициализация Flask-приложения ---
app = Flask(__name__)
logger.info(f"Используется Flask Secret Key: {config.FLASK_SECRET_KEY[:5]}...") # Логируем первые 5 символов ключа для проверки.
app.secret_key = config.FLASK_SECRET_KEY

# Конфигурация сессий Flask.
app.config.update(
    PERMANENT_SESSION_LIFETIME=config.SESSION_PERMANENT_LIFETIME, # Время жизни постоянной сессии.
    SESSION_COOKIE_SECURE=False,  # Установить в True при использовании HTTPS.
    SESSION_COOKIE_HTTPONLY=True, # Защита cookie от доступа через JavaScript.
    SESSION_COOKIE_SAMESITE="Strict" # Защита от CSRF-атак.
)

# --- Декоратор для проверки аутентификации ---
# Проверяет, вошел ли пользователь в систему, перед доступом к защищенному маршруту.
def login_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        session.permanent = True # Продлевает жизнь сессии при каждом запросе.
        if not session.get("logged_in"):
            return redirect(url_for("login")) # Если не аутентифицирован, перенаправляет на страницу входа.
        return func(*args, **kwargs)
    return wrapper

# --- Маршрут для входа в систему ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        # Пароль в конфиге предполагается уже хэшированным.
        hashed_password = config.DASHBOARD_PASSWORD.encode('utf-8')
        # Сравнение введенного пароля с хэшем с помощью bcrypt.
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
            session["logged_in"] = True
            session.permanent = True
            logger.info("Пользователь успешно вошел в систему.")
            return redirect(url_for("index")) # Перенаправление на главную страницу.
        else:
            logger.warning("Неудачная попытка входа.")
            return render_template("login.html", error="Неверный пароль")
    return render_template("login.html")

# --- Маршрут для выхода из системы ---
@app.route("/logout")
def logout():
    session.clear() # Очистка сессии.
    logger.info("Пользователь вышел из системы.")
    return redirect(url_for("login"))

# --- Главная страница панели управления ---
@app.route("/")
@login_required # Требует аутентификации.
def index():
    """Отображает главную страницу с открытыми позициями и отложенными ордерами."""
    try:
        positions = get_positions()
        pending_orders = get_pending_orders()
        return render_template("dashboard.html", positions=positions, pending_orders=pending_orders)
    except Exception as e:
        logger.error(f"Ошибка при загрузке главной страницы: {e}")
        return render_template("dashboard.html", error=str(e))

# --- API: Получение открытых позиций ---
@app.route("/positions", methods=["GET"])
@login_required
def positions():
    try:
        positions = get_positions()
        logger.info(f"Запрошены и отправлены открытые позиции.")
        return jsonify(positions)
    except Exception as e:
        logger.error(f"Ошибка при получении позиций: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- API: Получение отложенных ордеров ---
@app.route("/pending_orders", methods=["GET"])
@login_required
def pending_orders():
    try:
        orders = get_pending_orders()
        logger.info("Запрошены и отправлены отложенные ордера.")
        return jsonify(orders)
    except Exception as e:
        logger.error(f"Ошибка при получении отложенных ордеров: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- API: Получение сводной статистики ---
@app.route("/summary_stats", methods=["GET"])
@login_required
def summary_stats():
    try:
        stats = calculate_summary_stats() # Функция-заглушка из bot_logic.py
        logger.info(f"Запрошена и отправлена сводная статистика.")
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Ошибка при получении сводной статистики: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Действие: Закрытие конкретной позиции ---
@app.route("/close_position", methods=["POST"])
@login_required
def close_position_route():
    try:
        data = request.form
        exchange_name = data['EXCHANGE']
        symbol = data['SYMBOL']
        result = close_position(exchange_name, symbol)
        logger.info(f"Позиция для {symbol} на бирже {exchange_name} закрыта: {result}")
        return redirect(url_for("index"))
    except Exception as e:
        logger.error(f"Ошибка при закрытии позиции: {e}")
        return redirect(url_for("index"))

# --- Действие: Закрытие всех позиций ---
@app.route("/close_all_positions", methods=["POST"])
@login_required
def close_all_positions_route():
    try:
        result = close_all_positions()
        logger.info("Все открытые позиции закрыты.")
        return redirect(url_for("index"))
    except Exception as e:
        logger.error(f"Ошибка при закрытии всех позиций: {e}")
        return redirect(url_for("index"))

# --- Действие: Отмена ордера ---
@app.route("/cancel_order", methods=["POST"])
@login_required
def cancel_order_route():
    try:
        data = request.form
        exchange_name = data["EXCHANGE"]
        order_id = data["ORDER_ID"]
        symbol = data["SYMBOL"]
        result = cancel_order(exchange_name, order_id, symbol)
        logger.info(f"Ордер {order_id} на бирже {exchange_name} отменен.")
        return redirect(url_for("index"))
    except Exception as e:
        logger.error(f"Ошибка при отмене ордера: {e}")
        return redirect(url_for("index"))

# --- API: Получение логов ---
@app.route("/logs", methods=["GET"])
@login_required
def logs():
    """Собирает и возвращает содержимое всех .log файлов из директории логов."""
    try:
        log_files = [f for f in os.listdir(log_directory) if f.endswith(".log")]
        all_logs = {}
        for log_file in log_files:
            log_file_path = os.path.join(log_directory, log_file)
            try:
                with open(log_file_path, "r") as f:
                    all_logs[log_file] = f.readlines()
            except Exception as e:
                all_logs[log_file] = [f"Ошибка чтения лог-файла: {e}"]
        return jsonify({"status": "success", "logs": all_logs})
    except Exception as e:
        logger.error(f"Ошибка при получении логов: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Точка входа для запуска приложения ---
# Этот блок выполняется, только если скрипт запущен напрямую (например, `python dashboard_app.py`).
if __name__ == "__main__":
    app.run(host=config.DASHBOARD_HOST, port=config.DASHBOARD_PORT)
