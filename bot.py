import asyncio

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram.ext import Application, ApplicationBuilder, CommandHandler

import db
import handlers
from config import BOT_TOKEN
from handlers import give_passive_income


async def _init_db(app: Application) -> None:
    """Хук, который создаёт пул после `Application.initialize()`."""
    app.bot_data["db"] = await db.create_pool()


async def main() -> None:
    # 1) строим приложение
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(_init_db)      # <─ хук инициализации
        .build()
    )

    # 2) регистрируем хендлеры
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("ferma", handlers.farm_collect))
    app.add_handler(CommandHandler("shop", handlers.shop))
    app.add_handler(CommandHandler("buy", handlers.buy))
    app.add_handler(CommandHandler("balance", handlers.balance))

    # 3) APScheduler (использует тот же event-loop)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        lambda: give_passive_income(app),
        CronTrigger(hour=20, minute=0, timezone=pytz.timezone("Europe/Moscow")),
    )
    scheduler.start()

    print("✅ Бот запущен. Ожидаю команды...")

    # 4) корректный асинхронный лайф-цикл PTB-v20
    async with app:
        await app.start()
        await app.updater.start_polling()
        await app.wait_until_closed()   # ← блокирует до SIGINT/SIGTERM


if __name__ == "__main__":
    asyncio.run(main())
