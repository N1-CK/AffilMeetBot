from Scripts.initial_commands import *
from Scripts.google_table_parsing import add_report_to_sheet_report
from main import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta


router = Router()
calendar_router = Router()

REPORT_CHANNEL_ID = os.getenv('REPORT_CHANNEL_ID')
GT_FILE_NAME = os.getenv('GT_FILE_NAME')

class ReportStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_date2 = State()

    waiting_for_manager = State()
    waiting_for_manager2 = State()

    waiting_for_company = State()
    waiting_for_company2 = State()

    waiting_for_partner = State()
    waiting_for_partner2 = State()

    waiting_for_result = State()
    waiting_for_result2 = State()

    waiting_for_budget = State()
    waiting_for_budget2 = State()

    waiting_for_report_checking = State()

    waiting_for_confirmation = State()
    waiting_for_edit_choice = State()

class Calendar:
    @staticmethod
    async def start_calendar(
            year: int = datetime.now().year,
            month: int = datetime.now().month
    ) -> InlineKeyboardMarkup:
        """
        Creates an inline keyboard with a calendar for date selection.
        """
        builder = InlineKeyboardBuilder()

        # Navigation buttons (month/year)
        builder.row(
            InlineKeyboardButton(text="<", callback_data=f"prev-month_{year}_{month}"),
            InlineKeyboardButton(text=f"{Calendar.get_month_name(month)} {year}", callback_data="ignore"),
            InlineKeyboardButton(text=">", callback_data=f"next-month_{year}_{month}"),
        )

        # Weekday headers
        week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        builder.row(*[
            InlineKeyboardButton(text=day, callback_data="ignore")
            for day in week_days
        ])

        # Get days of the month
        month_days = Calendar.get_month_days(year, month)

        # Add days to the keyboard
        for week in month_days:
            builder.row(*[
                InlineKeyboardButton(
                    text=" " if day == 0 else str(day),
                    callback_data="ignore" if day == 0 else f"select-day_{year}_{month}_{day}"
                )
                for day in week
            ])

        return builder.as_markup()

    @staticmethod
    def get_month_name(month: int) -> str:
        """Returns the month name."""
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        return months[month - 1]

    @staticmethod
    def get_month_days(year: int, month: int) -> list[list[int]]:
        """Returns days of the month, split by weeks."""
        first_day = datetime(year, month, 1)
        last_day = datetime(year, month + 1, 1) - timedelta(days=1) if month < 12 else datetime(year + 1, 1,
                                                                                                1) - timedelta(days=1)

        # Find the weekday of the first day (0=Monday, 6=Sunday)
        start_weekday = (first_day.weekday()) % 7

        # Fill days
        days = []
        current_day = 1

        for _ in range(6):  # Max 6 weeks in a month
            week = []
            for day in range(7):
                if (len(days) == 0 and day < start_weekday) or current_day > last_day.day:
                    week.append(0)  # Empty placeholder
                else:
                    week.append(current_day)
                    current_day += 1
            days.append(week)
            if current_day > last_day.day:
                break

        return days


@calendar_router.callback_query(ReportStates.waiting_for_date, F.data.startswith("prev-month_"))
async def prev_month_handler(callback: CallbackQuery):
    _, year, month = callback.data.split("_")
    year = int(year)
    month = int(month) - 1  # Try to go to previous month

    # Handle year transition (e.g., January -> December of previous year)
    if month < 1:
        month = 12
        year -= 1

    await callback.message.edit_reply_markup(
        reply_markup=await Calendar.start_calendar(year, month)
    )


@calendar_router.callback_query(ReportStates.waiting_for_date, F.data.startswith("next-month_"))
async def next_month_handler(callback: CallbackQuery):
    _, year, month = callback.data.split("_")
    year = int(year)
    month = int(month) + 1  # Try to go to next month

    # Handle year transition (e.g., December -> January of next year)
    if month > 12:
        month = 1
        year += 1

    await callback.message.edit_reply_markup(
        reply_markup=await Calendar.start_calendar(year, month)
    )


@calendar_router.callback_query(ReportStates.waiting_for_date, F.data.startswith("select-day_"))
async def select_day_handler(callback: CallbackQuery, state: FSMContext):
    _, year, month, day = callback.data.split("_")
    formatted_month = f"{int(month):02d}"
    formatted_day = f"{int(day):02d}"
    selected_date = f"{formatted_day}.{formatted_month}.{year}"

    await state.update_data(Date=selected_date)
    await callback.message.edit_text(
        f"Enter company:"
    )
    await state.set_state(ReportStates.waiting_for_company)


@calendar_router.callback_query(ReportStates.waiting_for_date2, F.data.startswith("prev-month_"))
async def prev_month_handler(callback: CallbackQuery):
    _, year, month = callback.data.split("_")
    year = int(year)
    month = int(month) - 1  # Try to go to previous month

    # Handle year transition (e.g., January -> December of previous year)
    if month < 1:
        month = 12
        year -= 1

    await callback.message.edit_reply_markup(
        reply_markup=await Calendar.start_calendar(year, month)
    )


