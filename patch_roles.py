import re

with open(r'c:\tgbot\api\webhook.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add EXECUTOR_ROLES globally
content = content.replace("EXECUTORS = {}", "EXECUTORS = {}\nEXECUTOR_ROLES = {}")

# 2. Update ensure_db
old_ensure_1 = """            await conn.execute('''CREATE TABLE IF NOT EXISTS executors
                                  (user_id BIGINT PRIMARY KEY, name TEXT)''')"""
new_ensure_1 = """            await conn.execute('''CREATE TABLE IF NOT EXISTS executors
                                  (user_id BIGINT PRIMARY KEY, name TEXT)''')
            try:
                await conn.execute('''ALTER TABLE executors ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'manager' ''')
            except: pass"""

content = content.replace(old_ensure_1, new_ensure_1)

old_ensure_2 = """            exec_rows = await conn.fetch("SELECT user_id, name FROM executors")
            for row in exec_rows:
                EXECUTORS[row['user_id']] = row['name']"""
new_ensure_2 = """            exec_rows = await conn.fetch("SELECT user_id, name, role FROM executors")
            for row in exec_rows:
                EXECUTORS[row['user_id']] = row['name']
                EXECUTOR_ROLES[row['user_id']] = row['role'] or 'manager'"""

content = content.replace(old_ensure_2, new_ensure_2)

# 3. Update the insert in cmd_set_name (line 1060ish)
old_insert = """        await conn.execute(
            "INSERT INTO executors (user_id, name) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET name = $2",
            message.from_user.id, name
        )"""
new_insert = """        await conn.execute(
            "INSERT INTO executors (user_id, name, role) VALUES ($1, $2, 'manager') ON CONFLICT (user_id) DO UPDATE SET name = $2",
            message.from_user.id, name
        )"""
content = content.replace(old_insert, new_insert)

old_update_mem = """    EXECUTORS[message.from_user.id] = name"""
new_update_mem = """    EXECUTORS[message.from_user.id] = name\n    if message.from_user.id not in EXECUTOR_ROLES:\n        EXECUTOR_ROLES[message.from_user.id] = 'manager'"""
content = content.replace(old_update_mem, new_update_mem)

# 4. Add /setrole handler and /roles list
setrole_code = """
@dp.message(Command("setrole"))
async def cmd_setrole(message: types.Message):
    if message.from_user.id != 1472817960:
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Формат: /setrole <user_id> <role>")
        return
    try:
        target_id = int(parts[1])
    except:
        await message.answer("Неверный user_id")
        return
        
    role = parts[2]
    await ensure_db()
    
    if target_id not in EXECUTORS:
        await message.answer("Этот пользователь не зарегистрирован как менеджер.")
        return
        
    conn = await asyncpg.connect(POSTGRES_URL)
    try:
        await conn.execute("UPDATE executors SET role = $1 WHERE user_id = $2", role, target_id)
        EXECUTOR_ROLES[target_id] = role
        await message.answer(f"Роль пользователя {EXECUTORS[target_id]} (ID: {target_id}) обновлена на '{role}'.")
    except Exception as e:
        await message.answer(f"Ошибка БД: {e}")
    finally:
        await conn.close()

@dp.message(Command("roles"))
async def cmd_roles(message: types.Message):
    if message.from_user.id != 1472817960:
        return
    await ensure_db()
    if not EXECUTORS:
        await message.answer("Нет зарегистрированных пользователей.")
        return
        
    lines = ["Список пользователей и ролей:"]
    for uid, name in EXECUTORS.items():
        role = EXECUTOR_ROLES.get(uid, 'manager')
        lines.append(f"ID: <code>{uid}</code> | {name} | Роль: <b>{role}</b>")
    await message.answer("\\n".join(lines), parse_mode="HTML")
"""

idx = content.find('@dp.message(Command("check"))')
if idx != -1:
    content = content[:idx] + setrole_code + "\n" + content[idx:]


# 5. Modify cron to check role
old_cron_loop = """    for user_id in EXECUTORS:
        try:
            lang = await get_user_language(user_id)"""
new_cron_loop = """    for user_id in EXECUTORS:
        if EXECUTOR_ROLES.get(user_id) != 'admin':
            continue
        try:
            lang = await get_user_language(user_id)"""
            
content = content.replace(old_cron_loop, new_cron_loop)


with open(r'c:\tgbot\api\webhook.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
