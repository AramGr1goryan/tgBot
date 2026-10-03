const fs = require('fs');

let content = fs.readFileSync('c:\\tgbot\\api\\webhook.py', 'utf-8');

// Fix apply_crm_prefix to remove all prefixes
const applyPrefixRegex = /def apply_crm_prefix\(original_name: str, new_prefix: str\) -> str:[\s\S]*?return f"\{new_prefix\} \| \{original_name\.strip\(\)\}"/g;
const newApplyPrefix = `def apply_crm_prefix(original_name: str, new_prefix: str) -> str:
    parts = original_name.split('|')
    # Keep only the last part if all previous parts are short (like prefixes)
    # Actually, let's just find the actual name by taking the last part if the previous parts are <= 15 chars.
    name_part = parts[-1].strip()
    for i in range(len(parts) - 1):
        if len(parts[i].strip()) > 15:
            # If any part before the last one is long, it's probably not just prefixes.
            # In this case, just use the original logic (replace only the first part if it's short).
            if len(parts[0].strip()) <= 15:
                return f"{new_prefix} | {'|'.join(parts[1:]).strip()}"
            return f"{new_prefix} | {original_name.strip()}"
            
    # If all parts before the last are short, they are all prefixes. Remove them all.
    return f"{new_prefix} | {name_part}"`;

content = content.replace(applyPrefixRegex, newApplyPrefix);

// Now fix process_payment to add inline buttons for confirmation
const oldConfirmAsk = `ask_text = f"Գտնվել է «{customer_name}» աշակերտը, բայց նա չունի «{loc['crm_prefix']}» պրեֆիքս: Սա՞ է ճիշտ աշակերտը: (Այո/Ոչ)" if lang=='hy' else f"Найден клиент «{customer_name}», но он не имеет префикса «{loc['crm_prefix']}». Это правильный клиент? (Да/Нет)"
        await message.answer(ask_text)
        PENDING_PAYMENTS[message.from_user.id] = {
            'amount': amount_int,
            'method_raw': payment_method_raw,
            'response_text': response_text,
            'state': 'confirm_prefix',
            'customer': customer
        }
        return`;

const newConfirmAsk = `ask_text = f"Գտնվել է «{customer_name}» աշակերտը, բայց նա չունի «{loc['crm_prefix']}» պրեֆիքս: Սա՞ է ճիշտ աշակերտը: (Այո/Ոչ)" if lang=='hy' else f"Найден клиент «{customer_name}», но он не имеет префикса «{loc['crm_prefix']}». Это правильный клиент? (Да/Нет)"
        
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Այո" if lang == "hy" else "✅ Да", callback_data="conf_yes")
        builder.button(text="❌ Ոչ" if lang == "hy" else "❌ Нет", callback_data="conf_no")
        builder.adjust(2)
        
        await message.answer(ask_text, reply_markup=builder.as_markup())
        PENDING_PAYMENTS[message.from_user.id] = {
            'amount': amount_int,
            'method_raw': payment_method_raw,
            'response_text': response_text,
            'state': 'confirm_prefix',
            'customer': customer
        }
        return`;

content = content.replace(oldConfirmAsk, newConfirmAsk);

// Add the callback handler for conf_yes and conf_no
const callbackHandler = `
@dp.callback_query(F.data.in_({"conf_yes", "conf_no"}))
async def process_confirm_prefix_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in PENDING_PAYMENTS:
        await callback.message.edit_text("❌ Սեսիան ավարտվել է:" if True else "❌ Сессия устарела.")
        return
        
    pending = PENDING_PAYMENTS[user_id]
    if pending.get('state') != 'confirm_prefix':
        await callback.message.edit_text("❌ Սխալ կարգավիճակ:" if True else "❌ Неверный статус.")
        return
        
    lang = await get_user_language(user_id)
    loc = await get_user_location(user_id)
    
    if callback.data == "conf_no":
        await callback.message.edit_text(t("payment_pending", lang), parse_mode="Markdown")
        pending['state'] = 'need_id'
        return
        
    # User clicked YES
    customer = pending['customer']
    processing_msg = await callback.message.edit_text(t("payment_processing", lang))
    new_name = apply_crm_prefix(customer.get('name', ''), loc['crm_prefix'])
    await update_alfacrm_customer_name(customer['id'], new_name)
    payer_name = customer.get('legal_name') or new_name
    await _execute_payment(callback.message, customer['id'], payer_name, new_name, pending['amount'], pending['method_raw'], pending['response_text'], loc, lang, processing_msg)
    PENDING_PAYMENTS.pop(user_id, None)
`;

// Insert the callback handler before def apply_crm_prefix
content = content.replace("def apply_crm_prefix(", callbackHandler + "\ndef apply_crm_prefix(");

fs.writeFileSync('c:\\tgbot\\api\\webhook.py', content, 'utf-8');
console.log("done");
