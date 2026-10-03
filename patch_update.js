const fs = require('fs');

let content = fs.readFileSync('c:\\tgbot\\api\\webhook.py', 'utf-8');

const sendupdate_code = `
@dp.message(Command("sendupdate"))
async def cmd_sendupdate(message: types.Message):
    if message.from_user.id != 1472817960:
        return
        
    update_text = (
        "🚀 <b>Масштабное обновление бота!</b>\\n\\n"
        "Мы добавили множество новых и крутых функций, чтобы сделать вашу работу проще:\\n\\n"
        "1️⃣ <b>Умные префиксы филиалов:</b> Если у клиента уже был чужой префикс, бот не будет их наслаивать! Он аккуратно уберет старый и поставит ваш.\\n\\n"
        "2️⃣ <b>Интерактивные кнопки:</b> При подтверждении клиента без префикса теперь появляются удобные кнопки (Да/Нет) вместо текстового ответа.\\n\\n"
        "3️⃣ <b>Улучшенный поиск клиентов:</b> Если найдено несколько клиентов с одинаковым именем, бот покажет их списком — достаточно просто отправить номер нужного!\\n\\n"
        "4️⃣ <b>Новая команда <code>/check [сумма]</code>:</b> Теперь при сверке кассы бот не только говорит совпадает или нет, но и <b>считает точную разницу</b> (насколько сумма расходится с таблицей).\\n\\n"
        "5️⃣ <b>Ежедневные напоминания:</b> Бот научился сам каждый день напоминать администраторам о необходимости проверить кассу!\\n\\n"
        "6️⃣ <b>Система ролей:</b> Добавлены роли (Менеджер / Админ). Напоминания о кассе будут приходить только тем, кому они действительно нужны.\\n\\n"
        "<i>Если заметите какие-либо проблемы, сразу сообщайте разработчику. Приятной работы!</i>"
    )
    
    await ensure_db()
    count = 0
    for uid in EXECUTORS:
        try:
            await bot.send_message(uid, update_text, parse_mode="HTML")
            count += 1
        except Exception as e:
            print(f"Failed to send update to {uid}: {e}")
            
    await message.answer(f"✅ Уведомление об обновлении успешно разослано {count} пользователям!")
`;

const idx = content.indexOf('@dp.message(Command("check"))');
if (idx !== -1) {
    content = content.substring(0, idx) + sendupdate_code + "\n" + content.substring(idx);
}

fs.writeFileSync('c:\\tgbot\\api\\webhook.py', content, 'utf-8');
console.log("done");
