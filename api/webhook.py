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
from datetime import datetime, timedelta
import zoneinfo
import httpx

API_TOKEN = os.getenv("BOT_TOKEN")
POSTGRES_URL = os.getenv("POSTGRES_URL")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
TOPIC_THREAD_ID = os.getenv("TOPIC_THREAD_ID")
ALFACRM_EMAIL = os.getenv("ALFACRM_EMAIL", "aramgrigoryan2k4@gmail.com")
ALFACRM_API_KEY = os.getenv("ALFACRM_API_KEY", "70cc373b-bed2-11f0-bfab-3cecefbdd1ae")
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
BANNED_USERS = set()
EXECUTORS = {}
KNOWN_USERS = set()

PROB_SCHEDULE = {
    0: ("Երկուշաբթի", "• 15:00 — Lego (6 աշակերտ) կամ Makeblock (3 աշակերտ)\n• 17:00 — Lego (2 աշակերտ)\n• 18:30 — Lego (3 աշակերտ)"),
    1: ("Երեքշաբթի", "• 15:00 — Lego (6 աշակերտ) կամ Makeblock (3 աշակերտ)\n• 16:00 — Lego (6 աշակերտ) կամ Makeblock (3 աշակերտ)\n• 18:00 — Lego (1 աշակերտ)"),
    2: ("Չորեքշաբթի", "• 15:00 — Lego կամ Makeblock (1 աշակերտ)\n• 17:30 — Lego (3 աշակերտ)\n• 18:30 — Lego (3 աշակերտ)"),
    3: ("Հինգշաբթի", "• 14:00 — Lego (5 աշակերտ, ռուսերեն)\n• 15:00 — Lego կամ Makeblock (3 աշակերտ)\n• 17:00 — Lego (3 աշակերտ)"),
    4: ("Ուրբաթ", "• 13:00 - 16:00 — Lego (6 աշակերտ) և Makeblock (3 աշակերտ)\n• 18:30 — Lego (6 աշակերտ) և Makeblock (3 աշակերտ)"),
    5: ("Շաբաթ", "• 17:30 — Lego (6 աշակերտ)\n• 17:30 — Makeblock (3 աշակերտ)"),
    6: ("Կիրակի", "Այսօր փորձնական դասեր չկան։")
}

STRUCTURED_SCHEDULE = {
    0: [
        {"time": "15:00", "subject": "Lego", "capacity": 6},
        {"time": "15:00", "subject": "MakeBlock", "capacity": 3},
        {"time": "17:00", "subject": "Lego", "capacity": 2},
        {"time": "18:30", "subject": "Lego", "capacity": 3},
    ],
    1: [
        {"time": "15:00", "subject": "Lego", "capacity": 6},
        {"time": "15:00", "subject": "MakeBlock", "capacity": 3},
        {"time": "16:00", "subject": "Lego", "capacity": 6},
        {"time": "16:00", "subject": "MakeBlock", "capacity": 3},
        {"time": "18:00", "subject": "Lego", "capacity": 1},
    ],
    2: [
        {"time": "15:00", "subject": "Lego", "capacity": 1, "shared_capacity": True},
        {"time": "15:00", "subject": "MakeBlock", "capacity": 1, "shared_capacity": True},
        {"time": "17:30", "subject": "Lego", "capacity": 3},
        {"time": "18:30", "subject": "Lego", "capacity": 3},
    ],
    3: [
        {"time": "14:00", "subject": "Lego", "capacity": 5},
        {"time": "15:00", "subject": "Lego", "capacity": 3, "shared_capacity": True},
        {"time": "15:00", "subject": "MakeBlock", "capacity": 3, "shared_capacity": True},
        {"time": "17:00", "subject": "Lego", "capacity": 3},
    ],
    4: [
        {"time": "13:00-16:00", "subject": "Lego", "capacity": 6},
        {"time": "13:00-16:00", "subject": "MakeBlock", "capacity": 3},
        {"time": "18:30", "subject": "Lego", "capacity": 6},
        {"time": "18:30", "subject": "MakeBlock", "capacity": 3},
    ],
    5: [
        {"time": "17:30", "subject": "Lego", "capacity": 6},
        {"time": "17:30", "subject": "MakeBlock", "capacity": 3},
    ],
    6: []
}

