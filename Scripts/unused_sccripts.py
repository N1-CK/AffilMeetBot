# @router.callback_query(F.data == 'report')
# @check_auth
# async def handle_report(call: CallbackQuery):
#     keyboard = await reports_menu_main()
#     await call.message.edit_text(
#         "Select an action to continue",
#         reply_markup=keyboard
#     )
#     await call.answer()

# @router.callback_query(F.data == 'send_check')
# @check_auth
# async def process_result2(call: CallbackQuery, state: FSMContext):
#     keyboard = await report_skip_menu()
#     await call.message.edit_text("Please, send me file with check or press 'Skip check'", reply_markup=keyboard)
#     await state.set_state(ReportStates.waiting_for_report)


# @router.callback_query(F.data == 'skip_report', ReportStates.waiting_for_report)
# @check_auth
# async def skip_report(call: CallbackQuery, state: FSMContext):
#     await send_report_summary(call.message, state)
#     await state.clear()
    # keyboard = await reports_menu()
    # await call.message.answer("Report saved without receipt", reply_markup=keyboard)
    # await call.answer()


# async def process_report_file(msg: Message, state: FSMContext, bot: Bot):
#     await send_report_summary(msg, state)
#
#     try:
#         await bot.send_document(
#             chat_id=REPORT_CHANNEL_ID,
#             document=msg.document.file_id,
#             caption=f"Report from @{msg.from_user.username}"
#         )
#         keyboard = await reports_menu()
#         await msg.answer("✅ Report successfully submitted!", reply_markup=keyboard)
#     except Exception as e:
#         logging.error(f"Report error: {e}")
#         keyboard = await reports_menu()
#         await msg.answer("Failed to submit report", reply_markup=keyboard)
#     finally:
#         await state.clear()


# @router.message(F.document, ReportStates.waiting_for_report)
# @check_auth
# async def send_report_summary(message: Message, state: FSMContext):
#     data = await state.get_data()
#     report_text = (
#         "📝 Meeting Report Summary:\n\n"
#         f"📅 Meeting Date: {data.get('Date', 'Not specified')}\n"
#         f"👨‍💼 Manager: {data.get('Manager', 'Not specified')}\n"
#         f"🤝 Partner: {data.get('Partner', 'Not specified')}\n"
#         f"📌 Result: {data.get('Result', 'Not specified')}\n"
#         f"💰 Budget: {data.get('Budget', 'Not specified')}\n\n"
#         "Please confirm the information:"
#     )
#
#     await message.answer(report_text, reply_markup=await create_confirmation_keyboard())
#     await state.set_state(ReportStates.waiting_for_confirmation)