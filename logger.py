import json
import logging

LOG_FILE = "bot_log.json"

# Настройка логгера
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

def write_log(data):
    """Записывает логи в JSON-файл"""
    try:
        with open(LOG_FILE, "a") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
            file.write(",\n")  # Добавляем разделитель для новых записей
    except Exception as e:
        logger.error(f"Ошибка записи лога: {e}")

def log_command(user_id, username, command):
    """Логирует команды пользователей"""
    data = {"user_id": user_id, "username": username, "command": command}
    logger.info(f"Команда {command} от {username} ({user_id})")
    write_log(data)

def log_api_response(url, status_code, response_data):
    """Логирует запросы к API"""
    data = {"url": url, "status_code": status_code, "response": response_data}
    logger.info(f"API-ответ {status_code} с {url}")
    write_log(data)
