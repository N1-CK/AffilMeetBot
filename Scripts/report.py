from Scripts.initial_commands import *
from Scripts.google_table_parsing import *
from main import Bot

router = Router()

REPORT_CHANNEL_ID = os.getenv('REPORT_CHANNEL_ID')
GT_FILE_NAME = os.getenv('GT_FILE_NAME')

class ReportStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_manager = State()
    waiting_for_partner = State()
    waiting_for_result = State()
    waiting_for_report = State()


@router.callback_query(F.data == 'report')
@check_auth
async def handle_report(call: CallbackQuery, state: FSMContext):
    keyboard = await reports_menu_main()
    await call.message.edit_text(
        "Select an action to continue",
        reply_markup=keyboard
    )
    await call.answer()


@router.callback_query(F.data == 'make_report', StateFilter(None))
@check_auth
async def start_report(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Enter the meeting date with the partner (format: DD.MM.YYYY)")
    await state.set_state(ReportStates.waiting_for_date)
    await call.answer()


@router.message(ReportStates.waiting_for_date)
@check_auth
async def process_date(msg: Message, state: FSMContext):
    await state.update_data(Date=msg.text)
    await msg.answer('Which managers attended the meeting?')
    await state.set_state(ReportStates.waiting_for_manager)


@router.message(ReportStates.waiting_for_manager)
@check_auth
async def process_manager(msg: Message, state: FSMContext):
    await state.update_data(Manager=msg.text)
    await msg.answer('Which company/partner did you meet with?')
    await state.set_state(ReportStates.waiting_for_partner)


@router.message(ReportStates.waiting_for_partner)
@check_auth
async def process_partner(msg: Message, state: FSMContext):
    await state.update_data(Partner=msg.text)
    await msg.answer("What was the result of the meeting?")
    await state.set_state(ReportStates.waiting_for_result)


@router.message(ReportStates.waiting_for_result)
@check_auth
async def process_result(msg: Message, state: FSMContext):
    await state.update_data(Result=msg.text)
    await state.update_data(Nickname='@'+msg.from_user.username)
    await state.update_data(Datetime=msg.date.strftime('%d.%m.%Y %H:%M'))
    keyboard = await report_skip_menu()
    await msg.answer(
        "Please, send me file with check or press 'Skip check'",
        reply_markup=keyboard
    )
    await state.set_state(ReportStates.waiting_for_report)


@router.callback_query(F.data == 'skip_report', ReportStates.waiting_for_report)
@check_auth
async def skip_report(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await send_report_summary(call.message, data)
    await state.clear()
    keyboard = await reports_menu()
    await call.message.answer("Report saved without receipt", reply_markup=keyboard)
    await call.answer()


@router.message(F.document, ReportStates.waiting_for_report)
@check_auth
async def process_report_file(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await send_report_summary(msg, data)

    try:
        await bot.send_document(
            chat_id=REPORT_CHANNEL_ID,
            document=msg.document.file_id,
            caption=f"Report from @{msg.from_user.username}"
        )
        keyboard = await reports_menu()
        await msg.answer("✅ Report successfully submitted!", reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Report error: {e}")
        keyboard = await reports_menu()
        await msg.answer("Failed to submit report", reply_markup=keyboard)
    finally:
        await state.clear()


async def send_report_summary(message: Message, data: dict):
    report_text = (
        "📝 Meeting Report Summary:\n\n"
        f"📅 Meeting Date: {data.get('Date', 'Not specified')}\n"
        f"👨‍💼 Manager: {data.get('Manager', 'Not specified')}\n"
        f"🤝 Partner: {data.get('Partner', 'Not specified')}\n"
        f"📌 Result: {data.get('Result', 'Not specified')}\n"
    )

    success = await add_report_to_sheet(data)
    if not success:
        await message.answer("⚠️ We couldn't save your report")

    # print(data)
    await message.answer(report_text)