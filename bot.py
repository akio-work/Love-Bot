import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from database import (
    init_db, add_or_update_user, get_user_by_username, get_user_by_id,
    is_user_married, add_couple, remove_couple, get_couple_by_user, get_all_couples
)

API_TOKEN = "8232680735:AAG-GFL8ZOUla-OwP-0D5bDhnFpNaH6e-pU"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

pending_proposals = {}

MESSAGES = {
    "proposal_offer": "💌 @{target}, пропозиція руки і серця від {proposer}! Натисни ❤️ щоб погодитись або ❌ щоб відмовитись.",
    "proposal_accepted": "🎉 {couple}, тепер одружені! Хай живе любов! 💖",
    "proposal_declined": "🚫 @{target} відмовив(ла) {proposer}.",
    "self_propose": "🙅‍♀️ Не можна пропонувати собі.",
    "already_married": "⚠️ Ти вже одружений(а). Спочатку розвезтись через /divorce.",
    "not_married": "❌ Ти не одружений(а).",
    "divorce_success": "💔 {user1} та {user2} тепер розведені. Нехай шлях буде світлим!",
    "top_empty": "🤷‍♂️ Поки що немає одружених пар.",
    "profile_status_single": "Статус: вільний(а)",
    "profile_status_married": "Статус: одружений(а)",
    "profile_header": "📇 Профіль:\n",
    "profile_married_to": "Одружений(а) з: {partner}\n",
    "profile_married_since": "Одружені з: {since}\n",
    "commands_list": (
        "📜 Команди бота:\n"
        "/marry @username — зробити пропозицію руки і серця 💍\n"
        "/topcouples — топ пар 🥇\n"
        "/divorce — розвезтись 💔\n"
        "/profile — подивитись профіль 🕵️‍♂️\n"
        "/commands — показати список команд 📋\n"
    ),
}

async def update_user_info(message: types.Message):
    user = message.from_user
    username = user.username or ""
    fullname = user.full_name or ""
    add_or_update_user(user.id, username, fullname)

async def get_user_display_name(user_id: int):
    user = get_user_by_id(user_id)
    if user:
        _, username, fullname, _ = user
        return f"@{username}" if username else fullname
    return f"User {user_id}"

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
async def cmd_start(message: types.Message):
    await update_user_info(message)
    await message.answer("Привіт! Я допоможу знайти твою половинку 💖 /commands для списку команд.")

@dp.message(Command("commands"))
async def cmd_commands(message: types.Message):
    await message.answer(MESSAGES["commands_list"])

@dp.message(Command("marry"))
async def cmd_marry(message: types.Message):
    await update_user_info(message)
    text = message.text
    if not text or len(text.split()) < 2:
        await message.reply("Вкажи користувача через @username, щоб зробити пропозицію.")
        return

    proposer_id = message.from_user.id
    username_mention = text.split()[1].lstrip("@").lower()

    if username_mention == (message.from_user.username or "").lower():
        await message.reply(MESSAGES["self_propose"])
        return

    if is_user_married(proposer_id):
        await message.reply(MESSAGES["already_married"])
        return

    target_user = get_user_by_username(username_mention)

    if not target_user:
        # Спроба знайти по user_id у чаті (якщо username не в базі)
        # Оскільки username не знайшли, попросимо користувача, що треба він є в чаті, бот не знайде його автоматично.
        await message.reply(f"Не знайшов користувача @{username_mention} у базі. Проси його написати щось в чаті, щоб я його запам'ятав.")
        return

    target_user_id = target_user[0]
    if is_user_married(target_user_id):
        await message.reply("Цільова людина вже одружена.")
        return

    proposal_id = f"{message.chat.id}_{message.message_id}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️", callback_data=f"proposal_accept:{proposal_id}:{proposer_id}:{target_user_id}"),
            InlineKeyboardButton(text="❌", callback_data=f"proposal_decline:{proposal_id}:{proposer_id}:{target_user_id}")
        ]
    ])

    proposer_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    target_name = f"@{username_mention}"

    await message.answer(
        MESSAGES["proposal_offer"].format(target=target_name, proposer=proposer_name),
        reply_markup=kb
    )
    pending_proposals[proposal_id] = (proposer_id, target_user_id)

