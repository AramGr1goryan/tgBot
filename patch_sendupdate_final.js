const fs = require('fs');

let content = fs.readFileSync('c:\\tgbot\\api\\webhook.py', 'utf-8');

// The file was restored, so it still has the old cmd_sendupdate from line 2082 to 2147.
// We need to remove it.
let lines = content.split(/\r?\n/);
let out_lines = [];
let in_sendupdate = false;

for (let i = 0; i < lines.length; i++) {
    let line = lines[i];
    if (line.startsWith('@dp.message(Command("sendupdate"))')) {
        in_sendupdate = true;
        continue;
    }
    
    if (in_sendupdate) {
        if (line.startsWith('@dp.')) {
            in_sendupdate = false;
            out_lines.push(line);
        }
        continue;
    }
    
    out_lines.push(line);
}

content = out_lines.join('\n');

const new_sendupdate = `
PENDING_UPDATES = {}

@dp.message(Command("sendupdate"))
async def cmd_sendupdate(message: types.Message):
    if message.from_user.id != 1472817960:
        return
        
    ru_text = (
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
    hy_text = (
        "🚀 <b>Բոտի լայնածավալ թարմացում:</b>\\n\\n"
        "Մենք ավելացրել ենք բազմաթիվ նոր և հիանալի գործառույթներ՝ ձեր աշխատանքը հեշտացնելու համար.\\n\\n"
        "1️⃣ <b>Մասնաճյուղերի խելացի պրեֆիքսներ:</b> Եթե հաճախորդը արդեն ուներ այլ պրեֆիքս, բոտը չի կրկնապատկի դրանք: Այն զգուշորեն կհեռացնի հինը և կտեղադրի ձերը:\\n\\n"
        "2️⃣ <b>Ինտերակտիվ կոճակներ:</b> Առանց պրեֆիքսի հաճախորդին հաստատելիս այժմ հայտնվում են հարմար կոճակներ (Այո/Ոչ) տեքստային պատասխանի փոխարեն:\\n\\n"
        "3️⃣ <b>Հաճախորդների բարելավված որոնում:</b> Եթե գտնվել են մի քանի հաճախորդ նույն անունով, բոտը ցույց կտա նրանց ցանկը — բավական է պարզապես ուղարկել անհրաժեշտ համարը:\\n\\n"
        "4️⃣ <b>Նոր հրաման <code>/check [գումար]</code>:</b> Այժմ դրամարկղը ստուգելիս բոտը ոչ միայն ասում է համընկնում է, թե ոչ, այլև <b>հաշվարկում է ճշգրիտ տարբերությունը</b> (որքանով է գումարը տարբերվում աղյուսակից):\\n\\n"
        "5️⃣ <b>Ամենօրյա հիշեցումներ:</b> Բոտը սովորել է ինքնուրույն ամեն օր հիշեցնել ադմինիստրատորներին դրամարկղը ստուգելու անհրաժեշտության մասին:\\n\\n"
        "6️⃣ <b>Դերերի համակարգ:</b> Ավելացվել են դերեր (Մենեջեր / Ադմին): Դրամարկղի մասին հիշեցումները կստանան միայն նրանք, ում դրանք իսկապես պետք են:\\n\\n"
        "<i>Եթե նկատեք որևէ խնդիր, անմիջապես տեղեկացրեք ծրագրավորողին: Բարի աշխատանք:</i>"
    )
    
    PENDING_UPDATES[message.from_user.id] = {"ru": ru_text, "hy": hy_text}
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить всем", callback_data="broadcast_yes"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_no")
        ]
    ])
    
    preview_msg = "<b>Вот так выглядит текст (Русский):</b>\\n\\n" + ru_text + "\\n\\n<b>Вот так выглядит текст (Армянский):</b>\\n\\n" + hy_text + "\\n\\n<i>Отправить это сообщение всем пользователям?</i>"
    await message.answer(preview_msg, parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data.in_({"broadcast_yes", "broadcast_no"}))
async def callback_broadcast(callback: types.CallbackQuery):
    if callback.from_user.id != 1472817960:
        return
        
    ans = callback.data.split("_")[1]
    if ans == "no":
        await callback.message.edit_text("❌ Рассылка отменена.")
        PENDING_UPDATES.pop(callback.from_user.id, None)
        return
        
    data = PENDING_UPDATES.get(callback.from_user.id)
    if not data:
        await callback.message.edit_text("❌ Сессия устарела.")
        return
        
    await callback.message.edit_text("✅ Рассылка запущена...")
    await ensure_db()
    count = 0
    for uid in EXECUTORS:
        try:
            lang = await get_user_language(uid)
            text = data["hy"] if lang == "hy" else data["ru"]
            await bot.send_message(uid, text, parse_mode="HTML")
            count += 1
        except Exception as e:
            print(f"Failed to send update to {uid}: {e}")
            
    await callback.message.reply(f"✅ Уведомление об обновлении успешно разослано {count} пользователям!")
    PENDING_UPDATES.pop(callback.from_user.id, None)

`;

const idx = content.indexOf('@dp.message(Command("check"))');
if (idx !== -1) {
    content = content.substring(0, idx) + new_sendupdate + "\n" + content.substring(idx);
}

fs.writeFileSync('c:\\tgbot\\api\\webhook.py', content, 'utf-8');
console.log("done");
