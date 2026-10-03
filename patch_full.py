import re

with open(r'c:\tgbot\api\webhook.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add normalize_homoglyphs and fix_layout right before check_crm_prefix
additions = """
def normalize_homoglyphs(text: str) -> str:
    if not text: return text
    homoglyphs = {
        'А': 'A', 'а': 'a',
        'В': 'B', 'в': 'b', # 'b' doesn't look like 'в' but uppercase does. However, 'в' is often confused or we just map upper.
        'С': 'C', 'с': 'c',
        'Е': 'E', 'е': 'e',
        'Н': 'H', 'н': 'h',
        'К': 'K', 'к': 'k',
        'М': 'M', 'м': 'm',
        'О': 'O', 'о': 'o',
        'Р': 'P', 'р': 'p',
        'Т': 'T', 'т': 't',
        'Х': 'X', 'х': 'x',
        'У': 'Y', 'у': 'y'
    }
    res = []
    for ch in text:
        res.append(homoglyphs.get(ch, ch))
    return "".join(res)

def fix_layout(text: str) -> str:
    en_to_ru = str.maketrans(
        "qwertyuiop[]asdfghjkl;'zxcvbnm,./QWERTYUIOP{}ASDFGHJKL:\\"ZXCVBNM<>?",
        "йцукенгшщзхъфывапролджэячсмитьбю.ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,"
    )
    return text.translate(en_to_ru)

"""

if "def normalize_homoglyphs" not in content:
    content = content.replace("def check_crm_prefix(name: str, prefix: str) -> bool:", additions + "def check_crm_prefix(name: str, prefix: str) -> bool:")

# 2. Update check_crm_prefix
old_check = """def check_crm_prefix(name: str, prefix: str) -> bool:
    if not name or not prefix: return False
    n = name.upper()
    p = prefix.upper()
    return (n.startswith(f"{p} |") or 
            n.startswith(f"{p}|") or 
            n.startswith(f"{p}. |") or 
            n.startswith(f"{p}.|"))"""

new_check = """def check_crm_prefix(name: str, prefix: str) -> bool:
    if not name or not prefix: return False
    n = normalize_homoglyphs(name.upper())
    p = normalize_homoglyphs(prefix.upper())
    # Regex to match prefix optionally followed by dot, then optional spaces, then a pipe
    import re
    pattern = r"^" + re.escape(p) + r"\.?\s*\|"
    return bool(re.match(pattern, n))"""

content = content.replace(old_check, new_check)

# 3. Update get_alfacrm_customers_by_name
old_search_logic = """    clean_name = name.strip()
    rus_name = transliterate_name(clean_name)
    
    search_names = [clean_name]
    if rus_name.lower() != clean_name.lower():
        search_names.append(rus_name)"""

new_search_logic = """    clean_name = name.strip()
    rus_name = transliterate_name(clean_name)
    fixed_layout_name = fix_layout(clean_name)
    fixed_layout_rus = transliterate_name(fixed_layout_name)
    
    search_names = []
    for n in [clean_name, rus_name, fixed_layout_name, fixed_layout_rus]:
        if n and n.lower() not in [x.lower() for x in search_names]:
            search_names.append(n)"""

content = content.replace(old_search_logic, new_search_logic)

# 4. Update _execute_payment to use CRM name for group messages
old_execute = """async def _execute_payment(message, customer_id, payer_name, customer_name, amount_int, payment_method_raw, response_text, loc, lang, processing_msg=None):
    success, error_msg = await create_alfacrm_payment(customer_id, amount_int, payment_method_raw, payer_name, location_config=loc)"""

new_execute = """async def _execute_payment(message, customer_id, payer_name, customer_name, amount_int, payment_method_raw, response_text, loc, lang, processing_msg=None):
    executor_name = message.from_user.full_name
    payment_method = PAYMENT_METHODS.get(payment_method_raw, payment_method_raw)
    
    # Reconstruct response_text with the correct CRM customer_name
    # customer_name already contains the prefix if it's from CRM or if apply_crm_prefix was used
    response_text = f"Платеж обработал(а): {executor_name}\\n{customer_name} | {amount_int} | {payment_method}"
    
    success, error_msg = await create_alfacrm_payment(customer_id, amount_int, payment_method_raw, payer_name, location_config=loc)"""

content = content.replace(old_execute, new_execute)

with open(r'c:\tgbot\api\webhook.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied successfully.")
