import asyncio
from datetime import datetime
import sqlite3

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from flask import Flask, request, Response

API_TOKEN = "8232680735:AAG-GFL8ZOUla-OwP-0D5bDhnFpNaH6e-pU"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot=bot)

app = Flask(__name__)

# --- SQLite база ---
conn = sqlite3.connect("wedding_bot.db", check_same_thread=False)
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

MESSAGES = {
    "uk": {
        "proposal_offer": "{target}, вам роблять пропозицію руки і серця від {proposer}!\nНатисніть ✅ якщо згодні, або ❌ якщо ні.",
        "proposal_accepted": "🎉 {couple}, ви тепер заручені! Готуйтеся до великого свята! 💖",
        "proposal_declined": "{target} відмовив(ла) {proposer}.",
        "self_propose": "Не можна пропонувати собі.",
        "not_engaged_for_marry": "Ви ще не заручені, щоб почати весілля!",
        "wedding_in_progress": "Весілля вже триває, будь ласка, зачекайте.",
        "wedding_start": "💒 Розпочинаємо весільне гуляння для {couple}! 🎉",
        "wedding_finished": "Весілля {couple} завершено! Хай живе любов! ❤️",
        "top_empty": "Поки що немає заручених пар.",
        "commands_list": (
            "/propose - зробити пропозицію руки і серця\n"
            "/marry - почати весілля для заручених пар\n"
            "/topcouples - показати топ пар і скільки часу разом\n"
            "/divorce - розвезтись зі своєю половинкою\n"
            "/commands - показати цей список команд\n"
            "/profile - показати свій профіль\n"
        ),
        "help_dm": (
            "Вітання! Ось що я вмію:\n"
            "/propose — зробити пропозицію\n"
            "/marry — почати весілля\n"
            "/topcouples — показати топ пар\n"
            "/divorce — розвезтись зі своєю половинкою\n"
            "/commands — показати список команд\n"
            "/profile — показати свій профіль\n"
            "\nТех. підтримка: @KR_LVXH"
        ),
        "proposal_sent": "Пропозицію відправлено!",
        "divorce_no_spouse": "Ви не одружені, щоб розвезтись.",
        "divorce_success": "💔 {user1} та {user2} тепер розведені. Нехай шлях буде світлим і новим!",
        "profile_info": "👤 Профіль користувача:\nІм'я: {name}\nID: {id}\nМова: {lang}\nОдружений: {married}",
        "not_married": "Наразі ви не одружені."
    }
}

def get_lang(user_id: int):
    c.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    return row[0] if row else "uk"

def set_lang(user_id: int, lang: str):
    c.execute("INSERT OR REPLACE INTO users (user_id, lang) VALUES (?, ?)", (user_id, lang))
    conn.commit()

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

pending_proposals = {}

# --- Хендлери ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    lang = get_lang(message.from_user.id)
    await message.answer(MESSAGES[lang]["help_dm"])

@dp.message(Command("commands"))
async def cmd_commands(message: types.Message):
    lang = get_lang(message.from_user.id)
    await message.answer(MESSAGES[lang]["commands_list"])

@dp.message(Command("propose"))
async def cmd_propose(message: types.Message):
    lang = get_lang(message.from_user.id)
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Вкажи користувача, якому робиш пропозицію, через @username")
        return

    username = parts[1].lstrip("@").strip()
    if username.lower() == (message.from_user.username or "").lower():
        await message.reply(MESSAGES[lang]["self_propose"])
        return

    proposal_id = f"{message.chat.id}_{message.message_id}"
    proposer = message.from_user
    proposee_mention = f"@{username}"

    text = MESSAGES[lang]["proposal_offer"].format(target=proposee_mention, proposer=proposer.full_name)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅", callback_data=f"proposal_accept:{proposal_id}:{proposer.id}:{username}"),
            InlineKeyboardButton(text="❌", callback_data=f"proposal_decline:{proposal_id}:{proposer.id}:{username}")
        ]
    ])
    await message.answer(text, reply_markup=kb)
    pending_proposals[proposal_id] = (proposer.id, username)
    await message.reply(MESSAGES[lang]["proposal_sent"])

@dp.callback_query(lambda c: c.data and c.data.startswith("proposal_"))
async def proposal_callback(call: types.CallbackQuery):
    data = call.data.split(":")
    action = data[0].split("_")[1]
    proposal_id = data[1]
    proposer_id = int(data[2])
    username = data[3]

    lang = get_lang(call.from_user.id)
    proposer_accepted = (action == "accept")

    if call.from_user.username != username:
        await call.answer("Це не ваша пропозиція!", show_alert=True)
        return

    if proposal_id not in pending_proposals:
        await call.answer("Ця пропозиція вже оброблена.", show_alert=True)
        return

    if proposer_accepted:
        user1_id = min(proposer_id, call.from_user.id)
        user2_id = max(proposer_id, call.from_user.id)
        now_str = datetime.now().isoformat()
        try:
            c.execute('INSERT INTO couples (user1_id, user2_id, wed_date) VALUES (?, ?, ?)', (user1_id, user2_id, now_str))
            conn.commit()
        except sqlite3.IntegrityError:
            pass

        user1_chat = await bot.get_chat(user1_id)
        user2_chat = await bot.get_chat(user2_id)
        couple_name = f"[{user1_chat.first_name}](tg://user?id={user1_id}) і [{user2_chat.first_name}](tg://user?id={user2_id})"

        text = MESSAGES[lang]["proposal_accepted"].format(couple=couple_name)
        await call.message.edit_text(text, parse_mode="Markdown")
        pending_proposals.pop(proposal_id, None)
    else:
        text = MESSAGES[lang]["proposal_declined"].format(target=call.from_user.full_name, proposer=f"@{pending_proposals[proposal_id][1]}")
        await call.message.edit_text(text)
        pending_proposals.pop(proposal_id, None)

    await call.answer()

