import os
import logging
import asyncpg
from functools import wraps
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Router, F
from dotenv import load_dotenv
from keyboards import *

load_dotenv()

# Конфигурация
PASSWORD = os.getenv('PASSWORD')
DB_CONFIG = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME')
}

router = Router()

companies_list = os.getenv('COMPANIES_LIST').split(',')

class AuthState(StatesGroup):
    waiting_for_password = State()
    waiting_for_company_brand = State()
    waiting_for_company_brand2 = State()
    waiting_for_company_brand3 = State()

class AuthManager:
    flg = None

    @classmethod
    async def create_pool(cls):
        if cls.flg is None:
            cls.flg = await asyncpg.create_pool(**DB_CONFIG)
            # Создаем таблицу если ее нет
            async with cls.flg.acquire() as conn:
                await conn.execute('''
                       CREATE TABLE IF NOT EXISTS analytics.auth_users
                       (
                           username TEXT PRIMARY KEY,
                           company TEXT NOT NULL,
                           flag BOOLEAN
                        )
                   ''')

                await conn.execute('''
                       CREATE TABLE IF NOT EXISTS analytics.users_booking
                       (
                           username TEXT NOT NULL,
                           company TEXT NOT NULL,
                           flag BOOLEAN
                       )
                   ''')


                await conn.execute('''
                       CREATE TABLE IF NOT EXISTS analytics.bookings
                       (
                           id SERIAL PRIMARY KEY,
                           username TEXT NOT NULL,
                           manager TEXT NOT NULL,
                           datetime TEXT NOT NULL,
                           bookings TEXT NOT NULL,
                           partner TEXT NOT NULL,
                           restaurant TEXT NOT NULL,
                           payment_method TEXT NOT NULL,
                           created_at TIMESTAMP DEFAULT NOW()
                           )
                   ''')


    @classmethod
    async def is_authorized(cls, username):
        if not username:
            return False

        async with cls.flg.acquire() as conn:
            result = await conn.fetchval(
                'SELECT flag FROM analytics.auth_users WHERE username = $1',
                username
            )
            return result

    @classmethod
    async def add_user(cls, username, company):
        if not username or not company:
            return False

        async with cls.flg.acquire() as conn:
            try:
                await conn.execute(
                    'INSERT INTO analytics.auth_users (username, company, flag) VALUES ($1, $2, true)',
                    username, company
                )
                return True
            except asyncpg.UniqueViolationError:
                logging.warning(f"User {username} already exists")
                await conn.execute(
                    '''
                    UPDATE analytics.auth_users
                    SET flag = 'true'
                    WHERE username = $1
                    ''', username
                )
                await conn.execute(
                    '''
                    UPDATE analytics.auth_users
                    SET company = $2
                    WHERE username = $1
                    ''', username, company
                )
                return True
            except Exception as e:
                logging.error(f"Error adding user: {e}")
                return False

    @classmethod
    async def add_report(cls, username: str, company: str, report_data: dict) -> bool:
        try:
            async with cls.flg.acquire() as conn:
                await conn.execute(
                    '''
                    INSERT INTO analytics.reports
                        (username, company, meeting_date, manager, partner, result, budget, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ''',
                    username,
                    company,
                    report_data.get('Date'),
                    report_data.get('Manager'),
                    report_data.get('Partner'),
                    report_data.get('Result'),
                    report_data.get('Budget'),
                    report_data.get('Datetime')
                )
                return True
        except Exception as e:
            logging.error(f"Error saving report: {e}")
            return False


