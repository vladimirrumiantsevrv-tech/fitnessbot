"""
Фитнес бот для Telegram - ПОЛНАЯ ВЕРСИЯ
"""
import os
import time
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import telebot
from telebot import types

# Токен из переменных окружения
TOKEN = os.environ.get('BOT_TOKEN')
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_PRIVATE_URL')

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден!")

print("=" * 50)
print("🚀 ЗАПУСК ФИТНЕС БОТА")
print("=" * 50)

# Создаем бота
bot = telebot.TeleBot(TOKEN)

# Простое состояние активной тренировки по пользователю
ACTIVE_WORKOUTS = set()
# Упражнения, отмеченные «Выполнил» в текущей сессии (только с «Начать тренировку»)
SESSION_COMPLETED = {}  # user_id -> list of exercise names

def _is_image_data(data):
    """Проверка по magic bytes: JPEG, PNG, GIF, WebP"""
    if not data or len(data) < 4:
        return False
    d = data[:12]
    if d[:2] == b'\xff\xd8':
        return True  # JPEG
    if d[:8] == b'\x89PNG\r\n\x1a\n':
        return True  # PNG
    if d[:6] in (b'GIF87a', b'GIF89a'):
        return True  # GIF
    if d[:4] == b'RIFF' and d[8:12] == b'WEBP':
        return True  # WebP
    return False

