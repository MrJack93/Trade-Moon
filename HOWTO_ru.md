# HOWTO:
# Запуск TradeX как сервиса

Это руководство описывает пошаговую настройку TradeX как фонового сервиса с помощью **Supervisor** (`supervisord`) или **systemd**. Эти инструменты гарантируют стабильную работу приложения и автоматический перезапуск в случае падения.

---

## Содержание
- [Запуск TradeX с помощью Supervisord](#running-tradex-with-supervisord)
- [Запуск TradeX с помощью Systemd](#running-tradex-with-systemd)
- [Устранение неполадок](#troubleshooting)

---

## Запуск TradeX с помощью Supervisord

`supervisord` — это система управления процессами, которая позволяет запускать и контролировать несколько процессов (например, компоненты TradeX) как фоновые сервисы. Ниже — шаги по настройке TradeX через `supervisord`.

### Требования
1. Установите `supervisor`:
   ```bash
   sudo apt update
   sudo apt install supervisor
   ```

2. Убедитесь, что в каталоге проекта есть файл `supervisord.conf`. Если его нет — скопируйте из репозитория в рабочий каталог.

### Шаги

#### 1. Скопируйте `supervisord.conf`
Если вы запускаете TradeX локально (не в Docker), скопируйте файл конфигурации в системную директорию:
```bash
sudo cp supervisord.conf /etc/supervisor/conf.d/tradex.conf
```

В Docker‑сборке `supervisord.conf` уже интегрирован в `Dockerfile`, поэтому дополнительных действий обычно не требуется.

#### 2. Перезагрузите конфигурацию Supervisor
```bash
sudo supervisorctl reread
sudo supervisorctl update
```

#### 3. Запустите сервисы
Запустите все сервисы, указанные в `supervisord.conf`:
```bash
sudo supervisorctl start tradex:*
```

#### 4. Проверка статуса
Проверьте, что все сервисы работают корректно:
```bash
sudo supervisorctl status
```
Ожидаемый вывод:
```
tradex:dashboard_app      RUNNING   pid 1234, uptime 0:05:23
tradex:webhook_app        RUNNING   pid 1235, uptime 0:05:23
tradex:email_reader       RUNNING   pid 1236, uptime 0:05:23
```

#### 5. Просмотр логов
Для отладки смотрите файлы логов, указанные в конфигурации `supervisord.conf`:
```bash
tail -f /var/log/supervisor/dashboard_app.err.log
tail -f /var/log/supervisor/webhook_app.err.log
tail -f /var/log/supervisor/email_reader.err.log
```

#### 6. Перезапуск или остановка
```bash
sudo supervisorctl restart tradex:*
sudo supervisorctl stop tradex:*
```

---

## Запуск TradeX с помощью Systemd

`systemd` — менеджер сервисов для Linux, позволяющий управлять службами, которые автоматически стартуют при загрузке системы. Ниже — инструкция по созданию unit‑файлов для TradeX.

### Требования
1. Убедитесь, что Python окружение и зависимости установлены и работают.
2. Если вы используете виртуальное окружение, запомните путь до него.
3. Необходимы права `sudo` для создания и управления systemd‑unit файлами.

### Шаги

#### 1. Перейдите в директорию systemd
Файлы сервисов systemd располагаются в `/etc/systemd/system/`:
```bash
cd /etc/systemd/system/
```

#### 2. Создайте unit для dashboard
Файл для `dashboard_app` (выполняющего Gunicorn):
```bash
sudo nano dashboard_app.service
```

Добавьте содержимое (обязательно замените пути и пользователя на свои):
```ini
[Unit]
Description=Gunicorn instance to serve TradeX Dashboard
After=network.target

[Service]
User=your_user  # Замените на имя пользователя (например, "ubuntu")
Group=www-data  # При необходимости замените на свою группу
WorkingDirectory=/path/to/tradex  # Абсолютный путь к проекту
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 dashboard_app:app
Restart=always
Environment="PATH=/path/to/venv/bin"
EnvironmentFile=/path/to/tradex/.env  # Необязательно: загрузка переменных окружения из .env

[Install]
WantedBy=multi-user.target
```

#### 3. Создайте unit для webhook
Файл для `webhook_receiver`:
```bash
sudo nano webhook_app.service
```

Добавьте содержимое (замените пути/пользователя):
```ini
[Unit]
Description=Gunicorn instance to serve TradeX Webhook
After=network.target

[Service]
User=your_user
Group=www-data
WorkingDirectory=/path/to/tradex
ExecStart=/path/to/venv/bin/gunicorn -w 2 -b 0.0.0.0:5005 webhook_receiver:app
Restart=always
Environment="PATH=/path/to/venv/bin"
EnvironmentFile=/path/to/tradex/.env

[Install]
WantedBy=multi-user.target
```

#### 4. Перезагрузите systemd
```bash
sudo systemctl daemon-reload
```

#### 5. Запустите сервисы
```bash
sudo systemctl start dashboard_app
sudo systemctl start webhook_app
```

#### 6. Включите автозапуск при загрузке
```bash
sudo systemctl enable dashboard_app
sudo systemctl enable webhook_app
```

#### 7. Проверка статуса
```bash
sudo systemctl status dashboard_app
sudo systemctl status webhook_app
```

Если всё настроено верно, вы увидите активный (running) статус.

#### 8. Просмотр логов
Для просмотра логов используйте `journalctl`:
```bash
sudo journalctl -u dashboard_app -f
sudo journalctl -u webhook_app -f
```

#### 9. Перезапуск или остановка
```bash
sudo systemctl restart dashboard_app
sudo systemctl stop dashboard_app

sudo systemctl restart webhook_app
sudo systemctl stop webhook_app
```

---

## Устранение неполадок

### Общие рекомендации
1. **Проверяйте логи**: используйте `journalctl` (для systemd) или `tail -f` (для supervisord) для поиска ошибок.
2. **Права доступа**: пользователь, запускающий сервис, должен иметь доступ к проекту и логам.
3. **Порты**: проверьте, что порты `5000` и `5005` свободны.
4. **Зависимости**: убедитесь, что все Python‑зависимости установлены в виртуальном окружении.

### Частые проблемы
- **Сервис не стартует**:
  - Проверьте логи на предмет ошибок.
  - Убедитесь, что все пути в unit/supervisor файлах указаны корректно.
  - Проверьте наличие и корректность `.env` (если используется).

- **Конфликт портов**:
  - Если порты заняты, измените `ExecStart` в unit‑файлах или `supervisord.conf`.

- **Gunicorn не найден**:
  - Установите gunicorn в виртуальное окружение:
    ```bash
    pip install gunicorn
    ```

---

Если нужно, могу: добавить готовые `.service` файлы с заполненными примерами путей, или подготовить адаптированный `supervisord.conf` для вашей конфигурации. Просто скажите, какие пути/пользователи вы используете.
