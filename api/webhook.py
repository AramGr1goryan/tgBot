from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from transliterate import translit
import asyncpg
import os
import re

API_TOKEN = os.getenv("BOT_TOKEN")
POSTGRES_URL = os.getenv("POSTGRES_URL")
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

@dp.message(F.text.regexp(r'^(?i)/task(\d+)$'))
async def cmd_complete_task(message: types.Message):
    if not POSTGRES_URL:
        await message.answer("Բազան միացված չէ (POSTGRES_URL is missing):")
        return

    match = re.match(r'(?i)^/task(\d+)$', message.text)
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

@app.post("/api/webhook")
async def webhook(request: Request):
    if not bot:
        return {"error": "BOT_TOKEN is not set"}
        
    update_data = await request.json()
    update = types.Update(**update_data)
    
    await dp.feed_update(bot, update)
    return {"status": "ok"}
