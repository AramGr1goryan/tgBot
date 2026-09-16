import re

with open('api/webhook.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Single line: if message.from_user.id != ADMIN_ID: return
# We only want to remove this from cmd_getweek, cmd_getprob, cmd_freeprob.
# But there are no other places where this exact string is used, wait, except maybe others?
# Let's check where it is used.
# Let's just remove it in those specific functions.
funcs = ['cmd_getweek', 'cmd_getprob', 'cmd_freeprob']
for func in funcs:
    pattern = rf"(async def {func}\(message: types\.Message\):\n\s*)if message\.from_user\.id != ADMIN_ID: return\n\s*"
    content = re.sub(pattern, r'\1', content)

# 2. cmd_addtask
pattern_addtask = r"(async def cmd_addtask\(message: types\.Message\):\n\s*)if message\.from_user\.id != ADMIN_ID:\n\s*await message\.answer\(.*?\)\n\s*return\n\s*"
content = re.sub(pattern_addtask, r'\1', content)

# 3. cmd_lego
pattern_lego = r"(async def cmd_lego\(message: types\.Message\):\n\s*)if message\.from_user\.id != ADMIN_ID:\n\s*return\n\s*"
content = re.sub(pattern_lego, r'\1', content)

# 4. process_theme_selection
pattern_theme = r"(async def process_theme_selection\(message: types\.Message\):\n\s*)if message\.from_user\.id != ADMIN_ID:\n\s*return\n\s*"
content = re.sub(pattern_theme, r'\1', content)

with open('api/webhook.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Success')
