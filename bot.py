import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from database import get_db, get_lang_status
from keep_alive import keep_alive

API_TOKEN = "8232680735:AAG-GFL8ZOUla-OwP-0D5bDhnFpNaH6e-pU"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

pending_proposals = {}

MESSAGES = {
    "uk": {
        "proposal_offer": "💌 {target}, пропозиція руки і серця від {proposer}! Натисни ❤️ щоб погодитись або ❌ щоб відмовитись.",
        "proposal_accepted": "🎉 {couple}, тепер одружені! Нехай щастить у любові! 💖",
        "proposal_declined": "🚫 {target} відмовив(ла) {proposer}.",
        "self_propose": "🙅‍♂️ Не можна пропонувати собі.",
        "wedding_in_progress": "⏳ Весілля вже триває, зачекай.",
        "wedding_start": "💒 Починаємо весільне гуляння для {couple}! 🎉",
        "wedding_finished": "🎊 Весілля {couple} завершено! Хай живе любов! ❤️",
        "top_empty": "🤷‍♂️ Поки що немає одружених пар.",
        "commands_list": (
            "📜 Команди бота:\n"
            "/marry @username — зробити пропозицію руки і серця 💍\n"
            "/topcouples — топ пар 🥇\n"
            "/divorce — розвезтись 💔\n"
            "/profile — подивитись профіль 🕵️‍♂️\n"
            "/commands — показати список команд 📋\n"
        ),
        "help_dm": (
            "Привіт! Ось мої команди:\n"
            "/marry @username — зробити пропозицію руки і серця 💍\n"
            "/topcouples — топ пар 🥇\n"
            "/divorce — розвезтись 💔\n"
            "/profile — подивитись профіль 🕵️‍♂️\n"
            "/commands — показати список команд 📋\n"
            "\nТех. підтримка: @KR_LVXH"
        ),
        "no_spouse": "😢 Немає одруження.",
        "divorce_no_spouse": "❌ Ти не одружений(а), щоб розвезтись.",
        "divorce_success": "💔 {user1} та {user2} тепер розведені. Нехай шлях буде світлим!",
        "profile_header": "📇 Профіль:\n",
        "profile_married_to": "Одружений(а) з: {partner}\n",
        "profile_married_since": "Одружені з: {since}\n",
        "profile_status_single": "Статус: вільний(а)\n",
        "profile_status_married": "Статус: одружений(а)\n"
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

@dp.message(Command("marry"))
async def cmd_marry(message: Message):
    conn = get_db(message.chat.id)
    c = conn.cursor()
    lang, _ = get_lang_status(c, message.from_user.id)

    if not message.text:
        await message.reply("Введи команду з юзером: /marry @username")
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

    proposer_id = message.from_user.id

    # Перевірка, чи вже в парі
    c.execute('SELECT user1_id, user2_id FROM couples WHERE user1_id = ? OR user2_id = ?', (proposer_id, proposer_id))
    if c.fetchone():
        await message.reply("Ти вже одружений(а). Спочатку розвезтись через /divorce.")
        conn.close()
        return

    # Пошук user_id за username
    c.execute("SELECT user_id FROM users WHERE user_id = ?", (proposer_id,))
    if not c.fetchone():
        c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (proposer_id,))

    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        # Знаходимо user_id цільового
        target_user = None
        async for member_obj in bot.get_chat_administrators(message.chat.id):
            if member_obj.user.username and member_obj.user.username.lower() == username.lower():
                target_user = member_obj.user
                break
    except:
        target_user = None

    # Якщо не знайшли користувача, то пішли по базі
    if target_user is None:
        # Використовуємо Telegram API щоб знайти
        try:
            from aiogram.types import ChatMemberUpdated
            # Ні, це не дуже просто, тому відправимо повідомлення з пропозицією і будемо чекати підтвердження по кнопці
        except:
            await message.reply("Не вдалося знайти користувача в чаті.")
            conn.close()
            return

    # Для простоти візьмемо user_id як цільовий, якщо немає точного
    target_user = None
    # Візьмемо username з повідомлення і будемо чекати підтвердження

    # Створюємо інлайн клавіатуру для підтвердження
    proposal_id = f"{message.chat.id}_{message.message_id}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️", callback_data=f"proposal_accept:{proposal_id}:{proposer_id}:{username}"),
            InlineKeyboardButton(text="❌", callback_data=f"proposal_decline:{proposal_id}:{proposer_id}:{username}")
        ]
    ])

    text = MESSAGES[lang]["proposal_offer"].format(target=f"@{username}", proposer=message.from_user.full_name)
    await message.answer(text, reply_markup=kb)
    pending_proposals[proposal_id] = (proposer_id, username)

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
        await call.answer("Цю пропозицію вже оброблено.", show_alert=True)
        conn.close()
        return

    if action == "accept":
        user1_id = min(proposer_id, call.from_user.id)
        user2_id = max(proposer_id, call.from_user.id)
        now_str = datetime.now().isoformat()
        try:
            c.execute('INSERT INTO couples (user1_id, user2_id, wed_date) VALUES (?, ?, ?)', (user1_id, user2_id, now_str))
            c.execute("INSERT OR REPLACE INTO users (user_id, lang, status) VALUES (?, COALESCE((SELECT lang FROM users WHERE user_id=?), 'uk'), 'Одружений(а)')", (user1_id, user1_id))
            c.execute("INSERT OR REPLACE INTO users (user_id, lang, status) VALUES (?, COALESCE((SELECT lang FROM users WHERE user_id=?), 'uk'), 'Одружений(а)')", (user2_id, user2_id))
            conn.commit()
        except sqlite3.IntegrityError:
            pass

        proposer_name = await get_user_name(call.message.chat.id, proposer_id)
        target_name = await get_user_name(call.message.chat.id, call.from_user.id)
        couple_name = f"[{target_name}](tg://user?id={call.from_user.id}) і [{proposer_name}](tg://user?id={proposer_id})"

        await call.message.edit_text(MESSAGES[lang]["proposal_accepted"].format(couple=couple_name), parse_mode="Markdown")

        # Після 5 секунд влаштовуємо весільний текст
        await asyncio.sleep(5)
        wedding_texts = [
            "🎶 Звучить весільний марш... 🎶",
            f"Друзі і родина вітають {couple_name}!",
            "Нехай життя буде повним любові та щастя! 🌹",
            "Піднімемо келихи за молодят! 🥂",
            "Танці, сміх і радість заповнюють цей день! 💃🕺",
            "Цей день запам’ятається назавжди! 🎆"
        ]
        for text in wedding_texts:
            await call.message.answer(text, parse_mode="Markdown")
            await asyncio.sleep(4)

        pending_proposals.pop(proposal_id, None)
    else:
        proposer_name = await get_user_name(call.message.chat.id, proposer_id)
        text = MESSAGES[lang]["proposal_declined"].format(target=call.from_user.full_name, proposer=proposer_name)
        await call.message.edit_text(text)
        pending_proposals.pop(proposal_id, None)

    await call.answer()
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

    c.execute('SELECT user1_id, user2_id, wed_date FROM couples WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
    row = c.fetchone()

    if row:
        user1_id, user2_id, wed_date_str = row
        wed_date = datetime.fromisoformat(wed_date_str)
        spouse_id = user2_id if user1_id == user_id else user1_id
        spouse_name = await get_user_name(message.chat.id, spouse_id)

        profile_text = (
            MESSAGES[lang]["profile_header"] +
            MESSAGES[lang]["profile_status_married"] +
            MESSAGES[lang]["profile_married_to"].format(partner=spouse_name) +
            MESSAGES[lang]["profile_married_since"].format(since=wed_date.strftime("%d.%m.%Y"))
        )
    else:
        profile_text = (
            MESSAGES[lang]["profile_header"] +
            MESSAGES[lang]["profile_status_single"]
        )

    await message.answer(profile_text)
    conn.close()

async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Стартувати бота"),
        BotCommand(command="commands", description="Показати команди"),
        BotCommand(command="marry", description="Зробити пропозицію руки і серця"),
        BotCommand(command="topcouples", description="Топ одружених пар"),
        BotCommand(command="divorce", description="Розвезтись"),
        BotCommand(command="profile", description="Подивитись профіль"),
    ]
    await bot.set_my_commands(commands)

async def main():
    await set_bot_commands()
    await dp.start_polling(bot)  # Polling

if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())