_alfacrm_token = None
_alfacrm_token_expires = 0

async def get_alfacrm_token():
    global _alfacrm_token, _alfacrm_token_expires
    now = datetime.now().timestamp()
    if _alfacrm_token and now < _alfacrm_token_expires:
        return _alfacrm_token
        
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://robixlab.s20.online/v2api/auth/login",
            json={"email": ALFACRM_EMAIL, "api_key": ALFACRM_API_KEY}
        )
        if resp.status_code != 200:
            print(f"ALFACRM AUTH ERROR: {resp.status_code} {resp.text}")
            return None
            
        data = resp.json()
        _alfacrm_token = data.get("token")
        _alfacrm_token_expires = now + 7200 # 2 hours
        return _alfacrm_token

async def fetch_probation_lessons():
    token = await get_alfacrm_token()
    if not token:
        return None
        
    tz = zoneinfo.ZoneInfo("Asia/Yerevan")
    now = datetime.now(tz)
    
    monday = now - timedelta(days=now.weekday())
    sunday = monday + timedelta(days=6)
    
    date_from = monday.strftime("%Y-%m-%d")
    date_to = sunday.strftime("%Y-%m-%d")
    
    headers = {"X-ALFACRM-TOKEN": token, "Content-Type": "application/json"}
    payload = {"date_from": date_from, "date_to": date_to}
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://robixlab.s20.online/v2api/1/lesson/index",
            headers=headers,
            json=payload
        )
        data = resp.json()
        
    items = data.get("items", [])
    booked_slots = []
    
    for item in items:
        if item.get("status") == 3: # Отменен
            continue
            
        r_id = item.get("room_id")
        s_id = item.get("subject_id")
        t_id = item.get("lesson_type_id")
        
        if t_id not in [3, 8, 9]:
            continue
            
        subject = None
        if s_id == 24 and r_id in [30, 33]:
            subject = "Lego"
        elif s_id == 23 and r_id in [31, 34]:
            subject = "MakeBlock"
            
        if not subject:
            continue
            
        details = item.get("details", [])
        participants = len(details)
        if participants == 0:
            continue
            
        date_str = item.get("date")
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=tz)
        weekday = dt.weekday()
        
        time_from = item.get("time_from")
        time_only = time_from.split(" ")[1][:5]
        
        if weekday == 4 and "13:00" <= time_only <= "16:00":
            time_only = "13:00-16:00"
            
        booked_slots.append({
            "weekday": weekday,
            "time": time_only,
            "subject": subject,
            "participants": participants
        })
        
    return booked_slots

async def ensure_db():
    global db_initialized, BANNED_USERS
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
    
    # Таблица для заблокированных пользователей
    await conn.execute('''CREATE TABLE IF NOT EXISTS banned_users
                 (user_id BIGINT PRIMARY KEY)''')
                 
    # Таблица для исполнителей (кассиров)
    await conn.execute('''CREATE TABLE IF NOT EXISTS executors
                 (user_id BIGINT PRIMARY KEY, name TEXT)''')
                 
    # Таблица для абсолютно всех пользователей, кто хоть раз написал боту
    await conn.execute('''CREATE TABLE IF NOT EXISTS all_users
                 (user_id BIGINT PRIMARY KEY, username TEXT, full_name TEXT)''')
                 
    # Загружаем забаненных пользователей в память при холодном старте
    rows = await conn.fetch("SELECT user_id FROM banned_users")
    BANNED_USERS = {row['user_id'] for row in rows}
    
    # Загружаем имена исполнителей в память
    exec_rows = await conn.fetch("SELECT user_id, name FROM executors")
    for row in exec_rows:
        EXECUTORS[row['user_id']] = row['name']
        
    # Загружаем всех пользователей, чтобы не делать лишних инсертов
    known_rows = await conn.fetch("SELECT user_id FROM all_users")
    for row in known_rows:
        KNOWN_USERS.add(row['user_id'])
    
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
    await message.answer(
        "Ողջույն: Որպեսզի ես կարողանամ ուղարկել վճարումները խմբին, ինձ անհրաժեշտ է իմանալ ձեր անունը:\n\n"
        "Գրեք ձեր անունը ռուսերենով (օրինակ՝ Рипсиме):",
        reply_markup=ForceReply(selective=True)
    )

