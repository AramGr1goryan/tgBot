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
from api.sheets import append_payment_to_sheet
from api.locations import LOCATIONS, get_location, resolve_alias, DEFAULT_LOCATION
from api.i18n import t


API_TOKEN = os.getenv("BOT_TOKEN")
POSTGRES_URL = os.getenv("POSTGRES_URL")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
TOPIC_THREAD_ID = os.getenv("TOPIC_THREAD_ID")
ALFACRM_EMAIL = (os.getenv("ALFACRM_EMAIL") or "").strip()
ALFACRM_API_KEY = (os.getenv("ALFACRM_API_KEY") or "").strip()
ADMIN_ID = 1472817960
TASK_NOTIFY_USERS = [1472817960, 6062763343, 5636022981]

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
USER_SETTINGS: dict = {}  # user_id → {"location": "GN", "language": "hy"}

PROB_SCHEDULE = {
    0: ("Երկուշաբթի", "• 15:00 — Lego (6 աշակերտ) կամ Makeblock (3 աշակերտ)\n• 17:00 — Lego (2 աշակերտ)\n• 18:30 — Lego (3 աշակերտ)"),
    1: ("Երեքշաբթի", "• 15:00 — Lego (6 աշակերտ) կամ Makeblock (3 աշակերտ)\n• 16:00 — Lego (6 աշակերտ) կամ Makeblock (3 աշակերտ)\n• 18:00 — Lego (1 աշակերտ)"),
    2: ("Չորեքշաբթի", "• 15:00 — Lego կամ Makeblock (1 աշակերտ)\n• 17:30 — Lego (3 աշակերտ)\n• 18:30 — Lego (3 աշակերտ)"),
    3: ("Հինգշաբթի", "• 14:00 — Lego (5 աշակերտ, ռուսերեն)\n• 15:00 — Lego կամ Makeblock (3 աշակերտ)\n• 17:00 — Lego (3 աշակերտ)"),
    4: ("Ուրբաթ", "• 13:00 - 16:00 — Lego (6 աշակերտ) և Makeblock (3 աշակերտ)\n• 18:30 — Lego (6 աշակերտ) և Makeblock (3 աշակերտ)"),
    5: ("Շաբաթ", "• 17:30— Lego (6 աշակերտ)\n• 17:30 — Makeblock (3 աշակերտ)"),
    6: ("Կիրակի", "Այսօր փորձնական դասեր չկան։")
}

# Маппинг расписания пробных уроков по локации
PROB_SCHEDULES = {
    "GN": PROB_SCHEDULE,
    "K":  None,  # Расписание Комитас: добавить данные
    "S":  None,  # Расписание Саят-Нова: добавить данные
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

_db_pool = None
_http_client = None

def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=8.0)
    return _http_client

async def get_db_pool():
    global _db_pool
    if not POSTGRES_URL:
        return None
    if _db_pool is None:
        try:
            _db_pool = await asyncpg.create_pool(POSTGRES_URL, ssl='require', min_size=1, max_size=4, command_timeout=5.0)
        except Exception as e:
            print(f"Failed to create db pool: {e}")
            return None
    return _db_pool

_alfacrm_token = None
_alfacrm_token_expires = 0

async def get_alfacrm_token():
    global _alfacrm_token, _alfacrm_token_expires
    now = datetime.now().timestamp()
    if _alfacrm_token and now < _alfacrm_token_expires:
        return _alfacrm_token
        
    client = get_http_client()
    try:
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
    except Exception as e:
        print(f"ALFACRM AUTH EXCEPTION: {e}")
        return None

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

def check_crm_prefix(name: str, prefix: str) -> bool:
    if not name or not prefix: return False
    n = name.upper()
    p = prefix.upper()
    return (n.startswith(f"{p} |") or 
            n.startswith(f"{p}|") or 
            n.startswith(f"{p}. |") or 
            n.startswith(f"{p}.|"))
