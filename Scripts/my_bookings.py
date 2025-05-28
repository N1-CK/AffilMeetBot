from datetime import datetime
from Scripts.initial_commands import *
from Scripts.google_table_parsing import add_report_to_sheet_booking

class BookingStates(StatesGroup):
    waiting_for_city2 = State()
    waiting_for_city = State()

    waiting_for_manager = State()
    waiting_for_manager2 = State()

    waiting_for_datetime = State()
    waiting_for_datetime2 = State()

    waiting_for_partner = State()
    waiting_for_partner2 = State()

    waiting_for_payment = State()
    waiting_for_payment2 = State()

    waiting_for_restaurant2 = State()

    waiting_for_confirmation = State()
    waiting_for_edit_choice = State()
    waiting_for_result = State()
    waiting_for_result2 = State()

router = Router()

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
    await msg.answer("Enter the agreed date and time for your meeting with partner (format: DD.MM.YYYY HH:MM)")
    await state.set_state(BookingStates.waiting_for_datetime)

@router.message(BookingStates.waiting_for_datetime)
@check_auth
async def process_datetime(msg: Message, state: FSMContext):
    try:
        # Проверяем формат даты
        datetime.strptime(msg.text, '%d.%m.%Y %H:%M')
        await state.update_data(DateTime=msg.text)
        await msg.answer("Great! Please enter the partner's name and company (format: Partner @ Company)")
        await state.set_state(BookingStates.waiting_for_partner)
    except ValueError:
        await msg.answer("Invalid date format. Please use DD.MM.YYYY HH:MM format")


