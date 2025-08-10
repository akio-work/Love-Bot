import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

API_TOKEN = "8232680735:AAG-GFL8ZOUla-OwP-0D5bDhnFpNaH6e-pU"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot=bot)

# --- SQLite ---
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
conn.commit()

MESSAGES = {
    "uk": {
        "marry_offer": "{target}, надсилається пропозиція одружитися від {proposer}!\nНатисни ✅ щоб прийняти, або ❌ щоб відхилити.",
        "marry_accepted": "🎉 {couple}, ви тепер одружені! Вітаємо! 💖",
        "marry_declined": "{target} відмовив(ла) {proposer}.",
        "self_marry": "Не можна одружуватися з собою.",
        "marry_sent": "Пропозицію надіслано!",
        "no_partner": "Вкажи користувача через @username.",
        "not_married": "Поки що не одружені.",
        "divorce_no_spouse": "Ти не одружений, щоб розвезтись.",
        "divorce_success": "💔 {user1} та {user2} тепер розведені. Нехай шлях буде світлим і новим!",
        "commands_list": (
            "/marry - зробити пропозицію одружитися через @username\n"
            "/divorce - розвезтись\n"
            "/topcouples - показати топ пар\n"
            "/commands - показати список команд\n"
        ),
        "help_dm": (
            "Вітання! Ось що я вмію:\n"
            "/marry — зробити пропозицію одружитися\n"
            "/divorce — розвезтись\n"
            "/topcouples — показати топ пар\n"
            "/commands — показати список команд\n"
            "\nТех. підтримка: @KR_LVXH"
        ),
        "top_empty": "Поки що немає пар."
    }
}

def get_lang(user_id: int):
    # просто повертаємо "uk" — щоб не морочитись
    return "uk"

pending_marry = {}

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
        await message.reply(MESSAGES[lang]["no_partner"])
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
    pending_marry[proposal_id] = (proposer.id, username)
    await message.reply(MESSAGES[lang]["marry_sent"])

@dp.callback_query(lambda c: c.data and c.data.startswith("marry_"))
async def marry_callback(call: CallbackQuery):
    data = call.data.split(":")
    action = data[0].split("_")[1]
    proposal_id = data[1]
    proposer_id = int(data[2])
    username = data[3]

    lang = get_lang(call.from_user.id)
    accepted = (action == "accept")

    # Захист, щоб не міг натискати не той, кому адресовано
    if call.from_user.username is None or call.from_user.username.lower() != username.lower():
        await call.answer("Це не твоя пропозиція!", show_alert=True)
        return

    if proposal_id not in pending_marry:
        await call.answer("Цю пропозицію вже оброблено.", show_alert=True)
        return

    if accepted:
        user1_id = min(proposer_id, call.from_user.id)
        user2_id = max(proposer_id, call.from_user.id)
        now_str = datetime.now().isoformat()
        try:
            c.execute("INSERT INTO couples (user1_id, user2_id, wed_date) VALUES (?, ?, ?)", (user1_id, user2_id, now_str))
            conn.commit()
        except sqlite3.IntegrityError:
            pass

        user1_chat = await bot.get_chat(user1_id)
        user2_chat = await bot.get_chat(user2_id)
        couple_name = f"[{user1_chat.first_name}](tg://user?id={user1_id}) і [{user2_chat.first_name}](tg://user?id={user2_id})"

        text = MESSAGES[lang]["marry_accepted"].format(couple=couple_name)
        await call.message.edit_text(text, parse_mode="Markdown")
    else:
        text = MESSAGES[lang]["marry_declined"].format(target=call.from_user.full_name, proposer=f"@{pending_marry[proposal_id][1]}")
        await call.message.edit_text(text)

    pending_marry.pop(proposal_id, None)
    await call.answer()

@dp.message(Command("divorce"))
async def cmd_divorce(message: Message):
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

@dp.message(Command("topcouples"))
async def cmd_topcouples(message: Message):
    lang = get_lang(message.from_user.id)
    c.execute("SELECT user1_id, user2_id, wed_date FROM couples")
    rows = c.fetchall()

    if not rows:
        await message.reply(MESSAGES[lang]["top_empty"])
        return

    lines = []
    for user1_id, user2_id, wed_date_str in rows:
        try:
            user1 = await bot.get_chat(user1_id)
            user2 = await bot.get_chat(user2_id)
            lines.append(f"💑 {user1.first_name} і {user2.first_name}")
        except Exception:
            lines.append(f"💑 Пара {user1_id} і {user2_id}")

    await message.answer("🌹 Топ закоханих пар:\n" + "\n".join(lines))

async def set_bot_commands():
    from aiogram.types import BotCommand
    commands = [
        BotCommand(command="start", description="Почати спілкування з ботом"),
        BotCommand(command="marry", description="Зробити пропозицію одружитися"),
        BotCommand(command="divorce", description="Розвезтись"),
        BotCommand(command="topcouples", description="Показати топ пар"),
        BotCommand(command="commands", description="Показати список команд"),
    ]
    await bot.set_my_commands(commands)

async def main():
    await set_bot_commands()
    print("Бот запускається, тримайся 💍✨...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
