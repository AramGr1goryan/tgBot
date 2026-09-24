import asyncio
import os

WEBHOOK_PATH = r"C:\tgbot\api\webhook.py"

def main():
    with open(WEBHOOK_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # cmd_start
    content = content.replace(
        '"Ողջույն: Որպեսզի ես կարողանամ ուղարկել վճարումները խմբին, ինձ անհրաժեշտ է իմանալ ձեր անունը:\\n\\n"\\n        "Գրեք ձեր անունը ռուսերենով (օրինակ՝ Рипсиме):"',
        't("start_msg", lang)'
    )
    content = content.replace(
        'async def cmd_start(message: types.Message):',
        'async def cmd_start(message: types.Message):\n    await ensure_db()\n    lang = await get_user_language(message.from_user.id)'
    )
    
    # process_name_registration
    content = content.replace(
        '"Խնդրում ենք գրել միայն ռուսերեն տառերով (օրինակ՝ Рипсиме):"',
        't("start_req_ru", lang)'
    )
    content = content.replace(
        'f"✅ Ձեր անունը պահպանված է որպես \'{name}\':\\n\\n"\\n        "Այժմ կարող եք ուղարկել հաղորդագրություններ վճարումների համար հետևյալ ձևաչափով՝\\n"\\n        "Անուն Ազգանուն Գումար Վճարման_Եղանակ"',
        't("start_success", lang, name=name)'
    )
    content = content.replace(
        'async def process_name_registration(message: types.Message):\n    name = message.text.strip()',
        'async def process_name_registration(message: types.Message):\n    name = message.text.strip()\n    await ensure_db()\n    lang = await get_user_language(message.from_user.id)'
    )
    
    # cmd_addtask
    content = content.replace(
        '"Խնդրում ենք նշել առաջադրանքի նկարագրությունը: Օրինակ՝ /addtask Ջնջել խումբը"',
        't("task_desc_req", lang)'
    )
    content = content.replace(
        '"Բազան միացված չէ (POSTGRES_URL is missing):"',
        't("no_db", lang)'
    )
    content = content.replace(
        '"Առաջադրանքը ավելացված է:"',
        't("task_added", lang, loc=loc["name"])'
    )
    content = content.replace(
        'f"📌 **Նոր առաջադրանք!**\\n\\n👤 Ավելացրեց՝ {user_info}\\n🔹 {task_description}"',
        't("task_added_push", lang, loc=loc["name"], user=user_info, desc=task_description)'
    )
    content = content.replace(
        'async def cmd_addtask(message: types.Message):\n    task_description = message.text.replace("/addtask", "", 1).strip()',
        'async def cmd_addtask(message: types.Message):\n    await ensure_db()\n    lang = await get_user_language(message.from_user.id)\n    task_description = message.text.replace("/addtask", "", 1).strip()'
    )
    
    # cmd_checktasks
    content = content.replace(
        '"Առաջադրանքների ցանկը դատարկ է:"',
        't("task_empty", lang)'
    )
    content = content.replace(
        'f"📝 **{loc[\'name\']} — Առաջադրանքների ցանկ:**\\n\\n"',
        't("task_header", lang, loc=loc["name"])'
    )
    content = content.replace(
        'loc = await get_user_location(message.from_user.id)',
        'loc = await get_user_location(message.from_user.id)\n    lang = await get_user_language(message.from_user.id)'
    )
    
    # callback_complete_task
    content = content.replace(
        '"Այս առաջադրանքը արդեն կատարված է կամ ջնջված։"',
        't("task_not_found_cb", lang)'
    )
    content = content.replace(
        'f"✅ Task{task_id} կատարված է։"',
        't("task_done_cb", lang, n=task_id)'
    )
    content = content.replace(
        'f"✅ **Առաջադրանքը կատարվել է!**\\n\\n👤 Կատարեց՝ {user_info}\\n🔹 **Task{task_id}** — {task_desc}"',
        't("task_done_push", lang, user=user_info, n=task_id, desc=task_desc)'
    )
    content = content.replace(
        '"🎉 Բոլոր առաջադրանքները կատարված են։"',
        't("task_all_done", lang)'
    )
    content = content.replace(
        'f"📝 **{loc_name} — Առաջադրանքների ցանկ:**\\n\\n"',
        't("task_header", lang, loc=loc_name)'
    )
    content = content.replace(
        'async def callback_complete_task(callback: types.CallbackQuery):\n    await ensure_db()',
        'async def callback_complete_task(callback: types.CallbackQuery):\n    await ensure_db()\n    lang = await get_user_language(callback.from_user.id)'
    )

    # cmd_complete_task_number
    content = content.replace(
        'f"❌ Task{task_id} չի գտնվել կամ արդեն կատարված է:"',
        't("task_not_found_cmd", lang, n=task_id)'
    )
    content = content.replace(
        'f"✅ Task{task_id} — «{task_desc}» կատարված է:"',
        't("task_done_cmd", lang, n=task_id, desc=task_desc)'
    )
    content = content.replace(
        'async def cmd_complete_task_number(message: types.Message):\n    match = re.match',
        'async def cmd_complete_task_number(message: types.Message):\n    await ensure_db()\n    lang = await get_user_language(message.from_user.id)\n    match = re.match'
    )
    
    # cmd_task_hint
    content = content.replace(
        '"Խնդրում ենք նշել առաջադրանքի համարը, օրինակ՝ /task1"',
        't("task_hint", lang)'
    )
    content = content.replace(
        'async def cmd_task_hint(message: types.Message):\n    await message.answer(',
        'async def cmd_task_hint(message: types.Message):\n    await ensure_db()\n    lang = await get_user_language(message.from_user.id)\n    await message.answer('
    )

    with open(WEBHOOK_PATH, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    main()
