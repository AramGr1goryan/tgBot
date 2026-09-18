import os
import json
import gspread_asyncio
from google.oauth2.service_account import Credentials
from datetime import datetime

def get_creds():
    creds_json_str = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json_str:
        raise ValueError("GOOGLE_CREDENTIALS env var is missing or empty")
        
    # Some platforms escape newlines in JSON env vars
    # And some pass literal newlines which breaks strict JSON parsing
    creds_json_str = creds_json_str.replace('\\n', '\n')
    creds_dict = json.loads(creds_json_str, strict=False)
    
    # Ensure private_key has proper newlines for Google Auth
    if 'private_key' in creds_dict:
        creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
        
    creds = Credentials.from_service_account_info(creds_dict)
    scoped = creds.with_scopes([
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ])
    return scoped

agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)

async def append_payment_to_sheet(date_str: str, student_name: str, amount: int, method_raw: str):
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
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
            
        cash_income = amount if method_raw == 'n' else ""
        cashless_income = amount if method_raw in ['b.n', 'c'] else ""
        
        # Format:
        # A: ""
        # B: Month
        # C: Date
        # D: Приход
        # E: Student Name
        # F: Cash Income (Наличные)
        # G: Cash Expense (empty)
        # H: Сальдо (empty, usually auto-calculated)
        # I: Cashless Income (Безналичные)
        # J: Cashless Expense (empty)
        
        row_data = [
            "",               # A
            month,            # B
            date_str,         # C
            "Приход",         # D
            student_name,     # E
            cash_income,      # F
            "",               # G
            "",               # H
            cashless_income   # I
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
        
        await worksheet.update(
            values=[row_data],
            range_name=f"A{next_row}:I{next_row}",
            value_input_option='USER_ENTERED'
        )
        return True, f"Success (row {next_row})"
    except Exception as e:
        print(f"Error appending to Google Sheets: {e}")
        return False, str(e)
