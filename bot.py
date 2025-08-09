import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from database import get_db, update_last_active, add_couple, get_couple, remove_couple
from keep_alive import keep_alive

API_TOKEN = "8232680735:AAG-GFL8ZOUla-OwP-0D5bDhnFpNaH6e-pU"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

pending_marriages = {}

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
    await message.answer("Вітання! Я бот для весільних святкувань і профілів. Використовуй /marry щоб почати весілля, /profile щоб подивитись активність.")
    update_last_active(get_db(message.chat.id), message.from_user.id)

@dp.message(Command("marry"))
async def cmd_marry(message: Message):
    conn = get_db(message.chat.id)
    user_id = message.from_user.id
    update_last_active(conn, user_id)

    couple = get_couple(conn, user_id)
    if couple:
        await message.reply("Ви вже у парі! Весілля може бути тільки один раз, друже.")
        conn.close()
        return

    if user_id in pending_marriages:
        await message.reply("Ти вже ініціював весілля. Чекаємо підтвердження від партнера.")
        conn.close()
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Вкажи через @username, з ким хочеш одружитись. Приклад: /marry @partner")
        conn.close()
        return

    username = parts[1].lstrip("@").strip()
    if username.lower() == (message.from_user.username or "").lower():
        await message.reply("🙅‍♂️ Не можна одружуватись з собою.")
        conn.close()
        return

    proposal_id = f"{message.chat.id}_{message.message_id}"
    pending_marriages[user_id] = {
        "proposal_id": proposal_id,
        "partner_username": username,
        "chat_id": message.chat.id,
    }

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Згоден(на)", callback_data=f"marry_accept:{proposal_id}:{user_id}"),
            InlineKeyboardButton(text="❌ Відмовитись", callback_data=f"marry_decline:{proposal_id}:{user_id}")
        ]
    ])

    await message.answer(f"💌 {username}, {message.from_user.full_name} хоче одружитись з тобою! Натисни ✅, якщо згоден(на), або ❌, якщо ні.", reply_markup=kb)
    conn.close()

@dp.callback_query(lambda c: c.data and c.data.startswith("marry_"))
async def marry_callback(call: CallbackQuery):
    data = call.data.split(":")
    action = data[0].split("_")[1]
    proposal_id = data[1]
    proposer_id = int(data[2])
    chat_id = call.message.chat.id

    conn = get_db(chat_id)
    c = conn.cursor()

    partner_user = call.from_user
    partner_username = partner_user.username

    if proposer_id not in pending_marriages:
        await call.answer("Ця пропозиція вже оброблена або не існує.", show_alert=True)
        conn.close()
        return

    if partner_username != pending_marriages[proposer_id]["partner_username"]:
        await call.answer("Це не ваша пропозиція!", show_alert=True)
        conn.close()
        return

    if action == "accept":
        success = add_couple(conn, proposer_id, partner_user.id)
        if success:
            proposer_name = (await bot.get_chat_member(chat_id, proposer_id)).user.full_name
            partner_name = partner_user.full_name
            couple_name = f"[{proposer_name}](tg://user?id={proposer_id}) і [{partner_name}](tg://user?id={partner_user.id})"

            await call.message.edit_text(f"🎉 {couple_name}, ви тепер одружені! Починаємо весілля!", parse_mode="Markdown")

            wedding_messages = [
                "🎶 Звучить весільний марш... 🎶",
                f"Друзі та родина зібралися, щоб привітати {couple_name}!",
                "Нехай ваше життя буде сповнене любові та щастя! 🌹",
                "Піднімемо келихи за молодят! 🥂",
                "Танці, сміх і радість заповнюють цей день! 💃🕺",
                "Нехай цей день запам’ятається назавжди! 🎆"
            ]

            for msg_text in wedding_messages:
                await call.message.answer(msg_text, parse_mode="Markdown")
                await asyncio.sleep(4)
        else:
            await call.message.edit_text("Ця пара вже одружена.")
    else:
        await call.message.edit_text("💔 Весілля скасовано.")

    pending_marriages.pop(proposer_id, None)
    conn.close()
    await call.answer()

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    conn = get_db(message.chat.id)
    if not conn:
        await message.answer("❌ Помилка бази даних.")
        return

    user_id = message.from_user.id
    update_last_active(conn, user_id)

    couple = get_couple(conn, user_id)

    last_active_str = get_last_active(conn, user_id)
    last_active = last_active_str if last_active_str else "Немає даних"

    if couple:
        user1_id, user2_id, wed_date_str = couple
        wed_date = datetime.fromisoformat(wed_date_str)
        spouse_id = user2_id if user1_id == user_id else user1_id
        spouse_name = await safe_get_full_name(message.chat.id, spouse_id)
        duration = format_duration(wed_date)

        profile_text = (
            f"📇 Профіль:\n"
            f"Одружений(а) з: {spouse_name}\n"
            f"Разом вже: {duration}\n"
            f"Остання активність: {last_active}\n"
        )
    else:
        profile_text = (
            f"📇 Профіль:\n"
            f"Статус: Вільний(а)\n"
            f"Остання активність: {last_active}\n"
        )

    await message.answer(profile_text)
    conn.close()

@dp.message(Command("topcouples"))
async def cmd_topcouples(message: Message):
    conn = get_db(message.chat.id)
    c = conn.cursor()
    c.execute('SELECT user1_id, user2_id, wed_date FROM couples')
    rows = c.fetchall()
    if not rows:
        await message.answer("🤷‍♂️ Поки що немає одружених пар.")
        conn.close()
        return

    result_text = "🔥 Топ пар:\n\n"
    for user1_id, user2_id, wed_date_str in rows:
        wed_date = datetime.fromisoformat(wed_date_str)
        duration = format_duration(wed_date)
        user1_name = (await bot.get_chat_member(message.chat.id, user1_id)).user.full_name
        user2_name = (await bot.get_chat_member(message.chat.id, user2_id)).user.full_name
        result_text += f"{user1_name} ❤️ {user2_name} — разом вже {duration}\n"

    await message.answer(result_text)
    conn.close()

@dp.message(Command("commands"))
async def cmd_commands(message: Message):
    commands_list = (
        "/marry - Почати весілля\n"
        "/profile - Подивитись свій профіль\n"
        "/topcouples - Показати топ пар\n"
        "/commands - Показати список команд"
    )
    await message.answer(commands_list)

async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Стартувати бота"),
        BotCommand(command="marry", description="Почати весілля"),
        BotCommand(command="profile", description="Подивитись свій профіль"),
        BotCommand(command="topcouples", description="Показати топ пар"),
        BotCommand(command="commands", description="Показати список команд"),
    ]
    await bot.set_my_commands(commands)

async def main():
    keep_alive()  # запускаємо Flask у потоці
    await set_bot_commands()
    print("[BOT] Бот запущено!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
