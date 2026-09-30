const fs = require('fs');

let content = fs.readFileSync('c:\\tgbot\\api\\webhook.py', 'utf-8');

const helper = `
def apply_crm_prefix(original_name: str, new_prefix: str) -> str:
    parts = original_name.split('|', 1)
    if len(parts) == 2:
        left = parts[0].strip()
        if len(left) <= 15:
            return f"{new_prefix} | {parts[1].strip()}"
    return f"{new_prefix} | {original_name.strip()}"

`;

if (!content.includes("def apply_crm_prefix(")) {
    content = content.replace("async def update_alfacrm_customer_name(", helper + "async def update_alfacrm_customer_name(");
}

const callback_handler = `
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
        original_name = customer.get('name', '')
        new_name = apply_crm_prefix(original_name, loc['crm_prefix'])
        await update_alfacrm_customer_name(customer['id'], new_name)
        payer_name = customer.get('legal_name') or new_name
        
        await _execute_payment(callback.message, customer['id'], payer_name, new_name, pending['amount'], pending['method_raw'], pending['response_text'], loc, lang, processing_msg)
        PENDING_PAYMENTS.pop(user_id, None)
    else:
        await callback.message.edit_text(callback.message.text + "\\n\\n❌ " + ("Մերժված է" if lang=='hy' else "Отклонено"))
        await callback.message.answer(t("payment_pending", lang), parse_mode="Markdown")
        pending['state'] = 'need_id'

`;

if (!content.includes("def callback_confirm_prefix(")) {
    const idx = content.indexOf('@dp.message(Command("check"))');
    if (idx !== -1) {
        content = content.substring(0, idx) + callback_handler + content.substring(idx);
    }
}

const old_text_confirm = `                    new_name = f"{loc['crm_prefix']} | {customer.get('name', '')}"`;
const new_text_confirm = `                    new_name = apply_crm_prefix(customer.get('name', ''), loc['crm_prefix'])`;

content = content.replace(old_text_confirm, new_text_confirm);

fs.writeFileSync('c:\\tgbot\\api\\webhook.py', content, 'utf-8');
console.log("done");