@router.message(StateFilter(BookingStates.waiting_for_partner))
@check_auth
async def start_booking(msg: Message, state: FSMContext):
    await state.update_data(Partner=msg.text)
    partner = msg.text.strip(' ').split('@')
    # Получаем список городов из базы данных
    async with AuthManager.flg.acquire() as conn:
        cities = await conn.fetch("SELECT DISTINCT city FROM analytics.restaurants ORDER BY city")

    if not cities:
        await msg.answer("No cities available. Please contact administrator.")
        return

    builder = InlineKeyboardBuilder()
    for city in cities:
        builder.add(InlineKeyboardButton(
            text=f"🌆 {city['city']}",  # Добавляем эмодзи
            callback_data=f"city_{city['city']}"
        ))
    builder.adjust(2)

    await msg.answer(
        f"Awesome! Your meeting with {partner[0]} from {partner[1]}\n\n"
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
                FROM analytics.restaurants 
                WHERE city = '{city}'
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
            text=f" {row['restaurant']}",  # Добавляем эмодзи
            callback_data=f"restaurants_{row['restaurant']}"
        ))
    builder.adjust(2)

    await call.message.answer(
        "🍽 Super. Where’s your meeting taking place?\n"
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

    # Клавиатура для выбора способа оплаты
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="💳 Card", callback_data="payment_card"),
        InlineKeyboardButton(text="💵 Cash", callback_data="payment_cash")
    )

    await call.message.edit_text(
        "Payment method:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(BookingStates.waiting_for_result)


@router.message(BookingStates.waiting_for_payment)
@check_auth
async def process_custom_restaurant(msg: Message, state: FSMContext):
    await state.update_data(Restaurant=msg.text)

    # Клавиатура для выбора способа оплаты
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="💳 Card", callback_data="payment_card"),
        InlineKeyboardButton(text="💵 Cash", callback_data="payment_cash")
    )

    await msg.answer(
        "Payment method:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(BookingStates.waiting_for_result)

@router.message(
    StateFilter(
        BookingStates.waiting_for_city2,
        BookingStates.waiting_for_partner2,
        BookingStates.waiting_for_datetime2,
        BookingStates.waiting_for_manager2
    )
)
async def process_updated_field(msg: Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state == BookingStates.waiting_for_city2.state:
        await state.update_data(City=msg.text)
    elif current_state == BookingStates.waiting_for_restaurant2.state:
        await state.update_data(Restaurant=msg.text)
    elif current_state == BookingStates.waiting_for_partner2.state:
        await state.update_data(Partner=msg.text)
    elif current_state == BookingStates.waiting_for_datetime2.state:
        try:
            # Проверяем формат даты
            datetime.strptime(msg.text, '%d.%m.%Y %H:%M')
            await state.update_data(DateTime=msg.text)
        except ValueError:
            await msg.answer("Invalid date format. Please use DD.MM.YYYY HH:MM format")
            return
    elif current_state == BookingStates.waiting_for_manager2.state:
        await state.update_data(Manager=msg.text)

    data = await state.get_data()
    booking_text = (
        "📝 Booking Summary:\n\n"
        f"👨‍💼 Manager: {data.get('Manager', 'Not specified')}\n"
        f"📅 Date & Time: {data.get('DateTime', 'Not specified')}\n"
        f"🤝 Partner: {data.get('Partner', 'Not specified')}\n"
        f"🍽 Restaurant: {data.get('Restaurant', 'Not specified')}\n"
        f"💳 Payment: {'Card' if data.get('Payment') == 'card' else 'Cash'}\n\n"
        "Please confirm the information:"
    )

    await msg.answer(
        booking_text,
        reply_markup=await create_booking_confirmation_keyboard()
    )
    await state.set_state(BookingStates.waiting_for_confirmation)


@router.message(BookingStates.waiting_for_result)
@check_auth
async def process_payment(msg: Message, state: FSMContext):

    data = await state.get_data()
    booking_text = (
        "📝 Booking Summary:\n\n"
        f"👨‍💼 Manager: {data.get('Manager', 'Not specified')}\n"
        f"📅 Date & Time: {data.get('DateTime', 'Not specified')}\n"
        f"🤝 Partner: {data.get('Partner', 'Not specified')}\n"
        f"🍽 Restaurant: {data.get('Restaurant', 'Not specified')}\n"
        f"💳 Payment: {'Card' if data.get('Payment') == 'card' else 'Cash'}\n\n"
        "Please confirm the information:"
    )

    await msg.answer(
        booking_text,
        reply_markup=await create_booking_confirmation_keyboard()
    )
    await state.set_state(BookingStates.waiting_for_confirmation)


@router.callback_query(StateFilter(BookingStates.waiting_for_result,
                                   BookingStates.waiting_for_result2))
async def process_payment(call: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == BookingStates.waiting_for_result2.state:
        restaurant = call.data.split("_")[1]
        await state.update_data(Restaurant=restaurant)
    else:
        payment_method = call.data.split("_")[1]
        await state.update_data(Payment=payment_method)


    data = await state.get_data()
    booking_text = (
        "📝 Booking Summary:\n\n"
        f"👨‍💼 Manager: {data.get('Manager', 'Not specified')}\n"
        f"📅 Date & Time: {data.get('DateTime', 'Not specified')}\n"
        f"🤝 Partner: {data.get('Partner', 'Not specified')}\n"
        f"🍽 Restaurant: {data.get('Restaurant', 'Not specified')}\n"
        f"💳 Payment: {'Card' if data.get('Payment') == 'card' else 'Cash'}\n\n"
        "Please confirm the information:"
    )

    await call.message.edit_text(
        booking_text,
        reply_markup=await create_booking_confirmation_keyboard()
    )
    await state.set_state(BookingStates.waiting_for_confirmation)


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
        InlineKeyboardButton(text="🤝 Partner", callback_data="edit_booking_partner"),
        InlineKeyboardButton(text="🍽 Restaurant", callback_data="edit_booking_restaurant")
    )
    builder.row(
        InlineKeyboardButton(text="💳 Payment", callback_data="edit_booking_payment"),
        InlineKeyboardButton(text="🔙 Cancel", callback_data="edit_booking_cancel")
    )
    return builder.as_markup()


@router.callback_query(F.data == "booking_correct", BookingStates.waiting_for_confirmation)
@check_auth
async def process_correct_booking(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    username = call.from_user.username

    # Сохраняем бронирование в базу данных
    async with AuthManager.flg.acquire() as conn:
        try:
            await conn.execute(
                '''
                INSERT INTO analytics.bookings
                (username, manager, datetime, partner, restaurant, payment_method, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                ''',
                username,
                data.get('Manager'),
                data.get('DateTime'),
                data.get('Partner'),
                data.get('Restaurant'),
                data.get('Payment')
            )

            google_sheet_data = {
                'Date': data.get('DateTime').split()[0] if 'DateTime' in data else datetime.now().strftime('%d.%m.%Y'),
                'Manager': data.get('Manager', 'Not specified'),
                'Partner': data.get('Partner', 'Not specified'),
                'Restaurant': data.get('Restaurant', 'Not specified'),
                'Payment': 'Card' if data.get('Payment') == 'card' else 'Cash',
                'Nickname': f'@{username}' if username else 'Not specified',
                'Datetime': datetime.now().strftime('%d.%m.%Y %H:%M')
            }


            await call.message.edit_text(
                "✅ Booking successfully saved!\n\n"
                "Your meeting has been confirmed."
            )

            # Вызываем функцию добавления в Google Таблицу
            success = await add_report_to_sheet_booking(google_sheet_data)
            if not success:
                logging.warning("Failed to save booking to Google Sheet")


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
        data = await state.get_data()
        booking_text = (
            "📝 Booking Summary:\n\n"
            f"👨‍💼 Manager: {data.get('Manager', 'Not specified')}\n"
            f"📅 Date & Time: {data.get('DateTime', 'Not specified')}\n"
            f"🤝 Partner: {data.get('Partner', 'Not specified')}\n"
            f"🍽 Restaurant: {data.get('Restaurant', 'Not specified')}\n"
            f"💳 Payment: {'Card' if data.get('Payment') == 'card' else 'Cash'}\n\n"
            "Please confirm the information:"
        )

        await call.message.edit_text(
            booking_text,
            reply_markup=await create_booking_confirmation_keyboard()
        )
        await state.set_state(BookingStates.waiting_for_confirmation)
    elif edit_type == "manager":
        await call.message.edit_text("Please enter the name of the manager who will attend the meeting:")
        await state.set_state(BookingStates.waiting_for_manager2)
    elif edit_type == "datetime":
        await call.message.edit_text("Enter the agreed date and time for your meeting with partner (DD.MM.YYYY HH:MM):")
        await state.set_state(BookingStates.waiting_for_datetime2)
    elif edit_type == "partner":
        await call.message.edit_text("Please enter the partner's name and company (format: Partner @ Company):")
        await state.set_state(BookingStates.waiting_for_partner2)
    elif edit_type == "restaurant":
        async with AuthManager.flg.acquire() as conn:
            cities = await conn.fetch("SELECT DISTINCT city FROM analytics.restaurants ORDER BY city")

        if not cities:
            await call.message.edit_text("No cities available. Please contact administrator.")
            return

        builder = InlineKeyboardBuilder()
        for city in cities:
            builder.add(InlineKeyboardButton(
                text=f"🌆 {city['city']}",  # Добавляем эмодзи
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