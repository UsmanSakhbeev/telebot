import random
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

import db
from config import COOLDOWN
from farms import FARM_TYPES


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = context.bot_data["db"]
    user_id = update.effective_user.id
    username = update.effective_user.username

    async with pool.acquire() as conn:
        user = await db.get_user(conn, user_id)
        if not user:
            await db.create_user(conn, user_id, username)

    await update.message.reply_text(
        "👋 Добро пожаловать на ферму! Используй команду /shop, чтобы купить ферму."
    )


async def farm_collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = context.bot_data["db"]
    user_id = update.effective_user.id
    now = datetime.utcnow()

    async with pool.acquire() as conn:
        farms = await db.get_farms(conn, user_id)
        if not farms:
            await update.message.reply_text("У тебя пока нет ферм. Купи их в /shop.")
            return

        total_earned = 0
        messages = []

        for farm in farms:
            # Только активные фермы!
            if farm['farm_type'] not in ('Поле', 'Коровы'):
                continue

            if farm['next_collect'] and farm['next_collect'] > now:
                continue  # ещё не прошло 24ч

            if farm['farm_type'] == 'Поле':
                coins = random.randint(15, 35) + (farm['level'] - 1) * 5
            elif farm['farm_type'] == 'Коровы':
                coins = random.randint(20, 30) + (farm['level'] - 1) * 5
            else:
                continue

            crit_chance = 0.10 + (farm['crit_level'] - 1) * 0.10
            if random.random() < crit_chance:
                coins *= 2
                messages.append(f"✨ Критический доход от {farm['farm_type']}!")

            total_earned += coins

            await conn.execute(
                "UPDATE user_farms SET next_collect = $1 WHERE id = $2",
                now + timedelta(seconds=86400), farm['id']
            )

        await db.update_balance(conn, user_id, total_earned)

        if total_earned > 0:
            await update.message.reply_text(
                f"Ты собрал {total_earned} монет! 🪙\n" + "\n".join(messages)
            )
        else:
            await update.message.reply_text("Фермы ещё не готовы к сбору.")


async def give_passive_income(app):
    pool = app.bot_data["db"]
    now = datetime.utcnow()

    async with pool.acquire() as conn:
        farms = await conn.fetch("""
            SELECT * FROM user_farms
            WHERE farm_type IN ('Пасека', 'Курятник')
        """)

        earnings = {}

        for farm in farms:
            last_paid = farm['last_paid']
            if last_paid and last_paid.date() == now.date():
                continue  # уже платили сегодня

            if farm['farm_type'] == 'Пасека':
                coins = random.randint(5, 20) + (farm['level'] - 1) * 5
            elif farm['farm_type'] == 'Курятник':
                coins = random.randint(7, 16) + (farm['level'] - 1) * 5
            else:
                continue

            crit_chance = 0.10 + (farm['crit_level'] - 1) * 0.10
            if random.random() < crit_chance:
                coins *= 2

            # Добавляем к балансу владельца
            user_id = farm['user_id']
            earnings[user_id] = earnings.get(user_id, 0) + coins

            # Обновляем дату выплаты
            await conn.execute(
                "UPDATE user_farms SET last_paid = $1 WHERE id = $2",
                now, farm['id']
            )

        # Обновляем баланс всех пользователей разом
        for user_id, amount in earnings.items():
            await db.update_balance(conn, user_id, amount)


async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🏪 Доступные фермы для покупки:\n\n"
    for key, farm in FARM_TYPES.items():
        text += f"🔹 *{farm['name']}* — {farm['price']} монет\n_{farm['description']}_\n\n"
    text += "Чтобы купить, введи: `/buy название`, например: `/buy пасека`"
    await update.message.reply_text(text, parse_mode="Markdown")


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = context.bot_data["db"]
    user_id = update.effective_user.id
    args = context.args

    print(f"ARGS: {context.args}")

    if not args:
        await update.message.reply_text("Укажи название фермы. Пример: /buy пасека")
        return

    farm_key = " ".join(args).strip().lower()
    farm_key = farm_key.replace("🍯", "").replace("🐓", "").replace("🌾", "").replace("🐄", "").strip()

    if farm_key not in FARM_TYPES:
        await update.message.reply_text(f"Такой фермы не существует: '{farm_key}'. Посмотри в /shop")
        return

    async with pool.acquire() as conn:
        user = await db.get_user(conn, user_id)
        farms = await db.get_farms(conn, user_id)

        if user['balance'] < FARM_TYPES[farm_key]["price"]:
            await update.message.reply_text("Недостаточно монет 💸")
            return

        if len(farms) >= user['slots']:
            await update.message.reply_text("У тебя нет свободных слотов для фермы.")
            return

        await db.update_balance(conn, user_id, -FARM_TYPES[farm_key]["price"])
        await conn.execute(
            """
            INSERT INTO user_farms (user_id, farm_type, level, crit_level, next_collect, last_paid, active, slot)
            VALUES ($1, $2, 1, 1, NULL, NULL, TRUE, $3)
            """,
            user_id, FARM_TYPES[farm_key]["name"].split()[0], len(farms) + 1
        )

        await update.message.reply_text(f"✅ Ты купил ферму {FARM_TYPES[farm_key]['name']}!")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = context.bot_data["db"]
    user_id = update.effective_user.id

    async with pool.acquire() as conn:
        user = await db.get_user(conn, user_id)
        farms = await db.get_farms(conn, user_id)

    await update.message.reply_text(
        f"💰 Баланс: {user['balance']} монет\n"
        f"🏡 Фермы: {len(farms)} / {user['slots']} слотов"
    )
