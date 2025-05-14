import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

import db
import handlers
from config import BOT_TOKEN
from handlers import give_passive_income


async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    db_pool = await db.create_pool()
    app.bot_data["db"] = db_pool

    # Команды
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("ferma", handlers.farm_collect))  # /ferma
    app.add_handler(CommandHandler("shop", handlers.shop))
    app.add_handler(CommandHandler("buy", handlers.buy))
    app.add_handler(CommandHandler("balance", handlers.balance))

    print("✅ Бот запущен. Ожидаю команды...")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        lambda: give_passive_income(app),
        CronTrigger(hour=20, minute=0, timezone=pytz.timezone('Europe/Moscow'))
    )
    scheduler.start()

    await app.run_polling()


if __name__ == "__main__":
    import asyncio

    # asyncio.run создаёт петлю, выполняет main() и корректно закрывает её
    asyncio.run(main())

