import asyncio
import logging
import os
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from flask import Flask, request, Response

API_TOKEN = "8232680735:AAG-GFL8ZOUla-OwP-0D5bDhnFpNaH6e-pU"
WEBHOOK_HOST = "https://love-bot-f0dj.onrender.com"  # заміни на свій https URL
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_PATH

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# --- База даних для кожного чату окремо ---
def get_conn(chat_id: int):
    db_name = f"db_{chat_id}.sqlite"
    need_init = not os.path.exists(db_name)
    conn = sqlite3.connect(db_name)
    if need_init:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS couples (
                user1_id INTEGER NOT NULL,
                user2_id INTEGER NOT NULL,
                wed_date TEXT NOT NULL,
                PRIMARY KEY (user1_id, user2_id)
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                lang TEXT DEFAULT 'uk'
            )
            """
        )
        conn.commit()
    return conn

# --- Повідомлення ---
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
        ),
        "proposal_sent": "Пропозицію відправлено!",
        "divorce_no_spouse": "Ви не одружені, щоб розвезтись.",
        "divorce_success": "💔 {user1} та {user2} тепер розведені. Нехай шлях буде світлим і новим!"
    }
}

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

def get_lang(user_id: int, chat_id: int):
    conn = get_conn(chat_id)
    c = conn.cursor()
    c.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "uk"

def set_lang(user_id: int, lang: str, chat_id: int):
    conn = get_conn(chat_id)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, lang) VALUES (?, ?)", (user_id, lang))
    conn.commit()
    conn.close()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    lang = get_lang(message.from_user.id, message.chat.id)
    await message.answer(MESSAGES[lang]["help_dm"])

@dp.message(Command("commands"))
async def cmd_commands(message: Message):
    lang = get_lang(message.from_user.id, message.chat.id)
    await message.answer(MESSAGES[lang]["commands_list"])

@dp.message(Command("propose"))
async def cmd_propose(message: Message):
    lang = get_lang(message.from_user.id, message.chat.id)
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
async def proposal_callback(call: CallbackQuery):
    data = call.data.split(":")
    action = data[0].split("_")[1]
    proposal_id = data[1]
    proposer_id = int(data[2])
    username = data[3]

    lang = get_lang(call.from_user.id, call.message.chat.id)
    proposer_accepted = (action == "accept")

    if call.from_user.username != username:
        await call.answer("Це не ваша пропозиція!", show_alert=True)
        return

    if proposal_id not in pending_proposals:
        await call.answer("Ця пропозиція вже оброблена.", show_alert=True)
        return

    conn = get_conn(call.message.chat.id)
    c = conn.cursor()

    if proposer_accepted:
        user1_id = min(proposer_id, call.from_user.id)
        user2_id = max(proposer_id, call.from_user.id)
        now_str = datetime.now().isoformat()
        try:
            c.execute('INSERT INTO couples (user1_id, user2_id, wed_date) VALUES (?, ?, ?)', (user1_id, user2_id, now_str))
            conn.commit()
        except sqlite3.IntegrityError:
            pass

        try:
            user1_chat = await bot.get_chat(user1_id)
            user2_chat = await bot.get_chat(user2_id)
            couple_name = f"[{user1_chat.first_name}](tg://user?id={user1_id}) і [{user2_chat.first_name}](tg://user?id={user2_id})"
        except Exception:
            couple_name = f"Користувачі {user1_id} і {user2_id}"

        text = MESSAGES[lang]["proposal_accepted"].format(couple=couple_name)
        await call.message.edit_text(text, parse_mode="Markdown")
        pending_proposals.pop(proposal_id, None)
    else:
        text = MESSAGES[lang]["proposal_declined"].format(target=call.from_user.full_name, proposer=f"@{pending_proposals[proposal_id][1]}")
        await call.message.edit_text(text)
        pending_proposals.pop(proposal_id, None)

    conn.close()
    await call.answer()

@dp.message(Command("marry"))
async def cmd_marry(message: Message):
    lang = get_lang(message.from_user.id, message.chat.id)
    author_id = message.from_user.id
    conn = get_conn(message.chat.id)
    c = conn.cursor()

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
    conn.close()

@dp.message(Command("topcouples"))
async def cmd_topcouples(message: Message):
    lang = get_lang(message.from_user.id, message.chat.id)
    conn = get_conn(message.chat.id)
    c = conn.cursor()

    c.execute("SELECT user1_id, user2_id, wed_date FROM couples")
    rows = c.fetchall()
    if not rows:
        await message.reply(MESSAGES[lang]["top_empty"])
        conn.close()
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
    conn.close()

@dp.message(Command("divorce"))
async def cmd_divorce(message: Message):
    lang = get_lang(message.from_user.id, message.chat.id)
    user_id = message.from_user.id
    conn = get_conn(message.chat.id)
    c = conn.cursor()

    c.execute("SELECT user1_id, user2_id FROM couples WHERE user1_id = ? OR user2_id = ?", (user_id, user_id))
    couple = c.fetchone()
    if not couple:
        await message.reply(MESSAGES[lang]["divorce_no_spouse"])
        conn.close()
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
    conn.close()

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    conn = get_conn(chat_id)
    c = conn.cursor()

    c.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    lang = row[0] if row else "uk"

    c.execute("SELECT user1_id, user2_id, wed_date FROM couples WHERE user1_id = ? OR user2_id = ?", (user_id, user_id))
    couple = c.fetchone()

    profile_text = f"👤 Профіль користувача: {message.from_user.full_name}\n"
    if couple:
        user1_id, user2_id, wed_date_str = couple
        wed_date = datetime.fromisoformat(wed_date_str)
        duration = format_duration(wed_date)
        partner_id = user2_id if user1_id == user_id else user1_id
        try:
            partner = await bot.get_chat(partner_id)
            partner_name = partner.first_name
            if partner.username:
                partner_name = f"@{partner.username}"
        except Exception:
            partner_name = "ваша половинка"
        profile_text += f"❤️ Ви у парі з {partner_name}\n"
        profile_text += f"⏳ Разом вже: {duration}\n"
    else:
        profile_text += "💔 Ви наразі не у парі.\n"

    await message.answer(profile_text)
    conn.close()

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

# --- Flask + webhook handler ---
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = request.get_json()
    if update is None:
        return Response(status=400)
    asyncio.create_task(dp.process_update(update))
    return Response(status=200)

async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    await set_bot_commands()
    logging.info("Webhook встановлено, бот готовий!")

async def on_shutdown():
    logging.info("Відключення бота...")
    await bot.delete_webhook()

if __name__ == "__main__":
    import ssl
    import sys
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:8443"]  # порт 8443 — як приклад
    # ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    # ssl_context.load_cert_chain("fullchain.pem", "privkey.pem")
    # config.ssl = ssl_context
    # Залиш для свого ssl сертифіката

    loop = asyncio.get_event_loop()
    loop.run_until_complete(on_startup())
    try:
        loop.run_until_complete(serve(app, config))
    except KeyboardInterrupt:
        loop.run_until_complete(on_shutdown())
