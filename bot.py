import logging
import requests
import re
import time
from flask import Flask
import threading

# Создаем Flask приложение для порта
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Telegram Bot is running!"

@app.route('/health')
def health():
    return "🟢 Bot is healthy"

def run_web():
    app.run(host='0.0.0.0', port=10000)

# Настройки бота
BOT_TOKEN = "8337387211:AAE8y9hJ4T8jq4-F3BqhAoGB9IdFVYmHLXg"
CHANNEL_ID = "-1003377118326"  # Замените на цифровой ID вашего канала
ADMIN_CHAT_ID = "951804313"  # Замените на ваш ID

# Включение логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

user_states = {}

def validate_phone(phone):
    """Проверка номера телефона (без пробелов)"""
    clean_phone = re.sub(r'[\s\-\(\)\+]', '', phone.strip())
    
    pattern = r'^(\+7|8)?[489][0-9]{9}$'
    
    if len(clean_phone) == 10 and clean_phone[0] in '489':
        clean_phone = '8' + clean_phone
    
    return re.match(pattern, clean_phone) is not None

def format_phone(phone):
    """Форматирует номер телефона для красивого отображения"""
    clean_phone = re.sub(r'[\s\-\(\)\+]', '', phone.strip())
    
    if len(clean_phone) == 10 and clean_phone[0] in '489':
        clean_phone = '8' + clean_phone
    
    if len(clean_phone) == 11:
        if clean_phone.startswith('8'):
            return f"+7 ({clean_phone[1:4]}) {clean_phone[4:7]}-{clean_phone[7:9]}-{clean_phone[9:]}"
        elif clean_phone.startswith('7'):
            return f"+7 ({clean_phone[1:4]}) {clean_phone[4:7]}-{clean_phone[7:9]}-{clean_phone[9:]}"
    
    return phone

def validate_name(name):
    if len(name.strip()) < 2 or len(name.strip()) > 30:
        return False
    return re.match(r'^[a-zA-Zа-яА-ЯёЁ\s\-]+$', name.strip()) is not None

def validate_service(service):
    return 5 <= len(service.strip()) <= 100

def escape_markdown(text):
    """Экранирование символов Markdown"""
    if not text:
        return ""
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in str(text)])

