# -*- coding: utf-8 -*-

# =============================================================================
# ГЛАВНЫЙ ФАЙЛ ПРИЛОЖЕНИЯ (main.py)
# =============================================================================
#
# Этот скрипт является основной точкой входа для запуска приложения TradeX
# при локальной разработке (без Docker или Supervisord).
#
# Он выполняет следующие задачи:
# 1. Загружает переменные окружения из файла .env.
# 2. Настраивает обработчики сигналов для корректного завершения работы (Ctrl+C).
# 3. Запускает необходимые компоненты в зависимости от переменной `MODE`:
#    - `dashboard_app`: Веб-панель управления (запускается всегда).
#    - `webhook_receiver`: Приемник веб-хуков (если MODE="webhook" или "both").
#    - `email_reader`: Модуль чтения почты (если MODE="email" или "both").
#
# Для запуска веб-сервисов используется Gunicorn в виде дочерних процессов,
# а модуль чтения почты запускается в отдельном потоке.
#
# =============================================================================

import os
import threading
import logging
import signal
import sys
import subprocess
from dotenv import load_dotenv
from email_reader import run_email_reader

# --- Загрузка переменных окружения ---
# Загружает переменные из файла .env в окружение.
load_dotenv()

# Список для хранения дочерних процессов (Gunicorn).
processes = []

def handle_exit_signal(signum, frame):
    """
    Обработчик сигналов (SIGINT, SIGTERM) для корректного завершения работы.
    Вызывается при нажатии Ctrl+C или при получении сигнала на остановку.
    """
    logging.info("Завершение работы всех сервисов...")
    for proc in processes:
        logging.info(f"Остановка процесса {proc.pid}...")
        proc.terminate() # Отправляет сигнал SIGTERM дочернему процессу.
    sys.exit(0)

# --- Привязка обработчиков сигналов ---
# Назначаем функцию `handle_exit_signal` для обработки сигналов
# SIGINT (прерывание, Ctrl+C) и SIGTERM (терминация).
signal.signal(signal.SIGINT, handle_exit_signal)
signal.signal(signal.SIGTERM, handle_exit_signal)

def start_gunicorn(service_name, port):
    """
    Запускает Gunicorn для указанного сервиса (dashboard или webhook)
    в виде дочернего процесса.
    """
    logging.info(f"Запуск {service_name} на порту {port}...")
    # Команда для запуска Gunicorn с 2 воркерами.
    proc = subprocess.Popen(["gunicorn", "-w", "2", "-b", f"0.0.0.0:{port}", f"{service_name}:app"])
    processes.append(proc) # Добавляем процесс в список для последующего управления.

def start_email_reader():
    """
    Запускает модуль чтения почты в отдельном фоновом потоке.
    """
    logging.info("Запуск модуля чтения почты (Email Reader)...")
    # `daemon=True` означает, что поток завершится, когда основной поток завершит работу.
    email_thread = threading.Thread(target=run_email_reader, daemon=True)
    email_thread.start()
    return email_thread

# --- Точка входа ---
# Этот блок выполняется, если скрипт запущен напрямую (`python main.py`).
if __name__ == "__main__":
    # Получаем режим работы из переменных окружения.
    mode = os.getenv("MODE", "both").strip().lower()

    # Проверяем, что указан корректный режим.
    if mode not in ["webhook", "email", "both"]:
        logging.error(f"Неверное значение MODE в .env: {mode}. Ожидается 'webhook', 'email' или 'both'.")
        sys.exit(1)

    # --- Запуск сервисов в зависимости от режима ---
    if mode in ["webhook", "both"]:
        start_gunicorn("webhook_receiver", 5005)

    if mode in ["email", "both"]:
        email_thread = start_email_reader()

    # Панель управления запускается всегда.
    start_gunicorn("dashboard_app", 5000)

    # Ожидаем завершения дочерних процессов Gunicorn.
    # Это позволяет основному скрипту работать, пока работают дочерние процессы.
    for proc in processes:
        proc.wait()
