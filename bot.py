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
    cursor.execute('SELECT * FROM exercises WHERE id = %s', (exercise_id,))
    exercise = cursor.fetchone()
    conn.close()
    if exercise:
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

# Проверка подключения к БД
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM exercises')
    count = cursor.fetchone()['count']
    conn.close()
    print(f"✅ Подключено к БД. Найдено {count} упражнений")
    print(f"📊 Группы мышц: {', '.join(get_groups())}")
except Exception as e:
    print(f"❌ Ошибка подключения к БД: {e}")

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Показывает группы мышц"""
    print(f"📨 /start от {message.from_user.first_name}")
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    groups = get_groups()
    
    for group in groups:
        button = types.InlineKeyboardButton(group, callback_data=f'group_{group}')
        markup.add(button)
    
    markup.add(types.InlineKeyboardButton("📜 Моя история", callback_data="history"))
    
    bot.send_message(
        message.chat.id,
        f"👋 Привет, {message.from_user.first_name}!\n\nВыбери группу мышц:",
        reply_markup=markup
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
        # Нажатие на группу мышц
        if data.startswith('group_'):
            group = data.replace('group_', '')
            exercises = get_exercises_by_group(group)
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            
            for ex in exercises:
                button = types.InlineKeyboardButton(
                    ex['exercise_name'], 
                    callback_data=f'ex_{ex["id"]}'
                )
                markup.add(button)
            
            markup.add(types.InlineKeyboardButton("◀️ Назад к группам", callback_data="back_to_groups"))
            markup.add(types.InlineKeyboardButton("📜 Моя история", callback_data="history"))
            
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
                
                # Прямое mp4-видео — показываем встроенно в Telegram
                if direct_url and direct_url.strip().lower().endswith(('.mp4', '.webm', '.mov')):
                    try:
                        bot.send_video(
                            chat_id=chat_id,
                            video=direct_url.strip(),
                            caption=f"🎥 *{name}*",
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        print(f"⚠️ Не удалось отправить видео: {e}")
                
                # Формируем текст
                text = f"🏋️‍♂️ *{name}*\n\n"
                text += f"*Описание:* {desc}\n"
                if equip:
                    text += f"*Оборудование:* {equip}\n"
                if yt_link and yt_link.startswith('http') and not direct_url:
                    text += f"\n▶️ [Смотреть на YouTube]({yt_link})"
                
                markup = types.InlineKeyboardMarkup(row_width=1)
                if yt_link and yt_link.startswith('http') and not direct_url:
                    markup.add(types.InlineKeyboardButton("🎥 Смотреть на YouTube", url=yt_link))
                elif yt_link and yt_link.startswith('http'):
                    markup.add(types.InlineKeyboardButton("🎥 Также на YouTube", url=yt_link))
                markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data=f'group_{group}'))
                markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
                markup.add(types.InlineKeyboardButton("📜 Моя история", callback_data="history"))
                
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
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
                text = "📜 *Твоя история пуста*\n\nВыбери упражнение — оно появится здесь."
            else:
                text = "📜 *Твоя история упражнений:*\n\n"
                seen_ids = set()
                for row in history:
                    ex_id = row['exercise_id']
                    if ex_id in seen_ids:
                        continue
                    seen_ids.add(ex_id)
                    name = row['exercise_name']
                    muscle = row['muscle_group']
                    text += f"• *{name}* ({muscle})\n"
            
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
                parse_mode='Markdown'
            )
        
        # Навигационные кнопки
        elif data == "back_to_groups" or data == "main_menu":
            markup = types.InlineKeyboardMarkup(row_width=1)
            groups = get_groups()
            
            for group in groups:
                button = types.InlineKeyboardButton(group, callback_data=f'group_{group}')
                markup.add(button)
            
            markup.add(types.InlineKeyboardButton("📜 Моя история", callback_data="history"))
            
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="Выбери группу мышц:",
                reply_markup=markup
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