async def get_alfacrm_customer_by_name(name: str, crm_prefix: str = None):
    """Search CRM customer by name. If crm_prefix given, filters to that location only."""
    token = await get_alfacrm_token()
    if not token: return None
    
    headers = {
        "X-ALFACRM-TOKEN": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    clean_name = name.strip()
    rus_name = transliterate_name(clean_name)
    
    search_names = [clean_name]
    if rus_name.lower() != clean_name.lower():
        search_names.append(rus_name)
        
    client = get_http_client()
    for search_n in search_names:
        try:
            response = await client.post(
                "https://robixlab.s20.online/v2api/1/customer/index",
                headers=headers,
                json={"name": search_n, "is_study": [0, 1, 2]},
                timeout=5.0
            )
            if response.status_code == 200:
                items = response.json().get("items", [])
                if items:
                    if crm_prefix:
                        filtered = [i for i in items
                                    if check_crm_prefix(i.get("name", ""), crm_prefix)]
                        if filtered:
                            return filtered[0]
                    else:
                        return items[0]
        except Exception as e:
            print(f"Error searching customer '{search_n}': {e}")
            
    words = [w for w in clean_name.split() if len(w) >= 2]
    rus_words = [w for w in rus_name.split() if len(w) >= 2]
    all_words = list(dict.fromkeys(words + rus_words))
    
    if len(all_words) > 1:
        for word in all_words:
            try:
                response = await client.post(
                    "https://robixlab.s20.online/v2api/1/customer/index",
                    headers=headers,
                    json={"name": word, "is_study": [0, 1, 2]},
                    timeout=5.0
                )
                if response.status_code == 200:
                    items = response.json().get("items", [])
                    other_words = [w.lower() for w in all_words if w.lower() != word.lower()]
                    for item in items:
                        item_name = item.get("name", "").lower()
                        match = any(ow in item_name for ow in other_words) or len(items) == 1
                        if match:
                            if crm_prefix:
                                if check_crm_prefix(item.get("name", ""), crm_prefix):
                                    return item
                            else:
                                return item
            except Exception as e:
                print(f"Error searching candidate word '{word}': {e}")
            
    return None

async def get_alfacrm_customer_by_id(customer_id: int):
    token = await get_alfacrm_token()
    if not token: return None
    
    headers = {
        "X-ALFACRM-TOKEN": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payloads = [
        {"id": customer_id, "is_study": [0, 1, 2]},
        {"id": customer_id, "is_study": 0},
        {"id": customer_id, "is_study": 1}
    ]
    
    client = get_http_client()
    for payload in payloads:
        try:
            response = await client.post(
                "https://robixlab.s20.online/v2api/1/customer/index",
                headers=headers,
                json=payload,
                timeout=5.0
            )
            if response.status_code == 200:
                items = response.json().get("items", [])
                if items:
                    return items[0]
        except Exception as e:
            print(f"Error fetching customer by ID: {e}")
            
    return None

async def get_alfacrm_customer_by_phone(phone_raw: str, crm_prefix: str = None):
    """Search CRM customer by phone. If crm_prefix given, filters to that location only."""
    token = await get_alfacrm_token()
    if not token: return None
    
    # Extract only digits and get the core 8 digits for Armenian numbers
    digits = re.sub(r'\D', '', phone_raw)
    if len(digits) >= 8:
        base_phone = digits[-8:]
    else:
        base_phone = digits

    client = get_http_client()
    headers = {"X-ALFACRM-TOKEN": token, "Accept": "application/json", "Content-Type": "application/json"}
    
    try:
        response = await client.post(
            "https://robixlab.s20.online/v2api/1/customer/index",
            headers=headers,
            json={"phone": base_phone, "is_study": [0, 1]},
            timeout=5.0
        )
        if response.status_code == 200:
            items = response.json().get("items", [])
            if items:
                if crm_prefix:
                    filtered = [i for i in items
                                if check_crm_prefix(i.get("name", ""), crm_prefix)]
                    return filtered[0] if filtered else None
                return items[0]
    except Exception as e:
        print(f"Error fetching customer by phone: {e}")
        
    return None

async def get_alfacrm_lesson(date_str: str, time_str: str, subject_id: int,
                              lesson_type_id: int = 9, room_ids: list = None):
    """Search CRM lesson by date/time/subject. If room_ids given, filters to those rooms (location-specific)."""
    token = await get_alfacrm_token()
    if not token: return None
    
    headers = {"X-ALFACRM-TOKEN": token, "Accept": "application/json", "Content-Type": "application/json"}
    
    d_parts = date_str.split('.')
    if len(d_parts) == 2:
        year = datetime.now().year
        day, month = d_parts[0], d_parts[1]
    elif len(d_parts) == 3:
        day, month, year = d_parts[0], d_parts[1], d_parts[2]
    else:
        return None
        
    date_iso = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    if len(time_str) == 2:
        time_prefix = f"{time_str}:00"
    elif len(time_str) == 5:
        time_prefix = time_str
    else:
        return None

    client = get_http_client()
    payload = {
        "date_from": date_iso,
        "date_to": date_iso,
        "status": 1,
        "lesson_type_id": lesson_type_id
    }
    
    try:
        resp = await client.post(
            "https://robixlab.s20.online/v2api/1/lesson/index",
            headers=headers,
            json=payload,
            timeout=5.0
        )
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            valid_rooms = [rid for rid in (room_ids or []) if rid is not None]
            for lesson in items:
                if lesson.get("subject_id") != subject_id:
                    continue
                if valid_rooms and lesson.get("room_id") not in valid_rooms:
                    continue  # Фильтр по локации
                l_time = lesson.get("time_from", "")
                if l_time.startswith(f"{date_iso} {time_prefix}"):
                    return lesson
    except Exception as e:
        print(f"Error fetching lesson: {e}")
        
    return None


async def create_alfacrm_individual_lesson(date_str: str, time_str: str, subject_id: int, room_id: int, customer_id: int):
    token = await get_alfacrm_token()
    if not token: return False, "Token error"
    
    parts = date_str.split('.')
    if len(parts) == 2:
        year = datetime.now().year
        day, month = parts[0], parts[1]
    elif len(parts) == 3:
        day, month, year = parts[0], parts[1], parts[2]
    else:
        return False, "Invalid date"
        
    date_iso = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    date_api = f"{day.zfill(2)}.{month.zfill(2)}.{year}"
    
    if len(time_str) == 2:
        time_prefix = f"{time_str}:00"
    elif len(time_str) == 5:
        time_prefix = time_str
    else:
        return False, "Invalid time"
        
    payload = {
        "lesson_type_id": 3, # Individual Trial
        "lesson_date": date_api,
        "time_from": time_prefix,
        "duration": 50,
        "subject_id": subject_id,
        "room_id": room_id,
        "customer_ids": [customer_id],
        "status": 1 # Planned
    }
    
    headers = {"X-ALFACRM-TOKEN": token, "Accept": "application/json", "Content-Type": "application/json"}
    client = get_http_client()
    
    try:
        resp = await client.post(
            "https://robixlab.s20.online/v2api/1/lesson/create",
            headers=headers,
            json=payload,
            timeout=10.0
        )
        try:
            data = resp.json()
        except:
            data = {}
            
        if resp.status_code == 200:
            if data.get("success"):
                return True, "created"
            else:
                return False, str(data.get("errors", data))
        else:
            return False, f"HTTP {resp.status_code}: {str(data.get('errors', data))}"
    except Exception as e:
        return False, str(e)

async def add_customer_to_lesson(lesson_id: int, lesson_obj: dict, customer_id: int):
    token = await get_alfacrm_token()
    if not token: return False, "Token error"
    
    customer_ids = lesson_obj.get("customer_ids", [])
    if customer_id in customer_ids:
        return True, "already_added"
        
    new_customer_ids = list(customer_ids)
    new_customer_ids.append(customer_id)
    
    headers = {"X-ALFACRM-TOKEN": token, "Accept": "application/json", "Content-Type": "application/json"}
    client = get_http_client()
    
    try:
        resp = await client.post(
            f"https://robixlab.s20.online/v2api/1/lesson/update?id={lesson_id}",
            headers=headers,
            json={"customer_ids": new_customer_ids},
            timeout=10.0
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                return True, "added"
            else:
                return False, str(data.get("errors", data))
        return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, str(e)
async def check_customer_rooms(customer_id: int, valid_rooms: list = None) -> bool:
    token = await get_alfacrm_token()
    if not token: return False
    
    headers = {
        "X-ALFACRM-TOKEN": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    client = get_http_client()
    payload = {"customer_id": customer_id}
    try:
        response = await client.post(
            "https://robixlab.s20.online/v2api/1/lesson/index",
            headers=headers,
            json=payload,
            timeout=5.0
        )
        if response.status_code == 200:
            items = response.json().get("items", [])
            valid_r = valid_rooms if valid_rooms is not None else [33, 34]
            for lesson in items:
                if lesson.get("room_id") in valid_r:
                    return True
    except Exception as e:
        print(f"Error checking rooms: {e}")
    return False

async def get_all_alfacrm_groups():
    token = await get_alfacrm_token()
    if not token: return []
    
    headers = {
        "X-ALFACRM-TOKEN": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    client = get_http_client()
    try:
        resp = await client.post(
            "https://robixlab.s20.online/v2api/1/group/index",
            headers=headers,
            json={"page": 0, "per-page": 100},
            timeout=5.0
        )
        if resp.status_code == 200:
            return resp.json().get("items", [])
    except Exception as e:
        print(f"Error fetching all groups: {e}")
    return []

def find_group_in_list(group_query: str, all_groups: list):
    clean = group_query.strip().lower()
    if not clean: return None
    
    for g in all_groups:
        g_name = g.get("name", "").strip().lower()
        if clean == g_name:
            return g
            
    for g in all_groups:
        g_name = g.get("name", "").strip().lower()
        if clean in g_name:
            return g
            
    q_words = clean.split()
    for g in all_groups:
        g_name = g.get("name", "").strip().lower()
        if all(w in g_name for w in q_words):
            return g
            
    return None

async def get_alfacrm_group_by_name(group_name: str):
    all_groups = await get_all_alfacrm_groups()
    return find_group_in_list(group_name, all_groups)

async def add_customer_to_alfacrm_group(group_id: int, customer_id: int, group_obj: dict = None):
    token = await get_alfacrm_token()
    if not token: return False, "Token error"
    
    headers = {
        "X-ALFACRM-TOKEN": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    client = get_http_client()
    payload = {
        "customer_id": customer_id
    }
    
    try:
        update_resp = await client.post(
            f"https://robixlab.s20.online/v2api/1/cgi/create?group_id={group_id}",
            headers=headers,
            json=payload,
            timeout=10.0
        )
        if update_resp.status_code == 200:
            res_data = update_resp.json()
            if res_data.get("success"):
                return True, "added"
            else:
                errors = res_data.get("errors", {})
                group_errors = errors.get("group_id", [])
                if group_errors and "уже состоит" in group_errors[0]:
                    return True, "already_in_group"
                return False, str(errors or res_data)
        else:
            return False, f"HTTP {update_resp.status_code}: {update_resp.text}"
    except Exception as e:
        return False, str(e)
        
    return False, "Unknown error"

async def create_alfacrm_payment(customer_id: int, amount: int, method_raw: str,
                                  payer_name: str, location_config: dict = None):
    """Create payment in CRM. Uses location_config for account IDs and location_id."""
    token = await get_alfacrm_token()
    if not token: return False
    
    headers = {
        "X-ALFACRM-TOKEN": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Resolve location config (fall back to GN defaults if not provided)
    loc = location_config or get_location(DEFAULT_LOCATION)
    accounts = loc["accounts"]
    
    # Account Mapping by method
    method = method_raw.lower()
    if method == 'n':
        pay_account_id = accounts["cash"]
    elif method == 'b.n':
        pay_account_id = accounts["terminal"]
    elif method in ['c', 'с']:
        pay_account_id = accounts["card"]
    else:
        pay_account_id = accounts["cash"]
        
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
        "branch_id": loc["branch_id"],       # Всегда 1 (один CRM-филиал)
        "location_id": loc["location_id"],   # Различается по локации
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
            if response.status_code == 200:
                return True
            else:
                print(f"Alfa CRM Pay Error: {response.status_code} - {response.text}")
                return False
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
    pool = await get_db_pool()
    if not pool: return
    try:
        async with pool.acquire() as conn:
            await conn.execute('''CREATE TABLE IF NOT EXISTS tasks
                         (id SERIAL PRIMARY KEY, description TEXT, location TEXT NOT NULL DEFAULT 'GN')''')
            # Безопасная миграция: добавляем поле location в уже существующую таблицу
            try:
                await conn.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS location TEXT NOT NULL DEFAULT 'GN'")
            except Exception:
                pass
            await conn.execute('''CREATE TABLE IF NOT EXISTS lego_groups
                         (id SERIAL PRIMARY KEY, name TEXT UNIQUE)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS lego_themes
                         (id SERIAL PRIMARY KEY, group_id INTEGER REFERENCES lego_groups(id) ON DELETE CASCADE, name TEXT)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS banned_users
                         (user_id BIGINT PRIMARY KEY)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS executors
                         (user_id BIGINT PRIMARY KEY, name TEXT)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS all_users
                         (user_id BIGINT PRIMARY KEY, username TEXT, full_name TEXT)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS user_settings (
                         user_id         BIGINT PRIMARY KEY,
                         active_location TEXT   NOT NULL DEFAULT 'GN',
                         language        TEXT   NOT NULL DEFAULT 'hy')''')
                         
            rows = await conn.fetch("SELECT user_id FROM banned_users")
            BANNED_USERS = {row['user_id'] for row in rows}
            
            exec_rows = await conn.fetch("SELECT user_id, name FROM executors")
            for row in exec_rows:
                EXECUTORS[row['user_id']] = row['name']
                
            known_rows = await conn.fetch("SELECT user_id FROM all_users")
            for row in known_rows:
                KNOWN_USERS.add(row['user_id'])
            
            db_initialized = True
    except Exception as e:
        print(f"ensure_db error: {e}")
    # Загружаем настройки пользователей в кэш (разрешено после ensure_db, так как функция определяется ниже)
    await load_user_settings()

async def add_task(description: str, location: str = 'GN'):
    pool = await get_db_pool()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO tasks (description, location) VALUES ($1, $2)", description, location)

async def get_tasks(location: str = 'GN'):
    pool = await get_db_pool()
    if not pool: return []
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT id, description FROM tasks WHERE location = $1 ORDER BY id", location)

async def delete_task(task_id: int):
    pool = await get_db_pool()
    if not pool: return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT description FROM tasks WHERE id = $1", task_id)
        if row:
            await conn.execute("DELETE FROM tasks WHERE id = $1", task_id)
            return row['description']
    return None

# ─────────────────────── User Settings ───────────────────────

async def load_user_settings() -> None:
    """Load all user settings (location + language) from DB into USER_SETTINGS cache."""
    pool = await get_db_pool()
    if not pool:
        return
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id, active_location, language FROM user_settings")
            for row in rows:
                USER_SETTINGS[row['user_id']] = {
                    "location": row['active_location'],
                    "language": row['language'],
                }
    except Exception as e:
        print(f"load_user_settings error: {e}")

async def get_user_location(user_id: int) -> dict:
    """Returns the active location config dict for a user. Defaults to GN."""
    code = USER_SETTINGS.get(user_id, {}).get("location", DEFAULT_LOCATION)
    return get_location(code) or get_location(DEFAULT_LOCATION)

async def set_user_location(user_id: int, code: str) -> None:
    """Persist active location for user in DB and cache."""
    current = USER_SETTINGS.get(user_id, {})
    USER_SETTINGS[user_id] = {"location": code, "language": current.get("language", "hy")}
    pool = await get_db_pool()
    if pool:
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO user_settings (user_id, active_location, language)
                       VALUES ($1, $2, 'hy')
                       ON CONFLICT (user_id) DO UPDATE SET active_location = $2""",
                    user_id, code
                )
        except Exception as e:
            print(f"set_user_location error: {e}")

async def get_user_language(user_id: int) -> str:
    """Returns the language preference for a user ('hy' or 'ru'). Defaults to 'hy'."""
    return USER_SETTINGS.get(user_id, {}).get("language", "hy")

async def set_user_language(user_id: int, lang: str) -> None:
    """Persist language preference for user in DB and cache."""
    current = USER_SETTINGS.get(user_id, {})
    USER_SETTINGS[user_id] = {"location": current.get("location", DEFAULT_LOCATION), "language": lang}
    pool = await get_db_pool()
    if pool:
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO user_settings (user_id, active_location, language)
                       VALUES ($1, 'GN', $2)
                       ON CONFLICT (user_id) DO UPDATE SET language = $2""",
                    user_id, lang
                )
        except Exception as e:
            print(f"set_user_language error: {e}")


def transliterate_name(text: str) -> str:
    if re.search(r'[а-яА-ЯеЁ]', text):
        return text

    text = text.replace('kh', 'х').replace('Kh', 'Х')
    text = text.replace('gh', 'г').replace('Gh', 'Г')
    text = text.replace('ph', 'ф').replace('Ph', 'Ф')
    text = text.replace('sh', 'ш').replace('Sh', 'Ш')
    text = text.replace('ch', 'ч').replace('Ch', 'Ч')
    text = text.replace('zh', 'ж').replace('Zh', 'Ж')
    text = text.replace('ts', 'ц').replace('Ts', 'Ц')
    text = text.replace('dz', 'дз').replace('Dz', 'Дз')
    text = text.replace('yan', 'ян').replace('Yan', 'Ян')
    text = text.replace('ian', 'ян').replace('Ian', 'Ян')
    text = text.replace('ya', 'я').replace('Ya', 'Я')
    text = text.replace('yu', 'ю').replace('Yu', 'Ю')
    text = text.replace('x', 'х').replace('X', 'Х')
    
    try:
        return translit(text, 'ru')
    except Exception:
        return text

@dp.message(Command("addprob"))
async def cmd_addprob(message: types.Message):
    if message.from_user.id not in KNOWN_USERS and message.from_user.id != ADMIN_ID:
        return

    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    loc  = await get_user_location(message.from_user.id)

    cmd_parts = message.text.split()
    if len(cmd_parts) != 5:
        await message.answer(t("addprob_format", lang), parse_mode="Markdown")
        return

    phone_raw   = cmd_parts[1]
    lesson_type = cmd_parts[2].lower()
    date_raw    = cmd_parts[3]
    time_raw    = cmd_parts[4]

    if lesson_type not in ['mk', 'lg']:
        await message.answer(t("invalid_type", lang))
        return

    subject_id  = 23 if lesson_type == 'mk' else 24
    lesson_name = "MakeBlock" if lesson_type == 'mk' else "LEGO Education"
    # room_ids for the user's active location (filter lessons to correct location)
    room_ids = [v for v in loc["rooms"].values() if v is not None]

    status_msg = await message.answer(t("addprob_searching", lang))

    # 1. Search customer filtered by location prefix
    customer = await get_alfacrm_customer_by_phone(phone_raw, crm_prefix=loc["crm_prefix"])
    if not customer:
        await status_msg.edit_text(t("addprob_not_found", lang, phone=phone_raw))
        return

    customer_id        = customer.get("id")
    customer_name_full = customer.get("name", t("unknown", lang))

    # 2. Find specific lesson filtered by location rooms
    lesson = await get_alfacrm_lesson(
        date_raw, time_raw, subject_id,
        room_ids=room_ids if room_ids else None
    )
    if not lesson:
        d_parts_l = date_raw.split('.')
        d_f = f"{date_raw}.{datetime.now().year}" if len(d_parts_l) == 2 else date_raw
        t_f = f"{time_raw}:00" if len(time_raw) == 2 else time_raw
        await status_msg.edit_text(t("addprob_no_lesson", lang, lesson=lesson_name, dt=f"{d_f} {t_f}"))
        return

    lesson_id = lesson.get("id")
    # 3. Add to lesson
    success, result_msg = await add_customer_to_lesson(lesson_id, lesson, customer_id)

    if success:
        if result_msg == "already_added":
            await status_msg.edit_text(t("addprob_already", lang, name=customer_name_full))
        else:
            d_parts_l   = date_raw.split('.')
            d_formatted = f"{date_raw}.{datetime.now().year}" if len(d_parts_l) == 2 else date_raw
            t_formatted = f"{time_raw}:00" if len(time_raw) == 2 else time_raw
            await status_msg.edit_text(
                t("addprob_added", lang,
                  student=customer_name_full,
                  lesson=lesson_name,
                  dt=f"{d_formatted} {t_formatted}",
                  loc=loc["name"]),
                parse_mode="Markdown"
            )
    else:
        await status_msg.edit_text(t("addprob_error", lang, msg=result_msg))

@dp.message(Command("addprobk"))
async def cmd_addprobk(message: types.Message):
    if message.from_user.id not in KNOWN_USERS and message.from_user.id != ADMIN_ID:
        return
        
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    loc = await get_user_location(message.from_user.id)
        
    parts = message.text.split()
    if len(parts) != 5:
        await message.answer(t("addprobk_format", lang), parse_mode="Markdown")
        return
        
    phone_raw = parts[1]
    lesson_type = parts[2].lower()
    date_raw = parts[3]
    time_raw = parts[4].replace("։", ":")
    
    if lesson_type not in ['mk', 'lg']:
        await message.answer(t("invalid_type", lang))
        return
        
    subject_id = 23 if lesson_type == 'mk' else 24
    room_id = 31 if lesson_type == 'mk' else 30
    lesson_name = "MakeBlock" if lesson_type == 'mk' else "LEGO Education"
    
    status_msg = await message.answer(t("addprobk_creating", lang, loc=loc["name"]))
    
    # 1. Search customer
    customer = await get_alfacrm_customer_by_phone(phone_raw)
    if not customer:
        await status_msg.edit_text(t("addprob_not_found", lang, phone=phone_raw))
        return
        
    customer_id = customer.get("id")
    customer_name_full = customer.get("name", t("unknown", lang))
    
    # 2. Create new individual lesson
    success, result_msg = await create_alfacrm_individual_lesson(date_raw, time_raw, subject_id, room_id, customer_id)
    
    if success:
        y = datetime.now().year
        d_formatted = f"{date_raw}.{y}" if len(date_raw.split('.')) == 2 else date_raw
        t_formatted = f"{time_raw}:00" if len(time_raw) == 2 else time_raw
        await status_msg.edit_text(
            t("addprob_added", lang,
              student=customer_name_full,
              lesson=lesson_name,
              dt=f"{d_formatted} {t_formatted}",
              loc=loc["name"]),
            parse_mode="Markdown"
        )
    else:
        err_msg = result_msg
        if "Аудитория занята" in result_msg:
            err_msg = t("room_busy", lang)
        elif "Неверный формат" in result_msg or "Необходимо заполнить" in result_msg:
            err_msg = t("bad_format", lang)
        await status_msg.edit_text(t("addprobk_err_create", lang, msg=err_msg))

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    await message.answer(
        t("start_msg", lang),
        reply_markup=ForceReply(selective=True)
    )

def is_name_reply(message: types.Message) -> bool:
    if not message.reply_to_message or not message.reply_to_message.text:
        return False
    return "Рипсиме" in message.reply_to_message.text or "Рипсиме" in message.reply_to_message.text

@dp.message(is_name_reply)
async def process_name_registration(message: types.Message):
    name = message.text.strip()
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    
    # Проверка на то, что имя написано русскими буквами
    if not re.match(r'^[А-Яа-яЁё\s]+$', name):
        await message.answer(
            t("start_req_ru", lang),
            reply_markup=ForceReply(selective=True)
        )
        return
        
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    await conn.execute(
        "INSERT INTO executors (user_id, name) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name",
        message.from_user.id, name
    )
    await conn.close()
    
    EXECUTORS[message.from_user.id] = name
    await message.answer(t("start_success", lang, name=name))

@dp.message(Command("getid"))
async def cmd_getid(message: types.Message):
    await message.answer(
        f"Chat ID: {message.chat.id}\n"
        f"Topic (Thread) ID: {message.message_thread_id}"
    )

@dp.message(Command("about"))
async def cmd_about(message: types.Message):
    lang = await get_user_language(message.from_user.id)
    await message.answer(t("about_msg", lang), parse_mode="Markdown")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    lang = await get_user_language(message.from_user.id)
    await message.answer(t("help_msg", lang), parse_mode="Markdown")

# ─────────────────────── /branch ──────────────────────────────────────────────
@dp.message(Command("branch"))
async def cmd_branch(message: types.Message):
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    args = message.text.split()

    if len(args) >= 2:
        # /branch gn | /branch k | /branch s
        raw  = " ".join(args[1:]).lower().strip()
        code = resolve_alias(raw)
        if not code:
            await message.answer(
                t("location_invalid", lang, code=raw),
                parse_mode="Markdown"
            )
            return
        await set_user_location(message.from_user.id, code)
        loc_cfg = get_location(code)
        await message.answer(
            t("location_set", lang, name=loc_cfg["name"]),
            parse_mode="Markdown"
        )
        return

    # /branch without args → show current + inline buttons
    loc_cfg = await get_user_location(message.from_user.id)
    builder = InlineKeyboardBuilder()
    for code, cfg in LOCATIONS.items():
        label = f"{'✅ ' if code == loc_cfg['code'] else ''}{cfg['name']}"
        builder.button(text=label, callback_data=f"loc_{code}")
    builder.adjust(1)
    await message.answer(
        t("location_current", lang, name=loc_cfg["name"]),
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("loc_"))
async def callback_set_location(callback: types.CallbackQuery):
    await ensure_db()
    code    = callback.data[4:]  # "loc_GN" → "GN"
    loc_cfg = get_location(code)
    lang    = await get_user_language(callback.from_user.id)
    if not loc_cfg:
        await callback.answer("❌ Unknown location", show_alert=True)
        return
    await set_user_location(callback.from_user.id, code)
    await callback.answer(f"✅ {loc_cfg['name']}")
    # Rebuild keyboard with updated checkmark
    builder = InlineKeyboardBuilder()
    for c, cfg in LOCATIONS.items():
        label = f"{'✅ ' if c == code else ''}{cfg['name']}"
        builder.button(text=label, callback_data=f"loc_{c}")
    builder.adjust(1)
    await callback.message.edit_text(
        t("location_current", lang, name=loc_cfg["name"]),
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )

# ─────────────────────── /language ────────────────────────────────────────────
@dp.message(Command("language"))
async def cmd_language(message: types.Message):
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{'✅ ' if lang == 'hy' else ''}🇦🇲 Հայերեն", callback_data="lang_hy")
    builder.button(text=f"{'✅ ' if lang == 'ru' else ''}🇷🇺 Русский", callback_data="lang_ru")
    builder.adjust(2)
    await message.answer(
        t("language_choose", lang),
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("lang_"))
async def callback_set_language(callback: types.CallbackQuery):
    await ensure_db()
    new_lang = callback.data[5:]  # "lang_hy" → "hy"
    await set_user_language(callback.from_user.id, new_lang)
    await callback.answer(t("language_set", new_lang))
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{'✅ ' if new_lang == 'hy' else ''}🇦🇲 Հայերեն", callback_data="lang_hy")
    builder.button(text=f"{'✅ ' if new_lang == 'ru' else ''}🇷🇺 Русский", callback_data="lang_ru")
    builder.adjust(2)
    await callback.message.edit_text(
        t("language_set", new_lang),
        reply_markup=builder.as_markup()
    )

# ─────────────────────── /khelp ───────────────────────────────────────────────
@dp.message(Command("khelp"))
async def cmd_khelp(message: types.Message):
    lang = await get_user_language(message.from_user.id)
    await message.answer(t("khelp_msg", lang), parse_mode="Markdown")

# ─────────────────────── /kaddtask ────────────────────────────────────────────
@dp.message(Command("kaddtask"))
async def cmd_kaddtask(message: types.Message):
    task_description = message.text.replace("/kaddtask", "", 1).strip()
    lang = await get_user_language(message.from_user.id)
    if not task_description:
        await message.answer(t("task_desc_req", lang))
        return
    if not POSTGRES_URL:
        await message.answer(t("no_db", lang))
        return

    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    await add_task(task_description, location="K")
    await message.answer(t("kaddtask_success", lang))

    user_info = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    task_msg  = t("kaddtask_notify", lang, user=user_info, desc=task_description)
    target_users = set(KNOWN_USERS).union(EXECUTORS.keys())
    for u_id in target_users:
        try:
            await bot.send_message(u_id, task_msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Failed to send kaddtask notification to {u_id}: {e}")

# ─────────────────────── /kchecktasks ─────────────────────────────────────────
@dp.message(Command("kchecktasks"))
async def cmd_kchecktasks(message: types.Message):
    lang = await get_user_language(message.from_user.id)
    if not POSTGRES_URL:
        await message.answer(t("no_db", lang))
        return

    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    tasks = await get_tasks(location="K")
    if not tasks:
        await message.answer(t("kchecktasks_empty", lang))
        return

    response = t("kchecktasks_header", lang)
    builder  = InlineKeyboardBuilder()
    for task in tasks:
        t_id   = task['id']
        t_desc = task['description']
        response += f"🔹 **Task{t_id}** - {t_desc}\n"
        builder.button(text=f"✅ Task{t_id}", callback_data=f"complete_K_{t_id}")
    builder.adjust(2)
    await message.answer(response, parse_mode="Markdown", reply_markup=builder.as_markup())

import json


def get_mapping(filename):
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, filename)
        with open(file_path, 'r', encoding='utf-8-sig') as f:
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

async def check_uncompleted_lessons(bot: Bot, exclude_ids=None, override_ids=None):
    if exclude_ids is None:
        exclude_ids = []
    if override_ids is None:
        override_ids = {}
        
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
                    # Skip empty groups (no customers assigned)
                    items = [i for i in items if i.get("customer_ids") or i.get("details")]
                    if items:
                        count = len(items)
                        
                        items.sort(key=lambda x: x.get("time_from", ""))
                        times = []
                        for item in items:
                            t_from = item.get("time_from", "")[-8:-3]
                            t_to = item.get("time_to", "")[-8:-3]
                            if t_from and t_to:
                                times.append(f"• {t_from} - {t_to}")
                        times_str = "\n".join(times)
                        
                        text = t("teacher_alert", "ru", name=teacher_info['name'], count=count, today=today_str, times=times_str)
                        try:
                            target_tg_id = override_ids.get(tg_id, tg_id)
                            await bot.send_message(target_tg_id, text, parse_mode="Markdown")
                            messages_sent += 1
                        except Exception as e:
                            print(f"Failed to send to {target_tg_id}: {e}")
            except Exception as e:
                print(f"Error fetching lessons for teacher {teacher_id}: {e}")
                
    return {"status": "ok", "reminders_sent": messages_sent}

@dp.message(Command("testteacher"))
async def cmd_testteacher(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    lang = await get_user_language(message.from_user.id)
    await message.answer(t("testteacher_start", lang))
    result = await check_uncompleted_lessons(bot, exclude_ids=[1037044744], override_ids={1071411870: 8954540927})
    await message.answer(t("testteacher_end", lang, count=result.get('reminders_sent', 0)))

@dp.message(Command("myschedule"))
async def cmd_myschedule(message: types.Message):
    user_id = message.from_user.id
    if user_id not in TEACHERS_MAP:
        lang = await get_user_language(message.from_user.id)
        await message.answer(t("not_a_teacher", lang))
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
            await message.answer(f"❌ Ошибка: {e}")
            return
            
    if not items:
        await message.answer(t("no_lessons_today_tomorrow", lang, name=teacher['name']), parse_mode="Markdown")
        return
        
    schedule_today = []
    schedule_tomorrow = []
    
    # Sort items by time_from
    items.sort(key=lambda x: x.get("time_from", ""))
    
    for item in items:
        # Skip empty groups
        if not item.get("customer_ids") and not item.get("details"):
            continue
            
        date_str = item.get("date")
        time_from = item.get("time_from", "")[-8:-3]
        time_to = item.get("time_to", "")[-8:-3]
        room = ROOMS_MAP.get(item.get("room_id"), t("unknown", lang)).replace("*", "").replace("_", "").replace("[", "").replace("]", "")
        subject = SUBJECTS_MAP.get(item.get("subject_id"), t("unknown", lang)).replace("*", "").replace("_", "").replace("[", "").replace("]", "")
        
        lesson_text = f"🕒 {time_from} - {time_to} | 🏫 {room} | 📚 {subject}"
        
        if date_str == date_from:
            schedule_today.append(lesson_text)
        elif date_str == date_to:
            schedule_tomorrow.append(lesson_text)
            
    response_text = f"📅 <b>{teacher['name']} - {t('schedule', lang)}</b>\n\n"
    
    if schedule_today:
        response_text += f"🔹 <b>{t('today', lang)}</b>\n" + "\n".join(schedule_today) + "\n\n"
    else:
        response_text += f"🔹 <b>{t('today', lang)}:</b> {t('no_lessons', lang)}\n\n"
        
    if schedule_tomorrow:
        response_text += f"🔹 <b>{t('tomorrow', lang)}</b>\n" + "\n".join(schedule_tomorrow)
    else:
        response_text += f"🔹 <b>{t('tomorrow', lang)}:</b> {t('no_lessons', lang)}"
        
    await message.answer(response_text, parse_mode="HTML")

@dp.message(Command("prob"))
async def cmd_prob(message: types.Message):
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    loc  = await get_user_location(message.from_user.id)

    schedule = PROB_SCHEDULES.get(loc["code"])
    if not schedule:
        await message.answer(t("prob_no_schedule", lang, loc=loc["name"]))
        return

    tz = zoneinfo.ZoneInfo("Asia/Yerevan")
    today_weekday = datetime.now(tz).weekday()
    day_name, day_schedule = schedule[today_weekday]

    text = (
        f"{loc['name']} ({t('correct_branch', lang)})\n"
        "——————————————————————————\n"
        f"🔹 {day_name}\n"
        f"{day_schedule}\n"
        "——————————————————————————"
    )
    await message.answer(text)

@dp.message(Command("proball"))
async def cmd_proball(message: types.Message):
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    loc  = await get_user_location(message.from_user.id)

    schedule = PROB_SCHEDULES.get(loc["code"])
    if not schedule:
        await message.answer(t("prob_no_schedule", lang, loc=loc["name"]))
        return

    text = f"{loc['name']} ({t('correct_branch', lang)})\n——————————————————————————\n"
    for i in range(6):  # Пн-Сб
        day_name, day_schedule = schedule[i]
        text += f"🔹 {day_name}\n{day_schedule}\n——————————————————————————\n"

    await message.answer(text)


@dp.message(Command("getweek"))
async def cmd_getweek(message: types.Message):
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    
    await message.answer(t("getweek_searching", lang))
    booked_slots = await fetch_probation_lessons()
    
    if booked_slots is None:
        await message.answer(t("getweek_err_api", lang))
        return
        
    if not booked_slots:
        await message.answer(t("getweek_empty", lang))
        return
        
    DAYS = [t("mon", lang), t("tue", lang), t("wed", lang), t("thu", lang), t("fri", lang), t("sat", lang), t("sun", lang)]
    
    grouped = {}
    for slot in booked_slots:
        w = slot["weekday"]
        t_time = slot["time"]
        s = slot["subject"]
        p = slot["participants"]
        
        if w not in grouped: grouped[w] = {}
        if t_time not in grouped[w]: grouped[w][t_time] = {}
        if s not in grouped[w][t_time]: grouped[w][t_time][s] = 0
        grouped[w][t_time][s] += p
        
    text = t("getweek_header", lang)
    for w in sorted(grouped.keys()):
        text += f"🔹 {DAYS[w]}\n"
        for t_time in sorted(grouped[w].keys()):
            for s, p in grouped[w][t_time].items():
                text += t("getweek_row", lang, time=t_time, subj=s, count=p)
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
                    name = c.get("name")
                    phones = c.get("phone", [])
                    phone = phones[0] if phones else None
                    customers_map[cid] = {"name": name, "phone": phone}
                
    return {"lessons": target_lessons, "customers": customers_map}

@dp.message(Command("getprob"))
async def cmd_getprob(message: types.Message):
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    
    await message.answer(t("getweek_searching", lang))
    
    data = await fetch_probation_details()
    if data is None:
        await message.answer(t("getweek_err_api", lang))
        return
        
    if not data or not data.get("lessons"):
        await message.answer(t("getweek_empty", lang))
        return
        
    DAYS = [t("mon", lang), t("tue", lang), t("wed", lang), t("thu", lang), t("fri", lang), t("sat", lang), t("sun", lang)]
    
    schedule = {}
    for lesson in data["lessons"]:
        w = lesson["weekday"]
        t_time = lesson["time"]
        s = lesson["subject"]
        if w not in schedule: schedule[w] = {}
        if t_time not in schedule[w]: schedule[w][t_time] = {}
        if s not in schedule[w][t_time]: schedule[w][t_time][s] = []
        schedule[w][t_time][s].extend(lesson["customers"])
        
    text = t("getprob_header", lang)
    for w in sorted(schedule.keys()):
        text += f"📅 <b>{DAYS[w]}</b>\n"
        for t_time in sorted(schedule[w].keys()):
            for s, c_list in schedule[w][t_time].items():
                text += f"🕒 {t_time} — {s}\n"
                for cid in c_list:
                    c = data["customers"].get(cid, {})
                    name = c.get("name") or t("unknown", lang)
                    if name.startswith("G.N | "):
                        name = name[6:]
                    # Escape HTML for name
                    name = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    phone = c.get("phone") or t("no_phone", lang)
                    if phone != t("no_phone", lang):
                        phone_clean = "".join(filter(str.isdigit, phone))
                        if phone.startswith("+"): phone_clean = "+" + phone_clean
                        phone_link = f'<a href="tel:{phone_clean}">{phone}</a>'
                    else:
                        phone_link = phone
                        
                    card_link = f'<a href="https://robixlab.s20.online/company/1/customer/view?id={cid}">{t("card_link", lang)}</a>'
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
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    
    await message.answer(t("freeprob_searching", lang))
    booked_slots = await fetch_probation_lessons()
    
    if booked_slots is None:
        await message.answer(t("getweek_err_api", lang))
        return
        
    booked = {}
    for slot in booked_slots:
        w = slot["weekday"]
        t_time = slot["time"]
        s = slot["subject"]
        p = slot["participants"]
        key = f"{w}_{t_time}_{s}"
        booked[key] = booked.get(key, 0) + p
        
    DAYS = [t("mon", lang), t("tue", lang), t("wed", lang), t("thu", lang), t("fri", lang), t("sat", lang), t("sun", lang)]
    
    tz = zoneinfo.ZoneInfo("Asia/Yerevan")
    now = datetime.now(tz)
    current_w = now.weekday()
    current_time = now.time()
    
    text = t("freeprob_header", lang)
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
                day_text += t("freeprob_row", lang, time=t_time, subj=s, avail=available)
                has_slots = True
                has_any_slots = True
                
        if has_slots:
            text += day_text + "—\n"
            
    if not has_any_slots:
        text += t("freeprob_empty", lang)
        
    if text.endswith("—\n"):
        text = text[:-2]
        
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("addtask"))
async def cmd_addtask(message: types.Message):
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    task_description = message.text.replace("/addtask", "", 1).strip()
    if not task_description:
        await message.answer(t("task_desc_req", lang))
        return
        
    if not POSTGRES_URL:
        await message.answer(t("no_db", lang))
        return

    loc = await get_user_location(message.from_user.id)
    await add_task(task_description, location=loc["code"])
    await message.answer(t("task_added", lang, loc=loc["name"]))

    user_info = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    task_msg = t("task_added_push", lang, loc=loc["name"], user=user_info, desc=task_description)

    # Get all users who use the bot (from Postgres & memory) to send them private notification
    target_users = set(KNOWN_USERS).union(EXECUTORS.keys())
    if POSTGRES_URL:
        try:
            conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
            rows = await conn.fetch("SELECT user_id FROM all_users UNION SELECT user_id FROM executors")
            await conn.close()
            for r in rows:
                target_users.add(r['user_id'])
        except Exception as e:
            print(f"Failed to fetch users for addtask notification: {e}")

    for u_id in target_users:
        try:
            await bot.send_message(u_id, task_msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Failed to send task notification to user {u_id}: {e}")

@dp.message(Command("checktasks"))
async def cmd_checktasks(message: types.Message):
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    if not POSTGRES_URL:
        await message.answer(t("no_db", lang))
        return

    loc = await get_user_location(message.from_user.id)
    tasks = await get_tasks(location=loc["code"])
    if not tasks:
        await message.answer(t("task_empty", lang))
        return
        
    response = t("task_header", lang, loc=loc['name'])
    builder = InlineKeyboardBuilder()
    
    for task in tasks:
        t_id = task['id']
        t_desc = task['description']
        response += f"🔹 **Task{t_id}** - {t_desc}\n"
        builder.button(text=f"✅ Task{t_id}", callback_data=f"complete_{loc['code']}_{t_id}")
    builder.adjust(2)
        
    await message.answer(response, parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("complete_"))
async def callback_complete_task(callback: types.CallbackQuery):
    await ensure_db()
    lang = await get_user_language(callback.from_user.id)
    
    # Support both "complete_GN_5" (new) and "complete_5" (legacy)
    raw_parts = callback.data.split("_")
    if len(raw_parts) == 3:
        cb_location = raw_parts[1]  # "GN", "K", etc.
        task_id     = int(raw_parts[2])
    else:
        cb_location = "GN"
        task_id     = int(raw_parts[1])
        
    task_desc = await delete_task(task_id)
    if not task_desc:
        await callback.answer(t("task_not_found_cb", lang), show_alert=True)
    else:
        await callback.answer(t("task_done_cb", lang, n=task_id))
        user_info = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
        
        notify_text = t("task_done_push", lang, user=user_info, n=task_id, desc=task_desc)
        
        # Send completion notifications ONLY to Lusine (6062763343), Hripsime (5636022981), and Aram (1472817960)
        for u_id in TASK_NOTIFY_USERS:
            try:
                await bot.send_message(u_id, notify_text, parse_mode="Markdown")
            except Exception as e:
                print(f"Failed to send task completion notification to {u_id}: {e}")
                
    tasks = await get_tasks(location=cb_location)
    if not tasks:
        await callback.message.edit_text(t("task_all_done", lang), parse_mode="Markdown")
        return
        
    loc_name = (get_location(cb_location) or {}).get("name", cb_location)
    response = t("task_header", lang, loc=loc_name)
    builder = InlineKeyboardBuilder()
    
    for task in tasks:
        t_id = task['id']
        t_desc = task['description']
        response += f"🔹 **Task{t_id}** - {t_desc}\n"
        builder.button(text=f"✅ Task{t_id}", callback_data=f"complete_{cb_location}_{t_id}")
    builder.adjust(2)
        
    await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.message(F.text.regexp(r'(?i)^/task(\d+)$'))
async def cmd_complete_task_number(message: types.Message):
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    match = re.match(r'(?i)^/task(\d+)$', message.text)
    if not match:
        return
    task_id = int(match.group(1))
    
    task_desc = await delete_task(task_id)
    if not task_desc:
        await message.answer(t("task_not_found_cmd", lang, n=task_id))
        return
        
    await message.answer(t("task_done_cmd", lang, n=task_id, desc=task_desc))
    
    user_info = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
    notify_text = t("task_done_push", lang, user=user_info, n=task_id, desc=task_desc)
    
    # Send completion notifications ONLY to Lusine (6062763343), Hripsime (5636022981), and Aram (1472817960)
    for u_id in TASK_NOTIFY_USERS:
        try:
            await bot.send_message(u_id, notify_text, parse_mode="Markdown")
        except Exception as e:
            print(f"Failed to send task completion notification to {u_id}: {e}")

@dp.message(Command("task"))
async def cmd_task_hint(message: types.Message):
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    await message.answer(t("task_hint", lang))

@dp.message(Command("add"))
async def cmd_add_student_to_group(message: types.Message):
    await ensure_db()
    loc  = await get_user_location(message.from_user.id)
    lang = await get_user_language(message.from_user.id)
    
    raw_args = message.text.replace("/add", "", 1).strip()
    
    lang = await get_user_language(message.from_user.id)
    if not raw_args:
        await message.answer(
            t("add_help", lang, loc=loc['name'], prefix=loc['crm_prefix']),
            parse_mode="Markdown"
        )
        return

    status_msg = await message.answer(t("add_search", lang, loc=loc['name']))
    
    # 1. Fetch all groups in 1 single HTTP request
    all_groups = await get_all_alfacrm_groups()
    
    group = None
    student_query = None
    
    # Check if explicit separator (comma or pipe) is used
    if ',' in raw_args or '|' in raw_args:
        sep = ',' if ',' in raw_args else '|'
        parts = [p.strip() for p in raw_args.split(sep, 1)]
        p1, p2 = parts[0], parts[1]
        
        g1 = find_group_in_list(p1, all_groups)
        g2 = find_group_in_list(p2, all_groups)
        
        if g1 and not g2:
            group = g1
            student_query = p2
        elif g2 and not g1:
            group = g2
            student_query = p1
        elif g1 and g2:
            group = g1
            student_query = p2
        else:
            student_query = p1
    else:
        # Space separated search: try matching group in local memory without HTTP requests
        words = raw_args.split()
        
        # Try finding group from different slice combinations
        for i in range(len(words) - 1, 0, -1):
            g_cand = " ".join(words[i:])
            g = find_group_in_list(g_cand, all_groups)
            if g:
                group = g
                student_query = " ".join(words[:i])
                break
                
        if not group:
            for i in range(1, len(words)):
                g_cand = " ".join(words[:i])
                g = find_group_in_list(g_cand, all_groups)
                if g:
                    group = g
                    student_query = " ".join(words[i:])
                    break
                    
        if not group:
            # Fallback: check last word or first word as group query candidate
            g = find_group_in_list(words[-1], all_groups)
            if g:
                group = g
                student_query = " ".join(words[:-1])
            else:
                g = find_group_in_list(words[0], all_groups)
                if g:
                    group = g
                    student_query = " ".join(words[1:])

    if not group:
        await status_msg.edit_text(t("add_err_group", lang, query=raw_args, loc=loc['name']))
        return

    if not student_query:
        await status_msg.edit_text(t("add_err_no_student", lang, query=raw_args))
        return

    # Fetch customer ONCE (by ID or name)
    c_id = extract_customer_id(student_query)
    if c_id is not None:
        customer = await get_alfacrm_customer_by_id(c_id)
    else:
        customer = await get_alfacrm_customer_by_name(student_query, crm_prefix=loc["crm_prefix"])

    if not customer:
        await status_msg.edit_text(t("add_err_student", lang, query=student_query))
        return

    group_name = group.get("name", "")
    group_id = group.get("id")
    customer_name = customer.get("name") or customer.get("legal_name", t("unknown", lang))
    customer_id = customer.get("id")

    # Check location prefix for group
    if not check_crm_prefix(group_name, loc['crm_prefix']):
        await status_msg.edit_text(
            t("add_err_g_prefix", lang, group=group_name, prefix=loc['crm_prefix']),
            parse_mode="Markdown"
        )
        return

    # Check location prefix for student
    if not check_crm_prefix(customer_name, loc['crm_prefix']):
        await status_msg.edit_text(
            t("add_err_s_prefix", lang, student=customer_name, prefix=loc['crm_prefix']),
            parse_mode="Markdown"
        )
        return

    # Add student to group
    success, msg = await add_customer_to_alfacrm_group(group_id, customer_id, group)
    
    if success:
        if msg == "already_in_group":
            await status_msg.edit_text(t("add_already", lang, student=customer_name, group=group_name))
        else:
            await status_msg.edit_text(
                t("add_success", lang, student=customer_name, group=group_name),
                parse_mode="Markdown"
            )
    else:
        await status_msg.edit_text(
            t("add_fail", lang, student=customer_name, group=group_name, err=msg),
            parse_mode="Markdown"
        )

@dp.message(Command("ban"))
async def cmd_ban(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer(t("ban_format", lang))
        return
        
    target_id = int(parts[1])
    if target_id == ADMIN_ID:
        await message.answer(t("ban_self", lang))
        return
        
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    await conn.execute("INSERT INTO banned_users (user_id) VALUES ($1) ON CONFLICT DO NOTHING", target_id)
    await conn.close()
    
    BANNED_USERS.add(target_id)
    await message.answer(t("ban_success", lang, uid=target_id))

@dp.message(Command("unban"))
async def cmd_unban(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer(t("unban_format", lang))
        return
        
    target_id = int(parts[1])
    
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    await conn.execute("DELETE FROM banned_users WHERE user_id = $1", target_id)
    await conn.close()
    
    if target_id in BANNED_USERS:
        BANNED_USERS.remove(target_id)
    await message.answer(t("unban_success", lang, uid=target_id))

@dp.message(Command("testsheet"))
async def cmd_testsheet(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🔄 Пробую подключиться к Google Sheets...")
    from api.sheets import append_payment_to_sheet
    import traceback
    try:
        success, msg = await append_payment_to_sheet("18.09.2026", "Test Testyan", 5000, "n")
        if success:
            await message.answer("✅ Данные успешно добавлены в Google Sheets!")
        else:
            await message.answer(f"❌ Ошибка в Google Sheets:\n`{msg}`", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Техническая ошибка:\n`{traceback.format_exc()}`", parse_mode="Markdown")

@dp.message(Command("sendupdate"))
async def cmd_sendupdate(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
        
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    
    text = (
        "🚀 **Բոտի նոր գլոբալ թարմացում (V3.0)**\n\n"
        "Ողջույն բոլորին: Մենք ուրախ ենք տեղեկացնել RobixLab բոտի V3 տարբերակի թողարկման մասին: Սա մեծ և կարևոր թարմացում է.\n\n"
        "🌍 **Բազմամասնաճյուղային համակարգ (Multi-branch)**\n"
        "Այժմ բոտը սպասարկում է բոլոր մասնաճյուղերը: Ավելացել է `/branch` հրամանը, որով կարող եք ընտրել ձեր մասնաճյուղը (Գ. Նժդեհ, Կոմիտաս կամ Սայաթ-Նովա): Վճարումները, առաջադրանքները (Task) և փորձնականները այժմ ավտոմատ կուղղվեն ձեր մասնաճյուղի Google աղյուսակ և Alfa CRM:\n\n"
        "🇷🇺🇦🇲 **Ամբողջական երկլեզու ինտերֆեյս**\n"
        "Բոտն այժմ ամբողջությամբ թարգմանված է հայերեն և ռուսերեն: Լեզուն փոխելու համար կարող եք օգտագործել `/language` հրամանը:\n\n"
        "💳 **Խելացի վճարումների համակարգ**\n"
        "• Վճարումների որոնումն այժմ ավելի ճշգրիտ է աշխատում (ճանաչում է `K.` և նման պրեֆիքսները):\n"
        "• Եթե աշակերտի անունը անգլերենով եք գրում, բոտն այն ավտոմատ կթարգմանի կիրիլիցա:\n"
        "• Վճարումները ավտոմատ մուտքագրվում են ճիշտ Google աղյուսակում («Оплаты Манташяна», «Оплаты Комитаса» և այլն)՝ կախված ընտրված մասնաճյուղից:\n\n"
        "🆕 **Փորձնական դասերի նոր գործիքներ**\n"
        "Ավելացել են նոր հրամաններ փորձնական դասերի գրանցման համար.\n"
        "👉 `/addprob <հեռ.> <mk/lg> <օր.ամիս> <ժամ>` — Խմբային դասեր\n"
        "👉 `/addprobk <հեռ.> <mk/lg> <օր.ամիս> <ժամ>` — Անհատական դասեր (Կոմիտաս)\n\n"
        "🛠 **Այլ բարելավումներ**\n"
        "• Բոտի աշխատանքը զգալիորեն արագացվել է, իսկ սխալների մշակումը կատարելագործվել է:\n"
        "• Թարմացվել են `/about` և `/help` հրամանները նոր հրամանների ցանկով:\n\n"
        "rus --- >\n\n"
        "🚀 **Новое глобальное обновление бота! (V3.0)**\n\n"
        "Всем привет! Мы рады сообщить о запуске версии V3 для нашего бота RobixLab. Это масштабное и важное обновление:\n\n"
        "🌍 **Многофилиальная система (Multi-branch)**\n"
        "Теперь бот поддерживает все наши филиалы! Добавлена команда `/branch` для выбора вашей локации (Г. Нжде, Комитас, Саят-Нова). Теперь платежи, задачи (Task) и пробные уроки автоматически направляются в правильную таблицу Google и Alfa CRM вашего филиала.\n\n"
        "🇷🇺🇦🇲 **Полный двуязычный интерфейс**\n"
        "Бот теперь 100% двуязычный (Армянский и Русский). Чтобы переключить язык, используйте команду `/language`.\n\n"
        "💳 **Умная система платежей**\n"
        "• Поиск учеников работает гораздо точнее (бот теперь понимает префиксы вроде `K.` и другие вариации).\n"
        "• Если вы пишете имя ученика на латинице, бот сам транслитерирует его в кириллицу.\n"
        "• Платежи автоматически попадают в правильный лист Google Sheets («Оплаты Манташяна», «Оплаты Комитаса» и т.д.) в зависимости от выбранной локации.\n\n"
        "🆕 **Новые инструменты для пробных уроков**\n"
        "Добавлены новые команды для быстрой записи на пробные уроки прямо из бота:\n"
        "👉 `/addprob <телефон> <mk/lg> <день.месяц> <время>` — Групповые уроки\n"
        "👉 `/addprobk <телефон> <mk/lg> <день.месяц> <время>` — Индивидуальные уроки (Комитас)\n\n"
        "🛠 **Другие улучшения**\n"
        "• Значительно ускорена работа бота и улучшена обработка ошибок.\n"
        "• Обновлены команды `/about` и `/help`, где расписаны все новые функции."
    )
    
    target_users = set(KNOWN_USERS).union(EXECUTORS.keys())
    if POSTGRES_URL:
        try:
            conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
            rows = await conn.fetch("SELECT user_id FROM all_users UNION SELECT user_id FROM executors")
            await conn.close()
            for r in rows:
                target_users.add(r['user_id'])
        except Exception as e:
            print(f"Failed to fetch users: {e}")
            
    success_count = 0
    for u_id in target_users:
        try:
            await bot.send_message(u_id, text, parse_mode="Markdown")
            success_count += 1
        except Exception:
            pass
            
    await message.answer(t("update_success", lang, count=success_count))

@dp.message(Command("getusers"))
async def cmd_getusers(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
        
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    rows = await conn.fetch("SELECT user_id, username, full_name FROM all_users ORDER BY full_name")
    await conn.close()
    
    if not rows:
        await message.answer(t("no_users", lang))
        return
        
    response = t("users_header", lang)
    for row in rows:
        user_display = row['full_name']
        if row['username']:
            user_display += f" (@{row['username']})"
        response += f"{user_display} - {row['user_id']}\n"
        
    if len(response) > 4000:
        response = response[:4000] + t("list_too_long", lang)
        
    await message.answer(response)

# Загрузка HTML файла с темами Lego
@dp.message(F.document)
async def process_html_upload(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.document.file_name.endswith('.html'):
        return
        
    lang = await get_user_language(message.from_user.id)
    await message.answer(t("html_upload_start", lang))
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
    await message.answer(t("html_upload_success", lang, g=groups_added, t=themes_added))

@dp.message(Command("lego"))
async def cmd_lego(message: types.Message):
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    
    group_query = message.text.replace("/lego", "", 1).strip()
    if not group_query:
        await message.answer(t("lego_format", lang))
        return
        
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    
    # Ищем группу 
    groups = await conn.fetch("SELECT id, name FROM lego_groups WHERE name ILIKE $1 LIMIT 1", f"%{group_query}%")
    if not groups:
        await conn.close()
        await message.answer(t("lego_not_found", lang, group=group_query))
        return
        
    group_id = groups[0]['id']
    group_name = groups[0]['name']
    
    themes = await conn.fetch("SELECT name FROM lego_themes WHERE group_id = $1 ORDER BY name", group_id)
    await conn.close()
    
    if not themes:
        await message.answer(t("lego_no_themes", lang, group=group_name))
        return
        
    themes_list = "\n".join([f"- {t['name']}" for t in themes])
    prompt = t("lego_themes_list", lang, group=group_name, list=themes_list)
    
    # Лимит Telegram - 4096 символов.
    if len(prompt) > 4000:
        prompt = prompt[:4000] + t("lego_theme_prompt", lang)
        
    await message.answer(prompt, reply_markup=ForceReply(selective=True))

def is_theme_reply(message: types.Message) -> bool:
    if not message.reply_to_message or not message.reply_to_message.text:
        return False
    return "Հասանելի թեմաներ «" in message.reply_to_message.text or "Доступные темы для группы «" in message.reply_to_message.text

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
    
    await ensure_db()
    lang = await get_user_language(message.from_user.id)
    conn = await asyncpg.connect(POSTGRES_URL, ssl='require')
    
    group_id = await conn.fetchval("SELECT id FROM lego_groups WHERE name = $1", group_name)
    if not group_id:
        await conn.close()
        await message.answer(t("lego_err_group", lang))
        return
        
    deleted_id = await conn.fetchval(
        "DELETE FROM lego_themes WHERE group_id = $1 AND name ILIKE $2 RETURNING id",
        group_id, f"%{theme_choice}%"
    )
    
    await conn.close()
    
    if deleted_id:
        await message.answer(t("lego_theme_selected", lang, theme=theme_choice, group=group_name))
    else:
        await message.answer(t("lego_theme_invalid", lang, theme=theme_choice, group=group_name))

def extract_customer_id(text: str) -> int | None:
    text = text.strip()
    if not text:
        return None
        
    # Standalone digits (e.g. "8372")
    if text.isdigit():
        return int(text)
        
    # Explicit id parameter: id=8372 or ?id=8372 or &id=8372
    match_id = re.search(r'[?&]?id=(\d+)', text, re.IGNORECASE)
    if match_id:
        return int(match_id.group(1))
        
    # customer/view or lead/view path with ID: /customer/view?id=8372 or /lead/view?id=8372
    match_view = re.search(r'(?:customer|lead)/view.*?(\d+)', text, re.IGNORECASE)
    if match_view:
        return int(match_view.group(1))

    # Label pattern like "id: 8372", "id 8372", "#8372"
    match_label = re.search(r'(?:id|ID|#)[\s:=]*(\d+)', text)
    if match_label:
        return int(match_label.group(1))

    return None

def is_url_or_link(text: str) -> bool:
    t = text.lower()
    return 'http://' in t or 'https://' in t or 's20.online' in t or 'alfacrm' in t or 'customer/view' in t or 'lead/view' in t

@dp.message(F.chat.type == "private")
async def process_payment(message: types.Message):
    if not message.text or message.chat.type != "private":
        return
        
    text = message.text.strip()
    
    if text.startswith('/'):
        return

    # Проверка, зарегистрировал ли пользователь свое имя
    if message.from_user.id not in EXECUTORS:
        await ensure_db()
        lang = await get_user_language(message.from_user.id)
        await message.answer(t("unreg_user", lang))
        return
        
    executor_name = EXECUTORS[message.from_user.id]
    
    await ensure_db()
    loc  = await get_user_location(message.from_user.id)
    lang = await get_user_language(message.from_user.id)

    ERROR_INSTRUCTION = t("payment_format_err", lang)

    parts = text.split()
    is_valid_payment_cmd = False
    if len(parts) >= 3:
        payment_method_raw = parts[-1].lower()
        payment_sum = parts[-2]
        clean_sum = payment_sum.replace('.', '').replace(',', '')
        if payment_method_raw in PAYMENT_METHODS and clean_sum.isdigit():
            is_valid_payment_cmd = True

    if not is_valid_payment_cmd:
        # User is replying with link or ID for pending payment
        if message.from_user.id in PENDING_PAYMENTS:
            customer_id = extract_customer_id(text)
            if customer_id is not None:
                pending = PENDING_PAYMENTS.pop(message.from_user.id)
                
                processing_msg = await message.answer(t("payment_processing", lang))
                customer = await get_alfacrm_customer_by_id(customer_id)
                if not customer:
                    await processing_msg.edit_text(t("payment_not_found", lang))
                    PENDING_PAYMENTS[message.from_user.id] = pending
                    return
                    
                payer_name = customer.get("legal_name") or customer.get("name", t("unknown", lang))
                success = await create_alfacrm_payment(customer_id, pending['amount'], pending['method_raw'], payer_name, location_config=loc)
                
                if success:
                    tz = zoneinfo.ZoneInfo("Asia/Yerevan")
                    date_str = datetime.now(tz).strftime("%d.%m.%Y")
                    student_name = customer.get("name", t("unknown", lang))
                    await append_payment_to_sheet(date_str, student_name, pending['amount'], pending['method_raw'], tab_name=loc.get("sheets_tab"))
                    await processing_msg.edit_text(t("payment_success", lang, name=student_name, text=pending['response_text']))
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
                    await processing_msg.edit_text(t("payment_error", lang))
                return
            else:
                await message.answer(t("payment_pending", lang), parse_mode="Markdown")
                return
        else:
            if is_url_or_link(text):
                await message.answer(t("payment_no_pending", lang), parse_mode="Markdown")
                return
            else:
                await message.answer(ERROR_INSTRUCTION, parse_mode="Markdown")
                return

    amount_int = int(clean_sum)
    name_english = " ".join(parts[:-2])
    name_russian = transliterate_name(name_english)
    payment_method = PAYMENT_METHODS.get(payment_method_raw, payment_method_raw)
    
    response_text = f"Платеж обработал(а): {executor_name}\n{loc['crm_prefix']} | {name_russian} | {payment_sum} | {payment_method}"
    
    processing_msg = await message.answer(t("payment_searching", lang))
    
    customer = await get_alfacrm_customer_by_name(name_russian, crm_prefix=loc["crm_prefix"])
    
    if not customer:
        await processing_msg.edit_text(t("payment_not_found", lang))
        PENDING_PAYMENTS[message.from_user.id] = {
            'amount': amount_int,
            'method_raw': payment_method_raw,
            'response_text': response_text
        }
        return
        
    customer_name = customer.get("name", "")
    customer_id = customer.get("id")
    
    is_valid_loc = False
    if check_crm_prefix(customer_name, loc['crm_prefix']):
        is_valid_loc = True
    else:
        valid_rooms = [v for v in loc["rooms"].values() if v is not None]
        is_valid_loc = await check_customer_rooms(customer_id, valid_rooms=valid_rooms)
        
    if not is_valid_loc:
        await processing_msg.edit_text(t("payment_wrong_loc", lang, name=customer_name, loc=loc['name']))
        PENDING_PAYMENTS[message.from_user.id] = {
            'amount': amount_int,
            'method_raw': payment_method_raw,
            'response_text': response_text
        }
        return
        
    payer_name = customer.get("legal_name") or customer_name
    success = await create_alfacrm_payment(customer_id, amount_int, payment_method_raw, payer_name, location_config=loc)
    
    if success:
        tz = zoneinfo.ZoneInfo("Asia/Yerevan")
        date_str = datetime.now(tz).strftime("%d.%m.%Y")
        await append_payment_to_sheet(date_str, customer_name, amount_int, payment_method_raw, tab_name=loc.get("sheets_tab"))
        await processing_msg.edit_text(t("payment_success", lang, name=customer_name, text=response_text))
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
        await processing_msg.edit_text(t("payment_error", lang))
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
                
                pool = await get_db_pool()
                if pool:
                    try:
                        async with pool.acquire() as conn:
                            await conn.execute(
                                "INSERT INTO all_users(user_id, username, full_name) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                                user_id, username, full_name
                            )
                    except Exception as e:
                        print(f"Error saving user: {e}")
                KNOWN_USERS.add(user_id)
        
        print("Starting dp.feed_update")
        await asyncio.wait_for(dp.feed_update(bot, update), timeout=12.0)
        print("Finished dp.feed_update successfully")
    except asyncio.TimeoutError:
        print("CRITICAL ERROR: Timeout! The process hung for more than 12 seconds.")
        return {"error": "Timeout"}
    except Exception as e:
        print(f"CRITICAL ERROR: {repr(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
        
    return {"status": "ok"}

@app.get("/api/cron/warmup")
async def cron_warmup():
    await ensure_db()
    await get_alfacrm_token()
    return {"status": "warmed", "time": datetime.now().isoformat()}

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
            
            response = t("cron_tasks_header", "ru")
            for task in tasks:
                response += t("cron_task_item", "ru", id=task['id'], desc=task['description'])
                
            await bot.send_message(
                chat_id_int, 
                response,
                message_thread_id=thread_id_int,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Failed to send cron to group: {e}")
            
    return {"status": "ok", "count": len(tasks)}
