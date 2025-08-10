import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand

API_TOKEN = "8232680735:AAG-GFL8ZOUla-OwP-0D5bDhnFpNaH6e-pU"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ---
conn = sqlite3.connect("wedding_bot.db")
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS couples (
    user1_id INTEGER NOT NULL,
    user2_id INTEGER NOT NULL,
    wed_date TEXT NOT NULL,
    PRIMARY KEY (user1_id, user2_id)
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    lang TEXT DEFAULT 'uk'
)
""")
conn.commit()

def get_lang(user_id: int):
    c.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    return row[0] if row else "uk"

MESSAGES = {
    "uk": {
        "marry_offer": "{target}, вам пропонують одружитись від {proposer}!\nНатисніть ✅ щоб погодитись, або ❌ щоб відмовитись.",
        "marry_accepted": "🎉 {couple} тепер одружені! Вітаємо з новим союзом! 💖",
        "marry_declined": "{target} відмовив(ла) {proposer}.",
        "self_marry": "Не можна одружуватись із собою.",
        "no_spouse_to_divorce": "Ви не одружені, щоб розвезтись.",
        "divorce_success": "💔 {user1} і {user2} тепер розведені. Нехай шлях буде світлим і новим!",
        "top_empty": "Поки що немає одружених пар.",
        "commands_list": (
            "/marry - зробити пропозицію одружитись\n"
            "/topcouples - показати топ пар і скільки часу разом\n"
            "/divorce - розвезтись зі своєю половинкою\n"
            "/commands - показати цей список команд\n"
        ),
        "help_dm": (
            "Вітання! Ось що я вмію:\n"
            "/marry — зробити пропозицію одружитись\n"
            "/topcouples — показати топ пар\n"
            "/divorce — розвезтись зі своєю половинкою\n"
            "/commands — показати список команд\n"
            "\nТех. підтримка: @KR_LVXH"
        ),
        "proposal_sent": "Пропозицію відправлено!"
    }
}

pending_marries = {}

@dp.message(Command("start"))
async def cmd_start(message: Message):
    lang = get_lang(message.from_user.id)
    await message.answer(MESSAGES[lang]["help_dm"])

@dp.message(Command("commands"))
async def cmd_commands(message: Message):
    lang = get_lang(message.from_user.id)
    await message.answer(MESSAGES[lang]["commands_list"])

@dp.message(Command("marry"))
async def cmd_marry(message: Message):
    lang = get_lang(message.from_user.id)
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Вкажи користувача, якому робиш пропозицію, через @username")
        return

    username = parts[1].lstrip("@").strip()
    if username.lower() == (message.from_user.username or "").lower():
        await message.reply(MESSAGES[lang]["self_marry"])
        return

    proposer = message.from_user
    proposee_mention = f"@{username}"
    proposal_id = f"{message.chat.id}_{message.message_id}"

    text = MESSAGES[lang]["marry_offer"].format(target=proposee_mention, proposer=proposer.full_name)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅", callback_data=f"marry_accept:{proposal_id}:{proposer.id}:{username}"),
            InlineKeyboardButton(text="❌", callback_data=f"marry_decline:{proposal_id}:{proposer.id}:{username}")
        ]
    ])
    await message.answer(text, reply_markup=kb)
    pending_marries[proposal_id] = (proposer.id, username)
    await message.reply(MESSAGES[lang]["proposal_sent"])

@dp.callback_query(lambda c: c.data and c.data.startswith("marry_"))
async def marry_callback(call: CallbackQuery):
    data = call.data.split(":")
    action = data[0].split("_")[1]
    proposal_id = data[1]
    proposer_id = int(data[2])
    username = data[3]

    lang = get_lang(call.from_user.id)
    accepted = (action == "accept")

    if call.from_user.username != username:
        await call.answer("Це не ваша пропозиція!", show_alert=True)
        return

    if proposal_id not in pending_marries:
        await call.answer("Ця пропозиція вже оброблена.", show_alert=True)
        return

    if accepted:
        user1_id = min(proposer_id, call.from_user.id)
        user2_id = max(proposer_id, call.from_user.id)
        now_str = datetime.now().isoformat()
        try:
            c.execute('INSERT INTO couples (user1_id, user2_id, wed_date) VALUES (?, ?, ?)', (user1_id, user2_id, now_str))
            conn.commit()
        except sqlite3.IntegrityError:
            # Вже одружені
            pass

        user1_chat = await bot.get_chat(user1_id)
        user2_chat = await bot.get_chat(user2_id)
        couple_name = f"[{user1_chat.first_name}](tg://user?id={user1_id}) і [{user2_chat.first_name}](tg://user?id={user2_id})"

        text = MESSAGES[lang]["marry_accepted"].format(couple=couple_name)
        await call.message.edit_text(text, parse_mode="Markdown")
    else:
        text = MESSAGES[lang]["marry_declined"].format(target=call.from_user.full_name, proposer=f"@{pending_marries[proposal_id][1]}")
        await call.message.edit_text(text)

    pending_marries.pop(proposal_id, None)
    await call.answer()

@dp.message(Command("topcouples"))
async def cmd_topcouples(message: Message):
    lang = get_lang(message.from_user.id)
    c.execute("SELECT user1_id, user2_id, wed_date FROM couples")
    rows = c.fetchall()

    if not rows:
        await message.reply(MESSAGES[lang]["top_empty"])
        return

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

    couples_info = []
    for user1_id, user2_id, wed_date_str in rows:
        wed_date = datetime.fromisoformat(wed_date_str)
        duration = format_duration(wed_date)

        try:
            user1 = await bot.get_chat(user1_id)
            user2 = await bot.get_chat(user2_id)
            couple_name = f"{user1.first_name} і {user2.first_name}"
        except Exception:
            couple_name = f"Пара {user1_id} і {user2_id}"

        couples_info.append((couple_name, wed_date, duration))

    couples_info.sort(key=lambda x: x[1])

    text_lines = ["🌹 Топ одружених пар:"]
    for name, _, duration in couples_info:
        text_lines.append(f"💑 {name} — разом уже {duration}")

    await message.answer("\n".join(text_lines))

@dp.message(Command("divorce"))
async def cmd_divorce(message: Message):
    lang = get_lang(message.from_user.id)
    user_id = message.from_user.id

    c.execute("SELECT user1_id, user2_id FROM couples WHERE user1_id = ? OR user2_id = ?", (user_id, user_id))
    couple = c.fetchone()

    if not couple:
        await message.reply(MESSAGES[lang]["no_spouse_to_divorce"])
        return

    user1_id, user2_id = couple

    try:
        user1 = await bot.get_chat(user1_id)
        user2 = await bot.get_chat(user2_id)
        user1_name = user1.first_name
        user2_name = user2.first_name
    except Exception:
        user1_name = f"User {user1_id}"
        user2_name = f"User {user2_id}"

    c.execute("DELETE FROM couples WHERE user1_id = ? AND user2_id = ?", (user1_id, user2_id))
    conn.commit()

    await message.answer(MESSAGES[lang]["divorce_success"].format(user1=user1_name, user2=user2_name))

async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Почати спілкування з ботом"),
        BotCommand(command="marry", description="Зробити пропозицію одружитись"),
        BotCommand(command="topcouples", description="Показати топ пар"),
        BotCommand(command="divorce", description="Розвезтись зі своєю половинкою"),
        BotCommand(command="commands", description="Показати список команд"),
    ]
    await bot.set_my_commands(commands)

async def main():
    await set_bot_commands()
    print("Бот запускається, тримайся 💍✨...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