@dp.message(Command("marry"))
async def cmd_marry(message: types.Message):
    lang = get_lang(message.from_user.id)
    author_id = message.from_user.id

    c.execute('SELECT user1_id, user2_id, wed_date FROM couples WHERE user1_id = ? OR user2_id = ?', (author_id, author_id))
    result = c.fetchone()

    if not result:
        await message.reply(MESSAGES[lang]["not_engaged_for_marry"])
        return

    if getattr(dp, "marriage_active", False):
        await message.reply(MESSAGES[lang]["wedding_in_progress"])
        return

    dp.marriage_active = True
    user1_id, user2_id, wed_date = result

    try:
        user1 = await bot.get_chat(user1_id)
        user2 = await bot.get_chat(user2_id)
        couple_name = f"[{user1.first_name}](tg://user?id={user1_id}) і [{user2.first_name}](tg://user?id={user2_id})"
    except Exception:
        couple_name = f"Користувачі {user1_id} і {user2_id}"

    await message.answer(MESSAGES[lang]["wedding_start"].format(couple=couple_name), parse_mode="Markdown")

    wedding_messages = [
        "🎶 Звучить весільний марш... 🎶",
        f"Друзі та родина зібралися, щоб привітати {couple_name}!",
        "Нехай ваше життя буде сповнене любові та щастя!",
        "Піднімемо келихи за молодят! 🥂",
        "Танці, сміх і радість заповнюють цей день! 💃🕺",
        "Нехай цей день запам’ятається назавжди! 🎆"
    ]

    for msg_text in wedding_messages:
        await message.answer(msg_text, parse_mode="Markdown")
        await asyncio.sleep(4)

    dp.marriage_active = False
    await message.answer(MESSAGES[lang]["wedding_finished"].format(couple=couple_name), parse_mode="Markdown")

@dp.message(Command("topcouples"))
async def cmd_topcouples(message: types.Message):
    lang = get_lang(message.from_user.id)
    c.execute("SELECT user1_id, user2_id, wed_date FROM couples")
    rows = c.fetchall()

    if not rows:
        await message.reply(MESSAGES[lang]["top_empty"])
        return

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

    text_lines = ["🌹 Топ закоханих пар:"]
    for name, _, duration in couples_info:
        text_lines.append(f"💑 {name} — разом вже {duration}")

    await message.answer("\n".join(text_lines))

@dp.message(Command("divorce"))
async def cmd_divorce(message: types.Message):
    lang = get_lang(message.from_user.id)
    user_id = message.from_user.id

    c.execute("SELECT user1_id, user2_id FROM couples WHERE user1_id = ? OR user2_id = ?", (user_id, user_id))
    couple = c.fetchone()

    if not couple:
        await message.reply(MESSAGES[lang]["divorce_no_spouse"])
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

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    lang = get_lang(message.from_user.id)
    user_id = message.from_user.id
    user_name = message.from_user.full_name

    c.execute("SELECT user1_id, user2_id FROM couples WHERE user1_id = ? OR user2_id = ?", (user_id, user_id))
    couple = c.fetchone()

    if couple:
        partner_id = couple[1] if couple[0] == user_id else couple[0]
        try:
            partner = await bot.get_chat(partner_id)
            married = f"Одружений з {partner.full_name}"
        except Exception:
            married = "Одружений"
    else:
        married = MESSAGES[lang]["not_married"]

    text = MESSAGES[lang]["profile_info"].format(
        name=user_name,
        id=user_id,
        lang=lang,
        married=married
    )
    await message.answer(text)

# --- Встановлення команд ---
async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Почати спілкування з ботом"),
        BotCommand(command="propose", description="Зробити пропозицію руки і серця"),
        BotCommand(command="marry", description="Почати весілля для заручених пар"),
        BotCommand(command="topcouples", description="Показати топ пар"),
        BotCommand(command="divorce", description="Розвезтись зі своєю половинкою"),
        BotCommand(command="commands", description="Показати список команд"),
        BotCommand(command="profile", description="Показати свій профіль"),
    ]
    await bot.set_my_commands(commands)

# --- Вебхук --- 

@app.route(f"/webhook/{API_TOKEN}", methods=["POST"])
async def webhook():
    json_update = await request.get_json()
    update = types.Update(**json_update)
    await dp.feed_update(update)
    return Response("OK", status=200)

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(set_bot_commands())
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:8443"]

    print("Бот запускається, тримайся 💍✨...")
    loop.run_until_complete(serve(app, config))
