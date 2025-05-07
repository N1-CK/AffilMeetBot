from Scripts.initial_commands import *
from main import Bot

router = Router()

REPORT_CHANNEL_ID = os.getenv('REPORT_CHANNEL_ID')


@router.callback_query(F.data == 'report')
@check_auth
async def handle_report(call: CallbackQuery, state: FSMContext):
    keyboard = await reports_menu_main()
    await call.message.edit_text(
        "Пожалуйста, отправьте файл отчёта",
        reply_markup=keyboard
    )
    await state.set_state("waiting_for_report")
    await call.answer()


@router.message(F.document, StateFilter("waiting_for_report"))
async def process_report_file(msg: Message, state: FSMContext, bot: Bot):
    keyboard = await reports_menu()
    try:
        # Пересылаем файл напрямую
        await bot.send_document(
            chat_id=REPORT_CHANNEL_ID,
            document=msg.document.file_id,
            caption=f"Отчёт от @{msg.from_user.username}"
        )
        await msg.answer("Отчёт успешно отправлен!", reply_markup=keyboard)
        await state.clear()
    except Exception as e:
        logging.error(f"Report error: {e}")
        await msg.answer("Ошибка при отправке отчёта",  reply_markup=keyboard)