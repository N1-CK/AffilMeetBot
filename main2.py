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
BOOKINGS_WORKSHEET_NAME = os.getenv('GT_BOOKINGS_FILE', 'Bookings')


class GoogleSheetsToPostgresSync:
    def __init__(self):
        self.pg_pool = None
        self.gc = None
        self.last_sync_time = None

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

    async def sync_bookings_to_google_sheets(self):
        """Синхронизация с правильной обработкой временных меток"""
        try:
            await self.connect_to_google_sheets()
            await self.connect_to_postgres()

            # 1. Определяем структуру данных
            COLUMN_MAPPING = {
                'date': 'Date',
                'manager': 'Manager',
                'company': 'Company',
                'partner': 'Partner',
                'restaurant': 'Restaurant',
                'payment': 'Payment',
                'nickname': 'Nickname',
                'datetime': 'Datetime'
            }

            # 2. Получаем данные из Google Sheets
            sh = self.gc.open(SPREADSHEET_NAME)
            try:
                worksheet = sh.worksheet_by_title(BOOKINGS_WORKSHEET_NAME)
                worksheet.update_values('A1', [list(COLUMN_MAPPING.values())])
                gsheets_data = worksheet.get_all_records()

                # Создаем DataFrame и нормализуем названия столбцов
                df_gsheets = pd.DataFrame(gsheets_data)
                # Convert column names to strings before applying string operations
                df_gsheets.columns = [str(col).strip().lower() for col in df_gsheets.columns]

            except pygsheets.WorksheetNotFound:
                worksheet = sh.add_worksheet(BOOKINGS_WORKSHEET_NAME, rows=1000, cols=20)
                worksheet.update_values('A1', [list(COLUMN_MAPPING.values())])
                df_gsheets = pd.DataFrame(columns=COLUMN_MAPPING.keys())

            # Rest of your code remains the same...
            # 3. Получаем данные из PostgreSQL
            async with self.pg_pool.acquire() as conn:
                query = """
                        SELECT datetime        as date, \
                               manager         as manager, \
                               company         as company, \
                               partner         as partner, \
                               restaurant      as restaurant, \
                               CASE \
                                   WHEN payment_method = 'card' THEN 'Card' \
                                   ELSE 'Cash' \
                                   END         as payment, \
                               '@' || username as nickname, \
                               created_at      as datetime
                        FROM analytics.bookings
                        ORDER BY created_at
                        """
                records = await conn.fetch(query)

                # Конвертируем записи в список словарей
                postgres_data = []
                for record in records:
                    row = dict(record)
                    # Преобразуем datetime в строку
                    if 'datetime' in row and row['datetime']:
                        row['datetime'] = row['datetime'].strftime('%d.%m.%Y %H:%M')
                    postgres_data.append(row)

                df_postgres = pd.DataFrame(postgres_data)

            # 4. Приводим столбцы к единому формату
            # Для Google Sheets добавляем отсутствующие столбцы
            for col in COLUMN_MAPPING.keys():
                if col not in df_gsheets.columns:
                    df_gsheets[col] = None

            # 5. Находим новые строки
            if df_gsheets.empty:
                new_rows = df_postgres
            else:
                # Объединяем по всем столбцам
                merged = pd.merge(
                    df_postgres,
                    df_gsheets,
                    on=list(COLUMN_MAPPING.keys()),
                    how='left',
                    indicator=True
                )
                new_rows = merged[merged['_merge'] == 'left_only'][list(COLUMN_MAPPING.keys())]

            # 6. Добавляем новые строки в Google Sheets
            if not new_rows.empty:
                # Преобразуем в список словарей с правильными названиями столбцов
                rows_to_add = []
                for _, row in new_rows.iterrows():
                    formatted_row = {}
                    for col_key, col_name in COLUMN_MAPPING.items():
                        formatted_row[col_name] = row[col_key]
                    rows_to_add.append(formatted_row)

                # Конвертируем в список списков (значения в правильном порядке)
                values_to_add = [[row[col] for col in COLUMN_MAPPING.values()] for row in rows_to_add]

                # Добавляем данные
                worksheet.append_table(values=values_to_add)
                logging.info(f"Добавлено {len(values_to_add)} новых записей")
            else:
                logging.info("Нет новых записей для добавления")

            return True

        except Exception as e:
            logging.error(f"Ошибка синхронизации: {str(e)}", exc_info=True)
            return False
        finally:
            if self.pg_pool:
                await self.pg_pool.close()

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


async def scheduled_bookings_sync():
    """Запуск синхронизации бронирований по расписанию"""
    sync = GoogleSheetsToPostgresSync()
    start_time = datetime.now()
    logging.info(f"🚀 Начало синхронизации бронирований в {start_time}")

    success = await sync.sync_bookings_to_google_sheets()

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    if success:
        logging.info(f"✅ Синхронизация бронирований завершена за {duration:.2f} сек")
    else:
        logging.error(f"❌ Синхронизация бронирований не удалась за {duration:.2f} сек")


async def main():
    # Настройка планировщика
    scheduler = AsyncIOScheduler()

    # Синхронизация данных ресторанов
    scheduler.add_job(
        scheduled_sync,
        'interval',
        minutes=1,
        next_run_time=datetime.now()  # Запустить сразу при старте
    )

    # Синхронизация бронирований
    scheduler.add_job(
        scheduled_bookings_sync,
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