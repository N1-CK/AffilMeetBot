from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

async def main_menu():
    inline_kb_list = [
        [InlineKeyboardButton(text="📌 Restaurants", callback_data="restaurants")],
        [InlineKeyboardButton(text="Limit policy", callback_data="policy_limits")],
        [InlineKeyboardButton(text="Policy on conferences", callback_data="policy_conference")],
        [InlineKeyboardButton(text="Report", callback_data="report")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list)

async def restaurants_menu():
    inline_kb_list2 = [
        [InlineKeyboardButton(text=f"Back", callback_data=f"main_page"),
         InlineKeyboardButton(text=f"Main page", callback_data=f"main_page")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list2)

async def policy_limits_menu():
    inline_kb_list3 = [
        [InlineKeyboardButton(text=f"Back", callback_data=f"main_page"),
         InlineKeyboardButton(text=f"Main page", callback_data=f"main_page")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list3)

async def policy_conference_menu():
    inline_kb_list3 = [
        [InlineKeyboardButton(text=f"Back", callback_data=f"main_page"),
         InlineKeyboardButton(text=f"Main page", callback_data=f"main_page")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list3)

async def reports_menu():
    inline_kb_list3 = [
        [InlineKeyboardButton(text=f"Back", callback_data=f"main_page"),
         InlineKeyboardButton(text=f"Main page", callback_data=f"main_page")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb_list3)