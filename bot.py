import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand

API_TOKEN = "8232680735:AAG-GFL8ZOUla-OwP-0D5bDhnFpNaH6e-pU"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

pending_proposals = {}

MESSAGES = {
    "uk": {
        "marry_offer": "💌 {target}, тобі роблять пропозицію одружитися від {proposer}!\nНатисни ✅ щоб погодитися, або ❌ щоб відмовити.",
        "marry_accepted": "🎉 {couple}, ви тепер заручені! Готуйтеся до свята! 💖",
        "marry_declined": "🚫 {target} відмовив {proposer}.",
        "self_marry": "🙅‍♂️ Не можна одружуватися з собою.",
        "not_engaged_for_wedding": "😢 Ви ще не заручені, щоб почати весілля.",
        "wedding_in_progress": "⏳ Весілля вже триває, зачекайте.",
        "wedding_start": "💒 Розпочинаємо весільне гуляння для {couple}! 🎉",
        "wedding_finished": "🎊 Весілля {couple} завершено! Хай живе любов! ❤️",
        "top_empty": "🤷‍♂️ Поки що немає заручених пар.",
        "commands_list": (
            "📜 Ось мої команди:\n"
            "/marry — зробити пропозицію 💍\n"
            "/topcouples — показати топ пар 🥇\n"
            "/divorce — розвезтися 💔\n"
            "/profile — подивитися профіль 🕵️‍♂️\n"
            "/commands — показати список 📋\n"
        ),
        "help_dm": (
            "Вітання! Ось що я вмію:\n"
            "/marry — зробити пропозицію 💍\n"
            "/topcouples — показати топ пар 🥇\n"
            "/divorce — розвезтися 💔\n"
            "/profile — подивитися профіль 🕵️‍♂️\n"
            "/commands — список команд 📋\n"
            "\nТех. підтримка: @KR_LVXH"
        ),
        "marry_sent": "✅ Пропозицію надіслано!",
        "no_spouse": "😢 Ви не одружені.",
        "divorce_no_spouse": "❌ Ви не одружені, щоб розвезтися.",
        "divorce_success": "💔 {user1} та {user2} тепер розведені. Хай шлях буде світлим!",
        "profile_header": "📇 Ваш профіль:\n",
        "profile_joined": "🕰 У групі з: {joined}\n",
        "profile_nick": "🔹 Нікнейм: @{username}\n",
        "profile_partner": "💑 Одружені з: {partner}\n",
        "profile_active": "⚡ Активність: {active}\n",
    }
}

def get_db(chat_id: int):
    db_name = f"db_group_{chat_id}.db"
    conn = sqlite3.connect(db_name, check_same_thread=False)
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
        lang TEXT DEFAULT 'uk',
        joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
        active INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    return conn

def get_lang(cursor, user_id: int):
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else "uk"

async def get_user_name(chat_id: int, user_id: int):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.user.full_name
    except:
        return f"Користувач {user_id}"

async def get_user_username(chat_id: int, user_id: int):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.user.username or "немає"
    except:
        return "немає"

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
    conn = get_db(message.chat.id)
    c = conn.cursor()
    lang = get_lang(c, message.from_user.id)
    await message.answer(MESSAGES[lang]["help_dm"])
    conn.close()

@dp.message(Command("commands"))
async def cmd_commands(message: Message):
    conn = get_db(message.chat.id)
    c = conn.cursor()
    lang = get_lang(c, message.from_user.id)
    await message.answer(MESSAGES[lang]["commands_list"])
    conn.close()

@dp.message(Command("marry"))
async def cmd_marry(message: Message):
    conn = get_db(message.chat.id)
    c = conn.cursor()
    lang = get_lang(c, message.from_user.id)

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Вкажи користувача через @username для пропозиції.")
        conn.close()
        return

    username = parts[1].lstrip("@").strip()
    proposer = message.from_user

    if username.lower() == (proposer.username or "").lower():
        await message.reply(MESSAGES[lang]["self_marry"])
        conn.close()
        return

    proposal_id = f"{message.chat.id}_{message.message_id}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅", callback_data=f"marry_accept:{proposal_id}:{proposer.id}:{username}"),
            InlineKeyboardButton(text="❌", callback_data=f"marry_decline:{proposal_id}:{proposer.id}:{username}")
        ]
    ])

    text = MESSAGES[lang]["marry_offer"].format(target=f"@{username}", proposer=proposer.full_name)
    await message.answer(text, reply_markup=kb)
    pending_proposals[proposal_id] = (proposer.id, username)
    await message.reply(MESSAGES[lang]["marry_sent"])
    conn.close()

