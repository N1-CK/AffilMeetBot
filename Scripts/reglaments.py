from aiogram.types import FSInputFile

from Scripts.initial_commands import *


router = Router()

@router.callback_query(F.data == 'policy_limits')
@check_auth
async def policy_limits_page(call: CallbackQuery):
    try:
        file_path = './instructions/policy_limits.pdf'
        file = FSInputFile(file_path)
        keyboard = await policy_limits_menu()
        await call.message.delete()
        await call.message.answer_document(
            document=file,
            reply_markup=keyboard
        )

        await call.answer()
        return

    except FileNotFoundError:
        await call.answer("File not found!", show_alert=True)
    except Exception as e:
        logging.error(f"Error sending document: {e}")
        await call.answer("Error sending document", show_alert=True)
    return

@router.callback_query(F.data == 'policy_conference')
@check_auth
async def policy_conference_page(call: CallbackQuery):
    try:
        file_path = './instructions/policy_conference.pdf'
        file = FSInputFile(file_path)
        keyboard = await policy_conference_menu()
        await call.message.delete()
        await call.message.answer_document(
            document=file,
            reply_markup=keyboard
        )

        await call.answer()
        return

    except FileNotFoundError:
        await call.answer("File not found!", show_alert=True)
    except Exception as e:
        logging.error(f"Error sending document: {e}")
        await call.answer("Error sending document", show_alert=True)
    return
