from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ForceReply
from transliterate import translit
import asyncpg
import os
import re
from io import BytesIO
from bs4 import BeautifulSoup

API_TOKEN = os.getenv("BOT_TOKEN")
POSTGRES_URL = os.getenv("POSTGRES_URL")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
TOPIC_THREAD_ID = os.getenv("TOPIC_THREAD_ID")
ADMIN_ID = 1472817960

bot = Bot(token=API_TOKEN) if API_TOKEN else None
dp = Dispatcher()
app = FastAPI()

PAYMENT_METHODS = {
    'n': 'Наличка',
    'b.n': 'На терминал',
    'c': 'На карту',
    'с': 'На карту'
}

db_initialized = False

async def ensure_db():
    global db_initialized
    if db_initialized or not POSTGRES_URL:
        return
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    await conn.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id SERIAL PRIMARY KEY, description TEXT)''')
    # Таблицы для Lego
    await conn.execute('''CREATE TABLE IF NOT EXISTS lego_groups
                 (id SERIAL PRIMARY KEY, name TEXT UNIQUE)''')
    await conn.execute('''CREATE TABLE IF NOT EXISTS lego_themes
                 (id SERIAL PRIMARY KEY, group_id INTEGER REFERENCES lego_groups(id) ON DELETE CASCADE, name TEXT)''')
    await conn.close()
    db_initialized = True

async def add_task(description: str):
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    await conn.execute("INSERT INTO tasks (description) VALUES ($1)", description)
    await conn.close()

async def get_tasks():
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    rows = await conn.fetch("SELECT id, description FROM tasks ORDER BY id")
    await conn.close()
    return rows

async def delete_task(task_id: int):
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    row = await conn.fetchrow("SELECT description FROM tasks WHERE id = $1", task_id)
    if row:
        await conn.execute("DELETE FROM tasks WHERE id = $1", task_id)
        await conn.close()
        return row['description']
    await conn.close()
    return None

def transliterate_name(text: str) -> str:
    text = text.replace('yan', 'ян').replace('Yan', 'Ян')
    text = text.replace('ya', 'я').replace('Ya', 'Я')
    try:
        return translit(text, 'ru')
    except Exception:
        return text

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Ողջույն: Ուղարկեք ինձ հաղորդագրություն հետևյալ ձևաչափով՝\nԱնուն Ազգանուն Գումար Վճարման_Եղանակ")

@dp.message(Command("getid"))
async def cmd_getid(message: types.Message):
    await message.answer(
        f"Chat ID: {message.chat.id}\n"
        f"Topic (Thread) ID: {message.message_thread_id}"
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "Ինչպես ճիշտ գրել հաղորդագրությունները՝\n\n"
        "Ձևաչափ՝ Անուն Ազգանուն Գումար Եղանակ\n\n"
        "Օրինակ՝ Aram Grigoryan 50000 N\n\n"
        "Հասանելի վճարման եղանակներ՝\n"
        "N — Կանխիկ\n"
        "b.n — Տերմինալով\n"
        "c — Քարտով"
    )

@dp.message(Command("addtask"))
async def cmd_addtask(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Դուք չունեք առաջադրանքներ ավելացնելու իրավունք:")
        return
        
    task_description = message.text.replace("/addtask", "", 1).strip()
    if not task_description:
        await message.answer("Խնդրում ենք նշել առաջադրանքի նկարագրությունը: Օրինակ՝ /addtask Ջնջել խումբը")
        return
        
    if not POSTGRES_URL:
        await message.answer("Բազան միացված չէ (POSTGRES_URL is missing):")
        return

    await ensure_db()
    await add_task(task_description)
    await message.answer("Առաջադրանքը ավելացված է:")

@dp.message(Command("checktasks"))
async def cmd_checktasks(message: types.Message):
    if not POSTGRES_URL:
        await message.answer("Բազան միացված չէ (POSTGRES_URL is missing):")
        return

    await ensure_db()
    tasks = await get_tasks()
    if not tasks:
        await message.answer("Առաջադրանքների ցանկը դատարկ է:")
        return
        
    response = ""
    for task in tasks:
        response += f"Task{task['id']} - {task['description']}\n"
    await message.answer(response)

@dp.message(F.text.regexp(r'^/[Tt][Aa][Ss][Kk](\d+)$'))
async def cmd_complete_task(message: types.Message):
    if not POSTGRES_URL:
        await message.answer("Բազան միացված չէ (POSTGRES_URL is missing):")
        return

    match = re.match(r'^/task(\d+)$', message.text, re.IGNORECASE)
    if not match:
        return
    task_id = int(match.group(1))
    
    await ensure_db()
    task_desc = await delete_task(task_id)
    if task_desc:
        await message.answer(f"Task{task_id} - {task_desc} կատարված է")
        
        user_info = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
        await bot.send_message(ADMIN_ID, f"Ադմինիստրատոր {user_info} կատարեց առաջադրանքը:\nTask{task_id} - {task_desc}")
    else:
        await message.answer("Առաջադրանքը չի գտնվել:")

# Загрузка HTML файла с темами Lego
@dp.message(F.document)
async def process_html_upload(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.document.file_name.endswith('.html'):
        return
        
    await message.answer("Загружаю и обрабатываю HTML файл Lego...")
    file = await bot.get_file(message.document.file_id)
    file_bytes = BytesIO()
    await bot.download_file(file.file_path, file_bytes)
    html_content = file_bytes.getvalue().decode('utf-8')
    
    soup = BeautifulSoup(html_content, 'html.parser')
    rows = soup.select('table tbody tr')
    
    await ensure_db()
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    
    groups_added = 0
    themes_added = 0
    
    themes_to_insert = []
    
    for row in rows:
        tds = row.find_all('td')
        if len(tds) < 2:
            continue
        group_name = tds[0].get_text(strip=True)
        
        group_id = await conn.fetchval(
            "INSERT INTO lego_groups (name) VALUES ($1) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id", 
            group_name
        )
        groups_added += 1
        
        await conn.execute("DELETE FROM lego_themes WHERE group_id = $1", group_id)
        
        lis = tds[1].find_all('li')
        for li in lis:
            theme_name = li.get_text(strip=True)
            themes_to_insert.append((group_id, theme_name))
            
    if themes_to_insert:
        await conn.executemany(
            "INSERT INTO lego_themes (group_id, name) VALUES ($1, $2)",
            themes_to_insert
        )
        themes_added = len(themes_to_insert)
            
    await conn.close()
    await message.answer(f"База Lego успешно обновлена!\nОбработано групп: {groups_added}\nДобавлено тем: {themes_added}")

@dp.message(Command("lego"))
async def cmd_lego(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    group_query = message.text.replace("/lego", "", 1).strip()
    if not group_query:
        await message.answer("Укажите имя группы, например: /lego Spider man")
        return
        
    await ensure_db()
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    
    # Ищем группу 
    groups = await conn.fetch("SELECT id, name FROM lego_groups WHERE name ILIKE $1 LIMIT 1", f"%{group_query}%")
    if not groups:
        await conn.close()
        await message.answer(f"Группа '{group_query}' не найдена в базе.")
        return
        
    group_id = groups[0]['id']
    group_name = groups[0]['name']
    
    themes = await conn.fetch("SELECT name FROM lego_themes WHERE group_id = $1 ORDER BY name", group_id)
    await conn.close()
    
    if not themes:
        await message.answer(f"В группе '{group_name}' нет доступных тем (или они все пройдены).")
        return
        
    themes_list = "\n".join([f"- {t['name']}" for t in themes])
    prompt = f"Доступные темы для группы {group_name}:\n{themes_list}\n\nНапишите название темы, которую выбрали:"
    
    # Лимит Telegram - 4096 символов.
    if len(prompt) > 4000:
        prompt = prompt[:4000] + "...\n\nНапишите название темы, которую выбрали:"
        
    await message.answer(prompt, reply_markup=ForceReply(selective=True))

def is_theme_reply(message: types.Message) -> bool:
    if not message.reply_to_message or not message.reply_to_message.text:
        return False
    return "Доступные темы для группы" in message.reply_to_message.text

@dp.message(is_theme_reply)
async def process_theme_selection(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
        
    original_text = message.reply_to_message.text
    first_line = original_text.split('\n')[0]
    group_name = first_line.replace("Доступные темы для группы ", "").replace(":", "").strip()
    theme_choice = message.text.strip()
    
    await ensure_db()
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    
    group_id = await conn.fetchval("SELECT id FROM lego_groups WHERE name = $1", group_name)
    if not group_id:
        await conn.close()
        await message.answer("Ошибка: группа не найдена в базе.")
        return
        
    deleted_id = await conn.fetchval(
        "DELETE FROM lego_themes WHERE group_id = $1 AND name ILIKE $2 RETURNING id",
        group_id, f"%{theme_choice}%"
    )
    
    await conn.close()
    
    if deleted_id:
        await message.answer(f"✅ Тема '{theme_choice}' выбрана и удалена из группы '{group_name}'!")
    else:
        await message.answer(f"❌ Тема '{theme_choice}' не найдена в группе '{group_name}'. Убедитесь, что написали без ошибок.")

@dp.message()
async def process_payment(message: types.Message):
    if not message.text:
        return
        
    text = message.text.strip()
    
    if text.startswith('/'):
        return

    parts = text.split()
    if len(parts) < 4:
        await message.answer("Սխալ ձևաչափ:\nԽնդրում ենք օգտագործել հետևյալ ձևաչափը՝ Անուն Ազգանուն Գումար Վճարման_Եղանակ")
        return

    payment_method_raw = parts[-1].lower()
    payment_sum = parts[-2]
    name_english = " ".join(parts[:-2])
    
    name_russian = transliterate_name(name_english)
    payment_method = PAYMENT_METHODS.get(payment_method_raw, payment_method_raw)
    
    response = f"G.N | {name_russian} | {payment_sum} | {payment_method}"
    await message.answer(response)

    if GROUP_CHAT_ID:
        try:
            chat_id_int = int(GROUP_CHAT_ID)
            thread_id_int = int(TOPIC_THREAD_ID) if TOPIC_THREAD_ID and TOPIC_THREAD_ID.strip() != "None" else None
            await bot.send_message(
                chat_id=chat_id_int,
                text=response,
                message_thread_id=thread_id_int
            )
        except Exception as e:
            print(f"Failed to send to group: {e}")

@app.post("/api/webhook")
async def webhook(request: Request):
    print("Webhook endpoint triggered")
    if not bot:
        print("Error: BOT_TOKEN is not set")
        return {"error": "BOT_TOKEN is not set"}
        
    try:
        update_data = await request.json()
        print(f"Update received: {update_data.get('update_id')}")
        update = types.Update(**update_data)
        
        import asyncio
        print("Starting dp.feed_update")
        await asyncio.wait_for(dp.feed_update(bot, update), timeout=4.0)
        print("Finished dp.feed_update successfully")
    except asyncio.TimeoutError:
        print("CRITICAL ERROR: Timeout! The process hung for more than 4 seconds.")
        return {"error": "Timeout"}
    except Exception as e:
        print(f"CRITICAL ERROR: {repr(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
        
    return {"status": "ok"}
