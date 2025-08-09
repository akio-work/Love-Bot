import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from flask import Flask
from threading import Thread

# ----------------- 1. KEEP ALIVE -----------------
app = Flask('')

@app.route('/')
def home():
    return "Бот працює 24/7 🔥"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# --------------------------------------------------

API_TOKEN = "8232680735:AAG-GFL8ZOUla-OwP-0D5bDhnFpNaH6e-pU"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

pending_proposals = {}  # proposal_id -> (proposer_id, proposee_username)

MESSAGES = {
    "uk": {
        "proposal_offer": "💌 {target}, вам роблять пропозицію руки і серця від {proposer}!\nНатисніть ✅ якщо згодні, або ❌ якщо ні.",
        "proposal_accepted": "🎉 {couple}, ви тепер заручені! Готуйтеся до великого свята! 💖",
        "proposal_declined": "🚫 {target} відмовив(ла) {proposer}.",
        "self_propose": "🙅‍♂️ Не можна пропонувати собі.",
        "not_engaged_for_marry": "😢 Ви ще не заручені, щоб почати весілля!",
        "wedding_in_progress": "⏳ Весілля вже триває, будь ласка, зачекайте.",
        "wedding_start": "💒 Розпочинаємо весільне гуляння для {couple}! 🎉",
        "wedding_finished": "🎊 Весілля {couple} завершено! Хай живе любов! ❤️",
        "top_empty": "🤷‍♂️ Поки що немає заручених пар.",
        "commands_list": (
            "📜 Ось що я вмію:\n"
            "/propose - зробити пропозицію руки і серця 💍\n"
            "/marry - почати весілля для заручених пар 👰🤵\n"
            "/topcouples - показати топ пар і скільки часу разом 🥇\n"
            "/spouse - показати з ким ви одружені 💑\n"
            "/divorce - розвезтись зі своєю половинкою 💔\n"
            "/profile - подивитись свій профіль 🕵️‍♂️\n"
            "/commands - показати цей список команд 📋\n"
        ),
        "help_dm": (
            "Вітання! Ось що я вмію:\n"
            "/propose — зробити пропозицію 💌\n"
            "/marry — почати весілля 👰🤵\n"
            "/topcouples — показати топ пар 🥇\n"
            "/spouse — показати з ким ви одружені 💑\n"
            "/divorce — розвезтись 💔\n"
            "/profile — подивитись свій профіль 🕵️‍♂️\n"
            "/commands — список команд 📋\n"
            "\nТех. підтримка: @KR_LVXH"
        ),
        "proposal_sent": "✅ Пропозицію відправлено!",
        "no_spouse": "😢 Ви ще не одружені.",
        "your_spouse": "💖 Ви одружені з {partner}.",
        "divorce_no_spouse": "❌ Ви не одружені, щоб розвезтись.",
        "divorce_success": "💔 {user1} та {user2} тепер розведені. Нехай шлях буде світлим і новим!",
        "profile_no_marriage": "🕵️‍♂️ Профіль доступний лише одруженим. Спершу одружіться через /marry.",
        "profile_header": "📇 Ваш профіль:\n",
        "profile_status": "Статус: {status}\n",
        "profile_married_to": "Одружений(а) з: {partner}\n",
        "profile_married_since": "Одружені з: {since}\n"
    }
}

