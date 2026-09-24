import asyncio, httpx

async def main():
    async with httpx.AsyncClient() as client:
        resp = await client.post('https://robixlab.s20.online/v2api/auth/login', json={'email':'aram.g.gn@gmail.com','api_key':'a10d9223-3db4-11ef-be7a-3cecef6687ac'})
        token = resp.json()['token']
        headers = {'X-ALFACRM-TOKEN': token}
        payload = {
            'lesson_type_id': 3,
            'date': '2026-09-21',
            'time_from': '15:00',
            'time_to': '15:50',
            'subject_id': 23,
            'room_id': 34,
            'customer_ids': [2451], # Let's assume some customer ID exists
            'status': 1
        }
        resp = await client.post('https://robixlab.s20.online/v2api/1/lesson/create', headers=headers, json=payload)
        print(resp.status_code, resp.text)
        
        payload2 = payload.copy()
        payload2['date_from'] = '2026-09-21'
        payload2['date_to'] = '2026-09-21'
        resp2 = await client.post('https://robixlab.s20.online/v2api/1/lesson/create', headers=headers, json=payload2)
        print("With date_from/date_to:", resp2.status_code, resp2.text)

asyncio.run(main())
