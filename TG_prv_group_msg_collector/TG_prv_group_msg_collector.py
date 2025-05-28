import os
import logging
import glob
import time
from datetime import datetime, time as dt_time, timedelta
import pytz
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext,
)

# ========== НАСТРОЙКИ ==========
DEFAULT_TZ = pytz.timezone('Europe/Moscow')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'Collected_messages')
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'bot_token.txt')
LOG_FILE = os.path.join(SCRIPT_DIR, 'bot.log')
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 МБ
LOG_CHECK_INTERVAL = 3600  # Проверка каждые 3600 секунд (1 час)
LOG_RETENTION_DAYS = 7  # Хранить логи 7 дней
MESSAGE_RETENTION_DAYS = 7  # Хранить сообщения 7 дней
DELETE_AFTER_SECONDS = 10  # Удалять сообщения через 10 секунд
ADMIN_USER_ID = 813325749  # Замените на ваш ID в Telegram для получения файлов
MAX_FILE_SIZE = 100 * 1024  # 100 КБ максимальный размер файла

# Настройки Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r'........\TG_prv_group_msg_collector\tesseract-ocr\tesseract.exe'

# Словарь русских месяцев
RUS_MONTHS = {
    1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
    5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
    9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
}

# ========== УЛУЧШЕННОЕ РАСПОЗНАВАНИЕ ТЕКСТА ==========
async def preprocess_image(image):
    """Улучшение качества изображения для OCR"""
    try:
        image = image.convert('L')
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2)
        image = image.filter(ImageFilter.MedianFilter(size=3))
        image = image.point(lambda x: 0 if x < 128 else 255)
        return image
    except Exception as e:
        logging.error(f"Ошибка обработки изображения: {e}")
        return image

async def extract_text_from_image(image_bytes):
    """Извлечение текста с изображения"""
    try:
        image = Image.open(BytesIO(image_bytes))
        image = await preprocess_image(image)
        custom_config = r'--oem 3 --psm 6 -l eng+rus'
        text = pytesseract.image_to_string(image, config=custom_config)
        text = text.strip()
        if not text:
            return None
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)
    except Exception as e:
        logging.error(f"Ошибка OCR: {e}")
        return None

# ========== УДАЛЕНИЕ СООБЩЕНИЙ ==========
async def delete_message(context: CallbackContext):
    """Удаление сообщения"""
    try:
        await context.bot.delete_message(
            chat_id=context.job.chat_id,
            message_id=context.job.data
        )
    except Exception as e:
        logging.error(f"Ошибка удаления сообщения: {e}")

