import asyncio
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pygsheets
import pandas as pd
import asyncpg
import os
from dotenv import load_dotenv
from aiogram import Bot
from Scripts.initial_commands import *
import bot_status_agent as agent

load_dotenv()

LOG_PATH = os.getenv('LOG_PATH')
# Configure logging
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
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
REPORT_WORKSHEET_NAME = os.getenv('GT_REPORT_FILE', 'Report')
TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN')
db_schema = os.getenv('DB_SCHEMA')

class GoogleSheetsToPostgresSync:
    def __init__(self, bot: Bot = None):
        self.pg_pool = None
        self.gc = None
        self.last_sync_time = None
        self.bot = bot

    async def connect_to_postgres(self):
        """Подключение к PostgreSQL"""
        try:
            if self.pg_pool is None:
                self.pg_pool = await asyncpg.create_pool(**DB_CONFIG)
            return True
        except Exception as e:
            logging.error(f"Ошибка подключения к PostgreSQL: {str(e)}")
            return False

    async def close_connections(self):
        """Закрытие соединений"""
        if self.pg_pool:
            await self.pg_pool.close()
            self.pg_pool = None

    async def check_and_create_tables(self):
        """Проверка и создание таблиц если нужно"""
        try:
            await AuthManager.create_tables()
            return True
        except Exception as e:
            logging.error(f"Error checking tables: {str(e)}")
            return False

    async def connect_to_google_sheets(self):
        """Аутентификация в Google Sheets"""
        try:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            service_account_file = os.path.join(BASE_DIR, "configs/conferencebothelper-1134fe7c70c9.json")

            if not os.path.exists(service_account_file):
                raise FileNotFoundError(f"Service account file not found at {service_account_file}")

            self.gc = pygsheets.authorize(service_account_file=service_account_file)
            # logging.info("Успешная аутентификация в Google Sheets")
            return True
        except Exception as e:
            logging.error(f"Ошибка аутентификации: {str(e)}")
            return False

    async def get_google_sheets_data(self):
        """Получение данных из Google Sheets"""
        try:
            sh = self.gc.open(SPREADSHEET_NAME)
            worksheet = sh.worksheet_by_title(WORKSHEET_NAME)
            records = worksheet.get_all_records()
            return pd.DataFrame(records)
        except Exception as e:
            logging.error(f"Ошибка получения данных: {str(e)}")
            return pd.DataFrame()

    async def prepare_postgres_table(self, df):
        """Создание таблицы в PostgreSQL"""
        try:
            async with self.pg_pool.acquire() as conn:
                try:
                    count_result = await conn.fetchval(f'''
                        SELECT COUNT(*) FROM {db_schema}.restaurants
                    ''')

                    if count_result == 0:
                        raise Exception("Table is empty, skipping DELETE operation")
                    else:
                        await conn.execute(f'''DELETE FROM {db_schema}.restaurants
                            WHERE created_at != (
                                    select MAX(created_at) from {db_schema}.restaurants
                                    WHERE created_at IS NOT NULL
                            )     
                        ''')
                        return True
                except Exception as e:
                    logging.error(f"PostgreSQL: {str(e)}")

                    # Создаем новую таблицу с динамическими колонками
                    columns = []

                    df['created_at'] = datetime.now()

                    for col, dtype in df.dtypes.items():
                        pg_type = 'TEXT'  # По умолчанию TEXT
                        if 'int' in str(dtype):
                            pg_type = 'INTEGER'
                        elif 'float' in str(dtype):
                            pg_type = 'FLOAT'
                        elif 'datetime' in str(dtype):
                            pg_type = 'TIMESTAMP'
                        columns.append(f"{col} {pg_type}")

                    try:
                        await conn.execute(f'''
                            DROP TABLE IF EXISTS {db_schema}.restaurants
                        ''')

                        create_table_sql = f"""
                        CREATE TABLE IF NOT EXISTS {db_schema}.restaurants (
                            id SERIAL PRIMARY KEY,
                            {', '.join(columns)}
                        )
                        """
                        await conn.execute(create_table_sql)
                        logging.info("Таблица restaurants создана")
                        return True
                    except Exception as e:
                        logging.error(f"Ошибка создания таблицы: {str(e)}")
                        return False
        except Exception as e:
            logging.error(f"Таблица уже есть, либо произошла ошибка")
            return True

    async def insert_data_to_postgres(self, df):
        """Вставка данных в PostgreSQL"""
        try:
            async with self.pg_pool.acquire() as conn:
                df['created_at'] = datetime.now()
                # Конвертируем DataFrame в список кортежей
                data = [tuple(row) for row in df.to_numpy()]
                # Генерируем имена колонок и плейсхолдеры
                columns = ', '.join(df.columns)
                placeholders = ', '.join([f'${i + 1}' for i in range(len(df.columns))])

                # Подготавливаем и выполняем INSERT
                insert_sql = f"""
                INSERT INTO {db_schema}.restaurants ({columns})
                VALUES ({placeholders})
                """

                await conn.executemany(insert_sql, data)
                logging.info(f"Успешно вставлено {len(data)} записей")
                return True
        except Exception as e:
            logging.error(f"Ошибка вставки данных: {str(e)}")
            return False

    async def sync_data(self):
        """Основная функция синхронизации"""
        try:
            if not await self.check_and_create_tables():
                return False

            # Подключаемся к сервисам
            if not await self.connect_to_google_sheets():
                logging.error(f"Ошибка connect_to_google_sheets")
                return False
            if not await self.connect_to_postgres():
                logging.error(f"Ошибка connect_to_postgres")
                return False

            # Получаем данные
            df = await self.get_google_sheets_data()
            if df.empty:
                logging.warning("Нет данных в Google Sheets")
                return False

            # Подготавливаем таблицу и вставляем данные
            if not await self.prepare_postgres_table(df):
                logging.error(f"Ошибка prepare_postgres_table")
                return False
            if not await self.insert_data_to_postgres(df):
                logging.error(f"Ошибка insert_data_to_postgres")
                return False
            return True
        except Exception as e:
            logging.error(f"Ошибка синхронизации: {str(e)}")
            return False
        finally:
            await self.close_connections()

    async def sync_bookings_to_google_sheets(self):
        """Синхронизация бронирований с Google Sheets"""
        try:
            if not await self.check_and_create_tables():
                return False
            # Подключаемся к сервисам
            if not await self.connect_to_google_sheets():
                return False
            if not await self.connect_to_postgres():
                return False

            # Определяем структуру данных
            COLUMN_MAPPING = {
                'date': 'Date',
                'manager': 'Manager',
                'managercompany': 'ManagerCompany',
                'partner': 'Partner',
                'partnercompany': 'PartnerCompany',
                'partnertype': 'PartnerType',
                'restaurant': 'Restaurant',
                'people': 'People',
                'payment': 'Payment',
                'nickname': 'Nickname',
                'datetime': 'Datetime'
            }

            # Получаем данные из Google Sheets
            sh = self.gc.open(SPREADSHEET_NAME)
            try:
                worksheet = sh.worksheet_by_title(BOOKINGS_WORKSHEET_NAME)
                worksheet.update_values('A1', [list(COLUMN_MAPPING.values())])
                gsheets_data = worksheet.get_all_records()
                df_gsheets = pd.DataFrame(gsheets_data)
                df_gsheets.columns = [str(col).strip().lower() for col in df_gsheets.columns]
            except pygsheets.WorksheetNotFound:
                worksheet = sh.add_worksheet(BOOKINGS_WORKSHEET_NAME, rows=1000, cols=20)
                worksheet.update_values('A1', [list(COLUMN_MAPPING.values())])
                df_gsheets = pd.DataFrame(columns=COLUMN_MAPPING.keys())

            # Получаем данные из PostgreSQL
            async with self.pg_pool.acquire() as conn:
                query = f"""
                with book1 as (SELECT datetime        as date,
                          manager         as manager,
                          company         as company,
                          partner         as partner,
                          PartnerType     as partnertype,
                          restaurant      as restaurant,
                          people,
                          CASE
                              WHEN payment_method = 'card' THEN 'Card'
                              ELSE 'Cash'
                              END         as payment,
                          '@' || username as nickname,
                          username,
                          created_at      as datetime
                   FROM {db_schema}.bookings
                   ORDER BY created_at)

                select date, manager, aut.company as managercompany,
                       partner, book1.company as partnercompany,
                       partnertype, restaurant, people,
                       payment, '@' || book1.username as nickname,
                       datetime
                
                from book1
                left join {db_schema}.auth_users aut on (book1.username = aut.username)
                """
                records = await conn.fetch(query)
                postgres_data = [dict(record) for record in records]
                for row in postgres_data:
                    if 'datetime' in row and row['datetime']:
                        row['datetime'] = row['datetime'].strftime('%d.%m.%Y %H:%M')
                df_postgres = pd.DataFrame(postgres_data)

            # Добавляем отсутствующие колонки
            for col in COLUMN_MAPPING.keys():
                if col not in df_gsheets.columns:
                    df_gsheets[col] = None



            # Находим новые строки
            if df_gsheets.empty:
                new_rows = df_postgres
            else:
                numeric_cols = ['people']
                df_gsheets[numeric_cols] = df_gsheets[numeric_cols].astype(str)
                df_postgres[numeric_cols] = df_postgres[numeric_cols].astype(str)

                merged = pd.merge(
                    df_postgres,
                    df_gsheets,
                    on=list(COLUMN_MAPPING.keys()),
                    how='left',
                    indicator=True
                )
                new_rows = merged[merged['_merge'] == 'left_only'][list(COLUMN_MAPPING.keys())]

            # Добавляем новые строки в Google Sheets
            if not new_rows.empty:
                rows_to_add = []
                for _, row in new_rows.iterrows():
                    formatted_row = {}
                    for col_key, col_name in COLUMN_MAPPING.items():
                        formatted_row[col_name] = row[col_key]
                    rows_to_add.append(formatted_row)

                values_to_add = [[row[col] for col in COLUMN_MAPPING.values()] for row in rows_to_add]
                worksheet.append_table(values=values_to_add)
                logging.info(f"Добавлено {len(values_to_add)} новых записей в бронирования")
            else:
                logging.info("Нет новых записей для добавления в бронирования")

            return True
        except Exception as e:
            logging.error(f"Ошибка синхронизации бронирований: {str(e)}")
            return False
        finally:
            await self.close_connections()

    async def sync_report_to_google_sheets(self):
        """Синхронизация отчетов с Google Sheets"""
        try:
            if not await self.check_and_create_tables():
                return False
            # Подключаемся к сервисам
            if not await self.connect_to_google_sheets():
                return False
            if not await self.connect_to_postgres():
                return False

            # Определяем структуру данных для отчета
            REPORT_COLUMN_MAPPING = {
                'date': 'Date',
                'manager': 'Manager',
                'partner': 'Partner',
                'result': 'Result',
                'budget': 'Budget',
                'nickname': 'Nickname',
                'datetime': 'Datetime'
            }

            # Получаем данные из Google Sheets
            sh = self.gc.open(SPREADSHEET_NAME)
            try:
                worksheet = sh.worksheet_by_title(REPORT_WORKSHEET_NAME)
                worksheet.update_values('A1', [list(REPORT_COLUMN_MAPPING.values())])
                gsheets_data = worksheet.get_all_records()
                df_gsheets = pd.DataFrame(gsheets_data)
                # Standardize column names (lowercase and strip)
                df_gsheets.columns = [str(col).strip().lower() for col in df_gsheets.columns]
            except pygsheets.WorksheetNotFound:
                worksheet = sh.add_worksheet(REPORT_WORKSHEET_NAME, rows=1000, cols=20)
                worksheet.update_values('A1', [list(REPORT_COLUMN_MAPPING.values())])
                df_gsheets = pd.DataFrame(columns=REPORT_COLUMN_MAPPING.keys())

            # Получаем данные из PostgreSQL
            async with self.pg_pool.acquire() as conn:
                query = f"""
                        SELECT to_date(meeting_date, 'DD.MM.YYYY') as date, \
                               manager                             as manager, \
                               partner                             as partner, \
                               result                              as result, \
                               budget                              as budget, \
                               '@' || username                     as nickname, \
                               created_at                          as datetime
                        FROM {db_schema}.reports
                        ORDER BY created_at
                        """
                records = await conn.fetch(query)
                postgres_data = [dict(record) for record in records]

                for row in postgres_data:
                    if 'datetime' in row and row['datetime']:
                        if isinstance(row['datetime'], str):
                            row['datetime'] = datetime.strptime(row['datetime'], '%d.%m.%Y %H:%M')
                        row['datetime'] = row['datetime'].strftime('%d.%m.%Y %H:%M')

                    if 'date' in row and row['date']:
                        if isinstance(row['date'], str):
                            row['date'] = datetime.strptime(row['date'], '%d.%m.%Y').date()
                        row['date'] = row['date'].strftime('%d.%m.%Y')

                df_postgres = pd.DataFrame(postgres_data)

            # Ensure all expected columns exist in both DataFrames
            for col in REPORT_COLUMN_MAPPING.keys():
                if col not in df_gsheets.columns:
                    df_gsheets[col] = None
                if col not in df_postgres.columns:
                    df_postgres[col] = None

            # Convert all columns to string for comparison
            df_gsheets = df_gsheets.astype(str)
            df_postgres = df_postgres.astype(str)

            if df_postgres.empty:
                test_row = {
                    'manager': 'Test',
                    'datetime': '2025-11-04 16:44:16',
                    'partner': 'Test',
                    'result': 'Test',
                    'budget': '1000',
                    'username': 'test_user',
                    'meeting_date': '04.11.2025'
                }
                # Создаем DataFrame с тестовой строкой
                df_postgres = pd.DataFrame([test_row])
                logging.info("Добавлена тестовая строка в пустой df_postgres")

            # Create composite key for comparison
            KEY_COLUMNS = ['manager', 'datetime']  # Or other unique identifier columns
            df_postgres['composite_key'] = df_postgres[KEY_COLUMNS].apply(lambda x: '|'.join(x), axis=1)
            df_gsheets['composite_key'] = df_gsheets[KEY_COLUMNS].apply(lambda x: '|'.join(x), axis=1)

            # Find new rows
            new_rows = df_postgres[~df_postgres['composite_key'].isin(df_gsheets['composite_key'])]
            new_rows = new_rows[list(REPORT_COLUMN_MAPPING.keys())]

            # Добавляем новые строки в Google Sheets
            if not new_rows.empty:
                values_to_add = []
                for _, row in new_rows.iterrows():
                    formatted_row = [row[col] for col in REPORT_COLUMN_MAPPING.keys()]
                    values_to_add.append(formatted_row)

                # Append new rows starting after the last row
                start_row = len(df_gsheets) + 2  # +1 for header, +1 for next row
                worksheet.update_values(f'A{start_row}', values_to_add)
                logging.info(f"Добавлено {len(values_to_add)} новых записей в отчеты")
            else:
                logging.info("Нет новых записей для добавления в отчеты")

            return True
        except Exception as e:
            logging.error(f"Ошибка синхронизации отчетов: {str(e)}", exc_info=True)
            return False
        finally:
            await self.close_connections()

    async def send_booking_reminders(self):
        """Send booking reminders (pre-meeting and post-meeting)"""
        if not self.bot:
            logging.warning("Bot instance not available for sending reminders")
            return

        try:
            if not await self.connect_to_postgres():
                return

            now = datetime.now()

            # Pre-meeting reminders (24h and 1.5h before)
            reminder_time_24h_before = now + timedelta(hours=24)
            reminder_time_1_5h_before = now + timedelta(hours=1, minutes=30)

            # Post-meeting reminder (24h after)
            reminder_time_24h_after = now - timedelta(hours=24)

            # Format times for SQL query (use consistent format)
            time_format = '%d.%m.%Y %H:%M'
            reminder_time_24h_before_str = reminder_time_24h_before.strftime(time_format)
            reminder_time_1_5h_before_str = reminder_time_1_5h_before.strftime(time_format)
            reminder_time_24h_after_str = reminder_time_24h_after.strftime(time_format)

            async with self.pg_pool.acquire() as conn:
                # Get bookings that match any of our reminder times
                bookings = await conn.fetch(
                    f"SELECT * FROM {db_schema}.bookings WHERE datetime IN ($1, $2, $3)",
                    reminder_time_24h_before_str,
                    reminder_time_1_5h_before_str,
                    reminder_time_24h_after_str
                )

            for booking in bookings:
                try:
                    if not booking['user_id']:
                        continue

                    # Determine which reminder to send
                    reminder_text = ""
                    if booking['datetime'] == reminder_time_24h_before_str:
                        # 24-hour pre-meeting reminder
                        reminder_text = (
                            f"🔔 24-Hour Reminder: You have a meeting tomorrow at {booking['datetime']} "
                            f"with {booking['partner']} from {booking['company']} at {booking['restaurant']}"
                        )
                    elif booking['datetime'] == reminder_time_1_5h_before_str:
                        # 1.5-hour pre-meeting reminder
                        reminder_text = (
                            f"⏰ 1.5-Hour Reminder: Your meeting starts soon at {booking['datetime']} "
                            f"with {booking['partner']} from {booking['company']} at {booking['restaurant']}"
                        )
                    elif booking['datetime'] == reminder_time_24h_after_str:
                        # 24-hour post-meeting reminder (report submission)
                        reminder_text = (
                            f"📝 Report Reminder: It's been 24 hours since your meeting with {booking['partner']} "
                            f"from {booking['company']}. Don't forget to submit your meeting report!\n\n"
                        )

                    if reminder_text:
                        await self.bot.send_message(
                            chat_id=booking['user_id'],
                            text=reminder_text
                        )
                        logging.info(f"Successfully sent reminder to {booking['user_id']}")

                except Exception as e:
                    logging.error(f"Error sending reminder to {booking['user_id']}: {str(e)}", exc_info=True)

        except Exception as e:
            logging.error(f"Error in send_booking_reminders: {str(e)}", exc_info=True)
        finally:
            await self.close_connections()