def is_name_reply(message: types.Message) -> bool:
    if not message.reply_to_message or not message.reply_to_message.text:
        return False
    return "Գրեք ձեր անունը ռուսերենով" in message.reply_to_message.text

@dp.message(is_name_reply)
async def process_name_registration(message: types.Message):
    name = message.text.strip()
    
    # Проверка на то, что имя написано русскими буквами
    if not re.match(r'^[А-Яа-яЁё\s]+$', name):
        await message.answer(
            "Խնդրում ենք գրել միայն ռուսերեն տառերով (օրինակ՝ Рипсиме):",
            reply_markup=ForceReply(selective=True)
        )
        return
        
    await ensure_db()
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    await conn.execute(
        "INSERT INTO executors (user_id, name) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name",
        message.from_user.id, name
    )
    await conn.close()
    
    EXECUTORS[message.from_user.id] = name
    await message.answer(
        f"✅ Ձեր անունը պահպանված է որպես '{name}':\n\n"
        "Այժմ կարող եք ուղարկել հաղորդագրություններ վճարումների համար հետևյալ ձևաչափով՝\n"
        "Անուն Ազգանուն Գումար Վճարման_Եղանակ"
    )

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
        "Վճարումներ՝\n"
        "Ձևաչափ՝ Անուն Ազգանուն Գումար Եղանակ\n"
        "Օրինակ՝ Aram Grigoryan 50000 N\n\n"
        "Հասանելի վճարման եղանակներ՝\n"
        "N — Կանխիկ\n"
        "b.n — Տերմինալով\n"
        "c — Քարտով\n\n"
        "Առաջադրանքների կառավարում՝\n"
        "/addtask [տեքստ] - Ավելացնել առաջադրանք\n"
        "/checktasks - Տեսնել առաջադրանքները\n"
        "/task[համար] - Նշել որպես կատարված (օրինակ՝ /task1)\n\n"
        "Փորձնական դասեր (G.N ՃԻՇՏ մասնաճյուղ)՝\n"
        "/prob - Տեսնել այսօրվա հասանելի ժամերը\n"
        "/proball - Տեսնել բոլոր օրերի հասանելի ժամերը\n"
        "/getweek - Տեսնել այս շաբաթվա գրանցված դասերը (CRM)\n"
        "/freeprob - Հաշվել ազատ տեղերը (CRM)\n\n"
        "Lego թեմաներ՝\n"
        "/lego [խումբ] - Ընտրել թեմա (օրինակ՝ /lego Spider man)"
    )

@dp.message(Command("prob"))
async def cmd_prob(message: types.Message):
    tz = zoneinfo.ZoneInfo("Asia/Yerevan")
    today_weekday = datetime.now(tz).weekday()
    
    day_name, schedule = PROB_SCHEDULE[today_weekday]
    
    text = (
        "G.N (ՃԻՇՏ մասնաճյուղ)\n"
        "——————————————————————————\n"
        f"🔹 {day_name}\n"
        f"{schedule}\n"
        "——————————————————————————"
    )
    await message.answer(text)

