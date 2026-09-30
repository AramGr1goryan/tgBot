const fs = require('fs');

let content = fs.readFileSync('c:\\tgbot\\api\\webhook.py', 'utf-8');

const old_ask_1 = `                            ask_text = f"Ընտրված աշակերտը «{customer_name}» չունի «{loc['crm_prefix']}» պրեֆիքս: Սա՞ է ճիշտ աշակերտը: (Այո/Ոչ)" if lang=='hy' else f"Выбранный клиент «{customer_name}» не имеет префикса «{loc['crm_prefix']}». Это правильный клиент? (Да/Нет)"
                            await message.answer(ask_text)`;

const new_ask_1 = `                            ask_text = f"Ընտրված աշակերտը «{customer_name}» չունի «{loc['crm_prefix']}» պրեֆիքս: Սա՞ է ճիշտ աշակերտը:" if lang=='hy' else f"Выбранный клиент «{customer_name}» не имеет префикса «{loc['crm_prefix']}». Это правильный клиент?"
                            builder = InlineKeyboardBuilder()
                            builder.button(text="Այո" if lang=='hy' else "Да", callback_data="confirm_prefix_yes")
                            builder.button(text="Ոչ" if lang=='hy' else "Нет", callback_data="confirm_prefix_no")
                            await message.answer(ask_text, reply_markup=builder.as_markup())`;

content = content.replace(old_ask_1, new_ask_1);

fs.writeFileSync('c:\\tgbot\\api\\webhook.py', content, 'utf-8');
console.log("done");