async def scheduled_sync():
    """Задача синхронизации данных"""
    bot = Bot(token=TG_BOT_TOKEN)
    sync = GoogleSheetsToPostgresSync(bot)
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
    """Задача синхронизации бронирований"""
    bot = Bot(token=TG_BOT_TOKEN)
    sync = GoogleSheetsToPostgresSync(bot)
    start_time = datetime.now()
    logging.info(f"🚀 Начало синхронизации бронирований в {start_time}")

    success = await sync.sync_bookings_to_google_sheets()

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    if success:
        logging.info(f"✅ Синхронизация бронирований завершена за {duration:.2f} сек")
    else:
        logging.error(f"❌ Синхронизация бронирований не удалась за {duration:.2f} сек")


async def scheduled_report_sync():
    """Задача синхронизации отчетов"""
    bot = Bot(token=TG_BOT_TOKEN)
    sync = GoogleSheetsToPostgresSync(bot)
    start_time = datetime.now()
    # logging.info(f"🚀 Начало синхронизации отчетов в {start_time}")

    success = await sync.sync_report_to_google_sheets()

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # if success:
    #     logging.info(f"✅ Синхронизация отчетов завершена за {duration:.2f} сек")
    if not success:
        logging.error(f"❌ Синхронизация отчетов не удалась за {duration:.2f} сек")

