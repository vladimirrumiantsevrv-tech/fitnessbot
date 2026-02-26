"""
Бот на pyTelegramBotAPI - МАКСИМАЛЬНАЯ ОТЛАДКА
"""
import os
import sys
import time
import traceback

print("=" * 50)
print("🚀 ЗАПУСК БОТА - НАЧАЛО")
print("=" * 50)
print(f"🐍 Python версия: {sys.version}")
print(f"📂 Текущая директория: {os.getcwd()}")
print(f"📋 Содержимое директории: {os.listdir('.')}")

# Проверяем переменные окружения
print("\n🔍 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ:")
TOKEN = os.environ.get('BOT_TOKEN')
DATABASE_URL = os.environ.get('DATABASE_URL')

print(f"BOT_TOKEN: {'✅ НАЙДЕН' if TOKEN else '❌ НЕ НАЙДЕН'}")
print(f"DATABASE_URL: {'✅ НАЙДЕН' if DATABASE_URL else '❌ НЕ НАЙДЕН'}")

if DATABASE_URL:
    # Маскируем пароль для безопасности
    masked_url = DATABASE_URL.replace(DATABASE_URL.split(':')[2].split('@')[0], '****')
    print(f"DATABASE_URL (скрыт): {masked_url}")

if not TOKEN:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: BOT_TOKEN не найден!")
    sys.exit(1)

# Импортируем библиотеки
print("\n📚 ИМПОРТ БИБЛИОТЕК:")
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    print("✅ psycopg2 импортирован")
except Exception as e:
    print(f"❌ Ошибка импорта psycopg2: {e}")
    traceback.print_exc()

try:
    import telebot
    from telebot import types
    print("✅ telebot импортирован")
except Exception as e:
    print(f"❌ Ошибка импорта telebot: {e}")
    traceback.print_exc()

# Проверка подключения к БД
print("\n🔄 ПРОВЕРКА ПОДКЛЮЧЕНИЯ К БД:")
try:
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Проверяем существование таблицы
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'exercises'
            );
        """)
        table_exists = cursor.fetchone()['exists']
        print(f"📊 Таблица 'exercises' существует: {table_exists}")
        
        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM exercises")
            count = cursor.fetchone()['count']
            print(f"📊 Количество записей в exercises: {count}")
        
        conn.close()
        print("✅ Подключение к БД успешно")
    else:
        print("⚠️ DATABASE_URL не указан, пропускаем проверку БД")
except Exception as e:
    print(f"❌ Ошибка подключения к БД: {e}")
    traceback.print_exc()

# Создание бота
print("\n🤖 СОЗДАНИЕ БОТА:")
try:
    bot = telebot.TeleBot(TOKEN)
    print("✅ Экземпляр бота создан")
except Exception as e:
    print(f"❌ Ошибка создания бота: {e}")
    traceback.print_exc()
    sys.exit(1)

# Проверка работы бота
print("\n📡 ПРОВЕРКА СВЯЗИ С TELEGRAM:")
try:
    me = bot.get_me()
    print(f"✅ Бот @{me.username} (ID: {me.id}) успешно подключен")
except Exception as e:
    print(f"❌ Ошибка подключения к Telegram: {e}")
    traceback.print_exc()

# Простейший обработчик
@bot.message_handler(commands=['start'])
def start_command(message):
    print(f"📨 Получена команда /start от {message.from_user.id}")
    try:
        bot.send_message(
            message.chat.id,
            f"👋 Привет, {message.from_user.first_name}!\n\nБот работает и подключен к БД!"
        )
        print("✅ Сообщение отправлено")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

@bot.message_handler(commands=['test'])
def test_command(message):
    print(f"📨 Получена команда /test")
    try:
        if DATABASE_URL:
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM exercises")
            count = cursor.fetchone()['count']
            conn.close()
            bot.send_message(message.chat.id, f"✅ В базе {count} упражнений")
        else:
            bot.send_message(message.chat.id, "❌ База не подключена")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)[:100]}")

print("\n" + "=" * 50)
print("🚀 ЗАПУСК ПОЛЛИНГА")
print("=" * 50)

if __name__ == "__main__":
    while True:
        try:
            print("🔄 Удаление вебхука...")
            bot.remove_webhook()
            time.sleep(1)
            
            print("🔄 Запуск polling...")
            bot.polling(
                none_stop=True,
                interval=0,
                timeout=20,
                skip_pending=True
            )
        except Exception as e:
            print(f"❌ Ошибка polling: {e}")
            traceback.print_exc()
            print("🔄 Перезапуск через 5 секунд...")
            time.sleep(5)