import re

with open('api/webhook.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports
if 'InlineKeyboardBuilder' not in content:
    content = content.replace('from aiogram import Bot, Dispatcher, types, F', 'from aiogram import Bot, Dispatcher, types, F\nfrom aiogram.utils.keyboard import InlineKeyboardBuilder\nfrom aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup')

# Replace cmd_checktasks and cmd_complete_task
pattern = re.compile(r'@dp.message\(Command\("checktasks"\)\).*?(?=@dp.message\(Command\("task"\)\))', re.DOTALL)

new_tasks_code = '''@dp.message(Command("checktasks"))
async def cmd_checktasks(message: types.Message):
    if not POSTGRES_URL:
        await message.answer("???? ????????? ???? (POSTGRES_URL is missing):")
        return

    await ensure_db()
    tasks = await get_tasks()
    if not tasks:
        await message.answer("?????????????? ????? ?????? ?:")
        return
        
    response = "?? **?????????????? ????:**\\n\\n"
    builder = InlineKeyboardBuilder()
    
    for task in tasks:
        task_id = task['id']
        task_desc = task['description']
        response += f"?? **Task{task_id}** - {task_desc}\\n"
        builder.button(text=f"? Task{task_id}", callback_data=f"complete_{task_id}")
        
    builder.adjust(2)
    await message.answer(response, parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("complete_"))
async def callback_complete_task(callback: types.CallbackQuery):
    await ensure_db()
    task_id = int(callback.data.split("_")[1])
    
    task_desc = await delete_task(task_id)
    if not task_desc:
        await callback.answer("??? ??????????? ????? ???????? ? ??? ??????:", show_alert=True)
    else:
        await callback.answer(f"? Task{task_id} ???????? ?:")
        user_info = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
        await bot.send_message(ADMIN_ID, f"??????????? {user_info} ?????? ???????? ?:\\nTask{task_id} - {task_desc}")
                
    tasks = await get_tasks()
    if not tasks:
        await callback.message.edit_text("?? ????? ?????????????? ???????? ??:", parse_mode="Markdown")
        return
        
    response = "?? **?????????????? ????:**\\n\\n"
    builder = InlineKeyboardBuilder()
    
    for task in tasks:
        t_id = task['id']
        t_desc = task['description']
        response += f"?? **Task{t_id}** - {t_desc}\\n"
        builder.button(text=f"? Task{t_id}", callback_data=f"complete_{t_id}")
    builder.adjust(2)
        
    await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=builder.as_markup())

'''

content = pattern.sub(new_tasks_code, content)

with open('api/webhook.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Replaced successfully")
