const fs = require('fs');
let c = fs.readFileSync('c:\\tgbot\\api\\webhook.py', 'utf8');

const oldConfirmAskMultiple = `ask_text = f"Ընտրված աշակերտը «{customer_name}» չունի «{loc['crm_prefix']}» պրեֆիքս: Սա՞ է ճիշտ աշակերտը: (Այո/Ոչ)" if lang=='hy' else f"Выбранный клиент «{customer_name}» не имеет префикса «{loc['crm_prefix']}». Это правильный клиент? (Да/Нет)"
                            await message.answer(ask_text)
                            return`;

const newConfirmAskMultiple = `ask_text = f"Ընտրված աշակերտը «{customer_name}» չունի «{loc['crm_prefix']}» պրեֆիքս: Սա՞ է ճիշտ աշակերտը: (Այո/Ոչ)" if lang=='hy' else f"Выбранный клиент «{customer_name}» не имеет префикса «{loc['crm_prefix']}». Это правильный клиент? (Да/Нет)"
                            
                            builder = InlineKeyboardBuilder()
                            builder.button(text="✅ Այո" if lang == "hy" else "✅ Да", callback_data="conf_yes")
                            builder.button(text="❌ Ոչ" if lang == "hy" else "❌ Нет", callback_data="conf_no")
                            builder.adjust(2)
                            
                            await message.answer(ask_text, reply_markup=builder.as_markup())
                            return`;

c = c.replace(oldConfirmAskMultiple, newConfirmAskMultiple);
fs.writeFileSync('c:\\tgbot\\api\\webhook.py', c, 'utf8');
console.log("done");
