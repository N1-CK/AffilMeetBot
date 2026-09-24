from datetime import datetime, timedelta
from Scripts.initial_commands import *
import re
from typing import Union


class BookingStates(StatesGroup):
    waiting_for_city2 = State()
    waiting_for_city = State()
    waiting_for_manager = State()
    waiting_for_manager2 = State()
    waiting_for_datetime = State()
    waiting_for_datetime2 = State()
    waiting_for_time = State()
    waiting_for_time2 = State()
    waiting_for_company = State()
    waiting_for_company2 = State()
    waiting_for_partner = State()
    waiting_for_partner2 = State()
    waiting_for_partner_type = State()
    waiting_for_partner_type2 = State()
    waiting_for_payment = State()
    waiting_for_payment2 = State()
    waiting_for_restaurant2 = State()
    waiting_for_confirmation = State()
    waiting_for_edit_choice = State()
    waiting_for_result = State()
    waiting_for_result2 = State()
    waiting_for_people = State()
    waiting_for_people2 = State()


router = Router()
calendar_router = Router()

LOG_PATH = os.getenv('LOG_PATH')
# Configure logging
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
db_schema = os.getenv('DB_SCHEMA')
AFFIL_REQUEST_SCHEMA = os.getenv('DB_SCHEMA_PR', 'travelconference_pr')

class BookingCalendar:
    @staticmethod
    async def start_calendar(
            year: int = datetime.now().year,
            month: int = datetime.now().month
    ) -> InlineKeyboardMarkup:
        """Creates an inline keyboard with a calendar for date selection"""
        builder = InlineKeyboardBuilder()

        # Navigation buttons
        builder.row(
            InlineKeyboardButton(text="<", callback_data=f"booking_prev-month_{year}_{month}"),
            InlineKeyboardButton(text=f"{BookingCalendar.get_month_name(month)} {year}", callback_data="ignore"),
            InlineKeyboardButton(text=">", callback_data=f"booking_next-month_{year}_{month}"),
        )

        # Weekday headers
        week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        builder.row(*[
            InlineKeyboardButton(text=day, callback_data="ignore")
            for day in week_days
        ])

        # Get days of the month
        month_days = BookingCalendar.get_month_days(year, month)

        # Add days to keyboard
        for week in month_days:
            builder.row(*[
                InlineKeyboardButton(
                    text=" " if day == 0 else str(day),
                    callback_data="ignore" if day == 0 else f"booking_select-day_{year}_{month}_{day}"
                )
                for day in week
            ])

        return builder.as_markup()

    @staticmethod
    def get_month_name(month: int) -> str:
        """Returns month name"""
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        return months[month - 1]

    @staticmethod
    def get_month_days(year: int, month: int) -> list[list[int]]:
        """Returns days of month grouped by weeks"""
        first_day = datetime(year, month, 1)
        last_day = datetime(year, month + 1, 1) - timedelta(days=1) if month < 12 else datetime(year + 1, 1,
                                                                                                1) - timedelta(days=1)
        start_weekday = (first_day.weekday()) % 7
        days = []
        current_day = 1

        for _ in range(6):
            week = []
            for day in range(7):
                if (len(days) == 0 and day < start_weekday) or current_day > last_day.day:
                    week.append(0)
                else:
                    week.append(current_day)
                    current_day += 1
            days.append(week)
            if current_day > last_day.day:
                break
        return days


# Calendar handlers
@calendar_router.callback_query(F.data.startswith("booking_prev-month_"), BookingStates.waiting_for_datetime)
@calendar_router.callback_query(F.data.startswith("booking_prev-month_"), BookingStates.waiting_for_datetime2)
@check_auth
async def booking_prev_month_handler(callback: CallbackQuery):
    parts = callback.data.split("_")
    year = int(parts[2])
    month = int(parts[3])
    month -= 1
    if month < 1:
        month = 12
        year -= 1
    await callback.message.edit_reply_markup(
        reply_markup=await BookingCalendar.start_calendar(year, month)
    )