@dp.callback_query(lambda c: c.data and c.data.startswith("marry_"))
async def marry_callback(call: CallbackQuery):
    data = call.data.split(":")
    action = data[0].split("_")[1]
    proposal_id = data[1]
    proposer_id = int(data[2])
    username = data[3]

    conn = get_db(call.message.chat.id)
    c = conn.cursor()
    lang = get_lang(c, call.from_user.id)

    if call.from_user.username != username:
        await call.answer("Це не твоя пропозиція!", show_alert=True)
        conn.close()
        return

    if proposal_id not in pending_proposals:
        await call.answer("Пропозицію вже оброблено.", show_alert=True)
        conn.close()
        return

    if action == "accept":
        user1_id = min(proposer_id, call.from_user.id)
        user2_id = max(proposer_id, call.from_user.id)
        now_str = datetime.now().isoformat()
        try:
            c.execute('INSERT INTO couples (user1_id, user2_id, wed_date) VALUES (?, ?, ?)', (user1_id, user2_id, now_str))
            c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user1_id,))
            c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user2_id,))
            conn.commit()
        except sqlite3.IntegrityError:
            pass

        proposer_name = await get_user_name(call.message.chat.id, proposer_id)
        target_name = await get_user_name(call.message.chat.id, call.from_user.id)
        couple_name = f"[{target_name}](tg://user?id={call.from_user.id}) і [{proposer_name}](tg://user?id={proposer_id})"

        text = MESSAGES[lang]["marry_accepted"].format(couple=couple_name)
        await call.message.edit_text(text, parse_mode="Markdown")
        pending_proposals.pop(proposal_id, None)

        async def wedding_text():
            await asyncio.sleep(5)
            await call.message.answer(
                "🎶 Весільний марш звучить ніжно...\n"
                f"🎉 Родина і друзі вітають {couple_name}!\n"
                "Нехай буде життя сповнене щастям і любов’ю! 🌹\n"
                "Піднімемо келихи за молодят! 🥂\n"
                "Хай цей день запам’ятається назавжди! 🎆"
            )
        asyncio.create_task(wedding_text())

    else:
        proposer_name = await get_user_name(call.message.chat.id, proposer_id)
        text = MESSAGES[lang]["marry_declined"].format(target=call.from_user.full_name, proposer=proposer_name)
        await call.message.edit_text(text)
        pending_proposals.pop(proposal_id, None)

    await call.answer()
    conn.close()

@dp.message(Command("divorce"))
async def cmd_divorce(message: Message):
    conn = get_db(message.chat.id)
    c = conn.cursor()
    lang = get_lang(c, message.from_user.id)
    user_id = message.from_user.id

    c.execute('SELECT user1_id, user2_id FROM couples WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
    row = c.fetchone()

    if not row:
        await message.answer(MESSAGES[lang]["divorce_no_spouse"])
        conn.close()
        return

    user1_id, user2_id = row
    c.execute('DELETE FROM couples WHERE user1_id = ? AND user2_id = ?', (user1_id, user2_id))
    conn.commit()

    user1_name = await get_user_name(message.chat.id, user1_id)
    user2_name = await get_user_name(message.chat.id, user2_id)

    await message.answer(MESSAGES[lang]["divorce_success"].format(user1=user1_name, user2=user2_name))
    conn.close()

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    conn = get_db(message.chat.id)
    c = conn.cursor()
    lang = get_lang(c, message.from_user.id)
    user_id = message.from_user.id

    c.execute('SELECT user1_id, user2_id, wed_date FROM couples WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
    row = c.fetchone()

    if not row:
        await message.answer(MESSAGES[lang]["no_spouse"])
        conn.close()
        return

    user1_id, user2_id, wed_date_str = row
    wed_date = datetime.fromisoformat(wed_date_str)
    spouse_id = user2_id if user1_id == user_id else user1_id
    spouse_name = await get_user_name(message.chat.id, spouse_id)
    username = await get_user_username(message.chat.id, user_id)

    c.execute("SELECT joined_at FROM users WHERE user_id = ?", (user_id,))
    joined_row = c.fetchone()
    if joined_row and joined_row[0]:
        joined_date = datetime.fromisoformat(joined_row[0])
        active_duration = format_duration(joined_date)
    else:
        active_duration = "невідомо"

    profile_text = (
        MESSAGES[lang]["profile_header"] +
        MESSAGES[lang]["profile_joined"].format(joined=joined_date.strftime("%d.%m.%Y") if joined_row else "невідомо") +
        MESSAGES[lang]["profile_nick"].format(username=username) +
        MESSAGES[lang]["profile_partner"].format(partner=spouse_name) +
        MESSAGES[lang]["profile_active"].format(active=active_duration)
    )

    await message.answer(profile_text)
    conn.close()

@dp.message(Command("topcouples"))
async def cmd_topcouples(message: Message):
    conn = get_db(message.chat.id)
    c = conn.cursor()
    lang = get_lang(c, message.from_user.id)

    c.execute('SELECT user1_id, user2_id, wed_date FROM couples')
    rows = c.fetchall()

    if not rows:
        await message.answer(MESSAGES[lang]["top_empty"])
        conn.close()
        return

    result_text = "🔥 Топ заручених пар:\n\n"

    for user1_id, user2_id, wed_date_str in rows:
        wed_date = datetime.fromisoformat(wed_date_str)
        duration = format_duration(wed_date)
        user1_name = await get_user_name(message.chat.id, user1_id)
        user2_name = await get_user_name(message.chat.id, user2_id)
        couple_name = f"{user1_name} ❤️ {user2_name}"
        result_text += f"{couple_name} — разом вже {duration}\n"

    await message.answer(result_text)
    conn.close()

async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Стартувати бота"),
        BotCommand(command="commands", description="Показати команди"),
        BotCommand(command="marry", description="Зробити пропозицію"),
        BotCommand(command="divorce", description="Розвезтися"),
        BotCommand(command="topcouples", description="Топ заручених пар"),
        BotCommand(command="profile", description="Подивитись профіль"),
    ]
    await bot.set_my_commands(commands)

async def main():
    await set_bot_commands()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
