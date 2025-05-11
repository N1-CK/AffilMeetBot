from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

async def main_menu():
    inline_kb_list = [
        [InlineKeyboardButton(text="📌 Restaurants", callback_data="restaurants"),
         InlineKeyboardButton(text="📝 Report", callback_data="report")],
        [InlineKeyboardButton(text="ℹ️ Conference policy", callback_data="policy_conference"),
         InlineKeyboardButton(text="ℹ️ Limit policy", callback_data="policy_limits")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)

async def restaurants_menu():
    inline_kb_list2 = [
        [InlineKeyboardButton(text=f"Back", callback_data=f"main_page"),
         InlineKeyboardButton(text=f"🏠 Main page", callback_data=f"main_page")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list2)

async def policy_limits_menu():
    inline_kb_list3 = [
        [
         InlineKeyboardButton(text=f"🏠 Main page", callback_data=f"main_page")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list3)

async def policy_conference_menu():
    inline_kb_list3 = [
        [
         InlineKeyboardButton(text=f"🏠 Main page", callback_data=f"main_page")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list3)




async def report_skip_menu():
    inline_kb_list3 = [
        [InlineKeyboardButton(text="⏩️ Skip check", callback_data="skip_report")],
        [InlineKeyboardButton(text="↩️ Cancel", callback_data="main_page")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list3)


async def reports_menu_main():
    inline_kb_list3 = [
        [InlineKeyboardButton(text=f"Make report", callback_data=f"make_report"),
         InlineKeyboardButton(text=f"Send check", callback_data=f"send_check")],
        [InlineKeyboardButton(text=f"🏠 Main page", callback_data=f"main_page")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list3)

async def reports_menu():
    inline_kb_list3 = [
        [InlineKeyboardButton(text=f"New report?", callback_data=f"make_report"),
         InlineKeyboardButton(text=f"🏠 Main page", callback_data=f"main_page")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list3)