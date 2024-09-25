import asyncio
import requests
from dadata import Dadata
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Токен бота и API DaData
from config import BOT_TOKEN, DADATA_API_KEY
DADATA_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/postal_unit"

dadata = Dadata(DADATA_API_KEY)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# FSM состояния для получения данных от пользователя
class AddressForm(StatesGroup):
    waiting_for_address = State()
    waiting_for_coordinates = State()

@dp.message(Command('help'))
async def help(message: Message):
   await message.answer('Этот бот умеет выполнять команды: \n /start \n /location')

# Хендлер для команды /start
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await message.answer(
        "Привет! Я найду адрес почтового отделения по индексу или координатам в формате: широта, долгота (команда /location)")
    await state.set_state(AddressForm.waiting_for_address)


# Хендлер для команды /location
@dp.message(Command("location"))
async def cmd_location(message: Message, state: FSMContext):
    await message.answer("Введите координаты в формате: широта, долгота.")
    await state.set_state(AddressForm.waiting_for_coordinates)


# Хендлер для получения адреса
@dp.message(AddressForm.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    user_input = message.text
    postal_info = await get_postal_unit_by_address(user_input)

    if postal_info:
        await message.answer(f"Ближайшее почтовое отделение:\n"
                             f"Адрес: {postal_info['address']}\n"
                             f"Индекс: {postal_info['postal_code']}\n"
                             f"Название: {postal_info['name']}")
    else:
        await message.answer("Не удалось найти почтовое отделение по данному запросу. Попробуйте снова.")

    await state.clear()


# Хендлер для получения координат
@dp.message(AddressForm.waiting_for_coordinates)
async def process_coordinates(message: Message, state: FSMContext):
    try:
        # Разделяем ввод пользователя на широту и долготу
        lat, lon = map(float, message.text.split(","))
        postal_info = await get_postal_unit_by_coordinates(lat, lon)

        if postal_info:
            await message.answer(f"Ближайшее почтовое отделение по координатам:\n"
                                 f"Адрес: {postal_info['address']}\n"
                                 f"Индекс: {postal_info['postal_code']}\n"
                                 f"Название: {postal_info['name']}")
        else:
            await message.answer("Не удалось найти почтовое отделение по данным координатам.")

    except ValueError:
        await message.answer("Пожалуйста, введите корректные координаты в формате: широта, долгота.")

    await state.clear()


# Функция для получения данных о ближайшем почтовом отделении по адресу через DaData
async def get_postal_unit_by_address(address: str) -> dict:
    result = dadata.suggest("postal_unit", address)

    if result:
        postal_data = result[0]['data']
        return {
            "address": postal_data.get('address_str', 'Неизвестно'),
            "postal_code": postal_data.get('postal_code', 'Неизвестно'),
            "name": postal_data.get('name', 'Неизвестно')
        }
    return None


# Функция для получения данных о ближайшем почтовом отделении по координатам через DaData
async def get_postal_unit_by_coordinates(lat: float, lon: float, radius_meters: int = 1000) -> dict:
    headers = {
        "Authorization": f"Token {DADATA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    data = {
        "lat": lat,
        "lon": lon,
        "radius_meters": radius_meters
    }

    # Отправляем запрос в API DaData
    response = requests.post("https://suggestions.dadata.ru/suggestions/api/4_1/rs/geolocate/postal_unit",
                             json=data, headers=headers)

    if response.status_code == 200:
        result = response.json().get('suggestions', [])
        if result:
            postal_data = result[0]['data']
            return {
                "address": postal_data.get('address_str', 'Неизвестно'),
                "postal_code": postal_data.get('postal_code', 'Неизвестно'),
                "name": postal_data.get('name', 'Неизвестно')
            }
    return None


# Функция для запуска бота
async def main():
        await dp.start_polling(bot)


if __name__ == '__main__':
        asyncio.run(main())
