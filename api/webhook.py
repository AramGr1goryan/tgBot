from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from transliterate import translit
import asyncpg
import os
import re
from io import BytesIO
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import asyncio
import zoneinfo
import httpx

API_TOKEN = os.getenv("BOT_TOKEN")
POSTGRES_URL = os.getenv("POSTGRES_URL")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
TOPIC_THREAD_ID = os.getenv("TOPIC_THREAD_ID")
ALFACRM_EMAIL = (os.getenv("ALFACRM_EMAIL") or "").strip()
ALFACRM_API_KEY = (os.getenv("ALFACRM_API_KEY") or "").strip()
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
PENDING_PAYMENTS = {}

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

def _parse_lessons(items, tz):
    now = datetime.now(tz)
    booked_slots = []
    for item in items:
        r_id = item.get("room_id")
        s_id = item.get("subject_id")
        t_id = item.get("lesson_type_id")
        
        # Types: Пробный [3], Пробные групп [9]
        if t_id not in [3, 9]:
            continue
            
        # Location Garegin Nzhdeh uses room 33 for Lego and room 34 for MakeBlock
        subject = None
        if s_id == 24 and r_id == 33:
            subject = "Lego"
        elif s_id == 23 and r_id == 34:
            subject = "MakeBlock"
            
        if not subject:
            continue
            
        details = item.get("details", [])
        participants = len(details)
        if participants == 0:
            continue
            
        date_str = item.get("date")
        time_from = item.get("time_from")
        
        # Parse exact lesson datetime
        lesson_dt = datetime.strptime(time_from, "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
        if lesson_dt <= now:
            continue
            
        weekday = lesson_dt.weekday()
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

async def get_alfacrm_customer_by_name(name: str):
    token = await get_alfacrm_token()
    if not token: return None
    
    headers = {
        "X-ALFACRM-TOKEN": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Փնտրում ենք անունով
    async with httpx.AsyncClient() as client:
        payload = {"name": name}
        try:
            response = await client.post(
                "https://robixlab.s20.online/v2api/1/customer/index",
                headers=headers,
                json=payload,
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                if items:
                    return items[0]
        except Exception as e:
            print(f"Error searching customer: {e}")
            
    return None

async def get_alfacrm_customer_by_id(customer_id: int):
    token = await get_alfacrm_token()
    if not token: return None
    
    headers = {
        "X-ALFACRM-TOKEN": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://robixlab.s20.online/v2api/1/customer/index",
                headers=headers,
                json={"id": customer_id},
                timeout=10.0
            )
            if response.status_code == 200:
                items = response.json().get("items", [])
                if items: return items[0]
        except Exception:
            pass
    return None

async def check_customer_rooms(customer_id: int) -> bool:
    token = await get_alfacrm_token()
    if not token: return False
    
    headers = {
        "X-ALFACRM-TOKEN": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        payload = {"customer_id": customer_id}
        try:
            response = await client.post(
                "https://robixlab.s20.online/v2api/1/lesson/index",
                headers=headers,
                json=payload,
                timeout=10.0
            )
            if response.status_code == 200:
                items = response.json().get("items", [])
                for lesson in items:
                    if lesson.get("room_id") in [33, 34]:
                        return True
        except Exception as e:
            print(f"Error checking rooms: {e}")
    return False

async def create_alfacrm_payment(customer_id: int, amount: int, method_raw: str, payer_name: str):
    token = await get_alfacrm_token()
    if not token: return False
    
    headers = {
        "X-ALFACRM-TOKEN": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Account Mapping
    method = method_raw.lower()
    if method == 'n':
        pay_account_id = 5 # Касса Шенгавит
    elif method == 'b.n':
        pay_account_id = 6 # Терминал Шенгавит
    elif method in ['c', 'с']:
        pay_account_id = 2 # На карту
    else:
        pay_account_id = 5
        
    # Item Mapping
    if amount == 2000:
        income_item_id = 3 # Пробный урок
    else:
        income_item_id = 1 # Курсы
        
    today = datetime.now(zoneinfo.ZoneInfo('Asia/Yerevan')).strftime("%d.%m.%Y")
    
    payload = {
        "customer_id": customer_id,
        "document_date": today,
        "pay_account_id": pay_account_id,
        "pay_item_id": income_item_id,
        "pay_type_id": 1,
        "branch_id": 1,
        "location_id": 5,
        "payer_name": payer_name,
        "income": amount
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://robixlab.s20.online/v2api/1/pay/create",
                headers=headers,
                json=payload,
                timeout=10.0
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error creating payment: {e}")
    return False

async def _fetch_status(client, headers, date_from, date_to, status_val):
    items = []
    page = 0
    while True:
        payload = {"date_from": date_from, "date_to": date_to, "page": page, "status": status_val, "per-page": 100}
        resp = await client.post(
            "https://robixlab.s20.online/v2api/1/lesson/index",
            headers=headers,
            json=payload
        )
        if resp.status_code != 200:
            break
        data = resp.json()
        batch = data.get("items", [])
        if not batch:
            break
        items.extend(batch)
        if len(batch) < 20 or page >= 15:
            break
        page += 1
    return items

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
    
    async with httpx.AsyncClient() as client:
        # Fetch only status=1 (Planned) to save time, as conducted (status=2) are in the past
        all_items = await _fetch_status(client, headers, date_from, date_to, 1)
        
    return _parse_lessons(all_items, tz)

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

@dp.message(Command("about"))
@dp.message(Command("about"))
async def cmd_about(message: types.Message):
    await message.answer(
        "🤖 **Ադմինիստրատորի Օգնական (Admin Helper)**\n\n"
        "Այս բոտը ստեղծված է RobixLab-ի մենեջերների, ադմինների և ուսուցիչների աշխատանքը հեշտացնելու համար:\n\n"
        "👑 **Մենեջերներ և Ադմիններ**\n"
        "• Վճարումների ավտոմատ գրանցում Alfa CRM-ում (կանխիկ, քարտ, տերմինալ):\n"
        "• Առաջադրանքների (Task) ստեղծում և կառավարում ինտերակտիվ կոճակներով:\n"
        "• Ամենօրյա ավտոմատ հիշեցումներ չկատարված առաջադրանքների մասին (ամեն օր 18:00):\n"
        "• Օգտատերերի բլոկավորում և կառավարում:\n\n"
        "📞 **Վաճառքի բաժին (Sales / Alfa CRM)**\n"
        "• Փորձնական դասերի գրանցումների դիտում ըստ օրերի:\n"
        "• Alfa CRM-ից աշակերտների քարտերի և հեռախոսահամարների ստացում:\n\n"
        "🎓 **Ուսուցիչների բաժին**\n"
        "• Lego խմբերի համար բաց թեմաների որոնում և ընտրություն:\n"        "• Անձնական դասացուցակի դիտում այսօր և վաղը (/myschedule):\n\n"
        "Ամբողջական հրամանների համար գրեք /help:\n\n" 
        "Բոտը ստեղծվել է միակ ու անկրկնելի, մի հրաշք, բայց միևնույն ժամանակ հասարակ մահկանացու՝ Արամ Գրիգորյանի կողմից։ Յանի իմ բոտն ա, ինչ ուզեմ՝ կգրեմ, դեմ չեք, չէ՞",
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📋 **Հրամանների ցանկ**\n\n"
        "👑 **Մենեջերներ և Ադմիններ**\n"
        "• **Վճարում**՝ գրեք տեքստով (օրինակ՝ `Aram Grigoryan 50000 N`)\n"
        "  (N-կանխիկ, b.n-տերմինալ, c-քարտ)\n"
        "/addtask [տեքստ] - Ստեղծել առաջադրանք\n"
        "/checktasks - Ցուցադրել անավարտ առաջադրանքները (ինտերակտիվ կոճակներով)\n"
        "/getusers - Բոլոր օգտատերերի ցանկ\n"
        "/ban [ID] - Բլոկավորել\n"
        "/unban [ID] - Ապաբլոկավորել\n\n"
        "📞 **Վաճառքի բաժին (Sales / Alfa CRM)**\n"
        "/prob - Այսօրվա փորձնական դասերը (ըստ աղյուսակի)\n"
        "/proball - Շաբաթվա փորձնական դասերը (ըստ աղյուսակի)\n"
        "/getprob - Այս շաբաթվա գրանցվածները (Անուն, Հեռախոս, Անկետա)\n"
        "/getweek - Գալիք շաբաթվա գրանցվածները\n"
        "/freeprob - Ազատ տեղեր փորձնական դասի համար\n\n"
        "🎓 **Ուսուցիչների բաժին**\n"
        "/lego [թեմա] - Գտնել բաց թեմաներ (օրինակ՝ /lego Spider man)\n"        "/myschedule - Տեսնել սեփական դասացուցակը այսօրվա և վաղվա համար",
        parse_mode="Markdown"
    )

import json

def get_mapping(filename):
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {item['id']: item['name'] for item in data}
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return {}

ROOMS_MAP = get_mapping('rooms.json')
SUBJECTS_MAP = get_mapping('subjects.json')

TEACHERS_MAP = {
    1472817960: {"id": 20, "name": "Արամ Գրիգորյան"},
    1071411870: {"id": 25, "name": "Նարե Ազարյան"},
    1037044744: {"id": 12, "name": "Լիա Ավետիսյան"}
}

async def check_uncompleted_lessons(bot: Bot, exclude_ids=None):
    if exclude_ids is None:
        exclude_ids = []
        
    token = await get_alfacrm_token()
    if not token:
        return {"status": "error", "message": "No CRM token"}
        
    tz = zoneinfo.ZoneInfo("Asia/Yerevan")
    today_str = datetime.now(tz).strftime("%Y-%m-%d")
    
    headers = {
        "X-ALFACRM-TOKEN": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    messages_sent = 0
    async with httpx.AsyncClient() as client:
        for tg_id, teacher_info in TEACHERS_MAP.items():
            if tg_id in exclude_ids:
                continue
                
            teacher_id = teacher_info["id"]
            try:
                response = await client.post(
                    "https://robixlab.s20.online/v2api/1/lesson/index",
                    headers=headers,
                    json={"teacher_id": teacher_id, "date_from": today_str, "date_to": today_str, "status": 1},
                    timeout=10.0
                )
                if response.status_code == 200:
                    items = response.json().get("items", [])
                    if items:
                        count = len(items)
                        text = (
                            f"🔔 **Ուշադրություն**\n\n"
                            f"Հարգելի {teacher_info['name']}, դուք ունեք **{count}** չնշված (պլանավորված) դաս այսօր ({today_str}):\n\n"
                            f"Խնդրում ենք մուտք գործել CRM և նշել դասերը որպես անցկացված:"
                        )
                        try:
                            await bot.send_message(tg_id, text, parse_mode="Markdown")
                            messages_sent += 1
                        except Exception as e:
                            print(f"Failed to send to {tg_id}: {e}")
            except Exception as e:
                print(f"Error fetching lessons for teacher {teacher_id}: {e}")
                
    return {"status": "ok", "reminders_sent": messages_sent}

@dp.message(Command("testteacher"))
async def cmd_testteacher(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🔄 Սկսում եմ չնշված դասերի ստուգումը...")
    result = await check_uncompleted_lessons(bot, exclude_ids=[1037044744])
    await message.answer(f"✅ Ստուգումն ավարտվեց:\nՈւղարկված նամակներ՝ {result.get('reminders_sent', 0)}")

@dp.message(Command("myschedule"))
async def cmd_myschedule(message: types.Message):
    user_id = message.from_user.id
    if user_id not in TEACHERS_MAP:
        await message.answer("❌ Դուք գրանցված չեք որպես ուսուցիչ համակարգում:")
        return
        
    teacher = TEACHERS_MAP[user_id]
    teacher_id = teacher["id"]
    
    token = await get_alfacrm_token()
    if not token:
        await message.answer("❌ CRM API Token error")
        return
        
    tz = zoneinfo.ZoneInfo("Asia/Yerevan")
    today = datetime.now(tz)
    tomorrow = today + timedelta(days=1)
    
    date_from = today.strftime("%Y-%m-%d")
    date_to = tomorrow.strftime("%Y-%m-%d")
    
    headers = {
        "X-ALFACRM-TOKEN": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://robixlab.s20.online/v2api/1/lesson/index",
                headers=headers,
                json={"teacher_id": teacher_id, "date_from": date_from, "date_to": date_to, "status": 1},
                timeout=10.0
            )
            if response.status_code == 200:
                items = response.json().get("items", [])
            else:
                await message.answer("❌ CRM API Request failed")
                return
        except Exception as e:
            await message.answer(f"❌ Սխալ: {e}")
            return
            
    if not items:
        await message.answer(f"📅 **{teacher['name']}**\n\nԱյսօր և վաղը դասեր չկան:", parse_mode="Markdown")
        return
        
    schedule_today = []
    schedule_tomorrow = []
    
    # Sort items by time_from
    items.sort(key=lambda x: x.get("time_from", ""))
    
    for item in items:
        date_str = item.get("date")
        time_from = item.get("time_from", "")[-8:-3]
        time_to = item.get("time_to", "")[-8:-3]
        room = ROOMS_MAP.get(item.get("room_id"), "Անհայտ")
        subject = SUBJECTS_MAP.get(item.get("subject_id"), "Անհայտ")
        
        lesson_text = f"🕒 {time_from} - {time_to} | 🏫 {room} | 📚 {subject}"
        
        if date_str == date_from:
            schedule_today.append(lesson_text)
        elif date_str == date_to:
            schedule_tomorrow.append(lesson_text)
            
    response_text = f"📅 **{teacher['name']} - Գրաֆիկ**\n\n"
    
    if schedule_today:
        response_text += "🔹 **Այսօր**\n" + "\n".join(schedule_today) + "\n\n"
    else:
        response_text += "🔹 **Այսօր:** Դասեր չկան\n\n"
        
    if schedule_tomorrow:
        response_text += "🔹 **Վաղը**\n" + "\n".join(schedule_tomorrow)
    else:
        response_text += "🔹 **Վաղը:** Դասեր չկան"
        
    await message.answer(response_text, parse_mode="Markdown")

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

async def fetch_probation_details():
    token = await get_alfacrm_token()
    if not token: return None
    
    tz = zoneinfo.ZoneInfo("Asia/Yerevan")
    now = datetime.now(tz)
    monday = now - timedelta(days=now.weekday())
    sunday = monday + timedelta(days=6)
    
    date_from = monday.strftime("%Y-%m-%d")
    date_to = sunday.strftime("%Y-%m-%d")
    
    headers = {"X-ALFACRM-TOKEN": token, "Content-Type": "application/json"}
    
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            _fetch_status(client, headers, date_from, date_to, 1),
            _fetch_status(client, headers, date_from, date_to, 2),
            _fetch_status(client, headers, date_from, date_to, 3)
        )
        
    all_items = results[0] + results[1] + results[2]
    
    target_lessons = []
    customer_ids = set()
    
    for item in all_items:
        r_id = item.get("room_id")
        s_id = item.get("subject_id")
        t_id = item.get("lesson_type_id")
        
        if t_id not in [3, 9]:
            continue
            
        subject = None
        if s_id == 24 and r_id == 33:
            subject = "Lego"
        elif s_id == 23 and r_id == 34:
            subject = "MakeBlock"
            
        if not subject:
            continue
            
        details = item.get("details", [])
        if not details:
            continue
            
        date_str = item.get("date")
        time_from = item.get("time_from")
        dt = datetime.strptime(time_from, "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
        weekday = dt.weekday()
        time_only = time_from.split(" ")[1][:5]
        
        if weekday == 4 and "13:00" <= time_only <= "16:00":
            time_only = "13:00-16:00"
            
        cust_list = []
        for det in details:
            cid = det.get("customer_id")
            if cid:
                customer_ids.add(cid)
                cust_list.append(cid)
                
        if cust_list:
            target_lessons.append({
                "weekday": weekday,
                "time": time_only,
                "subject": subject,
                "customers": cust_list
            })
            
    if not customer_ids:
        return []
        
    customers_map = {}
    async with httpx.AsyncClient() as client:
        payload_students = {"id": list(customer_ids), "per-page": max(200, len(customer_ids))}
        payload_leads = {"id": list(customer_ids), "is_study": 0, "per-page": max(200, len(customer_ids))}
        
        reqs = await asyncio.gather(
            client.post("https://robixlab.s20.online/v2api/1/customer/index", headers=headers, json=payload_students),
            client.post("https://robixlab.s20.online/v2api/1/customer/index", headers=headers, json=payload_leads)
        )
        
        for resp in reqs:
            if resp.status_code == 200:
                cdata = resp.json().get("items", [])
                for c in cdata:
                    cid = c.get("id")
                    name = c.get("name", "Անհայտ")
                    phones = c.get("phone", [])
                    phone = phones[0] if phones else "Չկա"
                    customers_map[cid] = {"name": name, "phone": phone}
                
    return {"lessons": target_lessons, "customers": customers_map}

@dp.message(Command("getprob"))
async def cmd_getprob(message: types.Message):
    
    await message.answer("🔄 Բեռնում եմ այս շաբաթվա գրանցվածները...")
    
    data = await fetch_probation_details()
    if data is None:
        await message.answer("❌ Սխալ՝ չհաջողվեց կապ հաստատել Alfa CRM-ի հետ:")
        return
        
    if not data or not data.get("lessons"):
        await message.answer("Այս շաբաթվա համար գրանցված փորձնական դասեր չկան:")
        return
        
    DAYS = ["Երկուշաբթի", "Երեքշաբթի", "Չորեքշաբթի", "Հինգշաբթի", "Ուրբաթ", "Շաբաթ", "Կիրակի"]
    
    schedule = {}
    for lesson in data["lessons"]:
        w = lesson["weekday"]
        t = lesson["time"]
        s = lesson["subject"]
        if w not in schedule: schedule[w] = {}
        if t not in schedule[w]: schedule[w][t] = {}
        if s not in schedule[w][t]: schedule[w][t][s] = []
        schedule[w][t][s].extend(lesson["customers"])
        
    text = "🟢 <b>Այս շաբաթվա գրանցված փորձնական դասերը</b>\n\n"
    for w in sorted(schedule.keys()):
        text += f"📅 <b>{DAYS[w]}</b>\n"
        for t in sorted(schedule[w].keys()):
            for s, c_list in schedule[w][t].items():
                text += f"🕒 {t} — {s}\n"
                for cid in c_list:
                    c = data["customers"].get(cid, {})
                    name = c.get("name", "Անհայտ")
                    if name.startswith("G.N | "):
                        name = name[6:]
                    # Escape HTML for name
                    name = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    phone = c.get("phone", "Չկա")
                    if phone != "Չկա":
                        phone_clean = "".join(filter(str.isdigit, phone))
                        if phone.startswith("+"): phone_clean = "+" + phone_clean
                        phone_link = f'<a href="tel:{phone_clean}">{phone}</a>'
                    else:
                        phone_link = phone
                        
                    card_link = f'<a href="https://robixlab.s20.online/company/1/customer/view?id={cid}">Անկետա</a>'
                    text += f"  👤 {name} - {card_link} - {phone_link}\n"
                text += "\n"
        text += "—\n"
        
    if text.endswith("—\n"): text = text[:-2]
    
    if len(text) > 4000:
        for x in range(0, len(text), 4000):
            await message.answer(text[x:x+4000], parse_mode="HTML", disable_web_page_preview=True)
    else:
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
@dp.message(Command("freeprob"))
async def cmd_freeprob(message: types.Message):
    
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
    
    tz = zoneinfo.ZoneInfo("Asia/Yerevan")
    now = datetime.now(tz)
    current_w = now.weekday()
    current_time = now.time()
    
    text = "🟢 **Ազատ տեղեր փորձնական դասերի համար (առաջիկա)**\n\n"
    has_any_slots = False
    
    for w in range(6):
        if w < current_w:
            continue
            
        day_name = DAYS[w]
        slots = STRUCTURED_SCHEDULE[w]
        
        day_text = f"🔹 {day_name}\n"
        has_slots = False
        
        for slot in slots:
            t = slot["time"]
            s = slot["subject"]
            cap = slot["capacity"]
            
            # For today, check if slot is in the past
            if w == current_w:
                try:
                    slot_t_str = t.split("-")[0] if "-" in t else t
                    slot_time = datetime.strptime(slot_t_str, "%H:%M").time()
                    if slot_time <= current_time:
                        continue
                except ValueError:
                    pass
            
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
                has_any_slots = True
                
        if has_slots:
            text += day_text + "—\n"
            
    if not has_any_slots:
        text += "Այս շաբաթ այլևս ազատ տեղեր չկան:\n"
        
    if text.endswith("—\n"):
        text = text[:-2]
        
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("addtask"))
async def cmd_addtask(message: types.Message):
        
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
        
    response = "📝 **Առաջադրանքների ցանկ:**\n\n"
    builder = InlineKeyboardBuilder()
    
    for task in tasks:
        t_id = task['id']
        t_desc = task['description']
        response += f"🔹 **Task{t_id}** - {t_desc}\n"
        builder.button(text=f"✅ Task{t_id}", callback_data=f"complete_{t_id}")
    builder.adjust(2)
        
    await message.answer(response, parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("complete_"))
async def callback_complete_task(callback: types.CallbackQuery):
    await ensure_db()
    task_id = int(callback.data.split("_")[1])
    
    task_desc = await delete_task(task_id)
    if not task_desc:
        await callback.answer("Այս առաջադրանքը արդեն կատարված է կամ ջնջված։", show_alert=True)
    else:
        await callback.answer(f"✅ Task{task_id} կատարված է։")
        user_info = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
        
        # Notify the admin (or group) that it was completed
        await bot.send_message(ADMIN_ID, f"Առաջադրանքը {user_info}-ի կողմից կատարվել է:\nTask{task_id} - {task_desc}")
                
    tasks = await get_tasks()
    if not tasks:
        await callback.message.edit_text("🎉 Բոլոր առաջադրանքները կատարված են։", parse_mode="Markdown")
        return
        
    response = "📝 **Առաջադրանքների ցանկ:**\n\n"
    builder = InlineKeyboardBuilder()
    
    for task in tasks:
        t_id = task['id']
        t_desc = task['description']
        response += f"🔹 **Task{t_id}** - {t_desc}\n"
        builder.button(text=f"✅ Task{t_id}", callback_data=f"complete_{t_id}")
    builder.adjust(2)
        
    await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=builder.as_markup())

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

    ERROR_INSTRUCTION = (
        "❌ **Սխալ ձևաչափ**\n\n"
        "Վճարումը գրանցելու համար խնդրում ենք գրել ճիշտ հերթականությամբ՝\n"
        "👉 `Անուն Ազգանուն Գումար Եղանակ`\n\n"
        "Օրինակ՝ `Aram Grigoryan 50000 N`\n\n"
        "💳 **Հասանելի վճարման եղանակներ՝**\n"
        "• `n` — Կանխիկ (Наличные)\n"
        "• `b.n` — Տերմինալով (Безналичные)\n"
        "• `c` — Քարտով փոխանցում (Карта)\n\n"
        "⚠️ Ուշադրություն դարձրեք, որ գումարը պետք է լինի միայն թվերով, իսկ եղանակը՝ նշված տարբերակներից մեկը։"
    )

    # URL Handle
    if text.startswith('http') and 'customer/view?id=' in text:
        if message.from_user.id in PENDING_PAYMENTS:
            customer_id_str = text.split('id=')[-1].split('&')[0]
            if not customer_id_str.isdigit():
                await message.answer("❌ Սխալ հղում:")
                return
            customer_id = int(customer_id_str)
            pending = PENDING_PAYMENTS.pop(message.from_user.id)
            
            await message.answer("🔄 Կապվում եմ Alfa CRM-ի հետ...")
            customer = await get_alfacrm_customer_by_id(customer_id)
            if not customer:
                await message.answer("❌ Աշակերտը չգտնվեց նշված հղումով:")
                return
                
            payer_name = customer.get("legal_name") or customer.get("name", "Անհայտ")
            success = await create_alfacrm_payment(customer_id, pending['amount'], pending['method_raw'], payer_name)
            
            if success:
                await message.answer(f"✅ Վճարումը հաջողությամբ գրանցվեց Alfa CRM-ում ({customer.get('name')}):")
                if GROUP_CHAT_ID:
                    try:
                        chat_id_int = int(GROUP_CHAT_ID)
                        thread_id_int = int(TOPIC_THREAD_ID) if TOPIC_THREAD_ID and TOPIC_THREAD_ID.strip() != "None" else None
                        await bot.send_message(
                            chat_id_int, pending['response_text'], message_thread_id=thread_id_int
                        )
                    except Exception as e:
                        print(f"Failed to send to group: {e}")
            else:
                await message.answer("❌ Սխալ տեղի ունեցավ CRM-ում վճարումը գրանցելիս:")
        else:
            await message.answer("❌ Դուք չունեք սպասվող վճարում:")
        return

    parts = text.split()
    if len(parts) < 3:
        await message.answer(ERROR_INSTRUCTION, parse_mode="Markdown")
        return

    payment_method_raw = parts[-1].lower()
    payment_sum = parts[-2]
    clean_sum = payment_sum.replace('.', '').replace(',', '')
    
    if payment_method_raw not in PAYMENT_METHODS or not clean_sum.isdigit():
        await message.answer(ERROR_INSTRUCTION, parse_mode="Markdown")
        return

    amount_int = int(clean_sum)
    name_english = " ".join(parts[:-2])
    name_russian = transliterate_name(name_english)
    payment_method = PAYMENT_METHODS.get(payment_method_raw, payment_method_raw)
    
    response_text = f"Платеж обработал(а): {executor_name}\nG.N | {name_russian} | {payment_sum} | {payment_method}"
    
    processing_msg = await message.answer("🔄 Փնտրում եմ աշակերտին CRM-ում...")
    
    customer = await get_alfacrm_customer_by_name(name_russian)
    
    if not customer:
        await processing_msg.edit_text("❌ Աշակերտը չգտնվեց Alfa CRM-ում: Վճարումը հաստատելու համար խնդրում ենք ուղարկել նրա CRM անկետայի հղումը:")
        PENDING_PAYMENTS[message.from_user.id] = {
            'amount': amount_int,
            'method_raw': payment_method_raw,
            'response_text': response_text
        }
        return
        
    customer_name = customer.get("name", "")
    customer_id = customer.get("id")
    
    is_gn = False
    if customer_name.startswith("G.N"):
        is_gn = True
    else:
        is_gn = await check_customer_rooms(customer_id)
        
    if not is_gn:
        await processing_msg.edit_text(f"❌ Գտնվել է «{customer_name}» աշակերտը, բայց նա Գարեգին Նժդեհ մասնաճյուղից չէ: Վճարումը հաստատելու համար ուղարկեք նրա CRM անկետայի հղումը:")
        PENDING_PAYMENTS[message.from_user.id] = {
            'amount': amount_int,
            'method_raw': payment_method_raw,
            'response_text': response_text
        }
        return
        
    payer_name = customer.get("legal_name") or customer_name
    success = await create_alfacrm_payment(customer_id, amount_int, payment_method_raw, payer_name)
    
    if success:
        await processing_msg.edit_text(f"✅ Վճարումը հաջողությամբ գրանցվեց Alfa CRM-ում ({customer_name}):\n\n{response_text}")
        if GROUP_CHAT_ID:
            try:
                chat_id_int = int(GROUP_CHAT_ID)
                thread_id_int = int(TOPIC_THREAD_ID) if TOPIC_THREAD_ID and TOPIC_THREAD_ID.strip() != "None" else None
                await bot.send_message(
                    chat_id_int, response_text, message_thread_id=thread_id_int
                )
            except Exception as e:
                print(f"Failed to send to group: {e}")
    else:
        await processing_msg.edit_text(f"❌ Սխալ տեղի ունեցավ CRM-ում վճարումը գրանցելիս: Ստուգեք Alfa CRM-ը:")
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
        await asyncio.wait_for(dp.feed_update(bot, update), timeout=8.0)
        print("Finished dp.feed_update successfully")
    except asyncio.TimeoutError:
        print("CRITICAL ERROR: Timeout! The process hung for more than 8 seconds.")
        return {"error": "Timeout"}
    except Exception as e:
        print(f"CRITICAL ERROR: {repr(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
        
    return {"status": "ok"}

@app.get("/api/cron/teachers")
async def cron_teachers():
    if not bot:
        return {"status": "error", "message": "Bot not initialized"}
    result = await check_uncompleted_lessons(bot)
    return result

@app.get("/api/cron/tasks")
async def cron_tasks():
    await ensure_db()
    tasks = await get_tasks()
    if not tasks:
        return {"status": "ok", "message": "No tasks"}
        
    if GROUP_CHAT_ID:
        try:
            chat_id_int = int(GROUP_CHAT_ID)
            thread_id_int = int(TOPIC_THREAD_ID) if TOPIC_THREAD_ID and TOPIC_THREAD_ID.strip() != "None" else None
            
            response = "⚠️ **Ուշադրություն! Անավարտ առաջադրանքներ**\n\n"
            for task in tasks:
                response += f"🔹 **Task{task['id']}** - {task['description']}\n"
                
            await bot.send_message(
                chat_id_int, 
                response,
                message_thread_id=thread_id_int,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Failed to send cron to group: {e}")
            
    return {"status": "ok", "count": len(tasks)}
