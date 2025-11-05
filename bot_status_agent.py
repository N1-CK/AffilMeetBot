from datetime import datetime
import json
import asyncpg
import os
from aiogram import Router, types
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()

router = Router()


async def get_db_connection():
    """Создание подключения к БД"""
    return await asyncpg.connect(
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_NAME')
    )


async def update_bot_status():
    """Обновление статуса бота в БД"""
    try:
        conn = await get_db_connection()

        # Создаем схему и таблицу если не существуют
        await conn.execute("""
            CREATE SCHEMA IF NOT EXISTS systemcheck_bot;
        """)

        await conn.execute("""
                           CREATE TABLE IF NOT EXISTS systemcheck_bot.bots_status
                           (
                               bot_id     TEXT PRIMARY KEY,
                               status     TEXT NOT NULL,
                               components JSONB,
                               created_at TIMESTAMP DEFAULT NOW(),
                               updated_at TIMESTAMP DEFAULT NOW()
                           );
                           """)

        # Подготавливаем данные статуса
        health_status = {
            "bot_id": 'BotHelper123',
            "status": "online",
            "components": {
                "telegram": "online",
                "database": "online",
                "message_processing": "online"
            }
        }

        # Вставляем или обновляем запись
        await conn.execute("""
                           INSERT INTO systemcheck_bot.bots_status (bot_id, status, components, updated_at)
                           VALUES ($1, $2, $3, NOW())
                           ON CONFLICT (bot_id)
                               DO UPDATE SET status     = EXCLUDED.status,
                                             components = EXCLUDED.components,
                                             updated_at = EXCLUDED.updated_at
                           """,
                           health_status['bot_id'],
                           health_status['status'],
                           json.dumps(health_status['components']))

        await conn.close()
        return {"success": True, "status": health_status}

    except Exception as e:
        return {"success": False, "error": str(e)}