def send_photo_with_fallback(chat_id, url, caption=""):
    """Сначала по URL, при ошибке — скачивает и отправляет. С retry."""
    try:
        bot.send_photo(chat_id=chat_id, photo=url, caption=caption)
        return True
    except Exception as e:
        print(f"⚠️ send_photo URL fail: {e}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'}
    for attempt in range(2):
        try:
            if attempt > 0:
                time.sleep(1.5)
            r = requests.get(url, timeout=20, headers=headers)
            r.raise_for_status()
            data = r.content
            if _is_image_data(data):
                bot.send_photo(chat_id=chat_id, photo=data, caption=caption)
                return True
        except Exception as e2:
            print(f"⚠️ send_photo fallback attempt {attempt+1}: {e2}")
    return False

# Функции для работы с PostgreSQL
def get_db_connection():
    """Подключение к базе данных"""
    url = DATABASE_URL or ''
    if not url:
        raise ValueError("DATABASE_URL не задан")
    # Railway и облачный PostgreSQL требуют SSL
    if 'sslmode=' not in url and ('rlwy.net' in url or 'railway' in url.lower() or 'amazonaws.com' in url):
        url = url + ('&' if '?' in url else '?') + 'sslmode=require'
    return psycopg2.connect(url, cursor_factory=RealDictCursor)

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

# Отметка выполненных упражнений
def add_completed_exercise(user_id, exercise_id):
    """Сохранить выполненное упражнение пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO user_completed (user_id, exercise_id) VALUES (%s, %s)',
            (user_id, exercise_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Завершённые упражнения: {e}")
    finally:
        conn.close()

def get_today_completed_exercises(user_id):
    """Получить упражнения, отмеченные выполненными сегодня"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT uc.exercise_id,
               uc.completed_at,
               e.exercise_name
        FROM user_completed uc
        JOIN exercises e ON e.id = uc.exercise_id
        WHERE uc.user_id = %s
          AND uc.completed_at::date = CURRENT_DATE
        ORDER BY uc.completed_at
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

# Проверка подключения к БД и создание таблиц истории при отсутствии
def ensure_history_table():
    """Создаёт таблицы user_history и user_completed, если их нет"""
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_completed (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                exercise_id INTEGER NOT NULL REFERENCES exercises(id),
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_completed_user_id ON user_completed(user_id)')
        conn.commit()
        print("✅ Таблицы user_history и user_completed готовы")
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

def get_main_menu_markup(in_workout: bool = False):
    """Главное меню"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🏋️ Начать тренировку", callback_data="start_workout"))
    if in_workout:
        markup.add(types.InlineKeyboardButton("✅ Завершить тренировку", callback_data="finish_workout"))
    return markup

def get_groups_markup():
    """Меню групп мышц"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    groups = get_groups()
    for group in groups:
        markup.add(types.InlineKeyboardButton(group, callback_data=f'group_{group}'))
    markup.add(types.InlineKeyboardButton("✅ Завершить тренировку", callback_data="finish_workout"))
    return markup

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Главное меню"""
    print(f"📨 /start от {message.from_user.first_name}")
    welcome_text = (
        "Привет! Я твой личный помощник в тренировках.\n"
        "Я подскажу тебе варианты упражнений, которые собраны с учетом оборудования твоего зала!"
    )
    in_workout = message.from_user.id in ACTIVE_WORKOUTS
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=get_main_menu_markup(in_workout=in_workout)
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
            user_id = call.from_user.id
            ACTIVE_WORKOUTS.add(user_id)
            SESSION_COMPLETED[user_id] = []
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
            markup.add(types.InlineKeyboardButton("✅ Завершить тренировку", callback_data="finish_workout"))
            
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
                
                # 1. Редактируем сообщение в заголовок (техника ниже)
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"🏋️‍♂️ *{name}*\n\n⬇️ Техника выполнения ниже",
                    parse_mode='Markdown'
                )
                
                # 2. Картинки техники — начало и окончание (с fallback: скачать и отправить при 400)
                if img_start and img_start.startswith('http'):
                    send_photo_with_fallback(chat_id, img_start, "📍 Исходное положение")
                if img_finish and img_finish.startswith('http'):
                    send_photo_with_fallback(chat_id, img_finish, "📍 Конечная фаза")
                
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
                markup.add(types.InlineKeyboardButton("✅ Выполнил", callback_data=f'done_{exercise_id}'))
                markup.add(types.InlineKeyboardButton("◀️ Назад к упражнениям", callback_data=f'group_{group}'))
                markup.add(types.InlineKeyboardButton("✅ Завершить тренировку", callback_data="finish_workout"))
                
                bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=markup,
                    parse_mode='Markdown',
                    disable_web_page_preview=bool(direct_url)
                )
        
        # Выполнил — сохранить в сессию и в БД, вернуться к группам мышц
        elif data.startswith('done_'):
            exercise_id = int(data.replace('done_', ''))
            user_id = call.from_user.id
            add_completed_exercise(user_id, exercise_id)
            ex = get_exercise_by_id(exercise_id)
            if ex and user_id in SESSION_COMPLETED:
                SESSION_COMPLETED[user_id].append(ex['exercise_name'])
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="💪 Выбери группу мышц:",
                reply_markup=get_groups_markup()
            )

        # Назад к списку групп мышц (из списка упражнений)
        elif data == "back_to_groups":
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="💪 Выбери группу мышц:",
                reply_markup=get_groups_markup()
            )

        # Главное меню
        elif data == "main_menu":
            user_id = call.from_user.id
            in_workout = user_id in ACTIVE_WORKOUTS
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="Что делаем?",
                reply_markup=get_main_menu_markup(in_workout=in_workout)
            )

        # Завершить тренировку — показать упражнения, отмеченные в этой сессии
        elif data == "finish_workout":
            user_id = call.from_user.id
            if user_id not in ACTIVE_WORKOUTS:
                bot.answer_callback_query(call.id, text="Сначала нажми «Начать тренировку» 💪", show_alert=True)
                return

            completed_names = SESSION_COMPLETED.get(user_id, [])
            if not completed_names:
                text = (
                    "Отличный результат! В этой тренировке ты пока не отметил ни одного упражнения выполненным.\n\n"
                    "Выбери упражнение, нажми «Выполнил» и возвращайся к этой кнопке."
                )
            else:
                lines = [f"• {name}" for name in completed_names]
                text = "Отличный результат! В этой тренировке ты выполнил:\n\n" + "\n".join(lines)

            ACTIVE_WORKOUTS.discard(user_id)
            SESSION_COMPLETED.pop(user_id, None)
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=get_main_menu_markup(in_workout=False)
            )
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        err_msg = str(e).replace('<', '').replace('>', '')[:250]
        bot.send_message(chat_id, f"❌ Произошла ошибка. Нажми /start\n\n_Ошибка: {err_msg}_", parse_mode='Markdown')

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