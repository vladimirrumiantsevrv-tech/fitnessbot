import os
import psycopg2
from psycopg2.extras import RealDictCursor
import telebot
from telebot import types

# --- НОВОЕ: Получаем URL базы данных из переменной окружения ---
DATABASE_URL = os.environ.get('DATABASE_URL')
# Railway автоматически добавит эту переменную

def get_db_connection():
    """Подключение к PostgreSQL вместо SQLite"""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    """Создаем таблицы при первом запуске (если их нет)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # SQL для PostgreSQL немного отличается
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
    print("✅ Таблицы в PostgreSQL проверены/созданы.")

def get_groups():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT muscle_group FROM exercises ORDER BY muscle_group')
    groups = [row['muscle_group'] for row in cursor.fetchall()]
    conn.close()
    return groups

# --- Остальные функции (get_exercises_by_group, get_exercise_by_id) ---
# --- нужно обновить аналогично, используя psycopg2 и словари ---

# Инициализация базы при старте бота
init_db()

# Токен также берем из переменной окружения
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

def get_db_connection():
    conn = sqlite3.connect('fitness_bot.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_groups():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT muscle_group FROM exercises ORDER BY muscle_group')
    groups = [row[0] for row in cursor.fetchall()]
    conn.close()
    return groups

def get_exercises_by_group(group):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, exercise_name FROM exercises WHERE muscle_group = ? ORDER BY exercise_name', (group,))
    exercises = cursor.fetchall()
    conn.close()
    return exercises

def get_exercise_by_id(exercise_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT exercise_name, description, youtube_link, equipment_needed, muscle_group FROM exercises WHERE id = ?', (exercise_id,))
    exercise = cursor.fetchone()
    conn.close()
    return exercise

# Создаем бота
bot = telebot.TeleBot(TOKEN)

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    groups = get_groups()
    for group in groups:
        button = types.InlineKeyboardButton(group, callback_data=f'group_{group}')
        markup.add(button)
    
    bot.send_message(
        message.chat.id,
        f"👋 Привет, {message.from_user.first_name}!\n\nВыбери группу мышц:",
        reply_markup=markup
    )

# Обработчик нажатий на кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    data = call.data
    
    print(f"Нажата кнопка: {data}")  # Отладка
    
    try:
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
            
            # Добавляем кнопку "Назад"
            markup.add(types.InlineKeyboardButton("◀️ Назад к группам", callback_data="back_to_groups"))
            
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"💪 Группа: {group}\n\n👇 Выбери упражнение:",
                reply_markup=markup
            )
        
        elif data.startswith('ex_'):
            exercise_id = int(data.replace('ex_', ''))
            exercise = get_exercise_by_id(exercise_id)
            
            if exercise:
                name = exercise['exercise_name']
                desc = exercise['description']
                yt_link = exercise['youtube_link']
                equip = exercise['equipment_needed']
                group = exercise['muscle_group']
                
                # Формируем текст сообщения с новым форматом
                text_lines = []
                
                # Название упражнения большими буквами
                text_lines.append(f"🏋️‍♂️ {name.upper()}")
                text_lines.append("")
                
                # Техника выполнения (жирным в визуальном восприятии)
                text_lines.append("📋 ТЕХНИКА ВЫПОЛНЕНИЯ:")
                text_lines.append(desc)
                text_lines.append("")
                
                # Оборудование (если есть)
                if equip:
                    text_lines.append("🔧 ОБОРУДОВАНИЕ:")
                    text_lines.append(equip)
                    text_lines.append("")
                
                # Ссылка на YouTube (отдельным блоком)
                if yt_link and isinstance(yt_link, str) and (yt_link.startswith('http://') or yt_link.startswith('https://')):
                    text_lines.append("📺 ССЫЛКА НА YOUTUBE:")
                    text_lines.append("👇 Нажми кнопку ниже для просмотра видео")
                else:
                    text_lines.append("📺 ССЫЛКА НА YOUTUBE:")
                    text_lines.append("Видео暂时 недоступно")
                
                text = "\n".join(text_lines)
                
                # Создаем клавиатуру
                markup = types.InlineKeyboardMarkup(row_width=1)
                
                # Добавляем кнопку с видео ТОЛЬКО если это настоящая ссылка
                if yt_link and isinstance(yt_link, str) and (yt_link.startswith('http://') or yt_link.startswith('https://')):
                    markup.add(types.InlineKeyboardButton("🎥 СМОТРЕТЬ ВИДЕО", url=yt_link))
                
                # Навигационные кнопки
                markup.add(types.InlineKeyboardButton("◀️ НАЗАД К УПРАЖНЕНИЯМ", callback_data=f'group_{group}'))
                markup.add(types.InlineKeyboardButton("🏠 ГЛАВНОЕ МЕНЮ", callback_data="main_menu"))
                
                # Отправляем сообщение
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=markup,
                    disable_web_page_preview=True
                )
        
        elif data == "back_to_groups" or data == "main_menu":
            markup = types.InlineKeyboardMarkup(row_width=1)
            
            groups = get_groups()
            for group in groups:
                button = types.InlineKeyboardButton(group, callback_data=f'group_{group}')
                markup.add(button)
            
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="Выбери группу мышц:",
                reply_markup=markup
            )
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        # Пытаемся отправить упрощенное сообщение
        try:
            simplified_text = "❌ Ошибка отображения. Нажми /start"
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=simplified_text,
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🏠 ГЛАВНОЕ МЕНЮ", callback_data="main_menu")
                )
            )
        except:
            pass

# Запуск бота
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 ФИТНЕС БОТ ЗАПУСКАЕТСЯ")
    print("=" * 50)
    
    try:
        bot_info = bot.get_me()
        print(f"📱 Бот: @{bot_info.username}")
    except Exception as e:
        print(f"❌ Не удалось получить информацию о боте: {e}")
    
    print("✅ Бот готов к работе!")
    print("=" * 50)
    print("📋 Формат вывода:")
    print("   • Название упражнения")
    print("   • Техника выполнения")
    print("   • Оборудование")
    print("   • Ссылка на YouTube (кнопка)")
    print("=" * 50)
    
    # Бесконечный опрос с обработкой ошибок
    while True:
        try:
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print("🔄 Перезапуск через 5 секунд...")
            import time
            time.sleep(5)