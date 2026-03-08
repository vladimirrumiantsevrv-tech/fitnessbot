"""
Импорт ссылок на картинки техники из exercises_images_phases.csv в базу данных.
Запуск: python import_images.py
"""
import os
import csv
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL не задан в окружении")
    print("   Задайте переменную: $env:DATABASE_URL = \"postgresql://...\"")
    exit(1)

CSV_PATH = os.path.join(os.path.dirname(__file__), 'exercises_images_phases.csv')

def main():
    if not os.path.exists(CSV_PATH):
        print(f"❌ Файл не найден: {CSV_PATH}")
        exit(1)

    print("=" * 50)
    print("🖼️  ИМПОРТ КАРТИНОК ТЕХНИКИ")
    print("=" * 50)

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    try:
        # Добавляем колонки, если их нет
        cursor.execute('''
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                    WHERE table_name='exercises' AND column_name='image_start_url') THEN
                    ALTER TABLE exercises ADD COLUMN image_start_url TEXT;
                END IF;
            END $$
        ''')
        cursor.execute('''
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                    WHERE table_name='exercises' AND column_name='image_finish_url') THEN
                    ALTER TABLE exercises ADD COLUMN image_finish_url TEXT;
                END IF;
            END $$
        ''')
        conn.commit()
        print("✅ Колонки image_start_url и image_finish_url готовы")

        # Читаем CSV
        with open(CSV_PATH, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        updated = 0
        not_found = []
        for row in rows:
            name = row.get('exercise_name', '').strip()
            img_start = row.get('image_start', '').strip()
            img_finish = row.get('image_finish', '').strip()
            if not name:
                continue

            cursor.execute(
                '''UPDATE exercises 
                   SET image_start_url = %s, image_finish_url = %s 
                   WHERE exercise_name = %s''',
                (img_start or None, img_finish or None, name)
            )
            if cursor.rowcount > 0:
                updated += 1
            else:
                not_found.append(name)

        conn.commit()
        print(f"✅ Обновлено упражнений: {updated}")
        if not_found:
            print(f"⚠️  Не найдено в БД: {len(not_found)}")
            for n in not_found[:5]:
                print(f"   - {n}")
            if len(not_found) > 5:
                print(f"   ... и ещё {len(not_found) - 5}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

    print("\n🎉 Импорт завершён!")

if __name__ == "__main__":
    main()
