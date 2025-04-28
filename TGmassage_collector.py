# Импорт необходимых библиотек / Import required libraries
import asyncio  # Для асинхронного программирования / For asynchronous programming
from telethon.sync import TelegramClient  # Клиент Telegram API / Telegram API client
from telethon.tl.functions.messages import GetHistoryRequest  # Для получения истории сообщений / For getting message history
from telethon.errors import SessionPasswordNeededError  # Ошибка двухфакторной аутентификации / 2FA error
from datetime import datetime  # Для работы с датами и временем / For date and time handling
import pytz  # Для работы с часовыми поясами / For timezone handling
import configparser  # Для чтения конфигурационных файлов / For reading config files

# Настройки временной зоны / Timezone settings
# Временная зона по умолчанию (можно изменить) / Default timezone (can be changed):
# Примеры популярных зон: / Examples of popular timezones:
# Europe/Moscow (Москва), Europe/Kyiv (Киев), Asia/Tbilisi (Тбилиси) / (Moscow, Kyiv, Tbilisi)
# Asia/Dubai (Дубай), Asia/Tokyo (Токио), Europe/London (Лондон) / (Dubai, Tokyo, London)
# America/New_York (Нью-Йорк), Asia/Shanghai (Шанхай) / (New York, Shanghai)
DEFAULT_TZ = pytz.timezone('Europe/Moscow')

# Словарь русских названий месяцев / Dictionary of Russian month names
RUS_MONTHS = {
    1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
    5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
    9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
}

def input_current_month_time(prefix):
    """
    Ввод дня и времени для текущего месяца / 
    Input day and time for current month
    """
    now = datetime.now(DEFAULT_TZ)
    print(f"\n=== {prefix} дата (текущий месяц {RUS_MONTHS[now.month]} {now.year}) ===")
    print(f"=== {prefix} date (current month {RUS_MONTHS[now.month]} {now.year}) ===")
    
    while True:
        try:
            # Ввод дня / Input day
            day = int(input(f"День (1-31, Enter - {now.day}): ") or now.day)
            # Ввод часа / Input hour
            hour = int(input("Час (0-23, Enter - 00): ") or 0)
            # Ввод минут / Input minutes
            minute = int(input("Минуты (0-59, Enter - 00): ") or 0)

            # Создание объекта datetime с учетом временной зоны / Create datetime object with timezone
            dt = DEFAULT_TZ.localize(datetime(
                year=now.year,
                month=now.month,
                day=day,
                hour=hour,
                minute=minute
            ))

            # Проверка что дата не в будущем / Check date is not in the future
            if dt > datetime.now(DEFAULT_TZ):
                print("⚠️ Дата не может быть в будущем! / Date cannot be in the future!")
                continue

            return dt
        except ValueError as e:
            print(f"❌ Ошибка: {e} / Error: {e}")

def input_full_datetime(prefix):
    """
    Ввод полной даты (год, месяц, день, время) / 
    Input full date (year, month, day, time)
    """
    print(f"\n=== {prefix} дата ===")
    print(f"=== {prefix} date ===")
    
    while True:
        try:
            # Ввод года / Input year
            year = int(input("Год (например, 2024): / Year (e.g. 2024): "))
            # Ввод месяца / Input month
            month = int(input("Месяц (1-12): / Month (1-12): "))
            # Ввод дня / Input day
            day = int(input("День (1-31): / Day (1-31): "))
            # Ввод часа / Input hour
            hour = int(input("Час (0-23, Enter - 00): / Hour (0-23, Enter - 00): ") or 0)
            # Ввод минут / Input minutes
            minute = int(input("Минуты (0-59, Enter - 00): / Minutes (0-59, Enter - 00): ") or 0)

            # Создание объекта datetime с учетом временной зоны / Create datetime object with timezone
            dt = DEFAULT_TZ.localize(datetime(
                year=year,
                month=month,
                day=day,
                hour=hour,
                minute=minute
            ))

            # Проверка что дата не в будущем / Check date is not in the future
            if dt > datetime.now(DEFAULT_TZ):
                print("⚠️ Дата не может быть в будущем! / Date cannot be in the future!")
                continue

            return dt
        except ValueError as e:
            print(f"❌ Ошибка: {e} / Error: {e}")