def check_auth(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        update = args[0]  # Message или CallbackQuery
        username = update.from_user.username
        if not await AuthManager.is_authorized(username):
            if isinstance(update, Message):
                await update.answer("Please authenticate first. Send /start and enter the password.")
            elif isinstance(update, CallbackQuery):
                # keyboard = await main_menu()
                await update.answer("Authentication required. Send /start first.", show_alert=True)
            return
        return await func(*args, **kwargs)
    return wrapper


@router.message(Command("start"))
async def start_command(msg: Message, state: FSMContext):
    username = msg.from_user.username

    if not username:
        await msg.answer("Please set a username in your Telegram profile to use this bot.")
        return

    if await AuthManager.is_authorized(username):
        keyboard = await main_menu()
        await msg.answer('Hey! I’m AffilMeet, your trusty meeting setup bot. \nHow can I help you?', reply_markup=keyboard)
    else:
        await state.set_state(AuthState.waiting_for_password)
        await msg.answer("Please enter the password to access the bot:")


@router.message(AuthState.waiting_for_password)
async def process_password(msg: Message, state: FSMContext):
    username = msg.from_user.username

    if not username:
        await msg.answer("Please set a username in your Telegram profile to use this bot.")
        return

    if msg.text == PASSWORD:
        await state.clear()
        await msg.answer("Password correct! What brand do you work with?")
        await state.set_state(AuthState.waiting_for_company_brand)
    else:
        await msg.answer("Incorrect password. Please try again or contact the administrator.")

@router.message(AuthState.waiting_for_company_brand)
async def process_company_brand(msg: Message, state: FSMContext):
    user_input = msg.text.lower()
    matches = [word for word in companies_list if user_input.lower() in word.lower()]

    # Выводим результат
    if matches:
        inline_kb_list = list()
        for match in matches:
            inline_kb_list.append(
                [InlineKeyboardButton(text=f"{match}", callback_data=f"{match}_policy-conference")]
            )
        keyboard = InlineKeyboardMarkup(inline_keyboard=inline_kb_list)

        await msg.answer('Choose your company brand:', reply_markup=keyboard)
        await state.set_state(AuthState.waiting_for_company_brand)
    else:
        inline_kb_list =[
            [InlineKeyboardButton(text=f"Submit", callback_data=f"{user_input}_policy-conference_submit_type")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=inline_kb_list)
        await msg.answer(f'Nothing matched. Try again or press `Submit` to commit the company name. Your company is `{user_input}`',
                         reply_markup=keyboard)
        await state.set_state(AuthState.waiting_for_company_brand)


@router.callback_query(StateFilter(AuthState.waiting_for_company_brand))
async def process_company(call: CallbackQuery, state: FSMContext):
    username = call.from_user.username
    company = call.data.split('_')[0]
    print(company)

    if await AuthManager.add_user(username, company):
        await state.clear()
        keyboard = await main_menu()
        await call.message.edit_text("Hey! I’m AffilMeet, your trusty meeting setup bot. \nHow can I help you?", reply_markup=keyboard)


@router.message(F.text, StateFilter(None))
@check_auth
async def handle_text_message(msg: Message):
    keyboard = await main_menu()
    await msg.answer('Hey! I’m AffilMeet, your trusty meeting setup bot. \nHow can I help you?', reply_markup=keyboard)


@router.callback_query(F.data == 'main_page')
@check_auth
async def handle_callback_query(call: CallbackQuery, state: FSMContext):
    await state.clear()
    keyboard = await main_menu()
    try:
        # Редактируем текст и клавиатуру текущего сообщения
        await call.message.edit_text(
            'Hey! I’m AffilMeet, your trusty meeting setup bot. \nHow can I help you?',
            reply_markup=keyboard
        )
        await call.answer()
    except:
        # Если редактирование не удалось (например, у сообщения есть документ)
        try:
            await call.message.delete()
            await call.message.answer(
                'Hey! I’m AffilMeet, your trusty meeting setup bot. \nHow can I help you?',
                reply_markup=keyboard
            )
            await call.answer()
        except Exception as e:
            logging.error(f"Error: {e}")
            await call.answer("Error occurred", show_alert=True)


async def on_startup():
    await AuthManager.create_pool()
    logging.info("Database connection pool created")


async def on_shutdown():
    if AuthManager.flg:
        await AuthManager.flg.close()
        logging.info("Database connection pool closed")