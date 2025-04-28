# Импорт необходимых библиотек
import os
import asyncio
import configparser
from datetime import datetime
import pytz
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import PeerChannel

# Настройки
DEFAULT_TZ = pytz.timezone('Europe/Moscow')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'config.ini')
SESSION_FILE = os.path.join(SCRIPT_DIR, 'session_name.session')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'Collected_messages')

# Словарь русских названий месяцев
RUS_MONTHS = {
    1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
    5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
    9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
}

def load_config():
    """Загрузка и валидация конфигурации"""
    config = configparser.ConfigParser()
    
    # Проверка существования файла
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Конфигурационный файл не найден: {CONFIG_PATH}")
    
    try:
        # Чтение файла с указанием кодировки
        config.read(CONFIG_PATH, encoding='utf-8')
    except Exception as e:
        raise ValueError(f"Ошибка чтения config.ini: {str(e)}")
    
    # Проверка наличия секции Telegram
    if not config.has_section('Telegram'):
        raise ValueError("В config.ini отсутствует секция [Telegram]")
    
    # Проверка обязательных параметров
    required_keys = ['api_id', 'api_hash', 'phone']
    for key in required_keys:
        if not config.has_option('Telegram', key):
            raise ValueError(f"В секции [Telegram] отсутствует параметр: {key}")
    
    return config

def input_current_month_time(prefix):
    """Ввод даты и времени для текущего месяца"""
    now = datetime.now(DEFAULT_TZ)
    print(f"\n=== {prefix} дата (текущий месяц {RUS_MONTHS[now.month]} {now.year}) ===")
    
    while True:
        try:
            day = int(input(f"День (1-31, Enter - {now.day}): ") or now.day)
            hour = int(input("Час (0-23, Enter - 00): ") or 0)
            minute = int(input("Минуты (0-59, Enter - 00): ") or 0)

            dt = DEFAULT_TZ.localize(datetime(
                year=now.year,
                month=now.month,
                day=day,
                hour=hour,
                minute=minute
            ))

            if dt > datetime.now(DEFAULT_TZ):
                print("⚠️ Дата не может быть в будущем!")
                continue

            return dt
        except ValueError as e:
            print(f"❌ Ошибка: {e}")

async def get_chat_entity(client, chat_input):
    """Получение сущности чата с обработкой разных форматов"""
    try:
        if chat_input.startswith('-100'):
            return await client.get_entity(PeerChannel(int(chat_input[4:])))
        elif chat_input.startswith('https://t.me/joinchat/'):
            return await client.get_entity(chat_input)
        return await client.get_entity(chat_input)
    except Exception as e:
        print(f"\n❌ Ошибка подключения к чату: {e}")
        print("Доступные форматы:")
        print("- ID группы (начинается с -100, например -1001234567890)")
        print("- invite-ссылку (например https://t.me/joinchat/ABCDEF12345)")
        print("- @username (для публичных групп)")
        raise

async def main():
    print("=== Telegram Message Collector ===")
    print(f"Рабочая директория: {SCRIPT_DIR}")
    
    try:
        # Создаем папку для сохранения результатов
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        print(f"Создана папка для результатов: {OUTPUT_DIR}")

        # Загрузка конфигурации
        config = load_config()
        api_id = config.get('Telegram', 'api_id')
        api_hash = config.get('Telegram', 'api_hash')
        phone = config.get('Telegram', 'phone')
        
        # Инициализация клиента
        client = TelegramClient(SESSION_FILE, api_id, api_hash)
        
        # Подключение
        await client.connect()
        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            try:
                code = input("Введите код из Telegram: ")
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("Введите пароль двухфакторной аутентификации: ")
                await client.sign_in(password=password)
        
        # Ввод параметров чата
        chat_input = input("\nВведите ID группы (-100...), invite-ссылку или @username: ").strip()
        entity = await get_chat_entity(client, chat_input)
        
        print(f"\nУспешно подключено к: {entity.title}")
        
        # Ввод временного диапазона
        now = datetime.now(DEFAULT_TZ)
        current_month = f"{RUS_MONTHS[now.month]} {now.year}"
        
        if input(f"\nСобираем за {current_month}? (Enter - да, любой символ - нет): ").strip() == '':
            start_date = input_current_month_time("Начальная")
            end_date = datetime.now(DEFAULT_TZ) if input("\nИспользовать текущее время? (Enter - да, любой символ - нет): ").strip() == '' else input_current_month_time("Конечная")
        else:
            print("\nВведите начальную дату:")
            start_date = input_current_month_time("Начальная")
            print("\nВведите конечную дату:")
            end_date = input_current_month_time("Конечная")
        
        # Обработка сообщений
        all_messages = []
        offset_id = 0
        total = 0
        
        print(f"\n⏳ Собираем сообщения с {start_date.strftime('%d.%m.%Y %H:%M')} по {end_date.strftime('%d.%m.%Y %H:%M')}")
        
        while True:
            history = await client(GetHistoryRequest(
                peer=entity,
                offset_id=offset_id,
                limit=100,
                offset_date=None,
                add_offset=0,
                max_id=0,
                min_id=0,
                hash=0
            ))
            
            if not history.messages:
                break
                
            for msg in history.messages:
                msg_date = msg.date.astimezone(DEFAULT_TZ)
                if start_date <= msg_date <= end_date:
                    all_messages.append({
                        'date': msg_date.strftime("%d.%m.%Y %H:%M:%S"),
                        'text': msg.message
                    })
                    total += 1
                elif msg_date < start_date:
                    break
            
            offset_id = history.messages[-1].id
            print(f"Обработано сообщений: {total}", end='\r')
            
            if history.messages[-1].date.astimezone(DEFAULT_TZ) < start_date:
                break
        
        # Сохранение в файл
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = os.path.join(OUTPUT_DIR, f"messages_{timestamp}.txt")
        
        with open(filename, 'w', encoding='utf-8') as f:
            for msg in sorted(all_messages, key=lambda x: x['date']):
                f.write(f"[{msg['date']}]\n{msg['text']}\n\n")
        
        print(f"\n✅ Готово! Сохранено {total} сообщений в файл:")
        print(f"📂 {filename}")

    except Exception as e:
        print(f"\n❌ Ошибка: {str(e)}")
    finally:
        if 'client' in locals():
            await client.disconnect()
        print("Работа завершена.")

if __name__ == '__main__':
    asyncio.run(main())