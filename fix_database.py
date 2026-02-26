"""
Скрипт для исправления базы данных
Меняет местами youtube_link и equipment_needed
"""
import sqlite3

print("=" * 50)
print("🔄 ИСПРАВЛЕНИЕ БАЗЫ ДАННЫХ")
print("=" * 50)

# Подключаемся к базе
conn = sqlite3.connect('fitness_bot.db')
cursor = conn.cursor()

# Смотрим текущее состояние
print("\n📊 ТЕКУЩЕЕ СОСТОЯНИЕ:")
cursor.execute('SELECT id, exercise_name, youtube_link, equipment_needed FROM exercises LIMIT 3')
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f"\nID: {row[0]}")
        print(f"Упражнение: {row[1]}")
        print(f"  youtube_link: {row[2]}")
        print(f"  equipment_needed: {row[3]}")
else:
    print("В базе нет данных!")

# Создаем временную таблицу (БЕЗ КОММЕНТАРИЕВ)
print("\n🔄 МЕНЯЕМ МЕСТАМИ...")

# Сначала создаем новую таблицу с правильными полями
cursor.execute('''
    CREATE TABLE exercises_new (
        id INTEGER PRIMARY KEY,
        muscle_group TEXT,
        exercise_name TEXT,
        description TEXT,
        youtube_link TEXT,
        equipment_needed TEXT
    )
''')

# Копируем данные, меняя местами поля
cursor.execute('''
    INSERT INTO exercises_new (id, muscle_group, exercise_name, description, youtube_link, equipment_needed)
    SELECT id, muscle_group, exercise_name, description, equipment_needed, youtube_link
    FROM exercises
''')

# Удаляем старую таблицу
cursor.execute('DROP TABLE exercises')

# Переименовываем новую таблицу
cursor.execute('ALTER TABLE exercises_new RENAME TO exercises')

# Сохраняем изменения
conn.commit()

print("\n✅ БАЗА ДАННЫХ ИСПРАВЛЕНА!")

# Проверяем результат
print("\n📊 НОВОЕ СОСТОЯНИЕ:")
cursor.execute('SELECT id, exercise_name, youtube_link, equipment_needed FROM exercises LIMIT 3')
rows = cursor.fetchall()
for row in rows:
    print(f"\nID: {row[0]}")
    print(f"Упражнение: {row[1]}")
    print(f"  youtube_link: {row[2]}")
    print(f"  equipment_needed: {row[3]}")

# Покажем статистику
cursor.execute('SELECT COUNT(*) FROM exercises')
total = cursor.fetchone()[0]
print(f"\n📊 Всего записей в базе: {total}")

# Посчитаем сколько ссылок и сколько оборудования
cursor.execute("SELECT COUNT(*) FROM exercises WHERE youtube_link LIKE 'http%'")
valid_links = cursor.fetchone()[0]
print(f"✅ Корректных ссылок в youtube_link: {valid_links}")

cursor.execute("SELECT COUNT(*) FROM exercises WHERE equipment_needed NOT LIKE 'http%' AND equipment_needed IS NOT NULL AND equipment_needed != ''")
valid_equip = cursor.fetchone()[0]
print(f"✅ Записей с оборудованием: {valid_equip}")

conn.close()
print("\n" + "=" * 50)
print("🎉 ГОТОВО! Теперь можно запускать бота")
print("=" * 50)