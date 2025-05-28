import logging
import pygsheets
from dotenv import load_dotenv
import os
from datetime import datetime
from aiogram import Router

load_dotenv()

router = Router()

# Конфигурация
SPREADSHEET_NAME = os.getenv('GT_FILE_NAME')
WORKSHEET_NAME_BOOKING = os.getenv('GT_RESTAURANTS_FILE_BOOKED')
WORKSHEET_NAME_REPORTS = os.getenv('GT_RESTAURANTS_FILE_REPORT')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


async def authorize_google_sheets():
    """Аутентификация в Google Sheets API"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        PROJECT_ROOT = os.path.dirname(BASE_DIR)
        service_account_file = os.path.join(PROJECT_ROOT, "conferencebothelper-1134fe7c70c9.json")

        if not os.path.exists(service_account_file):
            raise FileNotFoundError(f"Service account file not found at {service_account_file}")

        return pygsheets.authorize(service_account_file=service_account_file)
    except Exception as e:
        logging.error(f"Authentication failed: {str(e)}", exc_info=True)
        raise


async def get_or_create_worksheet(gc, WORKSHEET_NAME, headers):
    """Получаем или создаем рабочий лист"""
    try:
        sh = gc.open(SPREADSHEET_NAME)

        # Проверяем существование листа
        try:
            worksheet = sh.worksheet_by_title(WORKSHEET_NAME)
            logging.info(f"Worksheet '{WORKSHEET_NAME}' found")
        except pygsheets.WorksheetNotFound:
            logging.info(f"Creating new worksheet '{WORKSHEET_NAME}'")
            worksheet = sh.add_worksheet(WORKSHEET_NAME, rows=3000, cols=4)
            # Устанавливаем заголовки

            worksheet.update_values('A1:G1', [headers])

        return worksheet
    except Exception as e:
        logging.error(f"Worksheet access error: {str(e)}", exc_info=True)
        raise


async def safe_append_data(worksheet, data):
    """Безопасное добавление данных с обработкой ошибок"""
    try:
        col_a = worksheet.get_col(1, include_tailing_empty=False)
        next_row = len(col_a) + 1

        # Вставляем данные
        worksheet.update_values(
            f'A{next_row}:G{next_row}',
            [data],
            extend=True
        )
        return True
    except Exception as e:
        logging.error(f"Data append error: {str(e)}", exc_info=True)
        return False

async def add_report_to_sheet_report(data: dict):
    """Добавляем отчет в таблицу"""
    try:
        # Проверяем обязательные поля
        required_fields = ['Date', 'Manager', 'Partner', 'Result', 'Nickname', 'Datetime']
        if not all(field in data for field in required_fields):
            logging.error("Missing required fields in report data")
            return False

        gc = await authorize_google_sheets()
        worksheet = await get_or_create_worksheet(gc, WORKSHEET_NAME_REPORTS,
                                                  headers=['Date', 'Manager', 'Partner', 'Result',
                                                           'Nickname', 'Datetime'])

        # Подготавливаем данные
        row_data = [
            data.get('Date', 'Not specified'),
            data.get('Manager', 'Not specified'),
            data.get('Partner', 'Not specified'),
            data.get('Result', 'Not specified'),
            data.get('Nickname', 'Not specified'),
            data.get('Datetime', 'Not specified')
        ]

        # Добавляем данные
        success = await safe_append_data(worksheet, row_data)
        if success:
            logging.info(f"Report added successfully: {row_data}")
            return True
        return False

    except Exception as e:
        logging.error(f"Failed to add report: {str(e)}", exc_info=True)
        return False


async def add_report_to_sheet_booking(data: dict):
    """Добавляем отчет в таблицу"""
    try:
        # Проверяем обязательные поля
        required_fields = ['Date', 'Manager', 'Partner', 'Restaurant', 'Payment', 'Nickname', 'Datetime']
        if not all(field in data for field in required_fields):
            logging.error("Missing required fields in report data")
            return False

        gc = await authorize_google_sheets()
        worksheet = await get_or_create_worksheet(gc, WORKSHEET_NAME_BOOKING,
                                                  headers = ['Date', 'Manager', 'Partner', 'Restaurant', 'Payment', 'Nickname', 'Datetime'])

        # Форматируем дату
        meeting_date = data['Date']
        if isinstance(meeting_date, datetime):
            meeting_date = meeting_date.strftime('%d.%m.%Y')
        elif not meeting_date:
            meeting_date = 'Not specified'

        # Подготавливаем данные
        row_data = [
            meeting_date,
            data.get('Manager', 'Not specified'),
            data.get('Partner', 'Not specified'),
            data.get('Restaurant', 'Not specified'),
            data.get('Payment', 'Not specified'),
            data.get('Nickname', 'Not specified'),
            data.get('Datetime', 'Not specified')
        ]

        # Добавляем данные
        success = await safe_append_data(worksheet, row_data)
        if success:
            logging.info(f"Report added successfully: {row_data}")
            return True
        return False

    except Exception as e:
        logging.error(f"Failed to add report: {str(e)}", exc_info=True)
        return False


# async def test_report_function():
#     """Тестовая функция для проверки работы"""
#     test_data = {
#         'Date': '25.05.2023',
#         'Manager': 'John Doe',
#         'Partner': 'Acme Inc',
#         'Result': 'Contract signed'
#     }
#
#     result = await add_report_to_sheet(test_data)
#     print("Test result:", "Success" if result else "Failed")
#
#
# # Для тестирования
# if __name__ == "__main__":
#     import asyncio
#
#     asyncio.run(test_report_function())

