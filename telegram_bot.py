# telegram_bot.py
import asyncio
import re
import traceback
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramConflictError

from config import TELEGRAM_BOT_TOKEN
from router import llm_route
from database import (
    init_db,
    create_user_if_not_exists,
    delete_user_by_id,
    save_user_weight,
    set_remind_weekly,
    list_users_for_weekly_reminder,
    update_last_weighin_reminder,
)

# --- Бот ---
bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()


# ---------- Вспомогательные ----------

async def _parse_and_save_profile(message: Message) -> bool:
    user_id = message.from_user.id
    text = (message.text or "").strip()
    nums = re.findall(r"\d+(?:[.,]\d+)?", text)
    if len(nums) < 3:
        return False

    try:
        age = int(float(nums[0].replace(",", ".")))
        weight = float(nums[1].replace(",", "."))
        height = float(nums[2].replace(",", "."))

        first_num = re.search(r"\d", text)
        name = text[:first_num.start()].strip(" ,") if first_num else None
        if name and re.search(r"\d", name):
            name = None

        create_user_if_not_exists(user_id, name=name, age=age, weight=weight, height=height)
        save_user_weight(user_id, weight)

        who = f"{name}, " if name else ""
        await message.answer(
            f"✅ Профиль сохранён: {who}{age} лет, {weight:.1f} кг, {int(height)} см.\n"
            f"💾 Вес сохранён: {weight:.1f} кг\n\n"
            "Теперь задай цель: «цель 75» или «похудеть на 10 кг за 12 недель»."
        )
        return True
    except Exception as e:
        print(f"[bot] profile-parse error: {e}\n{traceback.format_exc()}")
        return False


# ---------- Команды ----------

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я помогу с питанием, весом и тренировками.\n"
        "Напиши одной строкой: Имя, возраст, вес(кг), рост(см)\n"
        "Например: Юрий, 38, 88, 175\n\n"
        "Или команды: «цель 75», «я съел 2 яйца», «создай тренировку».\n\n"
        "Напоминание о взвешивании включено. Чтобы отключить: `/remind_off`"
    )


@dp.message(F.text == "/help")
async def cmd_help(message: Message):
    await message.answer(
        "Примеры:\n"
        "• Профиль: «Юрий, 38, 88, 175»\n"
        "• Взвесился: «взвесился 85.4»\n"
        "• Цель: «цель 75» или «на 7 кг за 2 месяца»\n"
        "• Еда: «я съел борщ 300 мл», «халва 40 г»\n"
        "• Тренировка: «создай тренировку на 60 минут»\n"
        "• Напоминания: `/remind_on`, `/remind_off`\n"
        "• Сброс профиля: «сброс»"
    )


@dp.message(F.text == "/remind_on")
async def cmd_remind_on(message: Message):
    user_id = message.from_user.id
    create_user_if_not_exists(user_id)
    set_remind_weekly(user_id, True)
    await message.answer("🔔 Еженедельное напоминание о взвешивании включено.")


@dp.message(F.text == "/remind_off")
async def cmd_remind_off(message: Message):
    user_id = message.from_user.id
    create_user_if_not_exists(user_id)
    set_remind_weekly(user_id, False)
    await message.answer("🔕 Еженедельное напоминание о взвешивании отключено.")


# ---------- Общий хендлер ----------

@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_text = (message.text or "").strip()

    # Сброс профиля
    if user_text.lower() in {"сброс", "/reset", "удали профиль"}:
        delete_user_by_id(user_id)
        await message.answer("🗑️ Профиль удалён. Начни заново командой /start.")
        return

    # Профиль одной строкой
    if await _parse_and_save_profile(message):
        return

    # Быстрые подтверждения планов (если есть pending в tools)
    low = user_text.lower()
    if low in {"да", "ок", "подтверждаю"}:
        from tools import confirm_pending_action
        await message.answer(confirm_pending_action(user_id))
        return
    if low in {"нет", "отмена"}:
        from tools import cancel_pending_action
        await message.answer(cancel_pending_action(user_id))
        return

    # Остальное — через роутер
    try:
        create_user_if_not_exists(user_id)
        result = llm_route(user_text, user_id)
        if result.strip().startswith("{") and '"tool"' in result:
            result = "Не понял. Пример: «цель 75» или «на 7 кг за 12 недель»."
        await message.answer(result)
    except Exception as e:
        print(f"[bot] handle_message error: {e}\n{traceback.format_exc()}")
        await message.answer("Ошибка обработки. Попробуй ещё раз.")


# ---------- Напоминания (фоновая задача) ----------

async def _weekly_reminder_loop():
    """
    Раз в ~час проверяем, кого пора пинговать:
    - remind_weekly=1
    - последний вес ≥ 7 дней назад или его нет
    - последнее напоминание ≥ ~6.5 дней назад
    """
    await asyncio.sleep(5)
    while True:
        try:
            user_ids = list_users_for_weekly_reminder()
            for uid in user_ids:
                try:
                    await bot.send_message(
                        uid,
                        "🔔 Еженедельное напоминание: взвесься сегодня и пришли сообщение: «взвесился 85.4»"
                    )
                    update_last_weighin_reminder(uid)
                except Exception as e:
                    print(f"[reminder] send failed for {uid}: {e}")
        except Exception as e:
            print(f"[reminder] loop error: {e}")
        await asyncio.sleep(3600)


# ---------- Точка входа ----------

async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✓ Webhook удалён. Перехожу на polling.")
    except Exception as e:
        print(f"[bot] delete_webhook warn: {e}")

    asyncio.create_task(_weekly_reminder_loop())

    print("🤖 Bot polling...")
    backoff = 1.0
    while True:
        try:
            await dp.start_polling(bot, allowed_updates=["message"])
        except TelegramConflictError as e:
            print(f"Failed to fetch updates - TelegramConflictError: {e}")
            print(f"Sleep for {backoff:.6f} seconds and try again...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 1.5, 10.0)
            continue
        except Exception as e:
            print(f"[bot] polling error: {e}\n{traceback.format_exc()}")
            await asyncio.sleep(2.0)
            continue


if __name__ == "__main__":
    asyncio.run(main())
