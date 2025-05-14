import asyncpg

from config import DB_URL


async def create_pool():
    return await asyncpg.create_pool(DB_URL)

async def get_user(conn, user_id):
    return await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)

async def create_user(conn, user_id, username):
    await conn.execute(
        "INSERT INTO users (user_id, username) VALUES ($1, $2)",
        user_id, username
    )

async def update_balance(conn, user_id, amount):
    await conn.execute(
        "UPDATE users SET balance = balance + $1 WHERE user_id = $2",
        amount, user_id
    )

async def get_farms(conn, user_id):
    return await conn.fetch("SELECT * FROM user_farms WHERE user_id = $1", user_id)