async def initialize_database():
    """Инициализация базы данных для планировщика"""
    sync = GoogleSheetsToPostgresSync()
    if await sync.connect_to_postgres():
        # Создаем таблицы через AuthManager
        await AuthManager.create_pool()
        return True
    return False

async def send_reminders():
    """Задача отправки напоминаний"""
    bot = Bot(token=TG_BOT_TOKEN)
    sync = GoogleSheetsToPostgresSync(bot)
    await sync.send_booking_reminders()

async def periodic_status_update():
    """Периодическое обновление статуса бота каждую минуту"""
    while True:
        try:
            result = await agent.update_bot_status()
            if result["success"]:
                logging.info("Статус бота успешно обновлен")
            else:
                logging.error(f"Ошибка обновления статуса бота: {result['error']}")
        except Exception as e:
            logging.error(f"Исключение при обновлении статуса бота: {e}")

        # Ждем 60 секунд перед следующим обновлением
        await asyncio.sleep(60)

async def main():
    if not await initialize_database():
        logging.error("Failed to initialize database")
        return

    """Основная функция"""
    scheduler = AsyncIOScheduler()

    # Добавляем задачи в планировщик
    scheduler.add_job(
        scheduled_sync,
        'interval',
        minutes=1,
        next_run_time=datetime.now()
    )

    scheduler.add_job(
        scheduled_bookings_sync,
        'interval',
        minutes=1,
        next_run_time=datetime.now()
    )

    scheduler.add_job(
        scheduled_report_sync,
        'interval',
        minutes=1,
        next_run_time=datetime.now()
    )

    scheduler.add_job(
        send_reminders,
        'interval',
        minutes=1,
        next_run_time=datetime.now()
    )

    scheduler.add_job(
        periodic_status_update,
        'interval',
        minutes=1,
        next_run_time=datetime.now()
    )

    scheduler.start()
    logging.info("Сервис синхронизации и напоминаний запущен. Ctrl+C для остановки.")

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Сервис остановлен")


if __name__ == "__main__":
    asyncio.run(main())