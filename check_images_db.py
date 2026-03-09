"""
Проверка наличия картинок в БД.
Запуск: python check_images_db.py
Требует: DATABASE_URL в окружении
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ Задайте DATABASE_URL")
    print("   Railway: скопируйте DATABASE_URL из Variables в дашборде")
    print('   PowerShell: $env:DATABASE_URL = "postgresql://..."')
    exit(1)

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
cur = conn.cursor()

# Проверяем колонки
cur.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name='exercises' 
    ORDER BY ordinal_position
""")
columns = [r['column_name'] for r in cur.fetchall()]
print("📋 Колонки таблицы exercises:", columns)

has_start = 'image_start_url' in columns
has_finish = 'image_finish_url' in columns
print(f"   image_start_url: {'есть' if has_start else 'НЕТ'}")
print(f"   image_finish_url: {'есть' if has_finish else 'НЕТ'}")

# Сколько записей с картинками
if has_start and has_finish:
    cur.execute("SELECT COUNT(*) as c FROM exercises WHERE image_start_url IS NOT NULL AND image_start_url != ''")
    with_start = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM exercises WHERE image_finish_url IS NOT NULL AND image_finish_url != ''")
    with_finish = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM exercises")
    total = cur.fetchone()['c']
    print(f"\n📊 С картинками: image_start={with_start}, image_finish={with_finish} из {total}")

    # Примеры
    cur.execute("SELECT id, exercise_name, image_start_url, image_finish_url FROM exercises WHERE image_start_url IS NOT NULL LIMIT 3")
    rows = cur.fetchall()
    if rows:
        print("\n📌 Примеры записей с картинками:")
        for r in rows:
            print(f"   {r['id']} {r['exercise_name'][:30]}: start={bool(r['image_start_url'])}, finish={bool(r['image_finish_url'])}")
    else:
        print("\n⚠️ Нет ни одной записи с image_start_url! Нужно запустить: python import_images.py")
else:
    print("\n⚠️ Колонок для картинок нет. Запустите: python import_images.py")

conn.close()
print("\n✅ Проверка завершена")
