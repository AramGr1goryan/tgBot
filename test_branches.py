import httpx, asyncio

async def main():
    async with httpx.AsyncClient() as client:
        resp = await client.post('https://robixlab.s20.online/v2api/auth/login', json={'email':'aramgrigoryan2k4@gmail.com', 'api_key':'70cc373b-bed2-11f0-bfab-3cecefbdd1ae'})
        token = resp.json()['token']
        headers = {'X-ALFACRM-TOKEN': token}
        b_resp = await client.post('https://robixlab.s20.online/v2api/branch/index', headers=headers)
        for b in b_resp.json().get('items', []):
            print(f"ID {b['id']}: {b['name']}")
        
asyncio.run(main())