@calendar_router.callback_query(ReportStates.waiting_for_date2, F.data.startswith("next-month_"))
async def next_month_handler(callback: CallbackQuery):
    _, year, month = callback.data.split("_")
    year = int(year)
    month = int(month) + 1  # Try to go to next month

    # Handle year transition (e.g., December -> January of next year)
    if month > 12:
        month = 1
        year += 1

    await callback.message.edit_reply_markup(
        reply_markup=await Calendar.start_calendar(year, month)
    )


@calendar_router.callback_query(ReportStates.waiting_for_date2, F.data.startswith("select-day_"))
async def select_day_handler(callback: CallbackQuery, state: FSMContext):
    _, year, month, day = callback.data.split("_")
    formatted_month = f"{int(month):02d}"
    formatted_day = f"{int(day):02d}"
    selected_date = f"{formatted_day}.{formatted_month}.{year}"

    await state.update_data(Date=selected_date)

    data = await state.get_data()
    report_text = (
        "📝 Meeting Report Summary:\n\n"
        f"📅 Meeting Date: {data.get('Date', 'Not specified')}\n"
        f"👨‍💼 Manager: {data.get('Manager', 'Not specified')}\n"
        f"🤝 Partner: {data.get('Partner', 'Not specified')}\n"
        f"📌 Result: {data.get('Result', 'Not specified')}\n"
        f"💰 Budget: {data.get('Budget', 'Not specified')}\n\n"
        "Please confirm the information:"
    )

    try:
        await callback.message.delete()
    except:
        pass
    await callback.message.answer(report_text, reply_markup=await create_confirmation_keyboard())
    await state.set_state(ReportStates.waiting_for_confirmation)


