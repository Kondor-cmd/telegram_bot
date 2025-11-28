import logging
import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

# Настройки
BOT_TOKEN = "8337387211:AAE8y9hJ4T8jq4-F3BqhAoGB9IdFVYmHLXg"
ADMIN_CHAT_ID = "951804313"  # Замените на ваш ID из @userinfobot

# Состояния для ConversationHandler
NAME, SERVICE, CONTACT = range(3)

# Включение логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Команда /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Привет! Я бот для приема заявок на услуги.\n"
        "Нажмите /order чтобы оставить заявку"
    )

# Начало оформления заявки
def order(update: Update, context: CallbackContext):
    update.message.reply_text("📝 Как вас зовут?")
    return NAME

# Получение имени
def get_name(update: Update, context: CallbackContext):
    context.user_data['name'] = update.message.text
    update.message.reply_text("💼 Какая услуга вас интересует?")
    return SERVICE

# Получение услуги
def get_service(update: Update, context: CallbackContext):
    context.user_data['service'] = update.message.text
    update.message.reply_text("📞 Укажите ваш контакт (телефон, email или Telegram):")
    return CONTACT

# Получение контакта и отправка заявки
def get_contact(update: Update, context: CallbackContext):
    context.user_data['contact'] = update.message.text
    
    # Формируем заявку
    application = f"""
🎯 НОВАЯ ЗАЯВКА:
├ Имя: {context.user_data['name']}
├ Услуга: {context.user_data['service']}
└ Контакт: {context.user_data['contact']}
    
От пользователя: @{update.message.from_user.username}
ID: {update.message.from_user.id}
    """
    
    # Отправляем заявку администратору
    try:
        context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=application)
    except Exception as e:
        logger.error(f"Ошибка отправки заявки: {e}")
    
    # Подтверждаем пользователю
    update.message.reply_text(
        "✅ Спасибо! Ваша заявка принята.\n"
        "Мы свяжемся с вами в ближайшее время."
    )
    
    return ConversationHandler.END

# Отмена заявки
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("❌ Заявка отменена")
    return ConversationHandler.END

# Обработка ошибок
def error(update: Update, context: CallbackContext):
    logger.warning(f'Update {update} caused error {context.error}')

def main():
    # Создаем Updater и передаем ему токен бота
    updater = Updater(BOT_TOKEN, use_context=True)
    
    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher
    
    # Обработчик диалога заявки
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('order', order)],
        states={
            NAME: [MessageHandler(Filters.text & ~Filters.command, get_name)],
            SERVICE: [MessageHandler(Filters.text & ~Filters.command, get_service)],
            CONTACT: [MessageHandler(Filters.text & ~Filters.command, get_contact)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Добавляем обработчики
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(conv_handler)
    dp.add_error_handler(error)
    
    # Запускаем бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

