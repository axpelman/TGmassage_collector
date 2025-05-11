import os
import logging
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ========== НАСТРОЙКИ ==========
DEFAULT_TZ = pytz.timezone('Europe/Moscow')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'Collected_messages')
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'bot_token.txt')
LOG_FILE = os.path.join(SCRIPT_DIR, 'bot.log')
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 МБ в байтах

# Словарь русских месяцев
RUS_MONTHS = {
    1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
    5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
    9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
}

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
def setup_logging():
    """Настройка системы логирования с автоматической очисткой"""
    try:
        # Проверяем размер файла и очищаем при необходимости
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.write(f"=== Лог-файл очищен {datetime.now(DEFAULT_TZ)} ===\n\n")
        
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE, encoding='utf-8', mode='a'),
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger(__name__)
        logger.info(f"Логирование настроено. Макс. размер лога: {MAX_LOG_SIZE//1024//1024} МБ")
        return logger
    except Exception as e:
        print(f"ОШИБКА НАСТРОЙКИ ЛОГИРОВАНИЯ: {e}")
        raise

logger = setup_logging()

# ========== ОСНОВНЫЕ ФУНКЦИИ ==========
def get_bot_token():
    """Получение токена бота из файла"""
    try:
        if not os.path.exists(TOKEN_FILE):
            raise FileNotFoundError(f"Файл с токеном не найден: {TOKEN_FILE}")
        
        with open(TOKEN_FILE, 'r') as f:
            token = f.read().strip()
        
        if not token:
            raise ValueError("Токен бота не может быть пустым")
        
        return token
    except Exception as e:
        logger.error(f"Ошибка получения токена: {e}")
        raise

def get_daily_filename(chat_id: int, date: datetime) -> str:
    """Генерация имени файла для дневного сбора"""
    chat_dir = os.path.join(OUTPUT_DIR, str(chat_id))
    os.makedirs(chat_dir, exist_ok=True)
    return os.path.join(chat_dir, f"{date.year}-{RUS_MONTHS[date.month]}-{date.day}.txt")

# ========== ОБРАБОТЧИКИ КОМАНД ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
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
    logger.info(f"Пользователь {user.id} запустил бота")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "Помощь по использованию бота:\n\n"
        "1. Добавьте бота в чат\n"
        "2. Дайте боту права администратора\n"
        "3. Отправьте /collect в чате\n"
        "4. Отправьте /stop для остановки\n\n"
        "Сообщения сохраняются в файлы по дням."
    )
    await update.message.reply_text(help_text)

async def collect_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало сбора сообщений"""
    if not update.message or not update.effective_chat:
        await update.message.reply_text("Эта команда работает только в чатах!")
        return

    chat = update.effective_chat
    chat_title = chat.title or "ЛС"
    chat_id = chat.id
    now = datetime.now(DEFAULT_TZ)

    try:
        filepath = get_daily_filename(chat_id, now)
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(f"=== Начало сбора {now.strftime('%d.%m.%Y %H:%M')} ===\n\n")
        
        context.chat_data['collecting'] = True
        context.chat_data['current_file'] = filepath
        
        await update.message.reply_text(
            f"✅ Сбор сообщений начат в чате '{chat_title}'\n"
            f"📁 Файл: {filepath}"
        )
        logger.info(f"Сбор активирован для чата {chat_id}. Файл: {filepath}")
    except Exception as e:
        error_msg = f"❌ Ошибка начала сбора: {e}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех сообщений"""
    if not update.message or not update.effective_chat:
        return

    if 'collecting' not in context.chat_data or not context.chat_data['collecting']:
        return

    message = update.message
    user = message.from_user
    msg_date = message.date.astimezone(DEFAULT_TZ)
    text = message.text or message.caption or "[медиа]"

    log_entry = (
        f"[{msg_date.strftime('%d.%m.%Y %H:%M:%S')}] "
        f"{user.full_name if user else 'Аноним'}:\n"
        f"{text}\n\n"
    )

    try:
        with open(context.chat_data['current_file'], 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        logger.error(f"Ошибка записи сообщения: {e}")

async def stop_collecting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Остановка сбора сообщений"""
    if 'collecting' in context.chat_data and context.chat_data['collecting']:
        context.chat_data['collecting'] = False
        await update.message.reply_text("❌ Сбор сообщений остановлен")
        logger.info("Сбор сообщений остановлен")
    else:
        await update.message.reply_text("ℹ️ Сбор не был активирован")

# ========== ЗАПУСК БОТА ==========
def main():
    """Основная функция запуска бота"""
    try:
        # Проверка и создание необходимых папок
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        logger.info(f"Папка для сообщений: {OUTPUT_DIR}")

        # Получение токена
        token = get_bot_token()
        
        # Создание и настройка бота
        application = Application.builder().token(token).build()
        
        # Регистрация обработчиков
        handlers = [
            CommandHandler("start", start),
            CommandHandler("help", help_command),
            CommandHandler("collect", collect_messages),
            CommandHandler("stop", stop_collecting),
            MessageHandler(filters.ALL, handle_message)
        ]
        
        for handler in handlers:
            application.add_handler(handler)

        logger.info("Бот запускается...")
        print(f"Бот запущен! Логи: {LOG_FILE} (макс. {MAX_LOG_SIZE//1024//1024} МБ)")
        application.run_polling()

    except Exception as e:
        logger.critical(f"ФАТАЛЬНАЯ ОШИБКА: {e}", exc_info=True)
    finally:
        logger.info("Бот остановлен")

if __name__ == '__main__':
    main()