@calendar_router.callback_query(F.data.startswith("booking_next-month_"), BookingStates.waiting_for_datetime)
@calendar_router.callback_query(F.data.startswith("booking_next-month_"), BookingStates.waiting_for_datetime2)
@check_auth
async def booking_next_month_handler(callback: CallbackQuery):
    parts = callback.data.split("_")
    year = int(parts[2])
    month = int(parts[3])
    month += 1
    if month > 12:
        month = 1
        year += 1
    await callback.message.edit_reply_markup(
        reply_markup=await BookingCalendar.start_calendar(year, month)
    )

@calendar_router.callback_query(F.data.startswith("booking_select-day_"), BookingStates.waiting_for_datetime)
@check_auth
async def booking_select_day_handler(callback: CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split("_")
        if len(parts) < 4:
            await callback.answer("Invalid date selection", show_alert=True)
            return

        _, _, year, month, day = parts[:5]
        formatted_month = f"{int(month):02d}"
        formatted_day = f"{int(day):02d}"
        selected_date = f"{formatted_day}.{formatted_month}.{year}"

        await state.update_data(selected_date=selected_date)
        await callback.message.edit_text(
            f"Selected date: {selected_date}\nPlease enter meeting time in HH:MM format (e.g., 14:30):"
        )
        await state.set_state(BookingStates.waiting_for_time)
    except Exception as e:
        logging.error(f"Error in booking_select_day_handler: {e}")
        await callback.answer("Error processing date selection", show_alert=True)


@router.message(BookingStates.waiting_for_time)
@check_auth
async def process_time_input(msg: Message, state: FSMContext):
    # Updated regex to require exactly 2 digits for hours (01-23)
    if not re.match(r'^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$', msg.text):
        await msg.answer("Invalid time format. Please use HH:MM format with leading zero (e.g., 09:30, 14:30)")
        return

    data = await state.get_data()
    selected_date = data.get('selected_date')

    if not selected_date:
        await msg.answer("Date not selected", show_alert=True)
        return

    datetime_str = f"{selected_date} {msg.text}"

    try:
        datetime.strptime(datetime_str, '%d.%m.%Y %H:%M')
        await state.update_data(DateTime=datetime_str)
        await msg.answer(
            "Great! Please enter the company name you're meeting with:"
        )
        await state.set_state(BookingStates.waiting_for_company)
    except ValueError:
        await msg.answer("Invalid datetime format. Please try again.")

# For editing datetime
@router.callback_query(F.data == "edit_booking_datetime", BookingStates.waiting_for_edit_choice)
@check_auth
async def edit_booking_datetime(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Select new meeting date:",
        reply_markup=await BookingCalendar.start_calendar()
    )
    await state.set_state(BookingStates.waiting_for_datetime2)
    await callback.answer()


@calendar_router.callback_query(F.data.startswith("booking_select-day_"), BookingStates.waiting_for_datetime2)
@check_auth
async def booking_select_day_handler2(callback: CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split("_")
        if len(parts) < 4:
            await callback.answer("Invalid date selection", show_alert=True)
            return

        _, _, year, month, day = parts[:5]
        formatted_month = f"{int(month):02d}"
        formatted_day = f"{int(day):02d}"
        selected_date = f"{formatted_day}.{formatted_month}.{year}"

        await state.update_data(selected_date=selected_date)
        await callback.message.edit_text(
            f"Selected new date: {selected_date}\nPlease enter new meeting time in HH:MM format (e.g., 14:30):"
        )
        await state.set_state(BookingStates.waiting_for_time2)
    except Exception as e:
        logging.error(f"Error in booking_select_day_handler2: {e}")
        await callback.answer("Error processing date selection", show_alert=True)


@router.message(BookingStates.waiting_for_time2)
@check_auth
async def process_time_input2(msg: Message, state: FSMContext):
    # Updated regex to require exactly 2 digits for hours (01-23)
    if not re.match(r'^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$', msg.text):
        await msg.answer("Invalid time format. Please use HH:MM format with leading zero (e.g., 09:30, 14:30):")
        return

    data = await state.get_data()
    selected_date = data.get('selected_date')

    if not selected_date:
        await msg.answer("Date not selected", show_alert=True)
        return

    datetime_str = f"{selected_date} {msg.text}"

    try:
        datetime.strptime(datetime_str, '%d.%m.%Y %H:%M')
        await state.update_data(DateTime=datetime_str)
        await show_confirmation(msg, state)
    except ValueError:
        await msg.answer("Invalid datetime format. Please try again.")

# Original handlers
@router.callback_query(F.data == 'booked_action', StateFilter(None))
@check_auth
async def start_booking(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Please enter the name of the manager who will attend the meeting (your name)")
    await state.set_state(BookingStates.waiting_for_manager)
    await call.answer()


@router.message(BookingStates.waiting_for_manager)
@check_auth
async def process_manager(msg: Message, state: FSMContext):
    await state.update_data(Manager=msg.text)
    await msg.answer(
        "Select meeting date:",
        reply_markup=await BookingCalendar.start_calendar()
    )
    await state.set_state(BookingStates.waiting_for_datetime)

@router.message(BookingStates.waiting_for_company)
@check_auth
async def process_company(msg: Message, state: FSMContext):
    await state.update_data(Company=msg.text)
    await msg.answer("Please enter the partner's name (person you're meeting with):")
    await state.set_state(BookingStates.waiting_for_partner)

@router.message(BookingStates.waiting_for_partner)
@check_auth
async def process_partner_type(msg: Message, state: FSMContext):
    await state.update_data(Partner=msg.text)
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="VIP Partner", callback_data="partner_VIP"),
        InlineKeyboardButton(text="Regular Partner", callback_data="partner_Regular"),
    )

    await msg.answer(
        "Choose partner type:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(BookingStates.waiting_for_partner_type)

@router.callback_query(BookingStates.waiting_for_partner_type)
@check_auth
async def process_partner(call: CallbackQuery, state: FSMContext):
    partner_type = call.data.split("_")[1]
    await state.update_data(PartnerType=partner_type)
    data = await state.get_data()

    # Get cities from database
    async with AuthManager.flg.acquire() as conn:
        cities = await conn.fetch(f"SELECT DISTINCT city FROM {AFFIL_REQUEST_SCHEMA}.affil_restaurants ORDER BY city")

    if not cities:
        await call.message.edit_text("No cities available. Please contact administrator.")
        return

    builder = InlineKeyboardBuilder()
    for city in cities:
        builder.add(InlineKeyboardButton(
            text=f"🌆 {city['city']}",
            callback_data=f"city_{city['city']}"
        ))
    builder.adjust(2)

    await call.message.answer(
        f"Meeting with {data.get('Partner', 'partner')} from {data.get('Company', 'company')}\n\n"
        "Please select the city for your meeting:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(BookingStates.waiting_for_city)


@router.callback_query(F.data.startswith("city_"),
                       StateFilter(BookingStates.waiting_for_city,
                                   BookingStates.waiting_for_city2))
@check_auth
async def process_city(call: CallbackQuery, state: FSMContext):
    city = call.data.split("_")[1]
    await state.update_data(City=city)

    async with AuthManager.flg.acquire() as conn:
        restaurants = await conn.fetch(f'''
                SELECT DISTINCT restaurant
                FROM {AFFIL_REQUEST_SCHEMA}.affil_restaurants 
                WHERE city = '{city}'
                and created_at = (select max(created_at) from {AFFIL_REQUEST_SCHEMA}.affil_restaurants)
            ''')

    if not restaurants:
        await call.message.edit_text("No restaurants available. Please contact administrator.")
        return
    else:
        try:
            await call.message.delete()
        except:
            pass

    builder = InlineKeyboardBuilder()
    for row in restaurants:
        builder.add(InlineKeyboardButton(
            text=f" {row['restaurant']}",
            callback_data=f"restaurants_{row['restaurant']}"
        ))
    builder.adjust(2)

    await call.message.answer(
        "🍽 Super. Where's your meeting taking place?\n"
        "Choose the restaurant from the list below or enter yours",
        reply_markup=builder.as_markup()
    )

    current_state = await state.get_state()
    if current_state == BookingStates.waiting_for_city2.state:
        await state.set_state(BookingStates.waiting_for_result2)
    else:
        await state.set_state(BookingStates.waiting_for_payment)



@router.callback_query(BookingStates.waiting_for_payment)
@check_auth
async def process_custom_restaurant(call: CallbackQuery, state: FSMContext):
    restaurant = call.data.split("_")[1]
    await state.update_data(Restaurant=restaurant)

    # Payment method keyboard
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="💳 Card", callback_data="payment_card"),
        InlineKeyboardButton(text="💵 Cash", callback_data="payment_cash")
    )

    await call.message.edit_text(
        "Payment method:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(BookingStates.waiting_for_people)


@router.message(BookingStates.waiting_for_payment)
@check_auth
async def process_custom_restaurant(msg: Message, state: FSMContext):
    await state.update_data(Restaurant=msg.text)

    # Payment method keyboard
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="💳 Card", callback_data="payment_card"),
        InlineKeyboardButton(text="💵 Cash", callback_data="payment_cash")
    )

    await msg.answer(
        "Payment method:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(BookingStates.waiting_for_people)


@router.callback_query(BookingStates.waiting_for_people)
@check_auth
async def process_people(call: CallbackQuery, state: FSMContext):
    payment_method = call.data.split("_")[1]
    await state.update_data(Payment=payment_method)
    await call.message.answer("Please enter how many people are expected (including you):")
    await state.set_state(BookingStates.waiting_for_result)


@router.message(
    StateFilter(
        BookingStates.waiting_for_city2,
        BookingStates.waiting_for_company2,
        BookingStates.waiting_for_partner2,
        BookingStates.waiting_for_people2,
        BookingStates.waiting_for_partner_type2,
        BookingStates.waiting_for_datetime2,
        BookingStates.waiting_for_manager2
    )
)
@check_auth
async def process_updated_field(msg: Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state == BookingStates.waiting_for_city2.state:
        await state.update_data(City=msg.text)
    elif current_state == BookingStates.waiting_for_restaurant2.state:
        await state.update_data(Restaurant=msg.text)
    elif current_state == BookingStates.waiting_for_company2.state:
        await state.update_data(Company=msg.text)
    elif current_state == BookingStates.waiting_for_partner2.state:
        await state.update_data(Partner=msg.text)
    elif current_state == BookingStates.waiting_for_people2.state:
        await state.update_data(People=msg.text)
    elif current_state == BookingStates.waiting_for_partner_type2.state:
        await state.update_data(PartnerType=msg.text)
    elif current_state == BookingStates.waiting_for_datetime2.state:
        try:
            # Validate date format
            datetime.strptime(msg.text, '%d.%m.%Y %H:%M')
            time_part = msg.text.split()[1]
            if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', time_part):
                await msg.answer("Invalid time format. Please use HH:MM in 24-hour format (e.g. 14:30)")
                return
            await state.update_data(DateTime=msg.text)
        except ValueError:
            await msg.answer("Invalid date format. Please use DD.MM.YYYY HH:MM format (e.g. 14:30)")
            return
    elif current_state == BookingStates.waiting_for_manager2.state:
        await state.update_data(Manager=msg.text)

    await show_confirmation(msg, state)


@router.message(BookingStates.waiting_for_result)
@check_auth
async def process_payment(msg: Message, state: FSMContext):
    await state.update_data(People=msg.text)
    await show_confirmation(msg, state)


@router.callback_query(StateFilter(BookingStates.waiting_for_result,
                                   BookingStates.waiting_for_result2,
                                   BookingStates.waiting_for_partner_type2))
@check_auth
async def process_payment(call: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == BookingStates.waiting_for_result2.state:
        restaurant = call.data.split("_")[1]
        await state.update_data(Restaurant=restaurant)
    elif current_state == BookingStates.waiting_for_partner_type2.state:
        partner_type = call.data.split("_")[1]
        await state.update_data(PartnerType=partner_type)
    else:
        payment_method = call.data.split("_")[1]
        await state.update_data(Payment=payment_method)

    await show_confirmation(call, state)



async def create_booking_confirmation_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Correct", callback_data="booking_correct"),
        InlineKeyboardButton(text="❌ Incorrect", callback_data="booking_incorrect")
    )
    builder.row(InlineKeyboardButton(text="↩️ Close without saving", callback_data="main_page"))
    return builder.as_markup()


async def create_booking_edit_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👨‍💼 Manager", callback_data="edit_booking_manager"),
        InlineKeyboardButton(text="📅 Date/Time", callback_data="edit_booking_datetime")
    )
    builder.row(
        InlineKeyboardButton(text="🏢 Company", callback_data="edit_booking_company"),
        InlineKeyboardButton(text="🤝 Partner", callback_data="edit_booking_partner")
    )
    builder.row(
        InlineKeyboardButton(text="🔹 Partner type", callback_data="edit_booking_partnertype"),
        InlineKeyboardButton(text="🍽 Restaurant", callback_data="edit_booking_restaurant")

    )
    builder.row(
        InlineKeyboardButton(text="💳 Payment", callback_data="edit_booking_payment"),
        InlineKeyboardButton(text="👨🏼 People", callback_data="edit_booking_people")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Cancel", callback_data="edit_booking_partnertype")

    )
    return builder.as_markup()


@router.callback_query(F.data == "booking_correct", BookingStates.waiting_for_confirmation)
@check_auth
async def process_correct_booking(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    username = call.from_user.username
    user_id = call.from_user.id

    # Save booking to database
    async with AuthManager.flg.acquire() as conn:
        try:
            await conn.execute(
                f'''
                INSERT INTO {AFFIL_REQUEST_SCHEMA}.affil_bookings
                (username, user_id, manager, datetime, company, partner, restaurant, people, payment_method, partnertype)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ''',
                username,
                user_id,
                data.get('Manager'),
                data.get('DateTime'),
                data.get('Company'),
                data.get('Partner'),
                data.get('Restaurant'),
                data.get('People'),
                data.get('Payment'),
                data.get('PartnerType')
            )

            # google_sheet_data = {
            #     'Date': data.get('DateTime').split()[0] if 'DateTime' in data else datetime.now().strftime('%d.%m.%Y'),
            #     'Manager': data.get('Manager', 'Not specified'),
            #     'Company': data.get('Company', 'Not specified'),
            #     'Partner': data.get('Partner', 'Not specified'),
            #     'PartnerType': data.get('PartnerType', 'Not specified'),
            #     'Restaurant': data.get('Restaurant', 'Not specified'),
            #     'Persons': data.get('Persons', 'Not specified'),
            #     'Payment': 'Card' if data.get('Payment') == 'card' else 'Cash',
            #     'Nickname': f'@{username}' if username else 'Not specified',
            #     'Datetime': datetime.now().strftime('%d.%m.%Y %H:%M')
            # }

            booking_text = (
                "📝 Booking Summary:\n\n"
                f"👨‍💼 Manager: {data.get('Manager', 'Not specified')}\n"
                f"📅 Date & Time: {data.get('DateTime', 'Not specified')}\n"
                f"🏢 Company: {data.get('Company', 'Not specified')}\n"
                f"🤝 Partner: {data.get('Partner', 'Not specified')}\n"
                f"🔹 PartnerType: {data.get('PartnerType', 'Not specified')}\n"
                f"🍽 Restaurant: {data.get('Restaurant', 'Not specified')}\n"
                f"👨🏼 People: {data.get('People', 'Not specified')}\n"
                f"💳 Payment: {'Card' if data.get('Payment') == 'card' else 'Cash'}\n\n"
            )
            await call.message.edit_text(booking_text)

            await call.message.answer(
                "✅ Booking successfully saved!\n\n"
                "Your meeting has been confirmed."
            )

            # Add to Google Sheet
            # success = await add_report_to_sheet_booking(google_sheet_data)
            # if not success:
            #     logging.warning("Failed to save booking to Google Sheet")

        except Exception as e:
            logging.error(f"Error saving booking: {e}")
            await call.message.edit_text("⚠️ Failed to save booking")

    await state.clear()
    keyboard = await conference_menu()
    await call.message.answer("What would you like to do next?", reply_markup=keyboard)


@router.callback_query(F.data == "booking_incorrect", BookingStates.waiting_for_confirmation)
@check_auth
async def process_incorrect_booking(call: CallbackQuery, state: FSMContext):
    keyboard = await create_booking_edit_keyboard()
    await call.message.edit_text(
        "What would you like to change?",
        reply_markup=keyboard
    )
    await state.set_state(BookingStates.waiting_for_edit_choice)


@router.callback_query(F.data.startswith("edit_booking_"), BookingStates.waiting_for_edit_choice)
@check_auth
async def process_booking_edit_choice(call: CallbackQuery, state: FSMContext):
    edit_type = call.data.split("_")[2]

    if edit_type == "cancel":
        await show_confirmation(call, state)
    elif edit_type == "manager":
        await call.message.edit_text("Please enter the name of the manager who will attend the meeting:")
        await state.set_state(BookingStates.waiting_for_manager2)
    elif edit_type == "datetime":
        await call.message.edit_text("Enter the agreed date and time for your meeting with partner (DD.MM.YYYY HH:MM):")
        await state.set_state(BookingStates.waiting_for_datetime2)
    elif edit_type == "company":
        await call.message.edit_text("Please enter the new company partner name:")
        await state.set_state(BookingStates.waiting_for_company2)
    elif edit_type == "partner":
        await call.message.edit_text("Please enter the new partner name:")
        await state.set_state(BookingStates.waiting_for_partner2)
    elif edit_type == "people":
        await call.message.edit_text("How many people? (including you):")
        await state.set_state(BookingStates.waiting_for_people2)
    elif edit_type == "restaurant":
        async with AuthManager.flg.acquire() as conn:
            cities = await conn.fetch(f'''
                SELECT DISTINCT city 
                FROM {AFFIL_REQUEST_SCHEMA}.affil_restaurants 
                WHERE created_at = (select max(created_at) from {AFFIL_REQUEST_SCHEMA}.affil_restaurants)
                ORDER BY city
            ''')

        if not cities:
            await call.message.edit_text("No cities available. Please contact administrator.")
            return

        builder = InlineKeyboardBuilder()
        for city in cities:
            builder.add(InlineKeyboardButton(
                text=f"🌆 {city['city']}",
                callback_data=f"city_{city['city']}"
            ))
        builder.adjust(2)

        await call.message.edit_text(
            "🏙 Please select the city for your meeting:",
            reply_markup=builder.as_markup()
        )

        await state.set_state(BookingStates.waiting_for_city2)

    elif edit_type == "payment":
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(text="💳 Card", callback_data="payment_card"),
            InlineKeyboardButton(text="💵 Cash", callback_data="payment_cash")
        )

        await call.message.edit_text(
            "Please select payment method:",
            reply_markup=builder.as_markup()
        )
        await state.set_state(BookingStates.waiting_for_result)
    elif edit_type == "partnertype":
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(text="VIP Partner", callback_data="partner_VIP"),
            InlineKeyboardButton(text="Regular Partner", callback_data="partner_Regular"),
        )

        await call.message.edit_text(
            "Choose partner type:",
            reply_markup=builder.as_markup()
        )

        await state.set_state(BookingStates.waiting_for_partner_type2)


async def show_confirmation(msg: Union[Message, CallbackQuery], state: FSMContext):
    data = await state.get_data()
    booking_text = (
        "📝 Booking Summary:\n\n"
        f"👨‍💼 Manager: {data.get('Manager', 'Not specified')}\n"
        f"📅 Date & Time: {data.get('DateTime', 'Not specified')}\n"
        f"🏢 Company: {data.get('Company', 'Not specified')}\n"
        f"🤝 Partner: {data.get('Partner', 'Not specified')}\n"
        f"🔹 Partner Type: {data.get('PartnerType', 'Not specified')}\n"
        f"🍽 Restaurant: {data.get('Restaurant', 'Not specified')}\n"
        f"👨🏼 People: {data.get('People', 'Not specified')}\n"
        f"💳 Payment: {'Card' if data.get('Payment') == 'card' else 'Cash'}\n\n"
        "Please confirm the information:"
    )

    if isinstance(msg, Message):
        await msg.answer(
            booking_text,
            reply_markup=await create_booking_confirmation_keyboard()
        )
    else:
        await msg.message.edit_text(
            booking_text,
            reply_markup=await create_booking_confirmation_keyboard()
        )
    await state.set_state(BookingStates.waiting_for_confirmation)
