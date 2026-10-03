import os
with open('c:\\tgbot\\api\\sheets.py', 'a', encoding='utf-8') as f:
    f.write('''\n
async def append_expense_to_sheet(date_str: str, reason: str, amount: int, tab_name: str = None):
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    if not tab_name:
        tab_name = os.environ.get("GOOGLE_SHEET_TAB_NAME", "Оплаты Манташяна")
    
    if not sheet_id:
        return False, "GOOGLE_SHEET_ID is not configured"
        
    try:
        # Pre-validate creds to catch parsing errors early
        _ = get_creds()

        client = await agcm.authorize()
        spreadsheet = await client.open_by_key(sheet_id)
        worksheet = await spreadsheet.worksheet(tab_name)
        
        # Parse month from date (e.g. 18.09.2026 -> 9)
        month = ""
        try:
            dt = datetime.strptime(date_str, "%d.%m.%Y")
            month = str(dt.month)
        except:
            pass
            
        row_data_ag = [
            "",               # A
            month,            # B
            date_str,         # C
            "Расход",         # D
            reason,           # E
            "",               # F
            amount,           # G
        ]
        
        # Fetch all values to find the real last row with data
        records = await worksheet.get_values()
        
        last_row_with_data = 0
        for i, row in enumerate(records):
            # Check if there's any text in Date (C), Type (D), or Name (E)
            has_data = False
            for col_idx in [2, 3, 4]:
                if col_idx < len(row) and str(row[col_idx]).strip():
                    has_data = True
                    break
            if has_data:
                last_row_with_data = i + 1
                
        next_row = last_row_with_data + 1
        
        # Update columns A through G
        await worksheet.update(
            values=[row_data_ag],
            range_name=f"A{next_row}:G{next_row}",
            value_input_option='USER_ENTERED'
        )
        return True, f"Success (row {next_row})"
    except gspread.exceptions.WorksheetNotFound:
        msg = f"Вкладка '{tab_name}' не найдена в таблице Google Sheets"
        print(f"Sheets Error: {msg}")
        return False, msg
    except gspread.exceptions.SpreadsheetNotFound:
        msg = f"Документ Google Sheets ({sheet_id}) не найден или у бота нет к нему доступа"
        print(f"Sheets Error: {msg}")
        return False, msg
    except gspread.exceptions.APIError as e:
        msg = f"Ошибка API Google Sheets (возможно, лимит запросов): {e}"
        print(f"Sheets Error: {msg}")
        return False, msg
    except GoogleAuthError as e:
        msg = f"Ошибка авторизации Google (Credentials): {e}"
        print(f"Sheets Error: {msg}")
        return False, msg
    except ValueError as e:
        msg = f"Ошибка конфигурации: {e}"
        print(f"Sheets Error: {msg}")
        return False, msg
    except Exception as e:
        msg = f"Неизвестная ошибка: {e}"
        print(f"Sheets Error: {msg}")
        import traceback
        traceback.print_exc()
        return False, msg
''')
print("Done appending")
