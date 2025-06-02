from aiogram import Bot, Dispatcher
import Scripts.initial_commands as initial
import Scripts.reglaments as reglaments
import Scripts.report as report
import Scripts.restaurants as restaurants
import Scripts.google_table_parsing as google_table
from Scripts.initial_commands import *
import Scripts.my_bookings as my_bookings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import logging

from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv('TG_BOT_TOKEN')

logging.basicConfig(
    filename='../logs/activity_log.log',
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


async def send_booking_reminders(bot: Bot):
    """Функция для отправки напоминаний о бронированиях"""
    try:
        now = datetime.now()
        reminder_time = now + timedelta(hours=1)
        reminder_time_str = reminder_time.strftime('%d.%m.%Y %H:%M')
        print(reminder_time_str)

        async with AuthManager.flg.acquire() as conn:
            bookings = await conn.fetch(
                "SELECT * FROM analytics.bookings WHERE datetime = $1",
                reminder_time_str
            )

        for booking in bookings:
            try:
                if booking['user_id']:
                    print(booking['user_id'])
                    await bot.send_message(
                        chat_id=booking['user_id'],
                        text=f"⏰ Reminder: You have a meeting in one hour at {booking['datetime']} " \
                             f"with {booking['partner']} from {booking['company']} at {booking['restaurant']}"
                    )
                    logging.info(f"Sent reminder to {booking['user_id']} for booking at {booking['datetime']}")
            except Exception as e:
                logging.error(f"Error sending reminder to {booking['user_id']}: {e}")
    except Exception as e:
        logging.error(f"Error in booking reminders system: {e}")


async def on_startup(bot: Bot):
    """Функция, выполняемая при старте бота"""
    await AuthManager.create_pool()
    logging.info("Database connection pool created")

    # Инициализация планировщика напоминаний
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_booking_reminders,
        'interval',
        minutes=1,  # Проверка каждую минуту
        args=[bot],
        misfire_grace_time=60
    )
    scheduler.start()
    logging.info("Booking reminders scheduler started")


async def on_shutdown(bot: Bot):
    """Функция, выполняемая при выключении бота"""
    if AuthManager.flg:
        await AuthManager.flg.close()
        logging.info("Database connection pool closed")


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
    dp.include_router(my_bookings.calendar_router)

    # Подключаем обработчики жизненного цикла
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())