async def main():
    """Основная функция / Main function"""
    # Загрузка конфигурации из файла / Load configuration from file
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    
    # Получение учетных данных Telegram / Get Telegram credentials
    api_id = config.get('Telegram', 'api_id')
    api_hash = config.get('Telegram', 'api_hash')
    phone = config.get('Telegram', 'phone')
    
    # Инициализация клиента Telegram / Initialize Telegram client
    client = TelegramClient('session_name', api_id, api_hash)
    
    try:
        # Подключение к Telegram / Connect to Telegram
        await client.connect()
        
        # Проверка авторизации / Check authorization
        if not await client.is_user_authorized():
            # Запрос кода подтверждения / Request verification code
            await client.send_code_request(phone)
            try:
                code = input("Введите код из Telegram: / Enter code from Telegram: ")
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                # Запрос пароля двухфакторной аутентификации / Request 2FA password
                password = input("Введите пароль двухфакторной аутентификации: / Enter 2FA password: ")
                await client.sign_in(password=password)
        
        # Ввод параметров канала / Input channel parameters
        channel = input("Введите @username или ID канала: / Enter @username or channel ID: ").strip()
        filename = f"report_{datetime.now(DEFAULT_TZ).strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        print(f"\n📁 Сообщения будут сохранены в файл: {filename}")
        print(f"📁 Messages will be saved to file: {filename}")

        # Выбор временного диапазона / Select time range
        now = datetime.now(DEFAULT_TZ)
        current_month = f"{RUS_MONTHS[now.month]} {now.year}"
        use_current = input(
            f"\nСобираем за {current_month}? (Enter - да / любой символ - нет): "
            f"\nCollect for {current_month}? (Enter - yes / any key - no): ")

        if not use_current.strip():
            # Режим текущего месяца / Current month mode
            start_date = input_current_month_time("Начальная / Start")
            end_input = input(
                "\nИспользовать текущее время для конечной даты? (Enter - да / любой символ - нет): "
                "\nUse current time for end date? (Enter - yes / any key - no): ")
            end_date = datetime.now(DEFAULT_TZ) if not end_input.strip() else input_current_month_time("Конечная / End")
        else:
            # Произвольный период / Custom period
            start_date = input_full_datetime("Начальная / Start")
            end_date = input_full_datetime("Конечная / End")

        # Проверка корректности диапазона дат / Check date range validity
        if start_date > end_date:
            print("❌ Начальная дата позже конечной! / ❌ Start date is after end date!")
            return

        # Конвертация дат в UTC / Convert dates to UTC
        start_utc = start_date.astimezone(pytz.utc)
        end_utc = end_date.astimezone(pytz.utc)

        # Вывод информации о диапазоне / Print range info
        print(f"\n⏳ Собираем сообщения с {start_date.strftime('%d.%m.%Y %H:%M')}")
        print(f"⏳ Collecting messages from {start_date.strftime('%d.%m.%Y %H:%M')}")
        print(f"                  по {end_date.strftime('%d.%m.%Y %H:%M')} ({DEFAULT_TZ.zone})")
        print(f"                  to {end_date.strftime('%d.%m.%Y %H:%M')} ({DEFAULT_TZ.zone})")

        # Получение сущности канала / Get channel entity
        entity = await client.get_entity(channel)
        print(f"\n⏳ Подключаемся к каналу: {entity.title}")
        print(f"⏳ Connecting to channel: {entity.title}")

        # Сбор сообщений / Collect messages
        all_messages = []
        offset_id = 0
        total = 0

        while True:
            # Запрос истории сообщений / Request message history
            history = await client(GetHistoryRequest(
                peer=entity,
                offset_id=offset_id,
                limit=100,  # Количество сообщений за один запрос / Number of messages per request
                offset_date=None,
                add_offset=0,
                max_id=0,
                min_id=0,
                hash=0
            ))

            # Если сообщений больше нет / If no more messages
            if not history.messages:
                break

            messages = history.messages
            for msg in messages:
                # Проверка попадания в диапазон / Check if within range
                if start_utc <= msg.date <= end_utc:
                    local_time = msg.date.astimezone(DEFAULT_TZ)
                    all_messages.append({
                        'datetime': local_time,  # Для сортировки / For sorting
                        'date': local_time.strftime("%d.%m.%Y %H:%M:%S"),  # Для вывода / For display
                        'text': msg.message
                    })
                    total += 1
                elif msg.date < start_utc:
                    break  # Прекращаем если вышли за нижнюю границу / Stop if below start date

            offset_id = messages[-1].id  # Смещение для следующего запроса / Offset for next request
            print(f"🔄 Обработано {total} сообщений / Processed {total} messages", end='\r')

            if messages[-1].date < start_utc:
                break  # Прекращаем если все сообщения старее начальной даты / Stop if all messages are older

        # Сортировка сообщений по дате / Sort messages by date
        all_messages.sort(key=lambda x: x['datetime'])

        # Сохранение в файл / Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            for msg in all_messages:
                f.write(f"[{msg['date']}]\n{msg['text']}\n\n")

        print(f"\n✅ Готово! Сохранено {total} сообщений в файл {filename}")
        print(f"✅ Done! Saved {total} messages to file {filename}")

    except Exception as e:
        print(f"❌ Критическая ошибка: {str(e)}")
        print(f"❌ Critical error: {str(e)}")
    finally:
        # Закрытие соединения / Close connection
        await client.disconnect()
        print("Соединение закрыто / Connection closed")

if __name__ == '__main__':
    # Запуск асинхронной функции / Run async function
    asyncio.run(main())