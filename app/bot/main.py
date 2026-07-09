import asyncio
import httpx
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

TOKEN = ("8754910617:AAGSPRuWLajAElMcKwZvFcBhLYMU1WUWsB0")
API_URL = "http://127.0.0.1:8000/extract"

if not TOKEN:
    print("Ошибка: TELEGRAM_BOT_TOKEN не найден в переменных окружения")
    raise SystemExit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def handle_start(message: types.Message):
    await message.answer("Отправьте мне описание товара, и я извлеку параметры")

@dp.message()
async def handle_text(message: types.Message):
    if not message.text:
        return

    try:
        async with httpx.AsyncClient() as client:
            # Отправляем запрос на наш FastAPI сервер
            response = await client.post(API_URL, json={"text": message.text}, timeout=30.0)
            
            if response.status_code == 200:
                data = response.json()
                # Выводим тот самый отчет, который мы настраивали
                report = f"=== РЕЗУЛЬТАТ АНАЛИЗА ===\n\n{data.get('debug_info', '<нет данных>')}"
                await message.answer(report)
            else:
                await message.answer(f"Ошибка сервера: {response.status_code}")
                
    except Exception as e:
        await message.answer(f"Ошибка при связи с API: {str(e)}")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен пользователем")
