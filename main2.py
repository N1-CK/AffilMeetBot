# main2.py
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pygsheets
import pandas as pd
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('activity_log.log'),
        logging.StreamHandler()
    ]
)

# Конфигурация
DB_CONFIG = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME')
}

SPREADSHEET_NAME = os.getenv('GT_FILE_NAME')
WORKSHEET_NAME = os.getenv('GT_RESTAURANTS_FILE')


class GoogleSheetsToPostgresSync:
    def __init__(self):
        self.pg_pool = None
        self.gc = None

    async def connect_to_google_sheets(self):
        """Аутентификация в Google Sheets"""
        try:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            service_account_file = os.path.join(BASE_DIR, "conferencebothelper-1134fe7c70c9.json")

            if not os.path.exists(service_account_file):
                raise FileNotFoundError(f"Service account file not found at {service_account_file}")

            self.gc = pygsheets.authorize(service_account_file=service_account_file)
            logging.info("Успешная аутентификация в Google Sheets")
        except Exception as e:
            logging.error(f"Ошибка аутентификации: {str(e)}")
            raise

    async def get_google_sheets_data(self):
        """Получение данных из Google Sheets"""
        try:
            sh = self.gc.open(SPREADSHEET_NAME)
            worksheet = sh.worksheet_by_title(WORKSHEET_NAME)
            records = worksheet.get_all_records()
            return pd.DataFrame(records)
        except Exception as e:
            logging.error(f"Ошибка получения данных: {str(e)}")
            raise

    async def connect_to_postgres(self):
        """Подключение к PostgreSQL"""
        try:
            self.pg_pool = await asyncpg.create_pool(**DB_CONFIG)
            logging.info("Успешное подключение к PostgreSQL")
        except Exception as e:
            logging.error(f"Ошибка подключения к PostgreSQL: {str(e)}")
            raise

    async def prepare_postgres_table(self, df):
        """Create table in PostgreSQL if not exists"""
        try:
            async with self.pg_pool.acquire() as conn:
                # Create table with dynamic columns based on DataFrame
                columns = []
                for col, dtype in df.dtypes.items():
                    pg_type = 'TEXT'  # Default to TEXT
                    if 'int' in str(dtype):
                        pg_type = 'INTEGER'
                    elif 'float' in str(dtype):
                        pg_type = 'FLOAT'
                    elif 'datetime' in str(dtype):
                        pg_type = 'TIMESTAMP'
                    columns.append(f"{col} {pg_type}")

                delete_table_sql = f"""
                                DROP TABLE IF EXISTS analytics.restaurants
                                """

                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS analytics.restaurants (
                    id SERIAL PRIMARY KEY,
                    {', '.join(columns)}
                )
                """
                await conn.execute(delete_table_sql)
                await conn.execute(create_table_sql)
                logging.info("PostgreSQL table prepared")
        except Exception as e:
            logging.error(f"Error preparing PostgreSQL table: {str(e)}")
            raise

    async def insert_data_to_postgres(self, df):
        """Insert DataFrame data into PostgreSQL"""
        try:
            async with self.pg_pool.acquire() as conn:
                # Convert DataFrame to list of tuples
                data = [tuple(row) for row in df.to_numpy()]

                # Generate column names and placeholders
                columns = ', '.join(df.columns)
                placeholders = ', '.join([f'${i + 1}' for i in range(len(df.columns))])

                # Prepare and execute INSERT statement
                insert_sql = f"""
                INSERT INTO analytics.restaurants ({columns})
                VALUES ({placeholders})
                """

                await conn.executemany(insert_sql, data)
                logging.info(f"Successfully inserted {len(data)} rows into PostgreSQL")
                return True
        except Exception as e:
            logging.error(f"Error inserting data to PostgreSQL: {str(e)}")
            return False

    async def sync_data(self):
        """Основной метод синхронизации"""
        try:
            await self.connect_to_google_sheets()
            await self.connect_to_postgres()

            df = await self.get_google_sheets_data()
            if df.empty:
                logging.warning("Нет данных в Google Sheets")
                return False

            await self.prepare_postgres_table(df)
            return await self.insert_data_to_postgres(df)

        except Exception as e:
            logging.error(f"Ошибка синхронизации: {str(e)}")
            return False
        finally:
            if self.pg_pool:
                await self.pg_pool.close()


async def scheduled_sync():
    """Запуск синхронизации по расписанию"""
    sync = GoogleSheetsToPostgresSync()
    start_time = datetime.now()
    logging.info(f"🚀 Начало синхронизации в {start_time}")

    success = await sync.sync_data()

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    if success:
        logging.info(f"✅ Синхронизация завершена за {duration:.2f} сек")
    else:
        logging.error(f"❌ Синхронизация не удалась за {duration:.2f} сек")


async def main():
    # Настройка планировщика
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scheduled_sync,
        'interval',
        minutes=1,
        next_run_time=datetime.now()  # Запустить сразу при старте
    )
    scheduler.start()

    logging.info("Сервис синхронизации запущен. Ctrl+C для остановки.")

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Сервис остановлен")


if __name__ == "__main__":
    asyncio.run(main())