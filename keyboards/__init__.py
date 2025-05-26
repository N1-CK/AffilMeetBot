from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

async def companies():
    inline_kb_list = [
        [InlineKeyboardButton(text="Betmen Affs", callback_data="betmen_policy-conference"),
         InlineKeyboardButton(text="ToTheMoon Affs", callback_data="tothemoon_policy-conference")],
        [InlineKeyboardButton(text="ChinChin Partners", callback_data="chinchin_policy-conference"),
         InlineKeyboardButton(text="FTD Gallery", callback_data="ftd_policy-conference")],
        [InlineKeyboardButton(text="Chilli Partners", callback_data="chilli_policy-conference"),]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)

async def main_menu():
    inline_kb_list = [
        [InlineKeyboardButton(text="🍽 Restaurants", callback_data="restaurants"),
         InlineKeyboardButton(text="📝 Expense Report", callback_data="report")],
        [InlineKeyboardButton(text="ℹ️ Conference policy", callback_data="policy_conference"),
         InlineKeyboardButton(text="ℹ️ Spending Limits", callback_data="policy_limits")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)

async def restaurants_menu():
    inline_kb_list2 = [
        [InlineKeyboardButton(text=f"🍽 Restaurants list", callback_data=f"restaurants_list"),
         InlineKeyboardButton(text=f"✅ My Bookings", callback_data=f"booked_action")],
        [InlineKeyboardButton(text=f"🏠 Main Menu", callback_data=f"main_page")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list2)

async def restaurants_menu_back():
    inline_kb_list4 = [
        [
         InlineKeyboardButton(text=f"🏠 Main Menu", callback_data=f"main_page")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list4)

async def policy_limits_menu():
    inline_kb_list3 = [
        [
         InlineKeyboardButton(text=f"🏠 Main Menu", callback_data=f"main_page")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list3)

async def policy_conference_menu():
    inline_kb_list3 = [
        [
         InlineKeyboardButton(text=f"🏠 Main Menu", callback_data=f"main_page")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list3)


async def report_skip_menu():
    inline_kb_list3 = [
        [InlineKeyboardButton(text="⏩️ Skip Receipt", callback_data="skip_report")],
        [InlineKeyboardButton(text="↩️ Back", callback_data="main_page")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list3)


async def reports_menu_main():
    inline_kb_list3 = [
        [InlineKeyboardButton(text=f"Create Report", callback_data=f"make_report"),
         InlineKeyboardButton(text=f"Upload Receipt", callback_data=f"send_check")],
        [InlineKeyboardButton(text=f"🏠 Main Menu", callback_data=f"main_page")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list3)

async def reports_menu():
    inline_kb_list3 = [
        [InlineKeyboardButton(text=f"New report?", callback_data=f"make_report"),
         InlineKeyboardButton(text=f"🏠 Main Menu", callback_data=f"main_page")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list3)