async def schedule_message_deletion(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    """Запланировать удаление сообщения"""
    context.job_queue.run_once(
        delete_message,
        DELETE_AFTER_SECONDS,
        chat_id=chat_id,
        data=message_id
    )

# ========== ОБРАБОТКА СООБЩЕНИЙ ==========
async def process_message_content(update: Update):
    """Определение и обработка содержимого сообщения"""
    message = update.message
    if not message:
        return "[пустое сообщение]"
    
    if message.text:
        return message.text
    
    if message.photo:
        try:
            photo_file = await message.photo[-1].get_file()
            image_bytes = await photo_file.download_as_bytearray()
            extracted_text = await extract_text_from_image(image_bytes)
            caption = message.caption or ""
            if extracted_text:
                return f"{caption}\n{extracted_text}" if caption else extracted_text
            return caption if caption else "[изображение без текста]"
        except Exception as e:
            logging.error(f"Ошибка обработки изображения: {e}")
            return "[ошибка распознавания изображения]"
    
    if message.caption:
        return message.caption
    
    return "[медиа-сообщение]"

def get_next_filename(base_path: str, extension: str = "txt") -> str:
    """Получить следующее имя файла с номером, если файл слишком большой"""
    counter = 1
    while True:
        if counter == 1:
            filename = f"{base_path}.{extension}"
        else:
            filename = f"{base_path}-{counter}.{extension}"
        
        # Если файл не существует или его размер меньше максимального, возвращаем его
        if not os.path.exists(filename) or os.path.getsize(filename) < MAX_FILE_SIZE:
            return filename
        
        counter += 1

def get_daily_filename(chat_id: int, date: datetime) -> str:
    """Генерация имени файла для дневного сбора с учетом размера"""
    chat_dir = os.path.join(OUTPUT_DIR, str(chat_id))
    os.makedirs(chat_dir, exist_ok=True)
    
    base_name = os.path.join(chat_dir, f"{date.year}-{RUS_MONTHS[date.month]}-{date.day}")
    return get_next_filename(base_name)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех входящих сообщений"""
    if not update.message or not update.effective_chat:
        return

    if 'collecting' not in context.chat_data or not context.chat_data['collecting']:
        return

    user = update.message.from_user
    msg_date = update.message.date.astimezone(DEFAULT_TZ)
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "ЛС"
    content = await process_message_content(update)
    
    forward_info = ""
    original_date_info = ""
    if update.message.forward_origin:
        origin = update.message.forward_origin
        # Добавляем информацию о дате оригинального сообщения
        if hasattr(origin, 'date'):
            original_date = origin.date.astimezone(DEFAULT_TZ)
            original_date_info = f" | Оригинальное сообщение: {original_date.strftime('%d.%m.%Y %H:%M')}"
        
        if origin.type == "user":
            forward_info = f" (переслано от: {origin.sender_user.full_name}, ID: {origin.sender_user.id}{original_date_info})"
        elif origin.type == "chat":
            forward_info = f" (переслано из чата: {origin.sender_chat.title}, ID: {origin.sender_chat.id}{original_date_info})"
        elif origin.type == "channel":
            forward_info = f" (переслано из канала: {origin.sender_chat.title}, ID: {origin.sender_chat.id}{original_date_info})"
        elif origin.type == "hidden_user":
            forward_info = f" (переслано от: {origin.sender_user_name}{original_date_info})"
    
    user_name = user.full_name if user else "Аноним"
    timestamp = msg_date.strftime('%d.%m.%Y %H:%M')
    
    log_entry = (
        f"{chat_title} | {user_name}{forward_info}, [{timestamp}]\n"
        f"{content}\n\n"
    )

    now = datetime.now(DEFAULT_TZ)
    filepath = get_daily_filename(chat_id, now)
    context.chat_data['current_file'] = filepath

    try:
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        logging.error(f"Ошибка записи сообщения: {e}")

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def setup_logging():
    """Настройка системы логирования"""
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE, encoding='utf-8', mode='a'),
                logging.StreamHandler()
            ]
        )
        logging.info(f"Логирование настроено. Макс. размер: {MAX_LOG_SIZE//1024//1024} МБ")
    except Exception as e:
        print(f"ОШИБКА НАСТРОЙКИ ЛОГИРОВАНИЯ: {e}")
        raise

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
        logging.error(f"Ошибка получения токена: {e}")
        raise

# ========== ОТПРАВКА ОТЧЕТА ==========
async def send_daily_report(context: CallbackContext):
    """Отправка ежедневного отчета за текущий день"""
    if not ADMIN_USER_ID:
        logging.warning("ADMIN_USER_ID не установлен, отправка отчета невозможна")
        return
    
    now = datetime.now(DEFAULT_TZ)
    today_str = now.strftime('%d.%m.%Y')
    report_date = now.date()
    
    for chat_id_dir in os.listdir(OUTPUT_DIR):
        chat_dir = os.path.join(OUTPUT_DIR, chat_id_dir)
        if os.path.isdir(chat_dir):
            # Ищем все файлы за текущую дату (основной и дополнительные)
            base_filename = f"{report_date.year}-{RUS_MONTHS[report_date.month]}-{report_date.day}"
            files_to_send = sorted(
                [f for f in os.listdir(chat_dir) if f.startswith(base_filename)],
                key=lambda x: (
                    int(x.split('-')[-1].split('.')[0]) 
                    if x.split('-')[-1].split('.')[0].isdigit() 
                    else 0
                )
            )
            
            if files_to_send:
                for filename in files_to_send:
                    filepath = os.path.join(chat_dir, filename)
                    try:
                        with open(filepath, 'rb') as f:
                            await context.bot.send_document(
                                chat_id=ADMIN_USER_ID,
                                document=f,
                                caption=f"Отчет за {today_str} из чата {chat_id_dir} ({filename})"
                            )
                        logging.info(f"Отправлен отчет {filename} за {today_str} для чата {chat_id_dir}")
                    except Exception as e:
                        logging.error(f"Ошибка отправки отчета {filename} для чата {chat_id_dir}: {e}")

def schedule_daily_report(job_queue):
    """Запланировать ежедневную отправку отчета"""
    report_time = dt_time(23, 59, tzinfo=DEFAULT_TZ)
    
    job_queue.run_daily(
        send_daily_report,
        time=report_time,
        days=(0, 1, 2, 3, 4, 5, 6),
        name="daily_report"
    )
    logging.info(f"Ежедневная отправка отчета запланирована на {report_time.strftime('%H:%M')} по Москве")

# ========== КОМАНДЫ БОТА ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    help_text = (
        f"Привет, {user.first_name}!\n"
        "Я бот для сбора сообщений из чатов с улучшенным распознаванием текста.\n\n"
        "Доступные команды:\n"
        "/start - показать это сообщение\n"
        "/collect - начать сбор сообщений\n"
        "/stop - остановить сбор сообщений\n\n"
        "Я умею распознавать текст с изображений на русском и английском языках!\n"
        "Ежедневно в 23:59 я буду присылать файл с собранными сообщениями за текущий день."
    )
    
    await schedule_message_deletion(context, update.effective_chat.id, update.message.message_id)
    
    sent_message = await update.message.reply_text(help_text)
    await schedule_message_deletion(context, update.effective_chat.id, sent_message.message_id)
    
    logging.info(f"Пользователь {user.id} запустил бота")

async def collect_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало сбора сообщений"""
    await schedule_message_deletion(context, update.effective_chat.id, update.message.message_id)
    
    if not update.message or not update.effective_chat:
        sent_message = await update.message.reply_text("Эта команда работает только в чатах!")
        await schedule_message_deletion(context, update.effective_chat.id, sent_message.message_id)
        return

    chat = update.effective_chat
    chat_title = chat.title or "ЛС"
    chat_id = chat.id
    now = datetime.now(DEFAULT_TZ)
    today_str = now.strftime('%d.%m.%Y')

    try:
        filepath = get_daily_filename(chat_id, now)
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(f"=== Начало сбора {now.strftime('%d.%m.%Y %H:%M')} ===\n\n")
        
        context.chat_data['collecting'] = True
        context.chat_data['current_file'] = filepath
        
        sent_message = await update.message.reply_text(
            f"✅ Сбор сообщений начат в чате '{chat_title}'\n"
            f"📅 Сегодняшняя дата: {today_str}\n"
            f"📁 Сообщения сохраняются в: {os.path.basename(filepath)}\n"
            f"⏰ Отчет будет отправлен сегодня в 23:59\n"
            f"📝 Макс. размер файла: {MAX_FILE_SIZE//1024} КБ"
        )
        await schedule_message_deletion(context, update.effective_chat.id, sent_message.message_id)
        
        logging.info(f"Сбор активирован для чата {chat_id}")
    except Exception as e:
        error_msg = f"❌ Ошибка начала сбора: {e}"
        sent_message = await update.message.reply_text(error_msg)
        await schedule_message_deletion(context, update.effective_chat.id, sent_message.message_id)
        logging.error(error_msg)

async def stop_collecting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Остановка сбора сообщений"""
    await schedule_message_deletion(context, update.effective_chat.id, update.message.message_id)
    
    if 'collecting' in context.chat_data and context.chat_data['collecting']:
        context.chat_data['collecting'] = False
        sent_message = await update.message.reply_text("❌ Сбор сообщений остановлен")
        await schedule_message_deletion(context, update.effective_chat.id, sent_message.message_id)
        logging.info("Сбор сообщений остановлен")
    else:
        sent_message = await update.message.reply_text("ℹ️ Сбор не был активирован")
        await schedule_message_deletion(context, update.effective_chat.id, sent_message.message_id)

# ========== УПРАВЛЕНИЕ ЛОГАМИ И ФАЙЛАМИ ==========
def rotate_logs():
    """Ротация лог-файла при превышении размера"""
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.write(f"=== Лог-файл очищен {datetime.now(DEFAULT_TZ)} ===\n\n")
            logging.info("Лог-файл был очищен из-за превышения размера")
            return True
    except Exception as e:
        logging.error(f"Ошибка при ротации лог-файла: {e}")
    return False

def cleanup_old_logs():
    """Удаление старых лог-файлов"""
    try:
        now = time.time()
        cutoff = now - LOG_RETENTION_DAYS * 86400
        
        for logfile in glob.glob(os.path.join(SCRIPT_DIR, 'bot_*.log')):
            if os.path.getmtime(logfile) < cutoff:
                try:
                    os.unlink(logfile)
                    logging.info(f"Удален старый лог: {os.path.basename(logfile)}")
                except Exception as e:
                    logging.error(f"Ошибка удаления {logfile}: {e}")
    except Exception as e:
        logging.error(f"Ошибка очистки старых логов: {e}")

def cleanup_old_message_files():
    """Удаление старых файлов с сообщениями"""
    try:
        now = time.time()
        cutoff = now - MESSAGE_RETENTION_DAYS * 86400
        
        if not os.path.exists(OUTPUT_DIR):
            return

        for chat_id_dir in os.listdir(OUTPUT_DIR):
            chat_dir = os.path.join(OUTPUT_DIR, chat_id_dir)
            if os.path.isdir(chat_dir):
                for filename in os.listdir(chat_dir):
                    filepath = os.path.join(chat_dir, filename)
                    if os.path.isfile(filepath):
                        file_time = os.path.getmtime(filepath)
                        if file_time < cutoff:
                            try:
                                os.unlink(filepath)
                                logging.info(f"Удален старый файл сообщений: {filename}")
                            except Exception as e:
                                logging.error(f"Ошибка удаления {filename}: {e}")
                
                # Если папка пустая, удаляем её
                if not os.listdir(chat_dir):
                    try:
                        os.rmdir(chat_dir)
                        logging.info(f"Удалена пустая папка: {chat_id_dir}")
                    except Exception as e:
                        logging.error(f"Ошибка удаления пустой папки {chat_id_dir}: {e}")
    except Exception as e:
        logging.error(f"Ошибка очистки старых файлов сообщений: {e}")

async def maintenance_job(context: CallbackContext):
    """Периодическое обслуживание (логи + файлы сообщений)"""
    rotate_logs()
    cleanup_old_logs()
    cleanup_old_message_files()

# ========== ЗАПУСК БОТА ==========
def main():
    """Основная функция запуска бота"""
    try:
        setup_logging()
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        logging.info(f"Папка для сообщений: {OUTPUT_DIR}")

        token = get_bot_token()
        
        application = (
            Application.builder()
            .token(token)
            .arbitrary_callback_data(True)
            .build()
        )
        
        handlers = [
            CommandHandler("start", start),
            CommandHandler("collect", collect_messages),
            CommandHandler("stop", stop_collecting),
            MessageHandler(filters.ALL, handle_message)
        ]
        
        for handler in handlers:
            application.add_handler(handler)

        job_queue = application.job_queue
        
        job_queue.run_repeating(
            maintenance_job,
            interval=LOG_CHECK_INTERVAL,
            first=10
        )
        
        schedule_daily_report(job_queue)

        logging.info("Бот запускается...")
        print("Бот успешно запущен! Ожидайте сообщений...")
        application.run_polling()

    except Exception as e:
        logging.critical(f"ФАТАЛЬНАЯ ОШИБКА: {e}", exc_info=True)
    finally:
        logging.info("Бот остановлен")

if __name__ == '__main__':
    main()