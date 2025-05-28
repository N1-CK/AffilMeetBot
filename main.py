from aiogram import Bot, Dispatcher
import Scripts.initial_commands as initial
import Scripts.reglaments as reglaments
import Scripts.report as report
import Scripts.restaurants as restaurants
import Scripts.google_table_parsing as google_table
from Scripts.initial_commands import *
import Scripts.my_bookings as my_bookings

from dotenv import load_dotenv
import os
load_dotenv()
token = os.getenv('TG_BOT_TOKEN')

logging.basicConfig(
    filename='../logs/activity_log.log',
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def on_startup(bot: Bot):
    await AuthManager.create_pool()
    logging.info("Database connection pool created")


async def on_shutdown(bot: Bot):
    if AuthManager.flg:
        await AuthManager.flg.close()
        logging.info("Database connection pool closed")


# В месте где создаете и запускаете бота (обычно в main.py):
async def main():
    bot = Bot(token=token)
    dp = Dispatcher()

    # Подключаем обработчики
    dp.include_router(initial.router)
    dp.include_router(reglaments.router)
    dp.include_router(report.router)
    dp.include_router(google_table.router)
    dp.include_router(restaurants.router)
    dp.include_router(report.calendar_router)
    dp.include_router(my_bookings.router)

    # Подключаем обработчики жизненного цикла
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