@dp.message(Command("proball"))
async def cmd_proball(message: types.Message):
    text = "G.N (ՃԻՇՏ մասնաճյուղ)\n——————————————————————————\n"
    for i in range(6): # Пн-Сб
        day_name, schedule = PROB_SCHEDULE[i]
        text += f"🔹 {day_name}\n{schedule}\n——————————————————————————\n"
        
    await message.answer(text)

@dp.message(Command("getweek"))
async def cmd_getweek(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    await message.answer("🔄 Կապ եմ հաստատում Alfa CRM-ի հետ...")
    booked_slots = await fetch_probation_lessons()
    
    if booked_slots is None:
        await message.answer("❌ Սխալ՝ չհաջողվեց կապ հաստատել Alfa CRM-ի հետ: Ստուգեք API բանալիները (ALFACRM_API_KEY) և համոզվեք, որ CRM-ում անջատված են IP սահմանափակումները:")
        return
        
    if not booked_slots:
        await message.answer("Այս շաբաթվա համար գրանցված փորձնական դասեր չկան:")
        return
        
    DAYS = ["Երկուշաբթի", "Երեքշաբթի", "Չորեքշաբթի", "Հինգշաբթի", "Ուրբաթ", "Շաբաթ", "Կիրակի"]
    
    grouped = {}
    for slot in booked_slots:
        w = slot["weekday"]
        t = slot["time"]
        s = slot["subject"]
        p = slot["participants"]
        
        if w not in grouped: grouped[w] = {}
        if t not in grouped[w]: grouped[w][t] = {}
        if s not in grouped[w][t]: grouped[w][t][s] = 0
        grouped[w][t][s] += p
        
    text = "🗓 **Գրանցված փորձնական դասեր (Այս շաբաթ)**\n\n"
    for w in sorted(grouped.keys()):
        text += f"🔹 {DAYS[w]}\n"
        for t in sorted(grouped[w].keys()):
            for s, p in grouped[w][t].items():
                text += f"  • {t} — {s} ({p} աշակերտ)\n"
        text += "—\n"
        
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("freeprob"))
async def cmd_freeprob(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    await message.answer("🔄 Հաշվարկում եմ ազատ տեղերը...")
    booked_slots = await fetch_probation_lessons()
    
    if booked_slots is None:
        await message.answer("❌ Սխալ՝ չհաջողվեց կապ հաստատել Alfa CRM-ի հետ: Ստուգեք API բանալիները (ALFACRM_API_KEY) և համոզվեք, որ CRM-ում անջատված են IP սահմանափակումները:")
        return
        
    booked = {}
    for slot in booked_slots:
        w = slot["weekday"]
        t = slot["time"]
        s = slot["subject"]
        p = slot["participants"]
        key = f"{w}_{t}_{s}"
        booked[key] = booked.get(key, 0) + p
        
    DAYS = ["Երկուշաբթի", "Երեքշաբթի", "Չորեքշաբթի", "Հինգշաբթի", "Ուրբաթ", "Շաբաթ", "Կիրակի"]
    
    text = "🟢 **Ազատ տեղեր փորձնական դասերի համար**\n\n"
    for w in range(6):
        day_name = DAYS[w]
        slots = STRUCTURED_SCHEDULE[w]
        
        day_text = f"🔹 {day_name}\n"
        has_slots = False
        
        for slot in slots:
            t = slot["time"]
            s = slot["subject"]
            cap = slot["capacity"]
            
            shared = slot.get("shared_capacity", False)
            if shared:
                b_lego = booked.get(f"{w}_{t}_Lego", 0)
                b_makeblock = booked.get(f"{w}_{t}_MakeBlock", 0)
                available = cap - b_lego - b_makeblock
            else:
                b = booked.get(f"{w}_{t}_{s}", 0)
                available = cap - b
                
            if available > 0:
                day_text += f"  • {t} — {s} (Ազատ՝ {available})\n"
                has_slots = True
                
        if has_slots:
            text += day_text + "—\n"
            
    if text.endswith("—\n"):
        text = text[:-2]
        
    await message.answer(text, parse_mode="Markdown")

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

@dp.message(Command("task"))
async def cmd_task_hint(message: types.Message):
    await message.answer("Խնդրում ենք նշել առաջադրանքի համարը, օրինակ՝ /task1")

@dp.message(Command("ban"))
async def cmd_ban(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Նշեք օգտատիրոջ ID-ն: Օրինակ՝ /ban 123456789")
        return
        
    target_id = int(parts[1])
    if target_id == ADMIN_ID:
        await message.answer("Դուք չեք կարող բլոկավորել ինքներդ ձեզ:")
        return
        
    await ensure_db()
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    await conn.execute("INSERT INTO banned_users (user_id) VALUES ($1) ON CONFLICT DO NOTHING", target_id)
    await conn.close()
    
    BANNED_USERS.add(target_id)
    await message.answer(f"✅ Օգտատեր {target_id}-ը բլոկավորված է և չի կարող օգտվել բոտից:")

@dp.message(Command("unban"))
async def cmd_unban(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Նշեք օգտատիրոջ ID-ն: Օրինակ՝ /unban 123456789")
        return
        
    target_id = int(parts[1])
    
    await ensure_db()
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    await conn.execute("DELETE FROM banned_users WHERE user_id = $1", target_id)
    await conn.close()
    
    if target_id in BANNED_USERS:
        BANNED_USERS.remove(target_id)
    await message.answer(f"✅ Օգտատեր {target_id}-ի բլոկավորումը հանված է:")

@dp.message(Command("getusers"))
async def cmd_getusers(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
        
    await ensure_db()
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    rows = await conn.fetch("SELECT user_id, username, full_name FROM all_users ORDER BY full_name")
    await conn.close()
    
    if not rows:
        await message.answer("Ակտիվ օգտատերեր չկան (ոչ ոք դեռ չի գրել բոտին):")
        return
        
    response = "Բոլոր օգտատերերը (Անուն - ID)՝\n\n"
    for row in rows:
        user_display = row['full_name']
        if row['username']:
            user_display += f" (@{row['username']})"
        response += f"{user_display} - {row['user_id']}\n"
        
    if len(response) > 4000:
        response = response[:4000] + "...\n[Ցանկը շատ երկար է]"
        
    await message.answer(response)

# Загрузка HTML файла с темами Lego
@dp.message(F.document)
async def process_html_upload(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.document.file_name.endswith('.html'):
        return
        
    await message.answer("Բեռնում և մշակում եմ Lego-ի HTML ֆայլը...")
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
    await message.answer(f"Lego-ի բազան հաջողությամբ թարմացվել է:\nՄշակված խմբեր՝ {groups_added}\nԱվելացված թեմաներ՝ {themes_added}")

@dp.message(Command("lego"))
async def cmd_lego(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    group_query = message.text.replace("/lego", "", 1).strip()
    if not group_query:
        await message.answer("Նշեք խմբի անունը, օրինակ՝ /lego Spider man")
        return
        
    await ensure_db()
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    
    # Ищем группу 
    groups = await conn.fetch("SELECT id, name FROM lego_groups WHERE name ILIKE $1 LIMIT 1", f"%{group_query}%")
    if not groups:
        await conn.close()
        await message.answer(f"«{group_query}» խումբը չի գտնվել բազայում:")
        return
        
    group_id = groups[0]['id']
    group_name = groups[0]['name']
    
    themes = await conn.fetch("SELECT name FROM lego_themes WHERE group_id = $1 ORDER BY name", group_id)
    await conn.close()
    
    if not themes:
        await message.answer(f"«{group_name}» խմբում հասանելի թեմաներ չկան (կամ բոլորն արդեն անցել են):")
        return
        
    themes_list = "\n".join([f"- {t['name']}" for t in themes])
    prompt = f"Հասանելի թեմաներ «{group_name}» խմբի համար:\n{themes_list}\n\nԳրեք այն թեմայի անվանումը, որն ընտրել եք:"
    
    # Лимит Telegram - 4096 символов.
    if len(prompt) > 4000:
        prompt = prompt[:4000] + "...\n\nԳրեք այն թեմայի անվանումը, որն ընտրել եք:"
        
    await message.answer(prompt, reply_markup=ForceReply(selective=True))

def is_theme_reply(message: types.Message) -> bool:
    if not message.reply_to_message or not message.reply_to_message.text:
        return False
    return "Հասանելի թեմաներ «" in message.reply_to_message.text

@dp.message(is_theme_reply)
async def process_theme_selection(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
        
    original_text = message.reply_to_message.text
    first_line = original_text.split('\n')[0]
    
    # Извлекаем имя группы из строки "Հասանելի թեմաներ «{group_name}» խմբի համար:"
    match_group = re.search(r'«(.*?)»', first_line)
    if not match_group:
        return
    group_name = match_group.group(1).strip()
    
    theme_choice = message.text.strip()
    
    await ensure_db()
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    
    group_id = await conn.fetchval("SELECT id FROM lego_groups WHERE name = $1", group_name)
    if not group_id:
        await conn.close()
        await message.answer("Սխալ․ խումբը բազայում չի գտնվել։")
        return
        
    deleted_id = await conn.fetchval(
        "DELETE FROM lego_themes WHERE group_id = $1 AND name ILIKE $2 RETURNING id",
        group_id, f"%{theme_choice}%"
    )
    
    await conn.close()
    
    if deleted_id:
        await message.answer(f"✅ «{theme_choice}» թեման ընտրված և հեռացված է «{group_name}» խմբից:")
    else:
        await message.answer(f"❌ «{theme_choice}» թեման չի գտնվել «{group_name}» խմբում։ Համոզվեք, որ այն ճիշտ եք գրել։")

@dp.message()
async def process_payment(message: types.Message):
    if not message.text:
        return
        
    text = message.text.strip()
    
    if text.startswith('/'):
        return

    # Проверка, зарегистрировал ли пользователь свое имя
    if message.from_user.id not in EXECUTORS:
        await message.answer("Խնդրում ենք նախ գրանցել ձեր անունը՝ սեղմելով /start հրամանը:")
        return
        
    executor_name = EXECUTORS[message.from_user.id]

    parts = text.split()
    if len(parts) < 4:
        await message.answer("Սխալ ձևաչափ:\nԽնդրում ենք օգտագործել հետևյալ ձևաչափը՝ Անուն Ազգանուն Գումար Վճարման_Եղանակ")
        return

    payment_method_raw = parts[-1].lower()
    payment_sum = parts[-2]
    name_english = " ".join(parts[:-2])
    
    name_russian = transliterate_name(name_english)
    payment_method = PAYMENT_METHODS.get(payment_method_raw, payment_method_raw)
    
    response = f"Платеж обработал(а): {executor_name}\nG.N | {name_russian} | {payment_sum} | {payment_method}"
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
        
        # Инициализируем базу данных и загружаем кэш
        await ensure_db()
        
        # Проверяем пользователя и сохраняем его, если он новый
        user_id = None
        user_obj = None
        if update.message and update.message.from_user:
            user_id = update.message.from_user.id
            user_obj = update.message.from_user
        elif update.callback_query and update.callback_query.from_user:
            user_id = update.callback_query.from_user.id
            user_obj = update.callback_query.from_user
            
        if user_id:
            if user_id in BANNED_USERS:
                print(f"Ignored update from banned user {user_id}")
                return {"status": "ok"}
                
            if user_id not in KNOWN_USERS:
                username = user_obj.username or ""
                full_name = user_obj.full_name or ""
                
                conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
                await conn.execute(
                    "INSERT INTO all_users (user_id, username, full_name) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                    user_id, username, full_name
                )
                await conn.close()
                KNOWN_USERS.add(user_id)
        
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