def send_message(chat_id, text, parse_mode=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if parse_mode:
        data["parse_mode"] = parse_mode
        
    try:
        response = requests.post(url, data=data, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        return None

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
        
    try:
        response = requests.get(url, params=params, timeout=35)
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка получения обновлений: {e}")
        return None

def process_message(chat_id, text, username, first_name):
    # Пропускаем команды бота
    if text.startswith('/'):
        if text == "/start":
            send_message(chat_id, "👋 Привет! Я бот для приема заявок на услуги.\nНапишите 'заявка' чтобы оставить заявку")
            user_states[chat_id] = None
        elif text == "/cancel":
            user_states[chat_id] = None
            send_message(chat_id, "❌ Заявка отменена")
        return
    
    # Пропускаем служебные сообщения
    if any(emoji in text for emoji in ["✅", "❌", "📝", "💼", "📞", "👋"]):
        return
        
    if text.lower() in ["заявка", "order"]:
        send_message(chat_id, "📝 *Как вас зовут?*\n\nУкажите ваше имя и фамилию", parse_mode="Markdown")
        user_states[chat_id] = "waiting_name"
    
    elif user_states.get(chat_id) == "waiting_name":
        if not validate_name(text):
            send_message(chat_id, "❌ *Неверный формат имени!*\n\nПожалуйста, укажите настоящее имя и фамилию (только буквы, от 2 до 30 символов)\n\nПример: Иван Иванов", parse_mode="Markdown")
            return
        
        user_states[chat_id] = {
            "name": text.strip(),
            "step": "waiting_service"
        }
        send_message(chat_id, "💼 *Какая услуга вас интересует?*\n\nОпишите подробно, что вам нужно", parse_mode="Markdown")
    
    elif user_states.get(chat_id) and user_states[chat_id].get("step") == "waiting_service":
        if not validate_service(text):
            send_message(chat_id, "❌ *Слишком короткое описание услуги!*\n\nПожалуйста, опишите подробнее что вам нужно (от 5 до 100 символов)\n\nПример: Нужен ремонт компьютера с заменой жесткого диска", parse_mode="Markdown")
            return
        
        user_states[chat_id]["service"] = text.strip()
        user_states[chat_id]["step"] = "waiting_phone"
        send_message(chat_id, "📞 *Укажите ваш номер телефона:*\n\nФормат: +79991234567 или 89991234567\n\nПример: +79991234567", parse_mode="Markdown")
    
    elif user_states.get(chat_id) and user_states[chat_id].get("step") == "waiting_phone":
        if not validate_phone(text):
            send_message(chat_id, "❌ *Неверный формат номера телефона!*\n\nПожалуйста, укажите номер в правильном формате:\n\n• +79991234567\n• 89991234567\n• 9991234567", parse_mode="Markdown")
            return
        
        user_data = user_states[chat_id]
        formatted_phone = format_phone(text)
        
        # Экранируем данные пользователя для Markdown
        safe_name = escape_markdown(user_data['name'])
        safe_phone = escape_markdown(formatted_phone)
        safe_service = escape_markdown(user_data['service'])
        safe_username = escape_markdown(username if username else "не указан")
        safe_first_name = escape_markdown(first_name if first_name else "не указано")
        
        # Формируем заявку с экранированием
        application = f"""🎯 *НОВАЯ ЗАЯВКА*

👤 *Клиент:* {safe_name}
📱 *Телефон:* `{safe_phone}`
💼 *Услуга:* {safe_service}
👤 *Telegram:* @{safe_username} ({safe_first_name})
🆔 *User ID:* `{chat_id}`
⏰ *Время:* {time.strftime('%d.%m.%Y %H:%M')}

#заявка #клиент"""
        
        # Отправляем в канал
        channel_result = send_message(CHANNEL_ID, application, "Markdown")
        
        # Уведомляем администратора
        send_message(ADMIN_CHAT_ID, f"📨 Новая заявка от {safe_name}")
        
        if channel_result and channel_result.get('ok'):
            send_message(chat_id, "✅ *Спасибо! Ваша заявка принята!*\n\nМы свяжемся с вами в ближайшее время.", parse_mode="Markdown")
        else:
            # Пробуем отправить без Markdown
            application_plain = f"""🎯 НОВАЯ ЗАЯВКА

👤 Клиент: {user_data['name']}
📱 Телефон: {formatted_phone}
💼 Услуга: {user_data['service']}
👤 Telegram: @{username} ({first_name})
🆔 User ID: {chat_id}
⏰ Время: {time.strftime('%d.%m.%Y %H:%M')}

#заявка #клиент"""
            
            channel_result_plain = send_message(CHANNEL_ID, application_plain)
            if channel_result_plain and channel_result_plain.get('ok'):
                send_message(chat_id, "✅ *Спасибо! Ваша заявка принята!*\n\nМы свяжемся с вами в ближайшее время.", parse_mode="Markdown")
            else:
                send_message(chat_id, "❌ *Ошибка отправки заявки.*\n\nПопробуйте позже.", parse_mode="Markdown")
                logger.error(f"Ошибка отправки в канал: {channel_result}")
        
        user_states[chat_id] = None

    elif text.lower() in ["отмена", "cancel"]:
        user_states[chat_id] = None
        send_message(chat_id, "❌ Заявка отменена")

def main():
    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()
    
    logger.info("Бот запущен! Веб-сервер работает на порту 10000")
    
    # Получаем последние обновления при старте
    updates = get_updates()
    if updates and updates.get("ok") and updates["result"]:
        # Берем самый последний update_id
        last_update_id = updates["result"][-1]["update_id"]
        logger.info(f"Начинаем с update_id: {last_update_id}")
    else:
        last_update_id = None
        logger.info("Начинаем с чистого листа")
    
    # Тестовое сообщение (только один раз)
    send_message(ADMIN_CHAT_ID, "🟢 Бот запущен и готов к работе!")
    
    while True:
        try:
            # Всегда запрашиваем обновления с последнего известного ID + 1
            updates = get_updates(last_update_id + 1 if last_update_id else None)
            
            if updates and updates.get("ok") and updates["result"]:
                for update in updates["result"]:
                    current_update_id = update["update_id"]
                    last_update_id = current_update_id  # Обновляем последний ID
                    
                    if "message" in update and "text" in update["message"]:
                        message = update["message"]
                        chat_id = message["chat"]["id"]
                        text = message["text"]
                        username = message["from"].get("username", "не указан")
                        first_name = message["from"].get("first_name", "не указано")
                        
                        logger.info(f"Обрабатываем сообщение: {text[:50]}... от {username}")
                        process_message(chat_id, text, username, first_name)
            
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Ошибка в основном цикле: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()







