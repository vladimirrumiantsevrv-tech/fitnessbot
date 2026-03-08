"""
Фитнес бот для Telegram - ПОЛНАЯ ВЕРСИЯ
"""
import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor
import telebot
from telebot import types

# Токен из переменных окружения
TOKEN = os.environ.get('BOT_TOKEN')
DATABASE_URL = os.environ.get('DATABASE_URL')

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден!")

print("=" * 50)
print("🚀 ЗАПУСК ФИТНЕС БОТА")
print("=" * 50)

# Создаем бота
bot = telebot.TeleBot(TOKEN)

# Функции для работы с PostgreSQL
def get_db_connection():
    """Подключение к базе данных"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def get_groups():
    """Получить все группы мышц"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT muscle_group FROM exercises ORDER BY muscle_group')
    groups = [row['muscle_group'] for row in cursor.fetchall()]
    conn.close()
    return groups

def get_exercises_by_group(group):
    """Получить упражнения по группе мышц"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, exercise_name FROM exercises WHERE muscle_group = %s ORDER BY exercise_name', (group,))
    exercises = cursor.fetchall()
    conn.close()
    return exercises

def get_exercise_by_id(exercise_id):
    """Получить детали упражнения по ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT id, muscle_group, exercise_name, description, youtube_link,
                  equipment_needed, direct_video_url, image_url,
                  image_start_url, image_finish_url
           FROM exercises WHERE id = %s''',
        (exercise_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    # Преобразуем в обычный dict (RealDictRow может вести себя иначе)
    exercise = dict(row)
    exercise['direct_video_url'] = exercise.get('direct_video_url') or ''
    return exercise

def add_to_history(user_id, exercise_id):
    """Добавить упражнение в историю пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO user_history (user_id, exercise_id) VALUES (%s, %s)',
            (user_id, exercise_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"⚠️ История: {e}")
    finally:
        conn.close()

def get_user_history(user_id, limit=15):
    """Получить историю выбранных упражнений пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT uh.exercise_id, uh.selected_at, e.exercise_name, e.muscle_group
        FROM user_history uh
        JOIN exercises e ON e.id = uh.exercise_id
        WHERE uh.user_id = %s
        ORDER BY uh.selected_at DESC
        LIMIT %s
    ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

# Проверка подключения к БД и создание user_history при отсутствии
def ensure_history_table():
    """Создаёт таблицу user_history, если её нет"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_history (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                exercise_id INTEGER NOT NULL REFERENCES exercises(id),
                selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_history_user_id ON user_history(user_id)')
        conn.commit()
        print("✅ Таблица user_history готова")
    except Exception as e:
        conn.rollback()
        print(f"⚠️ user_history: {e}")
    finally:
        conn.close()

try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM exercises')
    count = cursor.fetchone()['count']
    conn.close()
    print(f"✅ Подключено к БД. Найдено {count} упражнений")
    print(f"📊 Группы мышц: {', '.join(get_groups())}")
    ensure_history_table()
except Exception as e:
    print(f"❌ Ошибка подключения к БД: {e}")

def get_main_menu_markup():
    """Главное меню"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🏋️ Начать тренировку", callback_data="start_workout"))
    markup.add(types.InlineKeyboardButton("✅ Завершить тренировку", callback_data="finish_workout"))
    markup.add(types.InlineKeyboardButton("📜 Моя история", callback_data="history"))
    return markup

def get_groups_markup():
    """Меню групп мышц"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    groups = get_groups()
    for group in groups:
        markup.add(types.InlineKeyboardButton(group, callback_data=f'group_{group}'))
    markup.add(types.InlineKeyboardButton("✅ Завершить тренировку", callback_data="main_menu"))
    return markup

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Главное меню"""
    print(f"📨 /start от {message.from_user.first_name}")
    
    bot.send_message(
        message.chat.id,
        f"👋 Привет, {message.from_user.first_name}!\n\nЧто делаем?",
        reply_markup=get_main_menu_markup()
    )

# Обработчик нажатий на кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Обрабатывает все нажатия на кнопки"""
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    data = call.data
    bot.answer_callback_query(call.id)  # снимаем индикатор загрузки
    
    try:
        # Начать тренировку — показать группы
        if data == "start_workout":
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="💪 Выбери группу мышц:",
                reply_markup=get_groups_markup()
            )

        # Нажатие на группу мышц
        elif data.startswith('group_'):
            group = data.replace('group_', '')
            exercises = get_exercises_by_group(group)
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            for ex in exercises:
                markup.add(types.InlineKeyboardButton(ex['exercise_name'], callback_data=f'ex_{ex["id"]}'))
            markup.add(types.InlineKeyboardButton("◀️ Назад к группам", callback_data="back_to_groups"))
            markup.add(types.InlineKeyboardButton("✅ Завершить тренировку", callback_data="main_menu"))
            
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"💪 *Группа: {group}*\n\nВыбери упражнение:",
                reply_markup=markup,
                parse_mode='Markdown'
            )
        
        # Нажатие на упражнение
        elif data.startswith('ex_'):
            exercise_id = int(data.replace('ex_', ''))
            exercise = get_exercise_by_id(exercise_id)
            
            if exercise:
                user_id = call.from_user.id
                add_to_history(user_id, exercise_id)
                
                name = exercise['exercise_name']
                desc = exercise['description']
                yt_link = exercise.get('youtube_link')
                direct_url = exercise.get('direct_video_url') or ''
                equip = exercise['equipment_needed']
                group = exercise['muscle_group']
                # Пробуем разные варианты имён колонок (PostgreSQL, миграции)
                img_start = (exercise.get('image_start_url') or exercise.get('image_url') or '').strip()
                img_finish = (exercise.get('image_finish_url') or '').strip()
                
                # Отладка: показываем, есть ли URL картинок
                has_start = bool(img_start and img_start.startswith('http'))
                has_finish = bool(img_finish and img_finish.startswith('http'))
                if not has_start and not has_finish:
                    keys = ', '.join(sorted(exercise.keys()))
                    bot.send_message(chat_id, f"🔍 Отладка: URL не найдены. Колонки в записи: {keys[:400]}")
                
                # 1. Редактируем сообщение в заголовок (техника ниже)
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"🏋️‍♂️ *{name}*\n\n⬇️ Техника выполнения ниже",
                    parse_mode='Markdown'
                )
                
                # 2. Картинки техники — начало и окончание
                if img_start and img_start.startswith('http'):
                    try:
                        bot.send_photo(chat_id=chat_id, photo=img_start, caption="📍 Исходное положение")
                    except Exception as e:
                        print(f"⚠️ Не удалось отправить фото (start): {e}")
                        bot.send_message(chat_id, f"⚠️ Ошибка фото (исходное): {str(e)[:300]}")
                if img_finish and img_finish.startswith('http'):
                    try:
                        bot.send_photo(chat_id=chat_id, photo=img_finish, caption="📍 Конечная фаза")
                    except Exception as e:
                        print(f"⚠️ Не удалось отправить фото (finish): {e}")
                        bot.send_message(chat_id, f"⚠️ Ошибка фото (конечная): {str(e)[:300]}")
                
                # 3. Прямое mp4-видео (если есть)
                if direct_url and direct_url.strip().lower().endswith(('.mp4', '.webm', '.mov')):
                    try:
                        bot.send_video(chat_id=chat_id, video=direct_url.strip(), caption=f"🎥 {name}")
                    except Exception as e:
                        print(f"⚠️ Не удалось отправить видео: {e}")
                
                # 4. Описание упражнения (новое сообщение внизу)
                text = f"🏋️‍♂️ *{name}*\n\n"
                text += f"*Описание:* {desc}\n"
                if equip:
                    text += f"*Оборудование:* {equip}\n"
                if yt_link and yt_link.startswith('http'):
                    text += f"\n▶️ [Смотреть на YouTube]({yt_link})"
                
                markup = types.InlineKeyboardMarkup(row_width=1)
                markup.add(types.InlineKeyboardButton("✅ Выполнил", callback_data="back_to_groups"))
                markup.add(types.InlineKeyboardButton("◀️ Назад к упражнениям", callback_data=f'group_{group}'))
                markup.add(types.InlineKeyboardButton("✅ Завершить тренировку", callback_data="main_menu"))
                
                bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=markup,
                    parse_mode='Markdown',
                    disable_web_page_preview=bool(direct_url)
                )
        
        # История выбранных упражнений
        elif data == "history":
            user_id = call.from_user.id
            try:
                history = get_user_history(user_id)
            except Exception as e:
                print(f"⚠️ История: {e}")
                history = []
            
            if not history:
                text = "📜 <b>Твоя история пуста</b>\n\nВыбери упражнение — оно появится здесь."
            else:
                text = "📜 <b>Твоя история упражнений:</b>\n\n"
                seen_ids = set()
                for row in history:
                    ex_id = row['exercise_id']
                    if ex_id in seen_ids:
                        continue
                    seen_ids.add(ex_id)
                    name = row['exercise_name'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    muscle = row['muscle_group'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    text += f"• <b>{name}</b> ({muscle})\n"
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            seen_btn = set()
            for row in history:
                if len(seen_btn) >= 10:
                    break
                ex_id = row['exercise_id']
                if ex_id in seen_btn:
                    continue
                seen_btn.add(ex_id)
                name = row['exercise_name'][:35] + "…" if len(row['exercise_name']) > 35 else row['exercise_name']
                markup.add(types.InlineKeyboardButton(f"📍 {name}", callback_data=f"ex_{ex_id}"))
            markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
            
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=markup,
                parse_mode='HTML'
            )
        
        # Выполнил — вернуться к группам мышц
        elif data == "back_to_groups":
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="💪 Выбери группу мышц:",
                reply_markup=get_groups_markup()
            )

        # Главное меню / Завершить тренировку
        elif data == "main_menu" or data == "finish_workout":
            text = "Что делаем?" if data == "main_menu" else "✅ Тренировка завершена!\n\nЧто делаем?"
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=get_main_menu_markup()
            )
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        bot.send_message(chat_id, "❌ Произошла ошибка. Нажми /start")

# Запуск бота
if __name__ == "__main__":
    print("=" * 50)
    print("✅ БОТ ГОТОВ К РАБОТЕ!")
    print("=" * 50)
    
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print("🔄 Перезапуск через 10 секунд...")
            time.sleep(10)