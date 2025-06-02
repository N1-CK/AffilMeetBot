from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# async def companies():
#     inline_kb_list = [
#         [InlineKeyboardButton(text="Betmen Affs", callback_data="betmen_policy-conference"),
#          InlineKeyboardButton(text="ToTheMoon Affs", callback_data="tothemoon_policy-conference")],
#         [InlineKeyboardButton(text="ChinChin Partners", callback_data="chinchin_policy-conference"),
#          InlineKeyboardButton(text="FTD Gallery", callback_data="ftd_policy-conference")],
#         [InlineKeyboardButton(text="Chilli Partners", callback_data="chilli_policy-conference"),]
#     ]
#     return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)

async def create_confirmation_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Correct", callback_data="report_correct"),
        InlineKeyboardButton(text="❌ Incorrect", callback_data="report_incorrect")
    )
    builder.row(
        InlineKeyboardButton(text=f"↩️ Close without saving", callback_data=f"main_page")
    )
    return builder.as_markup()

async def create_edit_keyboard():
    inline_kb_list = [
        [InlineKeyboardButton(text="📅 Date", callback_data="edit_date"),
         InlineKeyboardButton(text="👨‍💼 Manager", callback_data="edit_manager")],
        [InlineKeyboardButton(text="🤝 Partner", callback_data="edit_partner"),
         InlineKeyboardButton(text="📌 Result", callback_data="edit_result")],
        [InlineKeyboardButton(text="💰 Budget", callback_data="edit_budget"),
         InlineKeyboardButton(text="🔙 Cancel", callback_data="edit_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)

async def main_menu():
    inline_kb_list = [
        [InlineKeyboardButton(text="🍽 Restaurants", callback_data="restaurants"),
         InlineKeyboardButton(text="📝 Expense Report", callback_data="make_report")],
        [InlineKeyboardButton(text="ℹ️ Conference policy", callback_data="policy_conference"),
         InlineKeyboardButton(text="ℹ️ Spending Limits", callback_data="policy_limits")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)

async def conference_menu():
    inline_kb_list2 = [
        [InlineKeyboardButton(text="📅 Cities list", callback_data="conference_list"),
         InlineKeyboardButton(text="✅ My Bookings", callback_data="booked_action")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_page")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list2)

# async def restaurants_menu():
#     inline_kb_list2 = [
#         [InlineKeyboardButton(text=f"🍽 Restaurants list", callback_data=f"restaurant_list"),
#          InlineKeyboardButton(text=f"✅ My Bookings", callback_data=f"booked_action")],
#         [InlineKeyboardButton(text=f"🏠 Main Menu", callback_data=f"main_page")]
#     ]
#     return InlineKeyboardMarkup(inline_keyboard=inline_kb_list2)

async def restaurants_menu_back(confa):
    inline_kb_list4 = [
        [
         InlineKeyboardButton(text=f"↩️ Back", callback_data=f"confa_{confa}"),
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


# async def report_skip_menu():
#     inline_kb_list3 = [
#         [InlineKeyboardButton(text="⏩️ Skip Receipt", callback_data="skip_report")],
#         [InlineKeyboardButton(text="↩️ Back", callback_data="main_page")]
#     ]
#     return InlineKeyboardMarkup(inline_keyboard=inline_kb_list3)


async def reports_menu_main():
    inline_kb_list3 = [
        [InlineKeyboardButton(text=f"Create Report", callback_data=f"make_report")],
        [InlineKeyboardButton(text=f"🏠 Main Menu", callback_data=f"main_page")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list3)

async def reports_menu():
    inline_kb_list3 = [
        [InlineKeyboardButton(text=f"New report?", callback_data=f"make_report"),
         InlineKeyboardButton(text=f"🏠 Main Menu", callback_data=f"main_page")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list3)