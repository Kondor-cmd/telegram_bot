import logging
import requests
import re
import time
import os

# Настройки бота
BOT_TOKEN = "8337387211:AAE8y9hJ4T8jq4-F3BqhAoGB9IdFVYmHLXg"
CHANNEL_ID = "-1003377118326"  # Замените на цифровой ID вашего канала
ADMIN_CHAT_ID = "951804313"  # Замените на ваш ID

# Включение логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

user_states = {}

def validate_phone(phone):
    pattern = r'^(\+7|8)[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$'
    return re.match(pattern, phone.strip()) is not None

def validate_name(name):
    if len(name.strip()) < 2 or len(name.strip()) > 30:
        return False
    return re.match(r'^[a-zA-Zа-яА-ЯёЁ\s\-]+$', name.strip()) is not None

def validate_service(service):
    return 5 <= len(service.strip()) <= 100

def escape_markdown(text):
    """Экранирование символов Markdown"""
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in text])

def send_message(chat_id, text, parse_mode=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if parse_mode:
        data["parse_mode"] = parse_mode
        
    try:
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        return None

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка получения обновлений: {e}")
        return None

def process_message(chat_id, text, username, first_name):
    if text == "/start":
        send_message(chat_id, "👋 Привет! Я бот для приема заявок на услуги.\nНапишите 'заявка' чтобы оставить заявку")
        user_states[chat_id] = None
    
    elif text.lower() in ["заявка", "/order"]:
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
        send_message(chat_id, "📞 *Укажите ваш номер телефона:*\n\nФормат: +7XXX XXX XX XX или 8XXX XXX XX XX\n\nПример: +7 999 123 45 67", parse_mode="Markdown")
    
    elif user_states.get(chat_id) and user_states[chat_id].get("step") == "waiting_phone":
        if not validate_phone(text):
            send_message(chat_id, "❌ *Неверный формат номера телефона!*\n\nПожалуйста, укажите номер в правильном формате:\n\n• +7 999 123 45 67\n• 89991234567\n• +7(999)123-45-67", parse_mode="Markdown")
            return
        
        user_data = user_states[chat_id]
        phone = text.strip()
        
        # Экранируем данные пользователя для Markdown
        safe_name = escape_markdown(user_data['name'])
        safe_phone = escape_markdown(phone)
        safe_service = escape_markdown(user_data['service'])
        safe_username = escape_markdown(username)
        safe_first_name = escape_markdown(first_name)
        
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
        
        # Уведомляем администратора (без Markdown для надежности)
        send_message(ADMIN_CHAT_ID, f"📨 Новая заявка от {safe_name}")
        
        if channel_result and channel_result.get('ok'):
            send_message(chat_id, "✅ *Спасибо! Ваша заявка принята!*\n\nМы свяжемся с вами в ближайшее время.", parse_mode="Markdown")
        else:
            # Пробуем отправить без Markdown
            application_plain = f"""🎯 НОВАЯ ЗАЯВКА

👤 Клиент: {user_data['name']}
📱 Телефон: {phone}
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

    elif text.lower() in ["отмена", "cancel", "/cancel"]:
        user_states[chat_id] = None
        send_message(chat_id, "❌ Заявка отменена")

def main():
    logger.info("Бот запущен!")
    
    # Тестовое сообщение
    send_message(ADMIN_CHAT_ID, "🟢 Бот запущен и готов к работе!")
    
    last_update_id = None
    
    while True:
        try:
            updates = get_updates(last_update_id)
            
            if updates and updates.get("ok"):
                for update in updates["result"]:
                    last_update_id = update["update_id"] + 1
                    
                    if "message" in update and "text" in update["message"]:
                        message = update["message"]
                        chat_id = message["chat"]["id"]
                        text = message["text"]
                        username = message["from"].get("username", "не указан")
                        first_name = message["from"].get("first_name", "не указано")
                        
                        process_message(chat_id, text, username, first_name)
            
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Ошибка в основном цикле: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()




