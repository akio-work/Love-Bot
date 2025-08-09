import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from database import get_db, get_lang_status, get_couple, add_couple, update_status_free, update_status_married, delete_couple
from keep_alive import keep_alive

API_TOKEN = "8232680735:AAG-GFL8ZOUla-OwP-0D5bDhnFpNaH6e-pU"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

MESSAGES = {
    "uk": {
        "help_dm": (
            "Вітання! Ось що я вмію:\n"
            "/marry @username — одружитись з користувачем 👰🤵\n"
            "/topcouples — показати топ пар 🥇\n"
            "/divorce — розвезтись 💔\n"
            "/profile — подивитись свій профіль 🕵️‍♂️\n"
            "/commands — показати список команд 📋\n"
            "\nТех. підтримка: @KR_LVXH"
        ),
        "commands_list": (
            "📜 Ось що я вмію:\n"
            "/marry @username — одружитись з користувачем 👰🤵\n"
            "/topcouples — показати топ пар 🥇\n"
            "/divorce — розвезтись 💔\n"
            "/profile — подивитись свій профіль 🕵️‍♂️\n"
            "/commands — показати список команд 📋\n"
        ),
        "already_married": "❌ Ви або ваш партнер вже одружені.",
        "not_found": "😢 Не можу знайти користувача в чаті.",
        "self_marry": "🙅‍♂️ Не можна одружитись з самим собою!",
        "marriage_start": "💒 {couple} починають весілля! 🎉",
        "wedding_messages": [
            "🎶 Звучить весільний марш... 🎶",
            "Друзі та родина зібралися, щоб привітати {couple}!",
            "Нехай ваше життя буде сповнене любові та щастя! 🌹",
            "Піднімемо келихи за молодят! 🥂",
            "Танці, сміх і радість заповнюють цей день! 💃🕺",
            "Нехай цей день запам’ятається назавжди! 🎆"
        ],
        "wedding_finished": "🎊 Весілля {couple} завершено! Хай живе любов! ❤️",
        "top_empty": "🤷‍♂️ Поки що немає заручених пар.",
        "top_list_header": "🔥 Топ пар в групі:\n\n",
        "divorce_no_spouse": "❌ Ви не одружені, щоб розвезтись.",
        "divorce_success": "💔 {user1} та {user2} тепер розведені. Нехай шлях буде світлим і новим!",
        "profile_no_marriage": "🕵️‍♂️ Профіль доступний лише одруженим. Спершу одружіться через /marry.",
        "profile_header": "📇 Ваш профіль:\n",
        "profile_status": "Статус: {status}\n",
        "profile_married_to": "Одружений(а) з: {partner}\n",
        "profile_married_since": "Одружені з: {since}\n"
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

async def get_user_name(chat_id: int, user_id: int):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.user.full_name
    except:
        return f"Користувач {user_id}"

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
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Щоб одружитись, використай: /marry @username")
        conn.close()
        return
    
    username = parts[1].lstrip("@").strip()
    if username.lower() == (message.from_user.username or "").lower():
        await message.reply(MESSAGES[lang]["self_marry"])
        conn.close()
        return
    
    # Шукаємо user_id по username (через get_chat_member)
    try:
        chat_members = await bot.get_chat_administrators(message.chat.id)
        target_user = None
        for member in chat_members:
            if member.user.username and member.user.username.lower() == username.lower():
                target_user = member.user
                break
        if not target_user:
            await message.reply(MESSAGES[lang]["not_found"])
            conn.close()
            return
    except Exception:
        await message.reply(MESSAGES[lang]["not_found"])
        conn.close()
        return

    author_id = message.from_user.id
    target_id = target_user.id

    # Перевіряємо чи вже одружені
    couple_author = get_couple(conn, author_id)
    couple_target = get_couple(conn, target_id)

    if couple_author or couple_target:
        await message.reply(MESSAGES[lang]["already_married"])
        conn.close()
        return

    # Додаємо пару, запускаємо весілля
    add_couple(conn, author_id, target_id)

    user1_name = message.from_user.full_name
    user2_name = target_user.full_name
    couple_name = f"[{user1_name}](tg://user?id={author_id}) і [{user2_name}](tg://user?id={target_id})"

    await message.answer(MESSAGES[lang]["marriage_start"].format(couple=couple_name), parse_mode="Markdown")

    for msg_text in MESSAGES[lang]["wedding_messages"]:
        await message.answer(msg_text.format(couple=couple_name), parse_mode="Markdown")
        await asyncio.sleep(4)

    update_status_married(conn, author_id, target_id)

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

    result_text = MESSAGES[lang]["top_list_header"]

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
    delete_couple(conn, user1_id, user2_id)
    update_status_free(conn, (user1_id, user2_id))

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
        await message.answer(MESSAGES[lang]["profile_no_marriage"])
        conn.close()
        return

    user1_id, user2_id, wed_date_str = row
    wed_date = datetime.fromisoformat(wed_date_str)
    spouse_id = user2_id if user1_id == user_id else user1_id
    spouse_name = await get_user_name(message.chat.id, spouse_id)

    profile_text = (
        MESSAGES[lang]["profile_header"] +
        MESSAGES[lang]["profile_status"].format(status=status) +
        MESSAGES[lang]["profile_married_to"].format(partner=spouse_name) +
        MESSAGES[lang]["profile_married_since"].format(since=wed_date.strftime("%d.%m.%Y"))
    )

    await message.answer(profile_text)
    conn.close()

async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Стартувати бота"),
        BotCommand(command="commands", description="Показати команди"),
        BotCommand(command="marry", description="Одружитись з користувачем"),
        BotCommand(command="topcouples", description="Топ пар"),
        BotCommand(command="divorce", description="Розвезтись"),
        BotCommand(command="profile", description="Подивитись профіль"),
    ]
    await bot.set_my_commands(commands)

async def main():
    await set_bot_commands()
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())
