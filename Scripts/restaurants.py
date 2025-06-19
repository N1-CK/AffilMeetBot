import os
import logging
import asyncpg
import pandas as pd
from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery
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


LOG_PATH = os.getenv('LOG_PATH')
# Configure logging
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.WARNING,
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
@check_auth
async def show_restaurants(call: CallbackQuery):
    keyboard_list_rest = await conference_menu()
    await call.message.edit_text(
        "Choose an option:",
        reply_markup=keyboard_list_rest
    )

@router.callback_query(F.data == "conference_list")
@check_auth
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
@check_auth
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
            text = "🍽 *Available restaurants:*"
            await call.message.edit_text(
                text,
                reply_markup=inline_kb,
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logging.error(f"Error in show_restaurants: {str(e)}")
        await call.answer("Error loading data", show_alert=True)


@router.callback_query(F.data.startswith('rest_'))
@check_auth
async def flight_info_tg(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    confa = data.get('confa_name')

    rest = int(call.data.split('_')[1])
    df_rest_info = await get_restaurants_from_db_by_id(rest)
    print(df_rest_info)

    str_final = txt_restaurant_info.format(
        name=df_rest_info['restaurant'][0].replace("&", "&amp;").replace("'", "&#39;"),
        city=df_rest_info['city'][0],
        address=df_rest_info['address'][0],
        cost=df_rest_info['cost'][0],
        link=df_rest_info['link'][0],
        comment=df_rest_info['comment'][0]
    )

    await call.answer()
    await call.message.edit_text(str_final, reply_markup=await restaurants_menu_back(confa),
                                 parse_mode=ParseMode.HTML)