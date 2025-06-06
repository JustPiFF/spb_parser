import json
import telebot
import threading
import requests
from telebot import types
from main import start_monitoring, stop_monitoring, load_config, save_config
from logger import log_command, log_api_response

CONFIG_FILE = "config.json"

# Инициализация бота
config = load_config()
bot = telebot.TeleBot(config["telegram_bot_token"])

monitoring_thread = None


def is_authorized(user_id):
    """Проверяет, есть ли пользователь в списке разрешенных"""
    return str(user_id) in config["telegram_user_id"]


def create_main_menu():
    """Создает главное меню с кнопками"""
    markup = types.InlineKeyboardMarkup(row_width=2)

    # Кнопки управления мониторингом
    btn_monitor = types.InlineKeyboardButton("🔍 Запустить мониторинг", callback_data="monitor")
    btn_stop = types.InlineKeyboardButton("⛔️ Остановить мониторинг", callback_data="stop")
    btn_status = types.InlineKeyboardButton("🚀 Статус", callback_data="status")

    # Кнопки настроек
    btn_config = types.InlineKeyboardButton("⚙️ Настройки", callback_data="settings")
    btn_get_ids = types.InlineKeyboardButton("🔍 Получить ID", callback_data="get_ids")
    btn_help = types.InlineKeyboardButton("❓ Помощь", callback_data="help")

    markup.add(btn_monitor, btn_stop)
    markup.add(btn_status, btn_config)
    markup.add(btn_get_ids, btn_help)

    return markup


def create_settings_menu():
    """Создает меню настроек"""
    markup = types.InlineKeyboardMarkup(row_width=2)

    btn_set_id = types.InlineKeyboardButton("🔢 Изменить ID", callback_data="set_id")
    btn_set_interval = types.InlineKeyboardButton("⏱️ Изменить интервал", callback_data="set_interval")
    btn_toggle_proxy = types.InlineKeyboardButton("🔄 Переключить прокси", callback_data="toggle_proxy")
    btn_toggle_notify = types.InlineKeyboardButton("📢 Переключить уведомления", callback_data="toggle_notify")
    btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")

    markup.add(btn_set_id, btn_set_interval)
    markup.add(btn_toggle_proxy, btn_toggle_notify)
    markup.add(btn_back)

    return markup


def get_config_text():
    """Возвращает текст с текущей конфигурацией"""
    config = load_config()
    return f"""🛠 Текущий конфиг:
🔍 ID поиска: {config["search_id"]}
⏳ Интервал: {config["check_interval"]} сек
🔄 Прокси: {'Включен' if config["use_proxy"] else 'Выключен'}
🚀 Мониторинг: {'Запущен' if config["monitoring"] else 'Остановлен'}
📢 Уведомления при изменении: {'Включены' if config.get("notify_on_change", True) else 'Выключены'}"""


@bot.message_handler(commands=["start"])
def start(message):
    if not is_authorized(message.chat.id):
        bot.send_message(message.chat.id, "⛔️ У вас нет доступа к боту!")
        return

    log_command(message.chat.id, message.from_user.username, "/start")
    print(f"[LOG] {message.from_user.username} ({message.chat.id}) отправил /start")

    welcome_text = f"""👋 Привет, {message.from_user.first_name}! 

🏥 Медорганизация: СПб ГБУЗ "Городская поликлиника №98"
🏨 Поликлиническое отделение №128

{get_config_text()}

Выберите действие:"""

    bot.send_message(message.chat.id, welcome_text, reply_markup=create_main_menu())


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if not is_authorized(call.message.chat.id):
        bot.answer_callback_query(call.id, "⛔️ У вас нет доступа к боту!")
        return

    # Отвечаем на callback, чтобы убрать "часики"
    bot.answer_callback_query(call.id)

    if call.data == "main_menu":
        bot.edit_message_text(
            f"👋 Главное меню\n\n{get_config_text()}\n\nВыберите действие:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=create_main_menu()
        )

    elif call.data == "monitor":
        handle_monitor_callback(call)

    elif call.data == "stop":
        handle_stop_callback(call)

    elif call.data == "status":
        handle_status_callback(call)

    elif call.data == "settings":
        bot.edit_message_text(
            f"⚙️ Настройки\n\n{get_config_text()}\n\nВыберите параметр для изменения:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=create_settings_menu()
        )

    elif call.data == "get_ids":
        handle_get_ids_callback(call)

    elif call.data == "help":
        handle_help_callback(call)

    elif call.data == "set_id":
        handle_set_id_callback(call)

    elif call.data == "set_interval":
        handle_set_interval_callback(call)

    elif call.data == "toggle_proxy":
        handle_toggle_proxy_callback(call)

    elif call.data == "toggle_notify":
        handle_toggle_notify_callback(call)


