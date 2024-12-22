import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import os
from dotenv import load_dotenv
import requests
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from requests.exceptions import RequestException

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEB_SERVICE_URL = "http://127.0.0.1:5000/weather"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

router = Router()
dp.include_router(router)

class WeatherState(StatesGroup):
    start_city = State()
    end_city = State()
    waypoints = State()
    days = State()

@router.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("Привет! Я бот для получения прогноза погоды по маршруту. Используй /weather для начала.")

@router.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer("Я бот, который покажет вам погоду на вашем маршруте. Начните с /weather")

@router.message(Command("weather"))
async def weather_command(message: types.Message, state: FSMContext):
    await message.answer("Введите начальную точку маршрута:")
    await state.set_state(WeatherState.start_city)

@router.message(WeatherState.start_city, F.text)
async def process_start_city(message: types.Message, state: FSMContext):
    await state.update_data(start_city=message.text)
    await message.answer("Теперь введите конечную точку:")
    await state.set_state(WeatherState.end_city)

@router.message(WeatherState.end_city, F.text)
async def process_end_city(message: types.Message, state: FSMContext):
    await state.update_data(end_city=message.text)
    await message.answer("Введите промежуточные точки (через запятую) или пропустите этот шаг, нажав /skip:")
    await state.set_state(WeatherState.waypoints)

@router.message(Command("skip"), WeatherState.waypoints)
async def skip_waypoints(message: types.Message, state: FSMContext):
    await state.update_data(waypoints=[])
    await message.answer("Выберите период для прогноза погоды", reply_markup=days_keyboard())
    await state.set_state(WeatherState.days)

@router.message(WeatherState.waypoints, F.text)
async def process_waypoints(message: types.Message, state: FSMContext):
     await state.update_data(waypoints=message.text.split(','))
     await message.answer("Выберите период для прогноза погоды", reply_markup=days_keyboard())
     await state.set_state(WeatherState.days)
    
def days_keyboard():
  keyboard = InlineKeyboardMarkup(inline_keyboard=[
      [
          InlineKeyboardButton(text='2 дня', callback_data='2'),
          InlineKeyboardButton(text='3 дня', callback_data='3'),
          InlineKeyboardButton(text='5 дней', callback_data='5')
      ]
  ])

  return keyboard

@router.callback_query(WeatherState.days, F.data.in_(['2', '3','5']))
async def process_days(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(days=callback.data)
    data = await state.get_data()
        
    start_city = data['start_city']
    end_city = data['end_city']
    waypoints = ",".join(data['waypoints']) if data.get('waypoints') else ""
    days = data['days']
    
    params = {
      "start_city":start_city,
      "end_city":end_city,
      "waypoints":waypoints,
      "days":days
    }
    try:
        response = requests.post(WEB_SERVICE_URL, data=params)
        response.raise_for_status()
        if response.status_code == 200:
            await callback.message.answer(f"Погода доступна по ссылке: http://127.0.0.1:5000/dashboard/")
        else:
            await callback.message.answer("Не удалось получить данные от веб сервиса.")

    except RequestException as e:
        logging.error(f"Error during request to web service: {e}")
        await callback.message.answer("Произошла ошибка при обращении к сервису, попробуйте позже.")
    
    await state.set_state(None)

async def main():
    await dp.start_polling(bot, skip_updates=True)
    

if __name__ == '__main__':
    asyncio.run(main())