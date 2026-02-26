# check_db.py - просмотр содержимого базы данных

import sqlite3

print("ПРОВЕРКА БАЗЫ ДАННЫХ")
print("-" * 40)

# Подключаемся к базе
conn = sqlite3.connect('fitness_bot.db')
cursor = conn.cursor()

# Смотрим все упражнения
print("\nСодержимое таблицы exercises:")
print("-" * 40)

cursor.execute('SELECT * FROM exercises')
exercises = cursor.fetchall()

for exercise in exercises:
    print(f"ID: {exercise[0]}")
    print(f"Группа мышц: {exercise[1]}")
    print(f"Упражнение: {exercise[2]}")
    print(f"Описание: {exercise[3][:50]}...")  # Первые 50 символов
    print(f"YouTube: {exercise[4]}")
    print(f"Оборудование: {exercise[5]}")
    print("-" * 40)

# Считаем количество упражнений по группам мышц
print("\nСтатистика по группам мышц:")
print("-" * 40)

cursor.execute('''
    SELECT muscle_group, COUNT(*) 
    FROM exercises 
    GROUP BY muscle_group
''')
stats = cursor.fetchall()

for group, count in stats:
    print(f"{group}: {count} упражнений")

conn.close()

print("\n✅ Проверка завершена!")