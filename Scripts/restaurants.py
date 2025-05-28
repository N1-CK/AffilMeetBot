import pygsheets
import os
import logging
import asyncpg
import pandas as pd
from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv

from Scripts.initial_commands import check_auth
from keyboards import *
from texts import *

load_dotenv()

router = Router()

class RestaurantsStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_manager = State()
    waiting_for_partner = State()
    waiting_for_result = State()
    waiting_for_report = State()


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Google Sheets configuration
SPREADSHEET_NAME = os.getenv('GT_FILE_NAME')
WORKSHEET_NAME = os.getenv('GT_RESTAURANTS_FILE')

# PostgreSQL configuration
DB_CONFIG = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME')
}


class GoogleSheetsToPostgres:
    def __init__(self):
        self.pg_pool = None
        self.gc = None

    async def connect_to_google_sheets(self):
        """Authenticate with Google Sheets"""
        try:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            PROJECT_ROOT = os.path.dirname(BASE_DIR)
            service_account_file = os.path.join(PROJECT_ROOT, "conferencebothelper-1134fe7c70c9.json")

            if not os.path.exists(service_account_file):
                raise FileNotFoundError(f"Service account file not found at {service_account_file}")

            self.gc = pygsheets.authorize(service_account_file=service_account_file)
            logging.info("Google Sheets authentication successful")
        except Exception as e:
            logging.error(f"Google Sheets authentication failed: {str(e)}")
            raise

    async def get_google_sheets_data(self):
        """Fetch data from Google Sheets worksheet"""
        try:
            sh = self.gc.open(SPREADSHEET_NAME)
            worksheet = sh.worksheet_by_title(WORKSHEET_NAME)

            # Get all records as pandas DataFrame
            records = worksheet.get_all_records()
            df = pd.DataFrame(records)

            logging.info(f"Retrieved {len(df)} records from Google Sheets")
            return df
        except Exception as e:
            logging.error(f"Error fetching Google Sheets data: {str(e)}")
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

    async def transfer_data(self):
        """Main method to transfer data from Google Sheets to PostgreSQL"""
        try:
            # Initialize connections
            await self.connect_to_postgres()
            await self.connect_to_google_sheets()

            # Get data from Google Sheets
            df = await self.get_google_sheets_data()
            if df.empty:
                logging.warning("No data found in Google Sheets")
                return False

            # Prepare PostgreSQL table
            await self.prepare_postgres_table(df)

            # Insert data
            return await self.insert_data_to_postgres(df)

        except Exception as e:
            logging.error(f"Data transfer failed: {str(e)}", exc_info=True)
            return False
        finally:
            # Clean up connections
            if self.pg_pool:
                await self.pg_pool.close()
            logging.info("Connections closed")

    async def connect_to_postgres(self):
        """Create PostgreSQL connection pool"""
        try:
            self.pg_pool = await asyncpg.create_pool(**DB_CONFIG)
            logging.info("PostgreSQL connection pool created")
        except Exception as e:
            logging.error(f"PostgreSQL connection failed: {str(e)}")
            raise

async def get_conference_from_db():
    """Получение ресторанов из PostgreSQL"""
    try:
        async with asyncpg.create_pool(**DB_CONFIG) as pool:
            async with pool.acquire() as conn:
                query = """
                    SELECT distinct city
                    FROM analytics.restaurants
                """
                records = await conn.fetch(query)
                return pd.DataFrame(records, columns=['city'])
    except Exception as e:
        logging.error(f"Ошибка при получении ресторанов: {str(e)}")
        return pd.DataFrame()

async def get_restaurants_from_db_by_conf(conf):
    """Получение ресторанов из PostgreSQL"""
    try:
        async with asyncpg.create_pool(**DB_CONFIG) as pool:
            async with pool.acquire() as conn:
                query = f"""
                    SELECT id, city, conference, restaurant, address, cost, link, comment
                    FROM analytics.restaurants
                    WHERE city = '{conf}'
                    ORDER BY cost DESC
                """
                records = await conn.fetch(query)
                return pd.DataFrame(records, columns=['id', 'city', 'conference', 'restaurant', 'address', 'cost', 'link', 'comment'])
    except Exception as e:
        logging.error(f"Ошибка при получении ресторанов: {str(e)}")
        return pd.DataFrame()


async def get_restaurants_from_db_by_id(index):
    """Получение ресторанов из PostgreSQL"""
    try:
        async with asyncpg.create_pool(**DB_CONFIG) as pool:
            async with pool.acquire() as conn:
                query = f"""
                    SELECT city, conference, restaurant, address, cost, link, comment
                    FROM analytics.restaurants
                    WHERE id = {index}
                    ORDER BY cost DESC
                """
                records = await conn.fetch(query)
                return pd.DataFrame(records, columns=['city', 'conference', 'restaurant', 'address', 'cost', 'link', 'comment'])
    except Exception as e:
        logging.error(f"Ошибка при получении ресторанов: {str(e)}")
        return pd.DataFrame()