def handle_monitor_callback(call):
    global monitoring_thread

    log_command(call.message.chat.id, call.from_user.username, "monitor_button")
    config = load_config()

    print("[LOG] Загруженный конфиг:", config)

    config["monitoring"] = True
    save_config(config)

    print("[LOG] Конфиг сохранен:", config)

    if monitoring_thread is None or not monitoring_thread.is_alive():
        print("[LOG] Запуск потока мониторинга...")
        monitoring_thread = threading.Thread(target=start_monitoring, daemon=True)
        monitoring_thread.start()

        bot.edit_message_text(
            f"🔍 Мониторинг запущен!\n\n{get_config_text()}\n\nВыберите действие:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=create_main_menu()
        )
    else:
        bot.edit_message_text(
            f"⚠️ Мониторинг уже работает!\n\n{get_config_text()}\n\nВыберите действие:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=create_main_menu()
        )


def handle_stop_callback(call):
    log_command(call.message.chat.id, call.from_user.username, "stop_button")
    config = load_config()

    print("[LOG] Загруженный конфиг перед изменением:", config)

    config["monitoring"] = False
    save_config(config)

    print("[LOG] Конфиг после сохранения:", config)

    stop_monitoring()

    bot.edit_message_text(
        f"⛔️ Мониторинг остановлен.\n\n{get_config_text()}\n\nВыберите действие:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=create_main_menu()
    )


def handle_status_callback(call):
    log_command(call.message.chat.id, call.from_user.username, "status_button")
    config = load_config()
    print(f"[LOG] {call.from_user.username} ({call.message.chat.id}) запросил статус мониторинга")

    status_text = f"🚀 Статус мониторинга: {'Запущен' if config['monitoring'] else 'Остановлен'}\n\n{get_config_text()}\n\nВыберите действие:"

    bot.edit_message_text(
        status_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=create_main_menu()
    )


