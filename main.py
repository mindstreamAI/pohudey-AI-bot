#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()

import asyncio
from database import init_db
from telegram_bot import main as run_bot

print("=" * 50)
print("🏋️ Fitness Coach AI Bot")
print("=" * 50)

print("✓ Инициализирую БД...")
init_db()

print("✓ Запускаю Telegram бота...\n")
asyncio.run(run_bot())
