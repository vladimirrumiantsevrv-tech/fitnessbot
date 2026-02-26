"""
Бот на pyTelegramBotAPI - с PostgreSQL на Railway
"""
import os
import time
import psycopg2  # вместо sqlite3
from psycopg2.extras import RealDictCursor
import telebot
from telebot import types

# Токен из переменных окружения
TOKEN = os.environ.get('BOT_TOKEN')
DATABASE_URL = os.environ.get('DATABASE_URL')  # Railway автоматически добавляет эту переменную

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в переменных окружения!")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL не найден! Добавьте PostgreSQL в проект Railway")

# Функция для работы с PostgreSQL
def get_db_connection():
    """Подключение к PostgreSQL"""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def get_groups():
    """Получить все группы мышц из PostgreSQL"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT muscle_group FROM exercises ORDER BY muscle_group')
    groups = [row['muscle_group'] for row in cursor.fetchall()]
    conn.close()
    return groups

def get_exercises_by_group(group):
    """Получить упражнения по группе из PostgreSQL"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, exercise_name FROM exercises WHERE muscle_group = %s ORDER BY exercise_name', (group,))
    exercises = cursor.fetchall()
    conn.close()
    return exercises

def get_exercise_by_id(exercise_id):
    """Получить детали упражнения по ID из PostgreSQL"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT exercise_name, description, youtube_link, equipment_needed, muscle_group, image_url 
        FROM exercises WHERE id = %s
    ''', (exercise_id,))
    exercise = cursor.fetchone()
    conn.close()
    return exercise

# Функция для инициализации таблиц (если их нет)
def init_database():
    """Создает таблицы при первом запуске"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercises (
            id SERIAL PRIMARY KEY,
            muscle_group TEXT NOT NULL,
            exercise_name TEXT NOT NULL,
            description TEXT,
            youtube_link TEXT,
            equipment_needed TEXT,
            image_url TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Таблицы в PostgreSQL проверены/созданы")

# Создаем бота
bot = telebot.TeleBot(TOKEN)

# Инициализируем базу данных при старте
init_database()

# ... ВЕСЬ ОСТАЛЬНОЙ КОД БЕЗ ИЗМЕНЕНИЙ ...
# (обработчики команд и кнопок остаются точно такими же)

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 БОТ ЗАПУСКАЕТСЯ НА RAILWAY С POSTGRESQL")
    print("=" * 50)
    
    # Проверяем подключение к БД
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM exercises')
        count = cursor.fetchone()['count']
        conn.close()
        print(f"📊 PostgreSQL: {count} упражнений в базе")
    except Exception as e:
        print(f"❌ Ошибка подключения к PostgreSQL: {e}")
    
    try:
        bot_info = bot.get_me()
        print(f"🤖 Бот: @{bot_info.username}")
    except:
        print("🤖 Бот: (не удалось получить имя)")
    
    print("✅ Бот готов к работе!")
    print("=" * 50)
    
    while True:
        try:
            bot.remove_webhook()
            time.sleep(1)
            bot.polling(
                none_stop=True,
                interval=0,
                timeout=20,
                skip_pending=True
            )
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print("🔄 Перезапуск через 5 секунд...")
            time.sleep(5)