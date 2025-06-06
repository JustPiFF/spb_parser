import json
import time
import requests
from page import PageAPI
from logger import logger

CONFIG_FILE = "config.json"

def save_config(data):
    with open(CONFIG_FILE, "w") as file:
        json.dump(data, file, indent=4)

def load_config():
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)


def send_telegram_notification(token, user_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": user_id if isinstance(user_id, str) else user_id[0], "text": message}

    print("[LOG] Запрос к Telegram API:", url, "Данные:", data)

    response = requests.post(url, json=data)

    logger.info(f"Запрос к Telegram API: {url} | Статус: {response.status_code} | Ответ: {response.text}")

    if response.status_code == 200:
        print("[LOG] Уведомление успешно отправлено:", message)
        return True
    else:
        print("[ERROR] Ошибка отправки уведомления:", response.status_code, response.text)
        return False


def start_monitoring():
    global monitoring
    monitoring = True
    last_count = None
    print("[LOG] Мониторинг запущен")

    while monitoring:
        config = load_config()
        page = PageAPI(config)

        try:
            data = page.fetch_data()
            if data:
                print("[LOG] Данные получены:", data)

                if "result" in data:
                    for item in data["result"]:
                        if item["id"] == config["search_id"]:
                            new_count = item["countFreeParticipant"]
                            if new_count > 0:
                                message = f"Свободных мест ({item['name']}): {new_count} 🚀 Бегом записываться! https://gorzdrav.spb.ru/"
                            else:
                                message = f"Свободных мест нет ({item['name']})!"
                            # Проверяем параметр notify_on_change
                            if config.get("notify_on_change", True):
                                if last_count is None or new_count != last_count:
                                    print("[LOG] Отправка уведомления:", message)
                                    send_telegram_notification(config["telegram_bot_token"], config["telegram_user_id"], message)
                                    last_count = new_count
                            else:
                                send_telegram_notification(config["telegram_bot_token"], config["telegram_user_id"], message)

            else:
                print("[ERROR] Ошибка получения данных: API вернул пустой ответ")

        except requests.exceptions.RequestException as e:
            print("[ERROR] Ошибка запроса:", e)

        time.sleep(config["check_interval"])


def stop_monitoring():
    global monitoring
    monitoring = False

def main():
    config = load_config()
    page = PageAPI(config)

    last_count = 0
    while True:
        data = page.fetch_data()
        if data and "result" in data:
            for item in data["result"]:
                if item["id"] == config["search_id"]:
                    new_count = item["countFreeParticipant"]
                    if new_count > 1 and new_count != last_count:
                        message = f"Свободных мест ({item['name']}): {new_count}"
                        logger.info("Значение изменилось! Отправка уведомления...")
                        send_telegram_notification(config["telegram_bot_token"], config["telegram_user_id"], message)
                    last_count = new_count
        time.sleep(config["check_interval"])

if __name__ == "__main__":
    main()
