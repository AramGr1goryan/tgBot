from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from transliterate import translit
import os

# Получаем токен из переменных окружения Vercel
API_TOKEN = os.getenv("BOT_TOKEN")

# Инициализируем бота и диспетчер (только если токен установлен)
bot = Bot(token=API_TOKEN) if API_TOKEN else None
dp = Dispatcher()
app = FastAPI()

PAYMENT_METHODS = {
    'n': 'Наличка',
    'b.n': 'На терминал',
    'c': 'На карту',
    'с': 'На карту'
}

def transliterate_name(text: str) -> str:
    text = text.replace('yan', 'ян').replace('Yan', 'Ян')
    text = text.replace('ya', 'я').replace('Ya', 'Я')
    try:
        return translit(text, 'ru')
    except Exception:
        return text

@dp.message()
async def process_payment(message: types.Message):
    if not message.text:
        return
        
    text = message.text.strip()
    if text.startswith('/start'):
        await message.answer("Привет! Отправь мне сообщение в формате:\nName Surname Payment_sum Payment_Method")
        return

    if text.startswith('/help'):
        await message.answer(
            "Как правильно писать сообщения:\n\n"
            "Формат: Имя Фамилия Сумма Метод\n\n"
            "Пример: Aram Grigoryan 50000 N\n\n"
            "Доступные методы оплаты:\n"
            "N — Наличной\n"
            "b.n — На терминал\n"
            "c — На карту"
        )
        return

    parts = text.split()
    if len(parts) < 4:
        await message.answer("Неверный формат.\nПожалуйста, используйте формат: Name Surname Payment_sum Payment_Method")
        return

    payment_method_raw = parts[-1].lower()
    payment_sum = parts[-2]
    name_english = " ".join(parts[:-2])
    
    name_russian = transliterate_name(name_english)
    payment_method = PAYMENT_METHODS.get(payment_method_raw, payment_method_raw)
    
    response = f"G.N | {name_russian} | {payment_sum} | {payment_method}"
    await message.answer(response)

@app.post("/api/webhook")
async def webhook(request: Request):
    if not bot:
        return {"error": "BOT_TOKEN is not set"}
        
    update_data = await request.json()
    update = types.Update(**update_data)
    
    # Передаем апдейт в aiogram
    await dp.feed_update(bot, update)
    return {"status": "ok"}
