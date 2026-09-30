import re

with open(r'c:\tgbot\api\webhook.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add the callback handler before process_payment
callback_handler = """
@dp.callback_query(F.data.startswith("confirm_prefix_"))
async def callback_confirm_prefix(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in PENDING_PAYMENTS:
        await callback.message.edit_text("Сессия истекла / Session expired.")
        return
        
    pending = PENDING_PAYMENTS[user_id]
    if pending.get('state') != 'confirm_prefix':
        await callback.message.edit_text("Неверное состояние / Invalid state.")
        return
        
    ans = callback.data.split("_")[-1]
    
    await ensure_db()
    loc  = await get_user_location(user_id)
    lang = await get_user_language(user_id)
    
    if ans == "yes":
        customer = pending['customer']
        await callback.message.edit_text(callback.message.text + "\\n\\n✅ " + ("Հաստատված է" if lang=='hy' else "Подтверждено"))
        processing_msg = await callback.message.answer(t("payment_processing", lang))
        new_name = f"{loc['crm_prefix']} | {customer.get('name', '')}"
        await update_alfacrm_customer_name(customer['id'], new_name)
        payer_name = customer.get('legal_name') or new_name
        
        await _execute_payment(callback.message, customer['id'], payer_name, new_name, pending['amount'], pending['method_raw'], pending['response_text'], loc, lang, processing_msg)
        PENDING_PAYMENTS.pop(user_id, None)
    else:
        await callback.message.edit_text(callback.message.text + "\\n\\n❌ " + ("Մերժված է" if lang=='hy' else "Отклонено"))
        await callback.message.answer(t("payment_pending", lang), parse_mode="Markdown")
        pending['state'] = 'need_id'

"""

content = content.replace('@dp.message(F.chat.type == "private")\nasync def process_payment', callback_handler + '@dp.message(F.chat.type == "private")\nasync def process_payment')

# 2. Replace the two occurrences of asking for prefix confirmation
old_ask_1 = """                            ask_text = f"Ընտրված աշակերտը «{customer_name}» չունի «{loc['crm_prefix']}» պրեֆիքս: Սա՞ է ճիշտ աշակերտը: (Այո/Ոչ)" if lang=='hy' else f"Выбранный клиент «{customer_name}» не имеет префикса «{loc['crm_prefix']}». Это правильный клиент? (Да/Нет)"
                            await message.answer(ask_text)"""

new_ask_1 = """                            ask_text = f"Ընտրված աշակերտը «{customer_name}» չունի «{loc['crm_prefix']}» պրեֆիքս: Սա՞ է ճիշտ աշակերտը:" if lang=='hy' else f"Выбранный клиент «{customer_name}» не имеет префикса «{loc['crm_prefix']}». Это правильный клиент?"
                            builder = InlineKeyboardBuilder()
                            builder.button(text="Այո" if lang=='hy' else "Да", callback_data="confirm_prefix_yes")
                            builder.button(text="Ոչ" if lang=='hy' else "Нет", callback_data="confirm_prefix_no")
                            await message.answer(ask_text, reply_markup=builder.as_markup())"""

content = content.replace(old_ask_1, new_ask_1)


old_ask_2 = """        ask_text = f"Գտնվել է «{customer_name}» աշակերտը, բայց նա չունի «{loc['crm_prefix']}» պրեֆիքս: Սա՞ է ճիշտ աշակերտը: (Այո/Ոչ)" if lang=='hy' else f"Найден клиент «{customer_name}», но он не имеет префикса «{loc['crm_prefix']}». Это правильный клиент? (Да/Нет)"
        await message.answer(ask_text)"""

new_ask_2 = """        ask_text = f"Գտնվել է «{customer_name}» աշակերտը, բայց նա չունի «{loc['crm_prefix']}» պրեֆիքս: Սա՞ է ճիշտ աշակերտը:" if lang=='hy' else f"Найден клиент «{customer_name}», но он не имеет префикса «{loc['crm_prefix']}». Это правильный клиент?"
        builder = InlineKeyboardBuilder()
        builder.button(text="Այո" if lang=='hy' else "Да", callback_data="confirm_prefix_yes")
        builder.button(text="Ոչ" if lang=='hy' else "Нет", callback_data="confirm_prefix_no")
        await message.answer(ask_text, reply_markup=builder.as_markup())"""

content = content.replace(old_ask_2, new_ask_2)

with open(r'c:\tgbot\api\webhook.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
