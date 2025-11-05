import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

# === НАСТРОЙКИ ===
BOT_TOKEN = "8203614183:AAHeOpEq_M1wPA_IWFI4XzKygEA_MOOg6mA"
ADMIN_ID = 8355862725

# Словарь активных диалогов: user_id → {last_message_time, chat_history, awaiting_reply}
active_chats = {}

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler("bot_log.txt", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Обработчик /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id == ADMIN_ID:
        await show_admin_menu(update, context)
    else:
        active_chats[user_id] = {
            "last_message_time": datetime.now(),
            "chat_history": [],
            "awaiting_reply": False
        }
        await update.message.reply_text(
            "Здравствуйте!\n\n"
            "Отправьте сообщение или файл — они будут пересланы администратору."
        )

# Показать меню админа
async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(active_chats) == 0:
        await update.message.reply_text("Нет активных диалогов.")
        return

    keyboard = []
    for user_id in active_chats:
        user = await context.bot.get_chat(user_id)
        name = user.full_name or user.username or str(user_id)
        keyboard.append([
            InlineKeyboardButton(f"Ответить {name}", callback_data=f"reply_{user_id}")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Активные диалоги:",
        reply_markup=reply_markup
    )

# Обработка нажатий кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("reply_"):
        return

    user_id = int(query.data.split("_")[1])
    
    # Отмечаем, что ждём ответ для этого пользователя
    for uid in active_chats:
        active_chats[uid]["awaiting_reply"] = (uid == user_id)
    
    await query.edit_message_text(
        f"Напишите ответ для пользователя {user_id}:\n"
        f"Формат: Ответ: ваш текст"
    )

# Пересылка сообщений от пользователя к админу
async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    if user_id == ADMIN_ID:
        return

    # Обновляем время последнего сообщения
    if user_id not in active_chats:
        active_chats[user_id] = {"chat_history": [], "awaiting_reply": False}
    active_chats[user_id]["last_message_time"] = datetime.now()

    # Логируем сообщение
    log_message(user_id, "user", update.message)

    try:
        # Формируем текст сообщения
        text = (
            f"📥 Новое сообщение от пользователя\n"
            f"Имя: {user.full_name}\n"
            f"ID: {user_id}\n"
            f"Username: @{user.username or 'нет'}\n\n"
        )

        if update.message.text:
            text += f"Текст:\n{update.message.text}"
        elif update.message.photo:
            text += "Фото:"
        elif update.message.document:
            text += f"Файл: {update.message.document.file_name}"

        # Отправляем админу
        await context.bot.send_message(chat_id=ADMIN_ID, text=text)

        # Пересылаем медиа (если есть)
        if update.message.photo:
            await update.message.copy(chat_id=ADMIN_ID)
        elif update.message.document:
            await update.message.copy(chat_id=ADMIN_ID)

        await update.message.reply_text("Ваше сообщение отправлено администратору. Спасибо!")

    except Exception as e:
        await update.message.reply_text("Ошибка отправки сообщения. Попробуйте позже.")
        logger.error(f"Ошибка пересылки от {user_id}: {e}")

# Обработка ответов админа
async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.message.from_user.id
    if admin_id != ADMIN_ID:
        return

    text = update.message.text
    if not text.startswith("Ответ:"):
        await update.message.reply_text(
            "Чтобы ответить, начните сообщение с:\n"
            "Ответ: ваш текст"
        )
        return

    # Ищем активный диалог
    last_reply = None
    for user_id, data in active_chats.items():
        if data["awaiting_reply"]:
            last_reply = user_id
            break

    if not last_reply:
        await update.message.reply_text("Выберите пользователя через меню /start.")
        return

    reply_text = text.split(":", 1)[1].strip()

    try:
        await context.bot.send_message(
            chat_id=last_reply,
            text=f!Ответ администратора:\n{reply_text}"
        )
        await update.message.reply_text(f"Ответ отправлен пользователю {last_reply}.")

        # Логируем ответ
        log_message(last_reply, "admin", update.message)

        # Снимаем флаг ожидания
        active_chats[last_reply]["awaiting_reply"] = False

    except Exception as e:
        await update.message.reply_text(f"Ошибка отправки ответа: {e}")
        logger.error(f"Ошибка ответа {last_reply}: {e}")

# Проверка задержек ответов
async def check_response_time(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    for user_id, data in list(active_chats.items()):
        last_time = data["last_message_time"]
        if now - last_time > timedelta(minutes=10):  # 10 минут без ответа
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="Администратор пока не ответил. Пожалуйста, ожидайте."
                )
                # Обновляем время уведомления, чтобы не спамить
                data["last_message_time"] = now
            except:
                pass

# Логирование сообщений
def log_message(user_id: int, sender: str, message: Update.message):
    with open("chat_history.log", "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = message.text or message.caption or "(медиа)"
        f.write(f"{timestamp} | {sender} ({user_id}): {text}\n")

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))

    # Обработчики сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        forward_to_admin
    ))
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.DOCUMENT,
        forward_to_admin
    ))
    application.add_handler(MessageHandler(
        filters.TEXT & filters.USER,  reply_to_user
    ))

    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запуск периодической проверки времени ответа
    job_queue = application.job_queue
    job_queue.run_repeating(check_response_time, interval=60, first=10)

    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()
