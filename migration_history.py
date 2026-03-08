"""
Миграция: добавляет таблицу user_history и опционально колонку direct_video_url
Запуск: python migration_history.py
"""
import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL не задан в окружении")
    exit(1)

def run_migration():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        # 1. Таблица истории выбранных упражнений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_history (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                exercise_id INTEGER NOT NULL REFERENCES exercises(id),
                selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_history_user_id ON user_history(user_id)')
        print("✅ Таблица user_history создана")
        
        # 2. Колонка для прямых ссылок на видео (mp4) — показ встроенным в Telegram
        cursor.execute('''
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='exercises' AND column_name='direct_video_url'
                ) THEN
                    ALTER TABLE exercises ADD COLUMN direct_video_url TEXT;
                END IF;
            END $$
        ''')
        print("✅ Колонка direct_video_url проверена/добавлена")
        
        conn.commit()
        print("\n🎉 Миграция выполнена успешно!")
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