def get_db(chat_id: int):
    db_name = f"db_group_{chat_id}.db"
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    # Створюємо таблицю пар, якщо нема
    c.execute("""
    CREATE TABLE IF NOT EXISTS couples (
        user1_id INTEGER NOT NULL,
        user2_id INTEGER NOT NULL,
        wed_date TEXT NOT NULL,
        PRIMARY KEY (user1_id, user2_id)
    )
    """)

    # Створюємо таблицю юзерів, якщо нема
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        lang TEXT DEFAULT 'uk'
    )
    """)

    # Перевіряємо, чи є колонка status, якщо нема — додаємо
    c.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in c.fetchall()]
    if "status" not in columns:
        c.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'Вільний(а)'")

    conn.commit()
    return conn

def get_lang_status(cursor, user_id: int):
    cursor.execute("SELECT lang, status FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        lang = row[0] if row[0] else "uk"
        status = row[1] if row[1] else "Вільний(а)"
        return lang, status
    return "uk", "Вільний(а)"

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
    conn = get_db(message.chat.id)
    c = conn.cursor()
    lang, _ = get_lang_status(c, message.from_user.id)
    await message.answer(MESSAGES[lang]["help_dm"])
    conn.close()

@dp.message(Command("commands"))
async def cmd_commands(message: Message):
    conn = get_db(message.chat.id)
    c = conn.cursor()
    lang, _ = get_lang_status(c, message.from_user.id)
    await message.answer(MESSAGES[lang]["commands_list"])
    conn.close()

@dp.message(Command("propose"))
async def cmd_propose(message: Message):
    conn = get_db(message.chat.id)
    c = conn.cursor()
    lang, _ = get_lang_status(c, message.from_user.id)

    if not message.text:
        await message.reply("Будь ласка, введи команду разом з аргументами.")
        conn.close()
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Вкажи користувача через @username, щоб зробити пропозицію.")
        conn.close()
        return

    username = parts[1].lstrip("@").strip()
    if username.lower() == (message.from_user.username or "").lower():
        await message.reply(MESSAGES[lang]["self_propose"])
        conn.close()
        return

    proposal_id = f"{message.chat.id}_{message.message_id}"
    proposer = message.from_user

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅", callback_data=f"proposal_accept:{proposal_id}:{proposer.id}:{username}"),
            InlineKeyboardButton(text="❌", callback_data=f"proposal_decline:{proposal_id}:{proposer.id}:{username}")
        ]
    ])

    text = MESSAGES[lang]["proposal_offer"].format(target=f"@{username}", proposer=proposer.full_name)
    await message.answer(text, reply_markup=kb)
    pending_proposals[proposal_id] = (proposer.id, username)
    await message.reply(MESSAGES[lang]["proposal_sent"])
    conn.close()

@dp.callback_query(lambda c: c.data and c.data.startswith("proposal_"))
async def proposal_callback(call: CallbackQuery):
    data = call.data.split(":")
    action = data[0].split("_")[1]
    proposal_id = data[1]
    proposer_id = int(data[2])
    username = data[3]

    conn = get_db(call.message.chat.id)
    c = conn.cursor()
    lang, _ = get_lang_status(c, call.from_user.id)

    if call.from_user.username != username:
        await call.answer("Це не ваша пропозиція!", show_alert=True)
        conn.close()
        return

    if proposal_id not in pending_proposals:
        await call.answer("Ця пропозиція вже оброблена.", show_alert=True)
        conn.close()
        return

    if action == "accept":
        user1_id = min(proposer_id, call.from_user.id)
        user2_id = max(proposer_id, call.from_user.id)
        now_str = datetime.now().isoformat()
        try:
            c.execute('INSERT INTO couples (user1_id, user2_id, wed_date) VALUES (?, ?, ?)', (user1_id, user2_id, now_str))
            c.execute("INSERT OR REPLACE INTO users (user_id, lang, status) VALUES (?, COALESCE((SELECT lang FROM users WHERE user_id=?), 'uk'), ?)", (user1_id, user1_id, "Заручений(а)"))
            c.execute("INSERT OR REPLACE INTO users (user_id, lang, status) VALUES (?, COALESCE((SELECT lang FROM users WHERE user_id=?), 'uk'), ?)", (user2_id, user2_id, "Заручений(а)"))
            conn.commit()
        except sqlite3.IntegrityError:
            pass

        proposer_name = await get_user_name(call.message.chat.id, proposer_id)
        target_name = await get_user_name(call.message.chat.id, call.from_user.id)
        couple_name = f"[{target_name}](tg://user?id={call.from_user.id}) і [{proposer_name}](tg://user?id={proposer_id})"
        text = MESSAGES[lang]["proposal_accepted"].format(couple=couple_name)
        await call.message.edit_text(text, parse_mode="Markdown")
        pending_proposals.pop(proposal_id, None)
    else:
        proposer_name = await get_user_name(call.message.chat.id, proposer_id)
        text = MESSAGES[lang]["proposal_declined"].format(target=call.from_user.full_name, proposer=proposer_name)
        await call.message.edit_text(text)
        pending_proposals.pop(proposal_id, None)

    await call.answer()
    conn.close()

@dp.message(Command("marry"))
async def cmd_marry(message: Message):
    conn = get_db(message.chat.id)
    c = conn.cursor()
    lang, _ = get_lang_status(c, message.from_user.id)
    author_id = message.from_user.id

    c.execute('SELECT user1_id, user2_id, wed_date FROM couples WHERE user1_id = ? OR user2_id = ?', (author_id, author_id))
    result = c.fetchone()

    if not result:
        await message.reply(MESSAGES[lang]["not_engaged_for_marry"])
        conn.close()
        return

    if getattr(dp, "marriage_active", False):
        await message.reply(MESSAGES[lang]["wedding_in_progress"])
        conn.close()
        return

    dp.marriage_active = True
    user1_id, user2_id, wed_date = result

    user1_name = await get_user_name(message.chat.id, user1_id)
    user2_name = await get_user_name(message.chat.id, user2_id)
    couple_name = f"[{user1_name}](tg://user?id={user1_id}) і [{user2_name}](tg://user?id={user2_id})"

    await message.answer(MESSAGES[lang]["wedding_start"].format(couple=couple_name), parse_mode="Markdown")

    wedding_messages = [
        "🎶 Звучить весільний марш... 🎶",
        f"Друзі та родина зібралися, щоб привітати {couple_name}!",
        "Нехай ваше життя буде сповнене любові та щастя! 🌹",
        "Піднімемо келихи за молодят! 🥂",
        "Танці, сміх і радість заповнюють цей день! 💃🕺",
        "Нехай цей день запам’ятається назавжди! 🎆"
    ]

    for msg_text in wedding_messages:
        await message.answer(msg_text, parse_mode="Markdown")
        await asyncio.sleep(4)

    c.execute("UPDATE users SET status = 'Одружений(а)' WHERE user_id IN (?, ?)", (user1_id, user2_id))
    conn.commit()

    dp.marriage_active = False
    await message.answer(MESSAGES[lang]["wedding_finished"].format(couple=couple_name), parse_mode="Markdown")
    conn.close()

@dp.message(Command("topcouples"))
async def cmd_topcouples(message: Message):
    conn = get_db(message.chat.id)
    c = conn.cursor()
    lang, _ = get_lang_status(c, message.from_user.id)

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

@dp.message(Command("spouse"))
async def cmd_spouse(message: Message):
    conn = get_db(message.chat.id)
    c = conn.cursor()
    lang, _ = get_lang_status(c, message.from_user.id)
    user_id = message.from_user.id

    c.execute('SELECT user1_id, user2_id FROM couples WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
    row = c.fetchone()

    if not row:
        await message.answer(MESSAGES[lang]["no_spouse"])
        conn.close()
        return

    spouse_id = row[1] if row[0] == user_id else row[0]
    spouse_name = await get_user_name(message.chat.id, spouse_id)

    await message.answer(MESSAGES[lang]["your_spouse"].format(partner=spouse_name))
    conn.close()

@dp.message(Command("divorce"))
async def cmd_divorce(message: Message):
    conn = get_db(message.chat.id)
    c = conn.cursor()
    lang, _ = get_lang_status(c, message.from_user.id)
    user_id = message.from_user.id

    c.execute('SELECT user1_id, user2_id FROM couples WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
    row = c.fetchone()

    if not row:
        await message.answer(MESSAGES[lang]["divorce_no_spouse"])
        conn.close()
        return

    user1_id, user2_id = row
    c.execute('DELETE FROM couples WHERE user1_id = ? AND user2_id = ?', (user1_id, user2_id))
    c.execute("UPDATE users SET status = 'Вільний(а)' WHERE user_id IN (?, ?)", (user1_id, user2_id))
    conn.commit()

    user1_name = await get_user_name(message.chat.id, user1_id)
    user2_name = await get_user_name(message.chat.id, user2_id)

    await message.answer(MESSAGES[lang]["divorce_success"].format(user1=user1_name, user2=user2_name))
    conn.close()

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    conn = get_db(message.chat.id)
    c = conn.cursor()
    lang, status = get_lang_status(c, message.from_user.id)
    user_id = message.from_user.id

    if status != "Одружений(а)":
        await message.answer(MESSAGES[lang]["profile_no_marriage"])
        conn.close()
        return

    c.execute('SELECT user1_id, user2_id, wed_date FROM couples WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
    row = c.fetchone()
    if not row:
        await message.answer(MESSAGES[lang]["no_spouse"])
        conn.close()
        return

    user1_id, user2_id, wed_date_str = row
    spouse_id = user2_id if user1_id == user_id else user1_id
    spouse_name = await get_user_name(message.chat.id, spouse_id)
    wed_date = datetime.fromisoformat(wed_date_str)
    wed_since = wed_date.strftime("%d.%m.%Y")

    text = (
        MESSAGES[lang]["profile_header"] +
        f"🆔 ID: {user_id}\n" +
        MESSAGES[lang]["profile_status"].format(status=status) +
        MESSAGES[lang]["profile_married_to"].format(partner=spouse_name) +
        MESSAGES[lang]["profile_married_since"].format(since=wed_since)
    )

    await message.answer(text)
    conn.close()

async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Стартувати бота"),
        BotCommand(command="commands", description="Показати команди"),
        BotCommand(command="propose", description="Зробити пропозицію руки і серця"),
        BotCommand(command="marry", description="Почати весілля"),
        BotCommand(command="topcouples", description="Топ заручених пар"),
        BotCommand(command="spouse", description="Показати свою половинку"),
        BotCommand(command="divorce", description="Розвезтись"),
        BotCommand(command="profile", description="Подивитись профіль"),
    ]
    await bot.set_my_commands(commands)

async def main():
    await set_bot_commands()
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive()  # Запускаємо вебсервер для підтримки живучості на Replit
    asyncio.run(main())