@dp.callback_query(lambda c: c.data and c.data.startswith("proposal_"))
async def proposal_callback(call: types.CallbackQuery):
    data = call.data.split(":")
    action = data[0].split("_")[1]
    proposal_id = data[1]
    proposer_id = int(data[2])
    target_user_id = int(data[3])

    if proposal_id not in pending_proposals:
        await call.answer("Цю пропозицію вже оброблено.", show_alert=True)
        return

    if call.from_user.id != target_user_id:
        await call.answer("Це не ваша пропозиція!", show_alert=True)
        return

    if action == "accept":
        # Додаємо пару
        wed_date = datetime.now().isoformat()
        add_couple(proposer_id, target_user_id, wed_date)

        proposer_name = await get_user_display_name(proposer_id)
        target_name = await get_user_display_name(target_user_id)

        couple_name = f"{target_name} і {proposer_name}"
        await call.message.edit_text(MESSAGES["proposal_accepted"].format(couple=couple_name))

        # Весільний марафон
        wedding_texts = [
            "🎶 Звучить весільний марш... 🎶",
            f"Друзі й родина вітають {couple_name}!",
            "Нехай життя буде повним любові та щастя! 🌹",
            "Піднімемо келихи за молодят! 🥂",
            "Танці, сміх і радість заповнюють цей день! 💃🕺",
            "Цей день запам’ятається назавжди! 🎆"
        ]
        for text in wedding_texts:
            await call.message.answer(text)
            await asyncio.sleep(4)

    else:
        proposer_name = await get_user_display_name(proposer_id)
        target_name = await get_user_display_name(target_user_id)
        await call.message.edit_text(MESSAGES["proposal_declined"].format(target=target_name.strip("@"), proposer=proposer_name))

    pending_proposals.pop(proposal_id, None)
    await call.answer()

@dp.message(Command("topcouples"))
async def cmd_topcouples(message: types.Message):
    couples = get_all_couples()
    if not couples:
        await message.answer(MESSAGES["top_empty"])
        return

    result_text = "🔥 Топ одружених пар:\n\n"
    for user1_id, user2_id, wed_date_str in couples:
        wed_date = datetime.fromisoformat(wed_date_str)
        duration = format_duration(wed_date)
        user1_name = await get_user_display_name(user1_id)
        user2_name = await get_user_display_name(user2_id)
        couple_name = f"{user1_name} ❤️ {user2_name}"
        result_text += f"{couple_name} — разом вже {duration}\n"

    await message.answer(result_text)

@dp.message(Command("divorce"))
async def cmd_divorce(message: types.Message):
    user_id = message.from_user.id
    if not is_user_married(user_id):
        await message.answer(MESSAGES["not_married"])
        return

    success = remove_couple(user_id)
    if success:
        await message.answer(MESSAGES["divorce_success"].format(
            user1=await get_user_display_name(user_id),
            user2="Той, з ким розійшлися"
        ))
    else:
        await message.answer("Щось пішло не так.")

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user_id = message.from_user.id
    user = get_user_by_id(user_id)
    if not user:
        await message.answer("Профіль не знайдено.")
        return

    _, username, fullname, status = user
    profile_text = MESSAGES["profile_header"]
    profile_text += f"Ім'я: {fullname}\n"
    profile_text += f"Нікнейм: @{username if username else 'немає'}\n"
    profile_text += f"Статус: {status}\n"

    couple = get_couple_by_user(user_id)
    if couple:
        user1_id, user2_id, wed_date_str = couple
        spouse_id = user2_id if user1_id == user_id else user1_id
        spouse_name = await get_user_display_name(spouse_id)
        wed_date = datetime.fromisoformat(wed_date_str)
        profile_text += MESSAGES["profile_married_to"].format(partner=spouse_name)
        profile_text += MESSAGES["profile_married_since"].format(since=wed_date.strftime("%d.%m.%Y"))

    await message.answer(profile_text)

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
    init_db()
    await set_bot_commands()
    await dp.start_polling(bot)

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
