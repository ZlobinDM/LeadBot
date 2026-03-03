import asyncio
import json
import logging
import os
import threading
from urllib.parse import quote
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ChatMemberStatus

# --------------------- НАСТРОЙКИ ---------------------
# Для проверки подписки: бот должен быть админом канала (право «просмотр участников»).
# CHANNEL_ID и CHANNEL_USERNAME должны относиться к одному каналу.
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1002042643493
CHANNEL_USERNAME = "yaothai"  # без @, для ссылки t.me/канал
PROGRESS_FILE = "lesson_progress.json"  # файл для сохранения прогресса

# Список уроков
LESSONS = [
    {
        "title": "От знакомства до секса",
        "link": "https://youtu.be/NP_mJGHaAhs?si=Szxg7PHheFf2itg2",
        "text": "🎁 Видео-урок «От знакомства до секса»\n\n"
                "Надеюсь, что это видео:\n"
                "➡вдохновит подходить знакомиться и не тупить со сближением\n"
                "➡подсветит вам важные технические и ментальные аспекты\n\n"
                "Приятного просмотра!",
        "buttons": ["next", "consult"]
    },
    {
        "title": "Подкаст-урок: Фаст в аэропорту",
        "link": "https://t.me/yaothai/711",
        "text": "🎁 Подкаст-урок «Фаст в аэропорту»\n\n"
                "Надеюсь, что это аудио:\n"
                "➡вдохновит подходить знакомиться и не тупить со сближением\n"
                "➡подсветит вам важные технические и ментальные аспекты\n\n"
                "Приятного прослушивания!",
        "buttons": ["next", "consult"]
    },
    {
        "title": "Капризная красавица",
        "link": "https://telegra.ph/Soblaznenie-CHSV-devochki-cherez-prohozhdenie-proverok-03-02",
        "text": "🎁 Отчет-урок «Капризная красавица»\n\n"
                "Надеюсь, что этот пост:\n"
                "➡вдохновит подходить знакомиться и не тупить со сближением\n"
                "➡подсветит вам важные технические и ментальные аспекты\n\n"
                "Приятного прочтения!",
        "buttons": ["consult", "reset"]
    }
]

# Настройки консультации
CONSULT_USERNAME = "ZlobinDev"
CONSULT_MESSAGE = "Приветствую, хотел бы попасть на консультацию.\n\nмой запрос:\n\n"

# ------------------------------------------------------

# Загрузка и сохранение прогресса
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ключи в JSON всегда строки, конвертируем в int
                return {int(k): v for k, v in data.items()}
        except Exception as e:
            logging.error(f"Ошибка загрузки прогресса: {e}")
    return {}

def save_progress(progress_dict):
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress_dict, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения прогресса: {e}")

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Главное меню с кнопкой "Получить урок"
def get_main_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Получить урок 👇", callback_data="get_lesson")]
    ])
    return kb


# Кнопка консультации
def get_consult_button():
    consult_url = f"https://t.me/{CONSULT_USERNAME}?text={quote(CONSULT_MESSAGE)}"
    return InlineKeyboardButton(text="📝 Записаться на консультацию", url=consult_url)


# Проверка подписки
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        )
    except Exception as e:
        logging.error(f"Ошибка проверки подписки: {e}")
        return False


# Стартовое сообщение с требованием подписки
@router.message(CommandStart())
async def cmd_start(message: Message):
    if await is_subscribed(message.from_user.id):
        await message.answer(
            "Привет! Ты уже подписан — можешь начинать учиться 🚀",
            reply_markup=get_main_kb()
        )
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton(text="Я подписался ✅", callback_data="check_sub")]
        ])
        await message.answer(
            "Для использования бота подпишись на канал:\n"
            f"👉 https://t.me/{CHANNEL_USERNAME}",
            reply_markup=kb,
            disable_web_page_preview=True
        )


# Кнопка "Я подписался"
@router.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery):
    subscribed = await is_subscribed(call.from_user.id)
    if subscribed:
        await call.answer()
        await call.message.edit_text(
            "Отлично! Подписка есть 🔥\nТеперь можно получать уроки.",
            reply_markup=get_main_kb()
        )
    else:
        await call.answer("Ты ещё не подписан 😕 Проверь подписку и попробуй снова.", show_alert=True)


# Основная логика выдачи контента
lesson_index = load_progress()  # {user_id: текущий индекс урока}

@router.callback_query(F.data == "get_lesson")
async def give_lesson(call: CallbackQuery):
    await call.answer()
    user_id = call.from_user.id

    if not await is_subscribed(user_id):
        await call.message.answer("Подпишись на канал, чтобы продолжить!")
        return

    idx = lesson_index.get(user_id, 0)

    if idx < len(LESSONS):
        lesson = LESSONS[idx]
        lesson_index[user_id] = idx + 1
        save_progress(lesson_index)

        # Формируем сообщение
        message_text = f"<b>{lesson['title']}</b>\n\n{lesson['text']}\n\n{lesson['link']}"
        
        # Формируем кнопки в зависимости от урока
        buttons = []
        for btn_type in lesson["buttons"]:
            if btn_type == "consult":
                buttons.append([get_consult_button()])
            elif btn_type == "next":
                # Разные тексты для кнопки в зависимости от урока
                if idx == 0:
                    button_text = "🎁 Бонусный урок"
                elif idx == 1:
                    button_text = "📚 Ещё урок"
                else:
                    button_text = "Следующий урок →"
                buttons.append([InlineKeyboardButton(text=button_text, callback_data="get_lesson")])
            elif btn_type == "reset":
                buttons.append([InlineKeyboardButton(text="🔄 Начать сначала", callback_data="reset_progress")])

        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await call.message.answer(message_text, reply_markup=kb, parse_mode="HTML")
    else:
        # Все уроки пройдены
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [get_consult_button()],
            [InlineKeyboardButton(text="🔄 Начать сначала", callback_data="reset_progress")]
        ])
        await call.message.answer(
            "Уроки закончились! 🎉\n\n"
            "Запишись на персональную консультацию или начни уроки заново:",
            reply_markup=kb
        )


# Кнопка "Начать сначала"
@router.callback_query(F.data == "reset_progress")
async def reset_progress(call: CallbackQuery):
    user_id = call.from_user.id
    lesson_index[user_id] = 0
    save_progress(lesson_index)
    
    await call.answer("Прогресс сброшен! Начинай заново 🚀")
    await call.message.edit_text(
        "Прогресс сброшен! Теперь можешь пройти уроки заново 🔥",
        reply_markup=get_main_kb()
    )


def run_health_server():
    """Минимальный HTTP-сервер на порту PORT для health check Fly.io."""
    import http.server
    import socketserver

    port = int(os.environ.get("PORT", "8080"))

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        def log_message(self, format, *args):
            pass  # отключаем логи каждого запроса

    with socketserver.TCPServer(("", port), Handler) as httpd:
        httpd.serve_forever()


async def main():
    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get("PORT", "8080"))
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()
    logging.info("Health check server listening on port %s", port)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
