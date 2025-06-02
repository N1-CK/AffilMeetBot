from aiogram.types import FSInputFile

from Scripts.initial_commands import *


router = Router()

## Отправка файла limits_policy
@router.callback_query(F.data == 'policy_limits')
@check_auth
async def policy_limits_page(call: CallbackQuery):
    try:
        file_path = './instructions/policy_limits.pdf'
        file = FSInputFile(file_path)
        keyboard = await policy_limits_menu()
        try:
            await call.message.delete()
        except:
            try:
                await call.message.edit_reply_markup(reply_markup=None)
            except:
                pass
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


## Получение данных policy_conference по username
async def get_conference_policy_from_db_by_username(username):
    """Получение компании из БД"""
    try:
        async with asyncpg.create_pool(**DB_CONFIG) as pool:
            async with pool.acquire() as conn:
                query = f"""
                    SELECT company
                    FROM analytics.auth_users
                    WHERE username = '{username}'
                """
                records = await conn.fetch(query)
                company = records[0]['company']
                return company
    except Exception as e:
        logging.error(f"Ошибка при получении компании: {str(e)}")
        return None

## Отправка файла conference_policy по нужной компании
@router.callback_query(F.data == 'policy_conference')
@check_auth
async def policy_conference_page(call: CallbackQuery):
    username = call.from_user.username
    company = await get_conference_policy_from_db_by_username(username)

    try:
        # Асинхронное удаление/очистка сообщения
        try:
            await call.message.delete()
        except:
            try:
                await call.message.edit_reply_markup(reply_markup=None)
            except:
                pass

        # Пути к файлам
        base_path = './instructions/'
        company_file = f'{company}_conference.pdf'
        base_file = 'policy_conference.pdf'

        # Пытаемся найти подходящий файл
        file_to_send = None
        for filename in [company_file, base_file]:
            try:
                file_path = os.path.join(base_path, filename)
                if os.path.isfile(file_path):
                    file_to_send = FSInputFile(file_path)
                    break
            except Exception:
                continue

        if not file_to_send:
            raise FileNotFoundError("No conference files found")

        keyboard = await policy_conference_menu()
        await call.message.answer_document(
            document=file_to_send,
            reply_markup=keyboard
        )
        await call.answer()

    except FileNotFoundError:
        await call.answer("Conference file not found!", show_alert=True)
    except Exception as e:
        logging.error(f"Error sending document: {e}")
        await call.answer("Error sending document", show_alert=True)