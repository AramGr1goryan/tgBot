const fs = require('fs');

let content = fs.readFileSync('c:\\tgbot\\api\\webhook.py', 'utf-8');

// 1. Add ALTER TABLE
const ensureRegex = /await conn\.execute\(\'\'\'CREATE TABLE IF NOT EXISTS executors[\s\S]*?name TEXT\)\'\'\'\)/g;
content = content.replace(ensureRegex, `await conn.execute('''CREATE TABLE IF NOT EXISTS executors
                         (user_id BIGINT PRIMARY KEY, name TEXT)''')
            try:
                await conn.execute("ALTER TABLE executors ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'manager'")
            except Exception as e:
                pass`);

// 2. Add SELECT role
const selectRegex = /exec_rows = await conn\.fetch\(\"SELECT user_id, name FROM executors\"\)\s*for row in exec_rows:\s*EXECUTORS\[row\['user_id'\]\] = row\['name'\]/g;
content = content.replace(selectRegex, `exec_rows = await conn.fetch("SELECT user_id, name, role FROM executors")
            for row in exec_rows:
                EXECUTORS[row['user_id']] = row['name']
                EXECUTOR_ROLES[row['user_id']] = row['role'] or 'manager'`);

fs.writeFileSync('c:\\tgbot\\api\\webhook.py', content, 'utf-8');
console.log("fixed ensure_db");
