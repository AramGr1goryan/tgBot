const fs = require('fs');

let content = fs.readFileSync('c:\\tgbot\\api\\webhook.py', 'utf-8');

const check_handler = `
@dp.message(Command("check"))
async def cmd_check_kassa(message: types.Message):
    user_id = message.from_user.id
    if user_id not in EXECUTORS:
        await ensure_db()
        lang = await get_user_language(user_id)
        await message.answer(t("unreg_user", lang))
        return
        
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Формат: /check [сумма]")
        return
        
    try:
        summ = float(parts[1].replace(',', '.'))
        if summ.is_integer():
            summ = int(summ)
    except ValueError:
        await message.answer("Неверный формат суммы. Укажите число.")
        return
        
    await ensure_db()
    loc = await get_user_location(user_id)
    lang = await get_user_language(user_id)
    
    tab_name = loc.get("sheets_tab")
    if not tab_name:
        await message.answer("Вкладка ДДС для вашей локации не настроена.")
        return
    
    processing_msg = await message.answer(f"⏳ Проверяю кассу для {loc['name']}...")
    
    success, val = await get_last_h_value(tab_name)
    if not success:
        await processing_msg.edit_text(f"❌ Ошибка при получении данных из таблицы: {val}")
        return
        
    try:
        last_h = float(str(val).replace(" ", "").replace("\\xa0", "").replace(",", "."))
        if last_h.is_integer():
            last_h = int(last_h)
    except ValueError:
        last_h = val
        
    match = (summ == last_h)
    
    response_text = f"По ДДС: {last_h}\\nКасса факт: {summ}\\n\\n"
    if match:
        response_text += "✅ Суммы совпадают!"
    else:
        response_text += "❌ Внимание! Суммы НЕ совпадают!"
        
    await processing_msg.edit_text(response_text)
    
    # Отправка в группу
    executor_name = EXECUTORS[user_id]
    group_msg = f"👤 {executor_name} проверял(а) кассу ({loc['crm_prefix']}):\\nСумма по ДДС: {last_h}\\nФакт: {summ}\\n{'✅ Совпадает' if match else '❌ Расхождение!'}"
    
    if GROUP_CHAT_ID:
        try:
            chat_id_int = int(GROUP_CHAT_ID)
            thread_id_int = int(TOPIC_THREAD_ID) if TOPIC_THREAD_ID and TOPIC_THREAD_ID.strip() != "None" else None
            await message.bot.send_message(
                chat_id_int, group_msg, message_thread_id=thread_id_int
            )
        except Exception as e:
            print(f"Failed to send kassa check to group: {e}")

`;

content = content.replace('@app.post("/api/webhook")', check_handler + '@app.post("/api/webhook")');

fs.writeFileSync('c:\\tgbot\\api\\webhook.py', content, 'utf-8');
console.log("done");
