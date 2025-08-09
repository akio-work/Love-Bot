import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, BotCommand
from keep_alive import keep_alive
import database  # імпорт database.py

API_TOKEN = "8232680735:AAG-GFL8ZOUla-OwP-0D5bDhnFpNaH6e-pU"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

MESSAGES = {
    "uk": {
        "marry_start": "💒 Розпочинаємо весільне гуляння для {couple}! 🎉",
        "wedding_messages": [
            "🎶 Звучить весільний марш... 🎶",
            "Друзі та родина зібралися, щоб привітати {couple}!",
            "Нехай життя буде сповнене любові та щастя! 🌹",
            "Піднімемо келихи за молодят! 🥂",
            "Танці, сміх і радість заповнюють цей день! 💃🕺",
            "Нехай цей день запам’ятається назавжди! 🎆"
        ],
        "wedding_finished": "🎊 Весілля {couple} завершено! Хай живе любов! ❤️",
        "already_married": "Вже є пара, спочатку розійдися через /divorce.",
        "not_married": "😢 Ви поки не одружені. Одруження через /marry.",
        "top_empty": "🤷‍♂️ Поки що немає одружених пар.",
        "top_couples_header": "🔥 Топ одружених пар:\n\n",
        "commands_list": (
            "📜 Ось мої команди:\n"
            "/marry - одружитись 👰🤵\n"
            "/topcouples - показати топ пар 🥇\n"
            "/divorce - розійтись 💔\n"
            "/profile - подивитись свій профіль 🕵️‍♂️\n"
            "/commands - список команд 📋\n"
        ),
        "help_dm": (
            "Вітання! Ось мої команди:\n"
            "/marry — одружитись 👰🤵\n"
            "/topcouples — топ пар 🥇\n"
            "/divorce — розійтись 💔\n"
            "/profile — подивитись свій профіль 🕵️‍♂️\n"
            "/commands — список команд 📋\n"
            "\nТех. підтримка: @KR_LVXH"
        ),
        "divorce_no_spouse": "❌ Ви не одружені, щоб розійтись.",
        "divorce_success": "💔 Пара {user1} та {user2} розійшлась. Нехай шлях буде світлим!",
        "profile_no_marriage": "🕵️‍♂️ Профіль доступний лише одруженим. Спершу одружіться через /marry.",
        "profile_header": "📇 Профіль:\n",
        "profile_married_to": "Одружені з: {partner}\n",
        "profile_married_since": "Одружені з: {since}\n",
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
    lang = "uk"
    await message.answer(MESSAGES[lang]["help_dm"])

@dp.message(Command("commands"))
async def cmd_commands(message: Message):
    lang = "uk"
    await message.answer(MESSAGES[lang]["commands_list"])

@dp.message(Command("marry"))
async def cmd_marry(message: Message):
    conn = database.get_db_connection(message.chat.id)
    user_id = message.from_user.id
    c = conn.cursor()

    # Перевірка чи вже в парі
    couple = database.get_couple_by_user(conn, user_id)
    if couple:
        await message.reply(MESSAGES["uk"]["already_married"])
        conn.close()
        return

    # Знайдемо другого учасника через реплаї (тобто reply)
    if not message.reply_to_message:
        await message.reply("Щоб одружитись, відповідай на повідомлення майбутнього партнера через /marry.")
        conn.close()
        return

    partner = message.reply_to_message.from_user
    if partner.id == user_id:
        await message.reply("Не можна одружуватись із самим собою.")
        conn.close()
        return

    # Вставляємо пару
    database.insert_couple(conn, user_id, partner.id)

    user1_name = await get_user_name(message.chat.id, user_id)
    user2_name = await get_user_name(message.chat.id, partner.id)
    couple_name = f"[{user1_name}](tg://user?id={user_id}) і [{user2_name}](tg://user?id={partner.id})"

    await message.answer(MESSAGES["uk"]["marry_start"].format(couple=couple_name), parse_mode="Markdown")

    # Весільне гуляння з паузами
    for text in MESSAGES["uk"]["wedding_messages"]:
        await asyncio.sleep(5)
        await message.answer(text.format(couple=couple_name), parse_mode="Markdown")

    await message.answer(MESSAGES["uk"]["wedding_finished"].format(couple=couple_name), parse_mode="Markdown")
    conn.close()

@dp.message(Command("topcouples"))
async def cmd_topcouples(message: Message):
    conn = database.get_db_connection(message.chat.id)
    couples = database.get_all_couples(conn)

    if not couples:
        await message.answer(MESSAGES["uk"]["top_empty"])
        conn.close()
        return

    result_text = MESSAGES["uk"]["top_couples_header"]

    for user1_id, user2_id, wed_date_str in couples:
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
    conn = database.get_db_connection(message.chat.id)
    user_id = message.from_user.id
    couple = database.get_couple_by_user(conn, user_id)

    if not couple:
        await message.answer(MESSAGES["uk"]["divorce_no_spouse"])
        conn.close()
        return

    user1_id, user2_id, _ = couple
    database.delete_couple(conn, user1_id, user2_id)

    user1_name = await get_user_name(message.chat.id, user1_id)
    user2_name = await get_user_name(message.chat.id, user2_id)

    await message.answer(MESSAGES["uk"]["divorce_success"].format(user1=user1_name, user2=user2_name))
    conn.close()

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    conn = database.get_db_connection(message.chat.id)
    user_id = message.from_user.id
    couple = database.get_couple_by_user(conn, user_id)

    if not couple:
        await message.answer(MESSAGES["uk"]["profile_no_marriage"])
        conn.close()
        return

    user1_id, user2_id, wed_date_str = couple
    wed_date = datetime.fromisoformat(wed_date_str)
    spouse_id = user2_id if user1_id == user_id else user1_id
    spouse_name = await get_user_name(message.chat.id, spouse_id)

    profile_text = (
        MESSAGES["uk"]["profile_header"] +
        MESSAGES["uk"]["profile_married_to"].format(partner=spouse_name) +
        MESSAGES["uk"]["profile_married_since"].format(since=wed_date.strftime("%d.%m.%Y"))
    )

    await message.answer(profile_text)
    conn.close()

async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Стартувати бота"),
        BotCommand(command="commands", description="Показати команди"),
        BotCommand(command="marry", description="Одружитись (відповісти на повідомлення партнера)"),
        BotCommand(command="topcouples", description="Показати топ пар"),
        BotCommand(command="divorce", description="Розійтись"),
        BotCommand(command="profile", description="Подивитись профіль"),
    ]
    await bot.set_my_commands(commands)

async def main():
    await set_bot_commands()
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())
