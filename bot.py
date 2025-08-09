import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, BotCommand
from database import get_db_connection
from keep_alive import keep_alive  # Імпорт Flask-keep_alive

API_TOKEN = "8232680735:AAG-GFL8ZOUla-OwP-0D5bDhnFpNaH6e-pU"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

MESSAGES = {
    "uk": {
        "top_empty": "🤷‍♂️ Поки що немає заручених пар.",
        "commands_list": (
            "📜 Ось мої команди:\n"
            "/marry - одружитись 👰🤵\n"
            "/topcouples - топ пар 🥇\n"
            "/divorce - розійтись 💔\n"
            "/profile - подивитись профіль 🕵️‍♂️\n"
            "/commands - цей список команд 📋\n"
        ),
        "help_dm": (
            "Вітаю! Ось мої команди:\n"
            "/marry — одружитись 👰🤵\n"
            "/topcouples — топ пар 🥇\n"
            "/divorce — розійтись 💔\n"
            "/profile — твій профіль 🕵️‍♂️\n"
            "/commands — список команд 📋\n"
            "\nТех. підтримка: @KR_LVXH"
        ),
        "already_married": "Ви вже в парі, спочатку розійдіться через /divorce.",
        "marry_start": "💒 Починаємо весільне гуляння для {couple}! 🎉",
        "marry_success": "🎉 {couple}, ви тепер одружені! Нехай щастить! 💖",
        "no_spouse": "😢 Ти ще не одружений(а).",
        "divorce_no_spouse": "❌ Ти не одружений(а), щоб розійтись.",
        "divorce_success": "💔 {user1} та {user2} тепер розведені. Нехай новий шлях буде світлим!",
        "profile_no_marriage": "🕵️‍♂️ Профіль доступний лише одруженим. Спочатку одружись через /marry.",
        "profile_header": "📇 Твій профіль:\n",
        "profile_married_to": "Одружений(а) з: {partner}\n",
        "profile_married_since": "Одружені з: {since}\n",
        "profile_username": "Нікнейм: @{username}\n",
        "profile_activity": "Активність у групі: {active} хвилин\n"
    }
}

async def get_user_name(chat_id: int, user_id: int):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.user.full_name
    except:
        return f"Користувач {user_id}"

def format_duration(start_time: datetime):
    now = datetime.now()
    diff = now - start_time
    minutes = int(diff.total_seconds() // 60)
    if minutes < 60:
        return f"{minutes} хвилин"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} годин"
    days = hours // 24
    if days < 30:
        return f"{days} днів"
    months = days // 30
    if months < 12:
        return f"{months} місяців"
    years = months // 12
    return f"{years} років"

@dp.message(Command("start"))
async def cmd_start(message: Message):
    lang = "uk"
    await message.answer(MESSAGES[lang]["help_dm"])

@dp.message(Command("commands"))
async def cmd_commands(message: Message):
    lang = "uk"
    await message.answer(MESSAGES[lang]["commands_list"])

