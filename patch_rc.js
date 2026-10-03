const fs = require('fs');

const rc_code = `
@dp.message(Command("rc"))
async def cmd_rc(message: types.Message):
    user_id = message.from_user.id
    if user_id not in EXECUTORS:
        await ensure_db()
        lang = await get_user_language(user_id)
        await message.answer(t("unreg_user", lang))
        return
        
    parts = message.text.split(" ", 2)
    if len(parts) < 3:
        await message.answer("Формат: /rc [сумма] [причина]")
        return
        
    try:
        amount = int(parts[1].replace(',', '').replace('.', '').replace(' ', ''))
    except ValueError:
        await message.answer("Неверный формат суммы. Укажите число.")
        return
        
    reason = parts[2].strip()
    
    await ensure_db()
    loc = await get_user_location(user_id)
    lang = await get_user_language(user_id)
    
    tab_name = loc.get("sheets_tab")
    if not tab_name:
        await message.answer("Вкладка ДДС для вашей локации не настроена.")
        return
    
    processing_msg = await message.answer(f"⏳ Добавляю расход для {loc['name']}...")
    
    import zoneinfo
    from datetime import datetime
    from api.sheets import append_expense_to_sheet
    tz = zoneinfo.ZoneInfo("Asia/Yerevan")
    date_str = datetime.now(tz).strftime("%d.%m.%Y")
    
    success, err = await append_expense_to_sheet(date_str, reason, amount, tab_name=tab_name)
    if success:
        await processing_msg.edit_text(f"✅ Расход успешно добавлен!\\nСумма: {amount}\\nПричина: {reason}\\nФилиал: {loc['name']}")
    else:
        await processing_msg.edit_text(f"❌ Ошибка при добавлении расхода:\\n{err}")

`;

let content = fs.readFileSync('c:\\tgbot\\api\\webhook.py', 'utf8');
content = content.replace('@dp.message(Command("check"))', rc_code + '@dp.message(Command("check"))');
fs.writeFileSync('c:\\tgbot\\api\\webhook.py', content, 'utf8');
console.log("Done");
