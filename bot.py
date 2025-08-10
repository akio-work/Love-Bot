import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from flask import Flask, request, Response

API_TOKEN = "8232680735:AAG-GFL8ZOUla-OwP-0D5bDhnFpNaH6e-pU"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot=bot)
app = Flask(__name__)

# --- Пам'ять замість бази ---
couples = {}  # ключ: tuple(user1_id, user2_id), значення: wed_date (datetime)
users_lang = {}  # ключ: user_id, значення: lang

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
            "\nТех. підтримка: @KR_LVXH"
        ),
        "proposal_sent": "Пропозицію відправлено!",
        "divorce_no_spouse": "Ви не одружені, щоб розвезтись.",
        "divorce_success": "💔 {user1} та {user2} тепер розведені. Нехай шлях буде світлим і новим!",
        "profile_info": "👤 Профіль користувача:\nІм'я: {name}\nID: {id}\nМова: {lang}\nОдружений: {married}",
        "not_married": "Наразі ви не одружені."
    }
}

pending_proposals = {}  # proposal_id: (proposer_id, proposee_id)

# --- Функції мови ---
def get_lang(user_id: int):
    return users_lang.get(user_id, "uk")

def set_lang(user_id: int, lang: str):
    users_lang[user_id] = lang

# --- Форматування часу ---
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

    username = parts[1].lstrip("@").strip().lower()
    if username == (message.from_user.username or "").lower():
        await message.reply(MESSAGES[lang]["self_propose"])
        return

    # Шукаємо proposee по username — треба отримати user_id, але у пам'яті немає — зробимо просто mock:
    # У реальному світі треба зберігати id користувачів, але для прикладу пропустимо це.
    # Тож будемо чекати що proposee вже знаємо (або відхиляти).
    await message.reply("Поки що підтримка пропозицій за username не реалізована. Надішли id користувача або допишемо пізніше.")
    # Можна тут додати логіку з mention та реєстрацією user_id.
    # Щоб не ускладнювати, поки пропозиції працюють лише на id.
    # Або запропонуй юзерам писати "/propose user_id"

@dp.message(Command("propose"))
async def cmd_propose_id(message: types.Message):
    lang = get_lang(message.from_user.id)
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return  # вже оброблено вище

    try:
        proposee_id = int(parts[1])
    except ValueError:
        return

    proposer_id = message.from_user.id
    if proposee_id == proposer_id:
        await message.reply(MESSAGES[lang]["self_propose"])
        return

    proposal_id = f"{message.chat.id}_{message.message_id}"
    proposer = message.from_user

    text = MESSAGES[lang]["proposal_offer"].format(target=f"User {proposee_id}", proposer=proposer.full_name)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅", callback_data=f"proposal_accept:{proposal_id}:{proposer_id}:{proposee_id}"),
            InlineKeyboardButton(text="❌", callback_data=f"proposal_decline:{proposal_id}:{proposer_id}:{proposee_id}")
        ]
    ])
    await message.answer(text, reply_markup=kb)
    pending_proposals[proposal_id] = (proposer_id, proposee_id)
    await message.reply(MESSAGES[lang]["proposal_sent"])

@dp.callback_query(lambda c: c.data and c.data.startswith("proposal_"))
async def proposal_callback(call: types.CallbackQuery):
    data = call.data.split(":")
    action = data[0].split("_")[1]
    proposal_id = data[1]
    proposer_id = int(data[2])
    proposee_id = int(data[3])

    lang = get_lang(call.from_user.id)
    proposer_accepted = (action == "accept")

    if call.from_user.id != proposee_id:
        await call.answer("Це не ваша пропозиція!", show_alert=True)
        return

    if proposal_id not in pending_proposals:
        await call.answer("Ця пропозиція вже оброблена.", show_alert=True)
        return

    if proposer_accepted:
        couple_key = tuple(sorted((proposer_id, proposee_id)))
        couples[couple_key] = datetime.now()

        user1 = await bot.get_chat(couple_key[0])
        user2 = await bot.get_chat(couple_key[1])
        couple_name = f"[{user1.first_name}](tg://user?id={couple_key[0]}) і [{user2.first_name}](tg://user?id={couple_key[1]})"

        text = MESSAGES[lang]["proposal_accepted"].format(couple=couple_name)
        await call.message.edit_text(text, parse_mode="Markdown")
        pending_proposals.pop(proposal_id, None)
    else:
        text = MESSAGES[lang]["proposal_declined"].format(target=call.from_user.full_name, proposer=f"User {proposer_id}")
        await call.message.edit_text(text)
        pending_proposals.pop(proposal_id, None)

    await call.answer()

@dp.message(Command("marry"))
async def cmd_marry(message: types.Message):
    lang = get_lang(message.from_user.id)
    author_id = message.from_user.id

    couple = None
    for (u1, u2), wed_date in couples.items():
        if author_id in (u1, u2):
            couple = (u1, u2, wed_date)
            break

    if not couple:
        await message.reply(MESSAGES[lang]["not_engaged_for_marry"])
        return

    if getattr(dp, "marriage_active", False):
        await message.reply(MESSAGES[lang]["wedding_in_progress"])
        return

    dp.marriage_active = True
    user1_id, user2_id, wed_date = couple

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

    if not couples:
        await message.reply(MESSAGES[lang]["top_empty"])
        return

    couples_info = []
    for (user1_id, user2_id), wed_date in couples.items():
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

    couple_key = None
    for (u1, u2) in couples.keys():
        if user_id in (u1, u2):
            couple_key = (u1, u2)
            break

    if not couple_key:
        await message.reply(MESSAGES[lang]["divorce_no_spouse"])
        return

    user1_id, user2_id = couple_key
    try:
        user1 = await bot.get_chat(user1_id)
        user2 = await bot.get_chat(user2_id)
        user1_name = user1.first_name
        user2_name = user2.first_name
    except Exception:
        user1_name = f"User {user1_id}"
        user2_name = f"User {user2_id}"

    couples.pop(couple_key)

    await message.answer(MESSAGES[lang]["divorce_success"].format(user1=user1_name, user2=user2_name))

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    lang = get_lang(message.from_user.id)
    user_id = message.from_user.id
    user_name = message.from_user.full_name

    couple_key = None
    for (u1, u2) in couples.keys():
        if user_id in (u1, u2):
            couple_key = (u1, u2)
            break

    if couple_key:
        partner_id = couple_key[1] if couple_key[0] == user_id else couple_key[0]
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
def webhook():
    json_update = request.get_json()
    update = types.Update(**json_update)
    loop = asyncio.get_event_loop()
    loop.create_task(dp.feed_update(update))
    return Response("OK", status=200)

# --- Запуск ---

async def main():
    await set_bot_commands()
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:8443"]

    print("Бот запускається, тримайся 💍✨...")
    await serve(app, config)

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
