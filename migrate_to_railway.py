"""
Скрипт для переноса данных из локальной SQLite в PostgreSQL на Railway
"""
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

# ===== НАСТРОЙКИ =====
# Путь к локальной SQLite базе
SQLITE_DB_PATH = 'fitness_bot.db'

# URL новой PostgreSQL базы на Railway (возьмите из дашборда)
# ⚠️ ЗАМЕНИТЕ НА ВАШ РЕАЛЬНЫЙ URL
POSTGRES_URL = "postgresql://postgres:jdSaIdDhNvodoNbCZYXREKyLNuUrBtaI@maglev.proxy.rlwy.net:22220/railway"

# ===== ПОДКЛЮЧЕНИЕ К SQLITE =====
print("=" * 50)
print("🚀 ПЕРЕНОС ДАННЫХ ИЗ SQLITE В POSTGRESQL")
print("=" * 50)

print(f"\n📂 Подключение к SQLite: {SQLITE_DB_PATH}")
sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
sqlite_conn.row_factory = sqlite3.Row
sqlite_cursor = sqlite_conn.cursor()

# Получаем список таблиц в SQLite
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = sqlite_cursor.fetchall()
print(f"📊 Найдено таблиц в SQLite: {len(tables)}")

# ===== ПОДКЛЮЧЕНИЕ К POSTGRESQL =====
print(f"\n🔄 Подключение к PostgreSQL...")
try:
    pg_conn = psycopg2.connect(POSTGRES_URL, cursor_factory=RealDictCursor)
    pg_cursor = pg_conn.cursor()
    print("✅ Подключение успешно!")
except Exception as e:
    print(f"❌ Ошибка подключения к PostgreSQL: {e}")
    exit(1)

# ===== ПЕРЕНОС ТАБЛИЦЫ EXERCISES =====
print("\n📦 Перенос данных из таблицы 'exercises'...")

# Проверяем, есть ли таблица в SQLite
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='exercises'")
if not sqlite_cursor.fetchone():
    print("❌ Таблица 'exercises' не найдена в SQLite!")
    exit(1)

# Получаем структуру таблицы из SQLite
sqlite_cursor.execute("PRAGMA table_info(exercises)")
columns = sqlite_cursor.fetchall()
column_names = [col['name'] for col in columns]
print(f"📋 Колонки: {', '.join(column_names)}")

# Читаем данные из SQLite
sqlite_cursor.execute("SELECT * FROM exercises")
rows = sqlite_cursor.fetchall()
print(f"📊 Найдено записей в SQLite: {len(rows)}")

if rows:
    # Создаем таблицу в PostgreSQL (если её нет)
    print("\n🔄 Создание таблицы в PostgreSQL...")
    pg_cursor.execute('''
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
    
    # Очищаем таблицу в PostgreSQL
    pg_cursor.execute("TRUNCATE TABLE exercises RESTART IDENTITY CASCADE;")
    print("🧹 Таблица очищена")
    
    # Вставляем данные
    print("🔄 Перенос данных...")
    for row in rows:
        # Преобразуем sqlite3.Row в словарь
        row_dict = dict(row)
        
        # Подготавливаем значения
        values = (
            row_dict.get('muscle_group', ''),
            row_dict.get('exercise_name', ''),
            row_dict.get('description', ''),
            row_dict.get('youtube_link', ''),
            row_dict.get('equipment_needed', ''),
            row_dict.get('image_url', None)
        )
        
        pg_cursor.execute("""
            INSERT INTO exercises 
            (muscle_group, exercise_name, description, youtube_link, equipment_needed, image_url)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, values)
    
    print(f"✅ Перенесено {len(rows)} записей")
    
    # Проверяем результат
    pg_cursor.execute("SELECT COUNT(*) FROM exercises")
    count = pg_cursor.fetchone()['count']
    print(f"📊 В PostgreSQL теперь: {count} записей")

# ===== ЗАВЕРШЕНИЕ =====
pg_conn.commit()
print("\n✅ Изменения сохранены в PostgreSQL")

sqlite_conn.close()
pg_conn.close()
print("🔌 Соединения закрыты")

print("\n" + "=" * 50)
print("🎉 МИГРАЦИЯ ЗАВЕРШЕНА!")
print("=" * 50)