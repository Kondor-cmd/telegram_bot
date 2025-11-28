import logging
import requests
import time

# Настройки
BOT_TOKEN = "8337387211:AAE8y9hJ4T8jq4-F3BqhAoGB9IdFVYmHLXg"
ADMIN_CHAT_ID = "951804313"  # Замените на ваш ID из @userinfobot

# Включение логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранилище состояний пользователей
user_states = {}

def send_message(chat_id, text):
    """Отправка сообщения через Telegram API"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        return None

def get_updates(offset=None):
    """Получение обновлений от Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        logger.error(f"Ошибка получения обновлений: {e}")
        return None

def process_message(chat_id, text, username):
    """Обработка входящих сообщений"""
    if text == "/start":
        send_message(chat_id, "👋 Привет! Я бот для приема заявок на услуги.\nНапишите 'заявка' чтобы оставить заявку")
        user_states[chat_id] = None
    
    elif text.lower() in ["заявка", "/order"]:
        send_message(chat_id, "📝 Как вас зовут?")
        user_states[chat_id] = "waiting_name"
    
    elif user_states.get(chat_id) == "waiting_name":
        user_states[chat_id] = {"name": text, "step": "waiting_service"}
        send_message(chat_id, "💼 Какая услуга вас интересует?")
    
    elif user_states.get(chat_id) and user_states[chat_id].get("step") == "waiting_service":
        user_states[chat_id]["service"] = text
        user_states[chat_id]["step"] = "waiting_contact"
        send_message(chat_id, "📞 Укажите ваш контакт (телефон, email или Telegram):")
    
    elif user_states.get(chat_id) and user_states[chat_id].get("step") == "waiting_contact":
        user_data = user_states[chat_id]
        
        # Формируем заявку
        application = f"""
🎯 НОВАЯ ЗАЯВКА:
├ Имя: {user_data['name']}
├ Услуга: {user_data['service']}
└ Контакт: {text}
        
От пользователя: @{username}
ID: {chat_id}
        """
        
        # Отправляем заявку администратору
        send_message(ADMIN_CHAT_ID, application)
        
        # Подтверждаем пользователю
        send_message(chat_id, "✅ Спасибо! Ваша заявка принята.\nМы свяжемся с вами в ближайшее время.")
        
        # Сбрасываем состояние
        user_states[chat_id] = None

def main():
    logger.info("Бот запущен!")
    last_update_id = None
    
    while True:
        try:
            # Получаем обновления
            updates = get_updates(last_update_id)
            
            if updates and updates.get("ok"):
                for update in updates["result"]:
                    last_update_id = update["update_id"] + 1
                    
                    if "message" in update and "text" in update["message"]:
                        message = update["message"]
                        chat_id = message["chat"]["id"]
                        text = message["text"]
                        username = message["from"].get("username", "не указан")
                        
                        # Обрабатываем сообщение
                        process_message(chat_id, text, username)
            
            # Пауза между запросами
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Ошибка в основном цикле: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()



