import os
import logging
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройки / Settings
DEFAULT_TZ = pytz.timezone('Europe/Moscow')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'Collected_messages')
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'bot_token.txt')

# Словарь русских названий месяцев / Russian month names dictionary
RUS_MONTHS = {
    1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
    5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
    9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
}

# Настройка логирования / Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def get_bot_token():
    """Получение токена бота / Get bot token"""
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(f"Файл с токеном не найден: {TOKEN_FILE}")
    
    with open(TOKEN_FILE, 'r') as f:
        token = f.read().strip()
    
    if not token:
        raise ValueError("Токен бота не может быть пустым / Bot token cannot be empty")
    
    return token

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start / Start command handler"""
    user = update.effective_user
    help_text = (
        f"Привет, {user.first_name}!\n"
        "Я бот для сбора сообщений из чатов.\n\n"
        "Доступные команды:\n"
        "/start - показать это сообщение\n"
        "/help - помощь\n"
        "/collect - начать сбор сообщений\n"
        "/stop - остановить сбор сообщений\n\n"
        "Просто добавьте меня в чат и дайте права администратора!"
    )
    await update.message.reply_text(help_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help / Help command handler"""
    help_text = (
        "Помощь по использованию бота:\n\n"
        "1. Добавьте бота в чат\n"
        "2. Дайте боту права администратора (чтобы он мог видеть сообщения)\n"
        "3. Отправьте команду /collect в чате для начала сбора\n"
        "4. Отправьте /stop для остановки\n\n"
        "Сообщения сохраняются в файлы по месяцам."
    )
    await update.message.reply_text(help_text)

async def collect_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /collect / Collect command handler"""
    chat = update.effective_chat
    
    if not chat:
        await update.message.reply_text("Эта команда работает только в чатах / This command works only in chats")
        return
    
    # Создаем папку для чата / Create folder for chat
    chat_dir = os.path.join(OUTPUT_DIR, str(chat.id))
    os.makedirs(chat_dir, exist_ok=True)
    
    # Файл для текущего месяца / File for current month
    now = datetime.now(DEFAULT_TZ)
    month_file = os.path.join(chat_dir, f"{now.year}-{RUS_MONTHS[now.month]}.txt")
    
    # Сохраняем информацию о чате / Save chat info
    context.chat_data['collecting'] = True
    context.chat_data['month_file'] = month_file
    
    await update.message.reply_text(
        f"Начинаю сбор сообщений в чате {chat.title}\n"
        f"Сообщения сохраняются в: {month_file}"
    )

async def stop_collecting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /stop / Stop command handler"""
    if 'collecting' in context.chat_data and context.chat_data['collecting']:
        context.chat_data['collecting'] = False
        await update.message.reply_text("Сбор сообщений остановлен / Message collection stopped")
    else:
        await update.message.reply_text("Сбор сообщений не был начат / Message collection was not started")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех сообщений / Handle all messages"""
    if not update.message or not update.effective_chat:
        return
    
    # Проверяем, активен ли сбор сообщений / Check if collection is active
    if 'collecting' not in context.chat_data or not context.chat_data['collecting']:
        return
    
    message = update.message
    chat = update.effective_chat
    
    # Форматирование сообщения / Message formatting
    msg_date = message.date.astimezone(DEFAULT_TZ)
    user_name = message.from_user.full_name if message.from_user else "Unknown"
    text = message.text or message.caption or "[медиа-сообщение / media message]"
    
    log_entry = (
        f"[{msg_date.strftime('%d.%m.%Y %H:%M:%S')}] {user_name}:\n"
        f"{text}\n\n"
    )
    
    # Запись в файл / Write to file
    try:
        with open(context.chat_data['month_file'], 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        logger.error(f"Ошибка записи в файл / File write error: {e}")

def main():
    """Запуск бота / Start the bot"""
    # Создаем папку для результатов / Create output folder
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    try:
        # Получаем токен бота / Get bot token
        token = get_bot_token()
        
        # Создаем приложение / Create application
        application = Application.builder().token(token).build()
        
        # Регистрируем обработчики / Register handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("collect", collect_messages))
        application.add_handler(CommandHandler("stop", stop_collecting))
        application.add_handler(MessageHandler(filters.ALL, handle_message))
        
        # Запускаем бота / Start the bot
        print("Бот запущен / Bot is running...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Ошибка в работе бота / Bot error: {e}")
    finally:
        print("Работа бота завершена / Bot stopped")

if __name__ == '__main__':
    main()