@router.callback_query(F.data == 'make_report', StateFilter(None))
@check_auth
async def start_report(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Which manager/s attended the meeting?")
    await state.set_state(ReportStates.waiting_for_manager)
    await call.answer()


@router.message(ReportStates.waiting_for_manager)
@check_auth
async def process_date(msg: Message, state: FSMContext):
    await state.update_data(Manager=msg.text)
    await msg.answer('Enter date of meeting: ', reply_markup=await Calendar.start_calendar())
    await state.set_state(ReportStates.waiting_for_date)

@router.message(ReportStates.waiting_for_company)
@check_auth
async def process_partner(msg: Message, state: FSMContext):
    await state.update_data(Partner=msg.text)
    await msg.answer("Enter partner name: ")
    await state.set_state(ReportStates.waiting_for_partner)

@router.message(ReportStates.waiting_for_partner)
@check_auth
async def process_partner(msg: Message, state: FSMContext):
    await state.update_data(Partner=msg.text)
    await msg.answer("What was agreed upon during the meeting?")
    await state.set_state(ReportStates.waiting_for_result)

@router.message(ReportStates.waiting_for_result)
@check_auth
async def process_budget(msg: Message, state: FSMContext):
    await state.update_data(Result=msg.text)
    await msg.answer("Enter the budget for the meeting: ")
    await state.set_state(ReportStates.waiting_for_report_checking)



@router.message(
    StateFilter(
        ReportStates.waiting_for_manager2,
        ReportStates.waiting_for_partner2,
        ReportStates.waiting_for_result2,
        ReportStates.waiting_for_budget2
    )
)
async def process_updated_field(msg: Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state == ReportStates.waiting_for_manager2.state:
        await state.update_data(Manager=msg.text)
    elif current_state == ReportStates.waiting_for_partner2.state:
        await state.update_data(Partner=msg.text)
    elif current_state == ReportStates.waiting_for_result2.state:
        await state.update_data(Result=msg.text)
    elif current_state == ReportStates.waiting_for_budget2.state:
        await state.update_data(Budget=msg.text)

    data = await state.get_data()
    report_text = (
        "📝 Meeting Report Summary:\n\n"
        f"📅 Meeting Date: {data.get('Date', 'Not specified')}\n"
        f"👨‍💼 Manager: {data.get('Manager', 'Not specified')}\n"
        f"🤝 Partner: {data.get('Partner', 'Not specified')}\n"
        f"📌 Result: {data.get('Result', 'Not specified')}\n"
        f"💰 Budget: {data.get('Budget', 'Not specified')}\n\n"
        "Please confirm the information:"
    )

    await msg.answer(report_text, reply_markup=await create_confirmation_keyboard())
    await state.set_state(ReportStates.waiting_for_confirmation)


@router.message(ReportStates.waiting_for_report_checking)
@check_auth
async def process_result(msg: Message, state: FSMContext):
    await state.update_data(Budget=msg.text)
    await state.update_data(Nickname='@'+msg.from_user.username)
    await state.update_data(Datetime=msg.date.strftime('%d.%m.%Y %H:%M'))

    data = await state.get_data()
    report_text = (
        "📝 Meeting Report Summary:\n\n"
        f"📅 Meeting Date: {data.get('Date', 'Not specified')}\n"
        f"👨‍💼 Manager: {data.get('Manager', 'Not specified')}\n"
        f"🤝 Partner: {data.get('Partner', 'Not specified')}\n"
        f"📌 Result: {data.get('Result', 'Not specified')}\n"
        f"💰 Budget: {data.get('Budget', 'Not specified')}\n\n"
        "Please confirm the information:"
    )

    await msg.answer(report_text, reply_markup=await create_confirmation_keyboard())
    await state.set_state(ReportStates.waiting_for_confirmation)

@router.callback_query(F.data.startswith("edit_cancel"), ReportStates.waiting_for_edit_choice)
@check_auth
async def process_back_choice(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    report_text = (
        "📝 Meeting Report Summary:\n\n"
        f"📅 Meeting Date: {data.get('Date', 'Not specified')}\n"
        f"👨‍💼 Manager: {data.get('Manager', 'Not specified')}\n"
        f"🤝 Partner: {data.get('Partner', 'Not specified')}\n"
        f"📌 Result: {data.get('Result', 'Not specified')}\n"
        f"💰 Budget: {data.get('Budget', 'Not specified')}\n\n"
        "Please confirm the information:"
    )

    await callback.message.edit_text(report_text, reply_markup=await create_confirmation_keyboard())
    await state.set_state(ReportStates.waiting_for_confirmation)

@router.callback_query(F.data.startswith("edit_"), ~F.data.startswith("edit_cancel"), ReportStates.waiting_for_edit_choice)
@check_auth
async def process_edit_choice(callback: CallbackQuery, state: FSMContext):
    edit_type = callback.data.split("_")[1]

    if edit_type == "date":
        await callback.message.edit_text("Please select new date:", reply_markup=await Calendar.start_calendar())
        await state.set_state(ReportStates.waiting_for_date2)
    elif edit_type == "manager":
        await callback.message.edit_text("Enter new manager name:")
        await state.set_state(ReportStates.waiting_for_manager2)
    elif edit_type == "partner":
        await callback.message.edit_text("Enter new partner name:")
        await state.set_state(ReportStates.waiting_for_partner2)
    elif edit_type == "result":
        await callback.message.edit_text("Enter new meeting results:")
        await state.set_state(ReportStates.waiting_for_result2)
    elif edit_type == "budget":
        await callback.message.edit_text("Enter new budget:")
        await state.set_state(ReportStates.waiting_for_budget2)


@router.callback_query(F.data == "report_correct", ReportStates.waiting_for_confirmation)
@check_auth
async def process_correct_report(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    username = callback.from_user.username

    # Получаем компанию пользователя из базы данных
    async with AuthManager.flg.acquire() as conn:
        company = await conn.fetchval(
            'SELECT company FROM analytics.auth_users WHERE username = $1',
            username
        )

    # Сохраняем отчет в PostgreSQL
    success = await AuthManager.add_report(username, company, data)

    if success:
        data = await state.get_data()
        report_text = (
            "📝 Meeting Report Summary:\n\n"
            f"📅 Meeting Date: {data.get('Date', 'Not specified')}\n"
            f"👨‍💼 Manager: {data.get('Manager', 'Not specified')}\n"
            f"🤝 Partner: {data.get('Partner', 'Not specified')}\n"
            f"📌 Result: {data.get('Result', 'Not specified')}\n"
            f"💰 Budget: {data.get('Budget', 'Not specified')}\n\n"
        )

        await callback.message.edit_text(report_text)
        await callback.message.answer('''
✅ Report successfully saved!\n
Don't forget to submit a request and attach the receipt.
https://pay.finheroes.pro/
        ''')
        google_sheet_data = {
            'Date': data.get('Date', 'Not specified'),
            'Manager': data.get('Manager', 'Not specified'),
            'Partner': data.get('Partner', 'Not specified'),
            'Result': data.get('Result', 'Not specified'),
            'Nickname': f'@{username}' if username else 'Not specified',
            'Datetime': data.get('Datetime', datetime.now().strftime('%d.%m.%Y %H:%M'))
        }

        # Вызываем функцию добавления в Google Таблицу
        google_success = await add_report_to_sheet_report(google_sheet_data)

        if not google_success:
            logging.warning("Failed to save report to Google Sheet")
    else:
        await callback.message.edit_text("⚠️ Failed to save report")

    await state.clear()
    keyboard = await reports_menu()
    await callback.message.answer("What would you like to do next?", reply_markup=keyboard)


@router.callback_query(F.data == "report_incorrect", ReportStates.waiting_for_confirmation)
@check_auth
async def process_incorrect_report(callback: CallbackQuery, state: FSMContext):
    keyboard = await create_edit_keyboard()
    await callback.message.edit_text("What would you like to change?", reply_markup=keyboard)
    await state.set_state(ReportStates.waiting_for_edit_choice)
