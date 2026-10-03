const fs = require('fs');

let content = fs.readFileSync('c:\\tgbot\\api\\webhook.py', 'utf8');

const oldBlock = `    success, err = await append_expense_to_sheet(date_str, reason, amount, tab_name=tab_name)
    if success:
        await processing_msg.edit_text(f"✅ Расход успешно добавлен!\\nСумма: {amount}\\nПричина: {reason}\\nФилиал: {loc['name']}")
    else:
        await processing_msg.edit_text(f"❌ Ошибка при добавлении расхода:\\n{err}")`;

const newBlock = `    success, err = await append_expense_to_sheet(date_str, reason, amount, tab_name=tab_name)
    if success:
        await processing_msg.edit_text(f"✅ Расход успешно добавлен!\\nСумма: {amount}\\nПричина: {reason}\\nФилиал: {loc['name']}")
        if GROUP_CHAT_ID:
            try:
                executor_name = EXECUTORS.get(user_id, "Неизвестный")
                chat_id_int = int(GROUP_CHAT_ID)
                thread_id_int = int(TOPIC_THREAD_ID) if TOPIC_THREAD_ID and str(TOPIC_THREAD_ID).strip() != "None" else None
                group_msg = f"💸 <b>Новый расход</b>\\nФилиал: {loc['name']}\\nСумма: {amount}\\nПричина: {reason}\\nДобавил(а): {executor_name}"
                await bot.send_message(
                    chat_id_int, 
                    group_msg,
                    message_thread_id=thread_id_int,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Failed to send expense notification to group: {e}")
    else:
        await processing_msg.edit_text(f"❌ Ошибка при добавлении расхода:\\n{err}")`;

content = content.replace(oldBlock, newBlock);
fs.writeFileSync('c:\\tgbot\\api\\webhook.py', content, 'utf8');
console.log("Done");
