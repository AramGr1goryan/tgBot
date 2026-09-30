import re

with open(r'c:\tgbot\api\webhook.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Helpers to inject
helpers = """
async def update_alfacrm_customer_name(customer_id: int, new_name: str):
    token = await get_alfacrm_token()
    if not token: return False
    
    headers = {
        "X-ALFACRM-TOKEN": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    client = get_http_client()
    try:
        response = await client.post(
            f"https://robixlab.s20.online/v2api/1/customer/update?id={customer_id}",
            headers=headers,
            json={"name": new_name},
            timeout=5.0
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error updating customer name: {e}")
        return False

async def _execute_payment(message, customer_id, payer_name, customer_name, amount_int, payment_method_raw, response_text, loc, lang, processing_msg=None):
    success, error_msg = await create_alfacrm_payment(customer_id, amount_int, payment_method_raw, payer_name, location_config=loc)
    
    if success:
        import zoneinfo
        from datetime import datetime
        tz = zoneinfo.ZoneInfo("Asia/Yerevan")
        date_str = datetime.now(tz).strftime("%d.%m.%Y")
        
        # update sheet
        sheet_success, sheet_err = await append_payment_to_sheet(date_str, customer_name, amount_int, payment_method_raw, tab_name=loc.get("sheets_tab"))
        if not sheet_success:
            response_text += f"\\n\\n⚠️ **Ուշադրություն (Внимание):** Alfa CRM-ում գրանցվել է, բայց ԴԴՍ աղյուսակում ավելացնելիս առաջացավ սխալ: Ստուգեք աղյուսակը:\\nՊատճառ՝ {sheet_err}"
            
        if processing_msg:
            await processing_msg.edit_text(t("payment_success", lang, name=customer_name, text=response_text))
        else:
            await message.answer(t("payment_success", lang, name=customer_name, text=response_text))
            
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
        if processing_msg:
            await processing_msg.edit_text(t("payment_error", lang, msg=error_msg))
        else:
            await message.answer(t("payment_error", lang, msg=error_msg))

@dp.message(F.chat.type == "private")
async def process_payment(message: types.Message):
    if not message.text or message.chat.type != "private":
        return
        
    text = message.text.strip()
    
    if text.startswith('/'):
        return

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
        if message.from_user.id in PENDING_PAYMENTS:
            pending = PENDING_PAYMENTS[message.from_user.id]
            state = pending.get('state', 'need_id')
            
            if state == 'confirm_prefix':
                ans = text.strip().lower()
                if ans in ['да', 'yes', 'ayo', 'այո', 'иа', '1', '+']:
                    customer = pending['customer']
                    processing_msg = await message.answer(t("payment_processing", lang))
                    new_name = f"{loc['crm_prefix']} | {customer.get('name', '')}"
                    await update_alfacrm_customer_name(customer['id'], new_name)
                    payer_name = customer.get('legal_name') or new_name
                    await _execute_payment(message, customer['id'], payer_name, new_name, pending['amount'], pending['method_raw'], pending['response_text'], loc, lang, processing_msg)
                    PENDING_PAYMENTS.pop(message.from_user.id, None)
                    return
                elif ans in ['нет', 'no', 'voch', 'ոչ', '0', '-']:
                    await message.answer(t("payment_pending", lang), parse_mode="Markdown")
                    pending['state'] = 'need_id'
                    return
                else:
                    await message.answer("Խնդրում ենք պատասխանել Այո կամ Ոչ (Yes/No):" if lang=='hy' else "Пожалуйста, ответьте Да или Нет (Yes/No):")
                    return
                    
            elif state == 'select_multiple':
                if text.strip().isdigit():
                    idx = int(text.strip()) - 1
                    candidates = pending['candidates']
                    if 0 <= idx < len(candidates):
                        customer = candidates[idx]
                        customer_name = customer.get("name", "")
                        customer_id = customer.get("id")
                        
                        is_valid_loc = False
                        if check_crm_prefix(customer_name, loc['crm_prefix']):
                            is_valid_loc = True
                        else:
                            valid_rooms = [v for v in loc["rooms"].values() if v is not None]
                            is_valid_loc = await check_customer_rooms(customer_id, valid_rooms=valid_rooms)
                            
                        if not is_valid_loc:
                            pending['state'] = 'confirm_prefix'
                            pending['customer'] = customer
                            ask_text = f"Ընտրված աշակերտը «{customer_name}» չունի «{loc['crm_prefix']}» պրեֆիքս: Սա՞ է ճիշտ աշակերտը: (Այո/Ոչ)" if lang=='hy' else f"Выбранный клиент «{customer_name}» не имеет префикса «{loc['crm_prefix']}». Это правильный клиент? (Да/Нет)"
                            await message.answer(ask_text)
                            return
                        else:
                            processing_msg = await message.answer(t("payment_processing", lang))
                            payer_name = customer.get("legal_name") or customer_name
                            await _execute_payment(message, customer_id, payer_name, customer_name, pending['amount'], pending['method_raw'], pending['response_text'], loc, lang, processing_msg)
                            PENDING_PAYMENTS.pop(message.from_user.id, None)
                            return
                    else:
                        await message.answer("Սխալ համար: Խնդրում ենք փորձել կրկին:" if lang=='hy' else "Неверный номер. Попробуйте еще раз:")
                        return
                else:
                    await message.answer("Խնդրում ենք մուտքագրել համարը ցանկից:" if lang=='hy' else "Пожалуйста, введите номер из списка:")
                    return
            
            customer_id = extract_customer_id(text)
            if customer_id is not None:
                processing_msg = await message.answer(t("payment_processing", lang))
                customer = await get_alfacrm_customer_by_id(customer_id)
                if not customer:
                    await processing_msg.edit_text(t("payment_not_found", lang))
                    return
                    
                payer_name = customer.get("legal_name") or customer.get("name", t("unknown", lang))
                customer_name = customer.get("name", t("unknown", lang))
                await _execute_payment(message, customer_id, payer_name, customer_name, pending['amount'], pending['method_raw'], pending['response_text'], loc, lang, processing_msg)
                PENDING_PAYMENTS.pop(message.from_user.id, None)
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
    
    response_text = f"Платеж обработал(а): {executor_name}\\n{loc['crm_prefix']} | {name_russian} | {payment_sum} | {payment_method}"
    
    processing_msg = await message.answer(t("payment_searching", lang))
    
    customers = await get_alfacrm_customers_by_name(name_russian)
    
    if not customers:
        await processing_msg.edit_text(t("payment_not_found", lang))
        PENDING_PAYMENTS[message.from_user.id] = {
            'amount': amount_int,
            'method_raw': payment_method_raw,
            'response_text': response_text,
            'state': 'need_id'
        }
        return
        
    if len(customers) > 1:
        await processing_msg.delete()
        list_str = "\\n".join([f"{i+1}. {c.get('name')} (ID: {c.get('id')})" for i, c in enumerate(customers)])
        ask_text = f"Գտնվել են մի քանի աշակերտներ:\\n{list_str}\\n\\nԸնտրեք համարը:" if lang=='hy' else f"Найдено несколько клиентов:\\n{list_str}\\n\\nВыберите номер:"
        await message.answer(ask_text)
        PENDING_PAYMENTS[message.from_user.id] = {
            'amount': amount_int,
            'method_raw': payment_method_raw,
            'response_text': response_text,
            'state': 'select_multiple',
            'candidates': customers
        }
        return
        
    customer = customers[0]
    customer_name = customer.get("name", "")
    customer_id = customer.get("id")
    
    is_valid_loc = False
    if check_crm_prefix(customer_name, loc['crm_prefix']):
        is_valid_loc = True
    else:
        valid_rooms = [v for v in loc["rooms"].values() if v is not None]
        is_valid_loc = await check_customer_rooms(customer_id, valid_rooms=valid_rooms)
        
    if not is_valid_loc:
        await processing_msg.delete()
        ask_text = f"Գտնվել է «{customer_name}» աշակերտը, բայց նա չունի «{loc['crm_prefix']}» պրեֆիքս: Սա՞ է ճիշտ աշակերտը: (Այո/Ոչ)" if lang=='hy' else f"Найден клиент «{customer_name}», но он не имеет префикса «{loc['crm_prefix']}». Это правильный клиент? (Да/Нет)"
        await message.answer(ask_text)
        PENDING_PAYMENTS[message.from_user.id] = {
            'amount': amount_int,
            'method_raw': payment_method_raw,
            'response_text': response_text,
            'state': 'confirm_prefix',
            'customer': customer
        }
        return
        
    payer_name = customer.get("legal_name") or customer_name
    await _execute_payment(message, customer_id, payer_name, customer_name, amount_int, payment_method_raw, response_text, loc, lang, processing_msg)
"""

start_pattern = r'@dp\.message\(F\.chat\.type == "private"\)\nasync def process_payment\(message: types\.Message\):'
end_pattern = r'@app\.post\("/api/webhook"\)'

match_start = re.search(start_pattern, content)
match_end = re.search(end_pattern, content)

if match_start and match_end:
    start_idx = match_start.start()
    end_idx = match_end.start()
    
    new_content = content[:start_idx] + helpers + "\n" + content[end_idx:]
    with open(r'c:\tgbot\api\webhook.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Success")
else:
    print("Failed to find patterns")
