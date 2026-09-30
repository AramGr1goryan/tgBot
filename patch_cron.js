const fs = require('fs');

let content = fs.readFileSync('c:\\tgbot\\api\\webhook.py', 'utf-8');

const route = `
@app.get("/api/cron/remind-kassa")
async def cron_remind_kassa():
    await ensure_db()
    if not bot:
        return {"status": "error", "message": "Bot not initialized"}
        
    count = 0
    for user_id in EXECUTORS:
        try:
            lang = await get_user_language(user_id)
            loc = await get_user_location(user_id)
            msg_text = f"⏰ <b>Напоминание</b>\\nПожалуйста, сверьте кассу (ДДС) для филиала {loc['name']} и отправьте команду: \\n<code>/check [сумма]</code>"
            await bot.send_message(user_id, msg_text, parse_mode="HTML")
            count += 1
        except Exception as e:
            print(f"Failed to send reminder to {user_id}: {e}")
            
    if GROUP_CHAT_ID:
        try:
            chat_id_int = int(GROUP_CHAT_ID)
            thread_id_int = int(TOPIC_THREAD_ID) if TOPIC_THREAD_ID and TOPIC_THREAD_ID.strip() != "None" else None
            group_msg = f"🔔 Бот успешно разослал напоминания {count} администраторам о проверке кассы (ДДС)."
            await bot.send_message(
                chat_id_int, 
                group_msg,
                message_thread_id=thread_id_int
            )
        except Exception as e:
            print(f"Failed to send kassa reminder to group: {e}")
            
    return {"status": "ok", "sent_to": count}
`;

content += route;
fs.writeFileSync('c:\\tgbot\\api\\webhook.py', content, 'utf-8');
console.log("done");