@dp.message(Command("marry"))
async def cmd_marry(message: Message):
    conn = get_db_connection()
    c = conn.cursor()
    user_id = message.from_user.id
    chat_id = message.chat.id

    c.execute('SELECT user1_id, user2_id FROM couples WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
    if c.fetchone():
        await message.reply(MESSAGES["uk"]["already_married"])
        conn.close()
        return

    # Для простоти — одружуємо користувача з самим собою (поправиш під реальний процес, де потрібна пропозиція)
    wed_date = datetime.now().isoformat()
    c.execute('INSERT INTO couples (user1_id, user2_id, wed_date) VALUES (?, ?, ?)', (user_id, user_id, wed_date))
    c.execute('INSERT OR IGNORE INTO users (user_id, status) VALUES (?, ?)', (user_id, "Одружений(а)"))
    c.execute("UPDATE users SET status = 'Одружений(а)' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    user_name = await get_user_name(chat_id, user_id)
    couple_name = f"{user_name} ❤️ {user_name}"

    await message.answer(MESSAGES["uk"]["marry_start"].format(couple=couple_name))
    await asyncio.sleep(5)  # Затримка 5 секунд
    await message.answer(MESSAGES["uk"]["marry_success"].format(couple=couple_name))

@dp.message(Command("topcouples"))
async def cmd_topcouples(message: Message):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT user1_id, user2_id, wed_date FROM couples')
    rows = c.fetchall()
    if not rows:
        await message.answer(MESSAGES["uk"]["top_empty"])
        conn.close()
        return
    result_text = "🔥 Топ одружених пар:\n\n"
    for user1_id, user2_id, wed_date_str in rows:
        wed_date = datetime.fromisoformat(wed_date_str)
        duration = format_duration(wed_date)
        user1_name = await get_user_name(message.chat.id, user1_id)
        user2_name = await get_user_name(message.chat.id, user2_id)
        couple_name = f"{user1_name} ❤️ {user2_name}"
        result_text += f"{couple_name} — разом вже {duration}\n"
    await message.answer(result_text)
    conn.close()

@dp.message(Command("divorce"))
async def cmd_divorce(message: Message):
    conn = get_db_connection()
    c = conn.cursor()
    user_id = message.from_user.id

    c.execute('SELECT user1_id, user2_id FROM couples WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
    row = c.fetchone()

    if not row:
        await message.answer(MESSAGES["uk"]["divorce_no_spouse"])
        conn.close()
        return

    user1_id, user2_id = row
    c.execute('DELETE FROM couples WHERE user1_id = ? AND user2_id = ?', (user1_id, user2_id))
    c.execute("UPDATE users SET status = 'Вільний(а)' WHERE user_id IN (?, ?)", (user1_id, user2_id))
    conn.commit()

    user1_name = await get_user_name(message.chat.id, user1_id)
    user2_name = await get_user_name(message.chat.id, user2_id)

    await message.answer(MESSAGES["uk"]["divorce_success"].format(user1=user1_name, user2=user2_name))
    conn.close()

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    conn = get_db_connection()
    c = conn.cursor()
    user_id = message.from_user.id
    chat_id = message.chat.id

    c.execute('SELECT lang, status FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    lang = row[0] if row else "uk"
    status = row[1] if row else "Вільний(а)"

    if status != "Одружений(а)":
        await message.answer(MESSAGES[lang]["profile_no_marriage"])
        conn.close()
        return

    c.execute('SELECT user1_id, user2_id, wed_date FROM couples WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
    row = c.fetchone()
    if not row:
        await message.answer(MESSAGES[lang]["profile_no_marriage"])
        conn.close()
        return

    user1_id, user2_id, wed_date_str = row
    wed_date = datetime.fromisoformat(wed_date_str)
    spouse_id = user2_id if user1_id == user_id else user1_id

    spouse_name = await get_user_name(chat_id, spouse_id)
    member = await bot.get_chat_member(chat_id, user_id)
    username = member.user.username or "немає"
    join_date = member.joined_date or datetime.now()
    active_minutes = int((datetime.now() - join_date).total_seconds() // 60)

    profile_text = (
        MESSAGES[lang]["profile_header"] +
        MESSAGES[lang]["profile_username"].format(username=username) +
        MESSAGES[lang]["profile_activity"].format(active=active_minutes) +
        MESSAGES[lang]["profile_married_to"].format(partner=spouse_name) +
        MESSAGES[lang]["profile_married_since"].format(since=wed_date.strftime("%d.%m.%Y"))
    )

    await message.answer(profile_text)
    conn.close()

async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Стартувати бота"),
        BotCommand(command="commands", description="Показати команди"),
        BotCommand(command="marry", description="Одружитись"),
        BotCommand(command="topcouples", description="Топ пар"),
        BotCommand(command="divorce", description="Розійтись"),
        BotCommand(command="profile", description="Подивитись профіль"),
    ]
    await bot.set_my_commands(commands)

async def main():
    keep_alive()  # Запускаємо Flask-сервер у окремому потоці
    await set_bot_commands()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
