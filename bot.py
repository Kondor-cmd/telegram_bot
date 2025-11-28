import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Настройки
BOT_TOKEN = "8337387211:AAE8y9hJ4T8jq4-F3BqhAoGB9IdFVYmHLXg"
ADMIN_CHAT_ID = "951804313"  # Ваш ID для получения заявок

# Состояния для ConversationHandler
NAME, SERVICE, CONTACT = range(3)

# Включение логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот для приема заявок на услуги.\n"
        "Нажмите /order чтобы оставить заявку"
    )

# Начало оформления заявки
async def order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Как вас зовут?")
    return NAME

# Получение имени
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("💼 Какая услуга вас интересует?")
    return SERVICE

# Получение услуги
async def get_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['service'] = update.message.text
    await update.message.reply_text("📞 Укажите ваш контакт (телефон, email или Telegram):")
    return CONTACT

# Получение контакта и отправка заявки
async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['contact'] = update.message.text
    
    # Формируем заявку
    application = f"""
🎯 НОВАЯ ЗАЯВКА:
├ Имя: {context.user_data['name']}
├ Услуга: {context.user_data['service']}
└ Контакт: {context.user_data['contact']}
    
От пользователя: @{update.message.from_user.username}
    """
    
    # Отправляем заявку администратору
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=application)
    
    # Подтверждаем пользователю
    await update.message.reply_text(
        "✅ Спасибо! Ваша заявка принята.\n"
        "Мы свяжемся с вами в ближайшее время."
    )
    
    return ConversationHandler.END

# Отмена заявки
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Заявка отменена")
    return ConversationHandler.END

# Основная функция
def main():
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчик диалога заявки
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('order', order)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_service)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    
    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
