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
    cursor.execute('''
        SELECT exercise_name, description, youtube_link, equipment_needed, muscle_group 
        FROM exercises WHERE id = %s
    ''', (exercise_id,))
    exercise = cursor.fetchone()
    conn.close()
    return exercise

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
                name = exercise['exercise_name']
                desc = exercise['description']
                yt_link = exercise['youtube_link']
                equip = exercise['equipment_needed']
                group = exercise['muscle_group']
                
                # Формируем текст
                text = f"🏋️‍♂️ *{name}*\n\n"
                text += f"*Описание:* {desc}\n"
                if equip:
                    text += f"*Оборудование:* {equip}\n"
                
                markup = types.InlineKeyboardMarkup(row_width=1)
                
                if yt_link and yt_link.startswith('http'):
                    markup.add(types.InlineKeyboardButton("🎥 Смотреть видео", url=yt_link))
                
                markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data=f'group_{group}'))
                markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
                
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=markup,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
        
        # Навигационные кнопки
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