@router.callback_query(F.data == "restaurants")
async def show_restaurants(call: CallbackQuery):
    keyboard_list_rest = await conference_menu()
    await call.message.edit_text(
        "Choose an option:",
        reply_markup=keyboard_list_rest
    )

@router.callback_query(F.data == "conference_list")
async def conference_get_info(call: CallbackQuery, state: FSMContext):
    await state.update_data(confa_name="")
    try:
        df_conferences = await get_conference_from_db()
        lst1 = []


        if not df_conferences.empty:
            # rest_len = len(df_rest)
            i = 1
            lss = list()
            for _, row in df_conferences.iterrows():
                btn_text = f"{row['city']}"
                if i % 2 == 0:
                    lss.append(InlineKeyboardButton(
                        text=f'🌆 {btn_text}',
                        callback_data=f"confa_{row['city']}"))
                    lst1.append(lss)
                else:
                    lss = [InlineKeyboardButton(
                        text=f'🌆 {btn_text}',
                        callback_data=f"confa_{row['city']}")]
                    if i == len(df_conferences):
                        lst1.append(lss)
                i += 1

        # Добавляем навигационные кнопки
        lst1.append(
            [InlineKeyboardButton(text=f"◀️ Back", callback_data=f"restaurants"),
             InlineKeyboardButton(text=f"🏠 Main Menu", callback_data=f"main_page")]
        )

        inline_kb = InlineKeyboardMarkup(inline_keyboard=lst1)

        await call.answer()
        if len(lst1) <= 1:  # Только навигационные кнопки
            await call.message.edit_text(
                "No available cities found",
                reply_markup=inline_kb
            )
        else:
            text = "Choose the city:"
            await call.message.edit_text(
                text,
                reply_markup=inline_kb,
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logging.error(f"Error in show_restaurants: {str(e)}")
        await call.answer("Error loading data", show_alert=True)



@router.callback_query(F.data.startswith("confa_"))
async def show_restaurants2(call: CallbackQuery, state: FSMContext):
    confa = call.data.split('_')[1]
    await state.update_data(confa_name=confa)
    print(confa)
    try:
        df_rest = await get_restaurants_from_db_by_conf(confa)
        lst = []

        if not df_rest.empty:
            i = 1
            lss = list()
            for _, row in df_rest.iterrows():
                btn_text = f"{row['restaurant']}"
                if i % 2 == 0:
                    lss.append(InlineKeyboardButton(
                    text=btn_text,
                    callback_data=f"rest_{row['id']}"))
                    lst.append(lss)
                else:
                    lss = [InlineKeyboardButton(
                    text=btn_text,
                    callback_data=f"rest_{row['id']}")]
                    if i == len(df_rest):
                        lst.append(lss)
                i += 1

        # Добавляем навигационные кнопки
        lst.append(
            [InlineKeyboardButton(text=f"◀️ Back", callback_data=f"conference_list"),
            InlineKeyboardButton(text=f"🏠 Main Menu", callback_data=f"main_page")]
        )

        inline_kb = InlineKeyboardMarkup(inline_keyboard=lst)

        await call.answer()
        if len(lst) <= 1:  # Только навигационные кнопки
            await call.message.edit_text(
                "No available restaurants or conferences found",
                reply_markup=inline_kb
            )
        else:
            text = "🍽 *Available options:*\n\n" \
                   "Conferences from your flights:\n" \
                   "or select restaurants in Dubai (rating 4.5+)"
            await call.message.edit_text(
                text,
                reply_markup=inline_kb,
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logging.error(f"Error in show_restaurants: {str(e)}")
        await call.answer("Error loading data", show_alert=True)


@router.callback_query(F.data.startswith('rest_'))
async def flight_info_tg(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    confa = data.get('confa_name')

    rest = int(call.data.split('_')[1])
    df_rest_info = await get_restaurants_from_db_by_id(rest)

    str_final = txt_restaurant_info.format(
        name=df_rest_info['restaurant'][0],
        city=df_rest_info['city'][0],
        address=df_rest_info['address'][0],
        cost=df_rest_info['cost'][0],
        link=df_rest_info['link'][0],
        comment=df_rest_info['comment'][0]
    )

    await call.answer()
    await call.message.edit_text(str_final, reply_markup=await restaurants_menu_back(confa),
                                 parse_mode=ParseMode.MARKDOWN)


# Example usage
async def main():
    transfer = GoogleSheetsToPostgres()
    success = await transfer.transfer_data()
    if success:
        print("Data transfer completed successfully")
    else:
        print("Data transfer failed")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())