def handle_get_ids_callback(call):
    log_command(call.message.chat.id, call.from_user.username, "get_ids_button")
    print(f"[LOG] {call.from_user.username} ({call.message.chat.id}) запросил /get_ids")

    url = "https://gorzdrav.spb.ru/_api/api/v2/schedule/lpu/1222/specialties"
    config = load_config()

    try:
        response = requests.get(url, proxies=config.get("proxy") if config["use_proxy"] else None, timeout=10)
        response_data = response.json() if response.status_code == 200 else {}

        log_api_response(url, response.status_code, response_data)
        print(f"[LOG] API ответ {response.status_code}: {response_data}")

        if response.status_code == 200:
            specialists = "\n".join([f"ID: {item['id']} - {item['name']}" for item in response_data["result"]])

            # Создаем кнопку "Назад"
            markup = types.InlineKeyboardMarkup()
            btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
            markup.add(btn_back)

            bot.edit_message_text(
                f"📋 Доступные ID:\n\n{specialists}\n\nДля изменения ID используйте: /set_id <номер>",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        else:
            markup = types.InlineKeyboardMarkup()
            btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
            markup.add(btn_back)

            bot.edit_message_text(
                "❌ Ошибка получения данных.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
    except requests.exceptions.RequestException as e:
        markup = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
        markup.add(btn_back)

        bot.edit_message_text(
            f"❌ Ошибка запроса: {e}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )


def handle_help_callback(call):
    help_text = """📌 Помощь по использованию бота:

🔍 Мониторинг
• Запустить/остановить отслеживание записей
• Проверить текущий статус

⚙️ Настройки
• Изменить ID специалиста для поиска
• Настроить интервал проверки
• Включить/выключить прокси
• Настроить уведомления

📋 Команды через текст:
• /set_id <номер> - изменить ID поиска
• /set_interval <секунды> - изменить интервал

💡 Совет: Используйте кнопки для удобной навигации!"""

    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")
    markup.add(btn_back)

    bot.edit_message_text(
        help_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )


def handle_set_id_callback(call):
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("⬅️ Назад к настройкам", callback_data="settings")
    markup.add(btn_back)

    bot.edit_message_text(
        "🔢 Для изменения ID поиска отправьте команду:\n\n/set_id <номер>\n\nНапример: /set_id 70\n\nИспользуйте кнопку 'Получить ID' для просмотра доступных ID.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )


def handle_set_interval_callback(call):
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("⬅️ Назад к настройкам", callback_data="settings")
    markup.add(btn_back)

    bot.edit_message_text(
        "⏱️ Для изменения интервала проверки отправьте команду:\n\n/set_interval <секунды>\n\nНапример: /set_interval 60\n\nРекомендуемый интервал: 30-120 секунд.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )


def handle_toggle_proxy_callback(call):
    log_command(call.message.chat.id, call.from_user.username, "toggle_proxy_button")
    config = load_config()
    config["use_proxy"] = not config["use_proxy"]
    save_config(config)

    proxy_status = "включен" if config["use_proxy"] else "выключен"
    print(f"[LOG] {call.from_user.username} ({call.message.chat.id}) изменил состояние прокси: {proxy_status}")

    bot.edit_message_text(
        f"🔄 Прокси теперь {proxy_status}.\n\n{get_config_text()}\n\nВыберите параметр для изменения:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=create_settings_menu()
    )


def handle_toggle_notify_callback(call):
    log_command(call.message.chat.id, call.from_user.username, "toggle_notify_button")

    config = load_config()
    config["notify_on_change"] = not config["notify_on_change"]
    save_config(config)

    notify_status = "теперь включены" if config["notify_on_change"] else "теперь отключены"
    print(f"[LOG] {call.from_user.username} ({call.message.chat.id}) изменил состояние уведомлений: {notify_status}")

    bot.edit_message_text(
        f"📢 Уведомления при изменении {notify_status}.\n\n{get_config_text()}\n\nВыберите параметр для изменения:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=create_settings_menu()
    )


# Обработчики текстовых команд (для обратной совместимости)
@bot.message_handler(commands=["help"])
def help(message):
    if not is_authorized(message.chat.id):
        bot.send_message(message.chat.id, "⛔️ У вас нет доступа к боту!")
        return

    bot.send_message(message.chat.id, "Используйте /start для открытия главного меню с кнопками!")


@bot.message_handler(commands=["set_id"])
def set_id(message):
    if not is_authorized(message.chat.id):
        bot.send_message(message.chat.id, "⛔️ У вас нет доступа к боту!")
        return

    log_command(message.chat.id, message.from_user.username, "/set_id")
    config = load_config()
    parts = message.text.split()

    if len(parts) > 1 and parts[1].isdigit():
        config["search_id"] = parts[1]
        save_config(config)
        print(f"[LOG] {message.from_user.username} ({message.chat.id}) изменил ID поиска на {parts[1]}")

        # Отправляем подтверждение с кнопкой возврата в меню
        markup = types.InlineKeyboardMarkup()
        btn_menu = types.InlineKeyboardButton("📋 Главное меню", callback_data="main_menu")
        markup.add(btn_menu)

        bot.send_message(
            message.chat.id,
            f"✅ ID поиска изменен на {parts[1]}\n\n{get_config_text()}",
            reply_markup=markup
        )
    else:
        bot.send_message(message.chat.id, "❌ Ошибка: Введите ID после команды. Например: /set_id 70")


@bot.message_handler(commands=["set_interval"])
def set_interval(message):
    if not is_authorized(message.chat.id):
        bot.send_message(message.chat.id, "⛔️ У вас нет доступа к боту!")
        return

    log_command(message.chat.id, message.from_user.username, "/set_interval")
    config = load_config()
    parts = message.text.split()

    if len(parts) > 1 and parts[1].isdigit():
        config["check_interval"] = int(parts[1])
        save_config(config)
        print(f"[LOG] {message.from_user.username} ({message.chat.id}) изменил интервал проверки на {parts[1]} сек.")

        # Отправляем подтверждение с кнопкой возврата в меню
        markup = types.InlineKeyboardMarkup()
        btn_menu = types.InlineKeyboardButton("📋 Главное меню", callback_data="main_menu")
        markup.add(btn_menu)

        bot.send_message(
            message.chat.id,
            f"✅ Интервал проверки изменен на {parts[1]} сек.\n\n{get_config_text()}",
            reply_markup=markup
        )
    else:
        bot.send_message(message.chat.id, "❌ Ошибка: Введите интервал после команды. Например: /set_interval 60")


# Обработчик для всех остальных сообщений
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if not is_authorized(message.chat.id):
        bot.send_message(message.chat.id, "⛔️ У вас нет доступа к боту!")
        return

    bot.send_message(
        message.chat.id,
        "👋 Используйте /start for открытия главного меню с кнопками!",
        reply_markup=create_main_menu()
    )


# Запускаем бота
if __name__ == "__main__":
    print("[LOG] Бот запущен с поддержкой кнопок!")
    bot.polling(none_stop=True, interval=0)