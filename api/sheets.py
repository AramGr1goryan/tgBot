import os
import json
import gspread_asyncio
from google.oauth2.service_account import Credentials
from datetime import datetime

def get_creds():
    creds_json_str = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json_str:
        return None
        
    try:
        # Some platforms escape newlines in JSON env vars
        creds_json_str = creds_json_str.replace('\\n', '\n')
        creds_dict = json.loads(creds_json_str)
        creds = Credentials.from_service_account_info(creds_dict)
        scoped = creds.with_scopes([
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ])
        return scoped
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None

agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)

async def append_payment_to_sheet(date_str: str, student_name: str, amount: int, method_raw: str):
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    tab_name = os.environ.get("GOOGLE_SHEET_TAB_NAME", "Оплаты Манташяна")
    
    if not sheet_id or not os.environ.get("GOOGLE_CREDENTIALS"):
        print("Google Sheets credentials or sheet ID not configured.")
        return False, "Not configured"
        
    try:
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
        
        await worksheet.append_row(row_data, value_input_option='USER_ENTERED')
        return True, "Success"
    except Exception as e:
        print(f"Error appending to Google Sheets: {e}")
        return False, str(e)
