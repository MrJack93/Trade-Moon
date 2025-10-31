# -*- coding: utf-8 -*-

# =============================================================================
# МОДУЛЬ ЧТЕНИЯ ЭЛЕКТРОННОЙ ПОЧТЫ (EMAIL READER)
# =============================================================================
#
# Этот модуль отвечает за подключение к почтовому ящику по протоколу IMAP,
# поиск непрочитанных писем, извлечение из них торговых сигналов
# (в формате JSON в теме письма) и их последующую обработку.
#
# =============================================================================


# --- Импорты ---
import time
import imaplib
import ssl
import email
import json
import logging
import os
import sys
import html
import re
import quopri
from logging.handlers import RotatingFileHandler

# Импорт конфигурации и обработчика сигналов
import config
from signal_handler import process_signal

# --- Настройка логирования ---
# (Аналогично другим модулям, настраивает вывод логов в файл и консоль)
if os.getenv("DOCKER_ENV"):
    log_directory = "/app/logs"
else:
    log_directory = "logs"
os.makedirs(log_directory, exist_ok=True)

log_file_path = os.path.join(log_directory, "email_reader.log")
file_handler = RotatingFileHandler(log_file_path, maxBytes=2_000_000, backupCount=5)
console_handler = logging.StreamHandler()

logger = logging.getLogger("email_reader")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("🎉 Модуль чтения почты инициализирован!")


def parse_email_subject(msg):
    """
    Извлекает и анализирует JSON-данные из темы (Subject) электронного письма.
    """
    subject = msg.get("Subject", "").strip()
    logger.info(f"[Email Reader] 📩 Проверка письма с темой: {subject}")

    # Сигнал должен начинаться с "Alert:"
    if subject.startswith("Alert:"):
        try:
            # Извлекаем часть строки, содержащую JSON
            json_part = subject.split("Alert:", 1)[1].strip()

            # Декодируем HTML-сущности (например, &nbsp;, &zwj;)
            json_part = html.unescape(json_part)

            # Удаляем невидимые символы и артефакты форматирования
            json_part = re.sub(r'[\u200B-\u200D\uFEFF]', '', json_part)  # Удаление пробелов нулевой ширины
            json_part = json_part.replace('\n', '').replace('\r', '')  # Удаление переносов строк

            # Пытаемся распарсить очищенную строку как JSON
            return json.loads(json_part)
        except json.JSONDecodeError as e:
            logger.error(f"[Email Reader] ❌ Не удалось распарсить тему как JSON: {e}")
    return None


def check_inbox():
    """
    Подключается к IMAP-серверу, читает непрочитанные письма и обрабатывает только те,
    которые являются торговыми сигналами.
    """
    try:
        logger.info("[Email Reader] 🔄 Подключение к IMAP серверу...")
        # Устанавливаем защищенное SSL-соединение или используем STARTTLS
        if config.IMAP_USE_SSL:
            mail = imaplib.IMAP4_SSL(config.IMAP_SERVER, config.IMAP_PORT)
        else:
            context = ssl.create_default_context()
            mail = imaplib.IMAP4(config.IMAP_SERVER, config.IMAP_PORT)
            mail.starttls(ssl_context=context)

        mail.login(config.IMAP_EMAIL, config.IMAP_PASSWORD)
        mail.select("INBOX") # Выбираем папку "Входящие"
        logger.info("[Email Reader] ✅ Соединение с IMAP установлено успешно.")

        # Ищем все непрочитанные письма
        status, data = mail.search(None, '(UNSEEN)')
        if status != "OK":
            logger.warning("[Email Reader] ⚠ Новых писем нет или не удалось выполнить поиск.")
            mail.logout()
            return

        email_ids = data[0].split()
        logger.info(f"[Email Reader] 📩 Найдено {len(email_ids)} новых писем.")

        for e_id in email_ids:
            try:
                # Получаем письмо в режиме "PEEK", чтобы не помечать его как прочитанное автоматически.
                status, msg_data = mail.fetch(e_id, "(BODY.PEEK[])")
                if status == "OK":
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # Декодируем тему письма, если она закодирована
                    subject = msg.get("Subject", "")
                    if msg.get_content_charset():
                        subject = subject.encode('latin-1').decode(msg.get_content_charset())
                    subject = quopri.decodestring(subject).decode('utf-8')  # Декодирование из Quoted-Printable

                    msg.replace_header("Subject", subject)  # Заменяем заголовок на декодированную версию

                    # Пытаемся извлечь данные сигнала из темы
                    alert_data = parse_email_subject(msg)
                    if alert_data:
                        logger.info(f"[Email Reader] ✅ Обработка сигнала: {alert_data}")

                        # Проверяем PIN-код, если он требуется в конфигурации
                        if config.WEBHOOK_PIN:
                            incoming_pin = alert_data.get("PIN", "")
                            if incoming_pin != config.WEBHOOK_PIN:
                                logger.warning(f"[Email Reader] ❌ Неверный PIN в сигнале из письма: {incoming_pin}")
                                continue # Переходим к следующему письму

                        # Отправляем данные на обработку
                        process_signal(alert_data)
                        # Помечаем письмо как прочитанное, только если это был торговый сигнал.
                        mail.store(e_id, "+FLAGS", "\\Seen")
                    else:
                        # Если это не торговый сигнал, оставляем письмо непрочитанным.
                        logger.info("[Email Reader] 📌 Обнаружено неторговое письмо, оставляем его непрочитанным.")
            except Exception as e:
                logger.error(f"[Email Reader] ❌ Ошибка при обработке письма {e_id}: {e}")

        mail.logout()
        logger.info("[Email Reader] ✅ Завершение обработки писем.")
    except imaplib.IMAP4.error as e:
        logger.error(f"[Email Reader] ❌ Ошибка IMAP: {e}")
    except Exception as e:
        logger.error(f"[Email Reader] ❌ Непредвиденная ошибка: {e}")


def run_email_reader():
    """Запускает модуль чтения почты в бесконечном цикле."""
    logger.info("[Email Reader] 🚀 Запуск модуля чтения почты...")
    try:
        while True:
            check_inbox()
            # Пауза между проверками почтового ящика.
            time.sleep(config.IMAP_CHECK_INTERVAL)
    except KeyboardInterrupt:
        logger.info("[Email Reader] 🛑 Остановка вручную.")
    except Exception as e:
        logger.error(f"[Email Reader] ❌ Фатальная ошибка: {e}")


# --- Точка входа ---
# Этот блок выполняется, если скрипт запущен напрямую.
if __name__ == "__main__":
    run_email_reader()
