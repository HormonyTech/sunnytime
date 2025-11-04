from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# === НАСТРОЙКИ (ваши данные) ===
BOT_TOKEN = "8203614183:AAHeOpEq_M1wPA_IWFI4XzKygEA_MOOg6mA"
ADMIN_ID = 8355862725

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Здравствуйте!\n\n"
        "Отправьте любое сообщение — оно будет переслано администратору."
    )

# Обработчик текстовых сообщений
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"📥 Новое сообщение от пользователя\n"
                f"Имя: {user.full_name}\n"
                f"ID: {user.id}\n"
                f"Username: @{user.username or 'нет'}\n\n"
                f"Текст:\n{update.message.text}"
            )
        )
        await update.message.reply_text("Ваше сообщение отправлено администратору. Спасибо!")
    except Exception as e:
        await update.message.reply_text("Ошибка отправки сообщения. Попробуйте позже.")
        print(f"Ошибка при пересылке: {e}")

# Обработчик не‑текстовых сообщений
async def handle_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Извините, принимаются только текстовые сообщения.")

def main():
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message))
    application.add_handler(MessageHandler(~filters.TEXT, handle_non_text))

    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()
