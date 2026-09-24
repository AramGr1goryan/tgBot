import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

ALFACRM_EMAIL = os.getenv("ALFACRM_EMAIL")
ALFACRM_API_KEY = os.getenv("ALFACRM_API_KEY")

async def get_token(client):
    resp = await client.post(
        "https://robixlab.s20.online/v2api/auth/login",
        json={"email": ALFACRM_EMAIL, "api_key": ALFACRM_API_KEY}
    )
    return resp.json().get("token")

async def test_search_customer(client, token, phone):
    headers = {"X-ALFACRM-TOKEN": token, "Content-Type": "application/json"}
    # The API might accept 'phone' in the payload
    print(f"--- Searching customer by phone: {phone} ---")
    resp = await client.post(
        "https://robixlab.s20.online/v2api/1/customer/index",
        headers=headers,
        json={"phone": phone, "is_study": [0, 1]}
    )
    data = resp.json()
    items = data.get("items", [])
    print(f"Found {len(items)} items")
    if items:
        print(f"First match: ID={items[0].get('id')}, Name={items[0].get('name')}, Phone={items[0].get('phone')}")

async def test_search_lesson(client, token):
    headers = {"X-ALFACRM-TOKEN": token, "Content-Type": "application/json"}
    print(f"--- Searching lesson ---")
    resp = await client.post(
        "https://robixlab.s20.online/v2api/1/lesson/index",
        headers=headers,
        json={
            "lesson_type_id": 9,
            "group_id": [23, 24],
            "location_id": 5,
            "date_from": "21.09.2026",
            "date_to": "21.09.2026"
        }
    )
    data = resp.json()
    items = data.get("items", [])
    print(f"Found {len(items)} lessons")
    for item in items:
        print(f"Lesson ID: {item.get('id')}, Group: {item.get('group_id')}, Time: {item.get('time_from')}, Details: {len(item.get('details', []))} participants")
        # Print first detail if exists
        if item.get('details'):
            print(f"  First participant: {item['details'][0]}")

async def main():
    async with httpx.AsyncClient() as client:
        token = await get_token(client)
        if not token:
            print("Auth failed")
            return
            
        print("Got token")
        
        # Test exact match
        await test_search_customer(client, token, "98024082")
        await test_search_customer(client, token, "+37498024082")
        await test_search_customer(client, token, "+374-98-024-082")
        await test_search_customer(client, token, "098024082")
        
        await test_search_lesson(client, token)

if __name__ == "__main__":
    asyncio.run(main())
