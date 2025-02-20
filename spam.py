import os
import json
import random
import datetime
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.markdown import html_decoration as hd
from bs4 import BeautifulSoup

# Конфигурация
BOT_TOKEN = "7243103974:AAH3YEuKRtQKOVRKaDqKD1c0f6mDi4zYK9I"
ADMIN_IDS = [78206270404]  # Замените на ваш ID администратора

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Состояния для FSM
class AdminStates(StatesGroup):
    WAITING_FOR_TOKENS = State()

# Данные пользователей
if os.path.exists("user_data.json"):
    with open("user_data.json", "r") as f:
        user_data = json.load(f)
        # Инициализация ключа "captcha_required", если его нет
        if "captcha_required" not in user_data:
            user_data["captcha_required"] = {}
else:
    user_data = {"balances": {}, "chat_contexts": {}, "gift_used": set(), "captcha_required": {}}

def save_data():
    with open("user_data.json", "w") as f:
        json.dump(user_data, f)

# Обновление баланса
def update_balance(user_id):
    today = datetime.date.today().isoformat()
    if user_id not in user_data["balances"]:
        user_data["balances"][user_id] = {"balance": 100000, "last_update": today}
    elif user_data["balances"][user_id]["last_update"] != today:
        user_data["balances"][user_id]["balance"] += 100000
        user_data["balances"][user_id]["last_update"] = today
    save_data()

# Основное меню
def get_main_keyboard(user_id):
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="🔄 Закончить беседу"))
    keyboard.add(KeyboardButton(text="🧹 Очистить историю сообщений"))
    keyboard.add(KeyboardButton(text="💰 Баланс"))
    if user_id in ADMIN_IDS:
        keyboard.add(KeyboardButton(text="[АДМИН ПАНЕЛЬ]"))
    return keyboard.as_markup(resize_keyboard=True)

# Админ-меню
def get_admin_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(KeyboardButton(text="Раздать токены"))
    keyboard.add(KeyboardButton(text="Назад"))
    return keyboard.as_markup(resize_keyboard=True)

# Генерация капчи
def generate_fruit_captcha():
    fruits = ["🍎", "🍌", "🍇", "🍊", "🍓", "🍉"]
    correct_fruit = random.choice(fruits)
    builder = InlineKeyboardBuilder()
    for fruit in fruits:
        builder.button(text=fruit, callback_data=fruit)
    builder.adjust(3)  # Устанавливаем 3 кнопки в ряд
    return correct_fruit, builder.as_markup()

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data["captcha_required"] or user_data["captcha_required"][user_id]:
        correct_fruit, keyboard = generate_fruit_captcha()
        user_data["captcha_required"][user_id] = {"correct_fruit": correct_fruit, "message_id": None}
        sent_message = await message.answer(f"Для начала работы с ботом нажмите на {correct_fruit}.", reply_markup=keyboard)
        user_data["captcha_required"][user_id]["message_id"] = sent_message.message_id
        return
    update_balance(user_id)
    if user_id not in user_data["chat_contexts"]:
        user_data["chat_contexts"][user_id] = [{"role": "system", "content": "Ты — помощник, который отвечает на вопросы. Используй только HTML-теги для форматирования. Для жирного текста используй <b>жирный текст</b>. Не используй **, ### или другие символы для форматирования. Не добавляй лишние символы, такие как `'` или `\"`, если они не являются частью текста."}]
    await message.answer("👋 Привет! Я ваш помощник GPT-4 🤖.", reply_markup=get_main_keyboard(user_id))

# Обработчик капчи
@dp.callback_query(F.data.in_({"🍎", "🍌", "🍇", "🍊", "🍓", "🍉"}))
async def handle_captcha(call: types.CallbackQuery):
    user_id = call.from_user.id
    if user_id in user_data["captcha_required"] and user_data["captcha_required"][user_id]:
        correct_fruit = user_data["captcha_required"][user_id]["correct_fruit"]
        if call.data == correct_fruit:
            await call.answer("Верно! Доступ к боту открыт. 😊", show_alert=True)
            await call.message.edit_text("Доступ к боту открыт! 🎉")
            user_data["captcha_required"][user_id] = False
            await cmd_start(call.message)
        else:
            await call.answer("Неверно! Попробуйте ещё раз. 😢", show_alert=True)
            correct_fruit, keyboard = generate_fruit_captcha()
            user_data["captcha_required"][user_id]["correct_fruit"] = correct_fruit
            await call.message.edit_text(f"Неверно! Попробуйте ещё раз. Нажмите на {correct_fruit}.", reply_markup=keyboard)

# Обработчик кнопки "💰 Баланс"
@dp.message(F.text == "💰 Баланс")
async def show_balance(message: types.Message):
    user_id = message.from_user.id
    update_balance(user_id)
    balance = user_data["balances"][user_id]["balance"]
    await message.answer(f"Ваш баланс: {balance:,} токенов 💰", reply_markup=get_main_keyboard(user_id))

# Обработчик кнопки "🧹 Очистить историю сообщений"
@dp.message(F.text == "🧹 Очистить историю сообщений")
async def clear_history(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_data["chat_contexts"]:
        user_data["chat_contexts"][user_id] = [{"role": "system", "content": "Ты — помощник, который отвечает на вопросы. Используй только HTML-теги для форматирования. Для жирного текста используй <b>жирный текст</b>. Не используй **, ### или другие символы для форматирования. Не добавляй лишние символы, такие как `'` или `\"`, если они не являются частью текста."}]
    await message.answer("История сообщений очищена. 🧹", reply_markup=get_main_keyboard(user_id))

# Обработчик кнопки "🔄 Закончить беседу"
@dp.message(F.text == "🔄 Закончить беседу")
async def end_chat(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_data["chat_contexts"]:
        user_data["chat_contexts"][user_id] = [{"role": "system", "content": "Ты — помощник, который отвечает на вопросы. Используй только HTML-теги для форматирования. Для жирного текста используй <b>жирный текст</b>. Не используй **, ### или другие символы для форматирования. Не добавляй лишние символы, такие как `'` или `\"`, если они не являются частью текста."}]
    await message.answer("Беседа завершена. Можете начать новую беседу, просто задав вопрос. 😊", reply_markup=get_main_keyboard(user_id))

# Обработчик кнопки "[АДМИН ПАНЕЛЬ]"
@dp.message(F.text == "[АДМИН ПАНЕЛЬ]")
async def admin_panel(message: types.Message):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        await message.answer("Меню:", reply_markup=get_admin_keyboard())

# Обработчик кнопки "Раздать токены"
@dp.message(F.text == "Раздать токены")
async def distribute_tokens(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        await message.answer("Введите количество токенов:")
        await state.set_state(AdminStates.WAITING_FOR_TOKENS)

# Обработчик ввода количества токенов
@dp.message(AdminStates.WAITING_FOR_TOKENS)
async def process_tokens(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        if message.text.isdigit():
            tokens = int(message.text)
            for user in user_data["balances"]:
                user_data["balances"][user]["balance"] += tokens
            save_data()
            await message.answer(f"Каждому пользователю начислено {tokens} токенов.", reply_markup=get_admin_keyboard())
        else:
            await message.answer("Некорректный ввод. Введите число.", reply_markup=get_admin_keyboard())
        await state.clear()

# Обработчик кнопки "Назад"
@dp.message(F.text == "Назад")
async def back_to_admin_menu(message: types.Message):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        await message.answer("Меню:", reply_markup=get_admin_keyboard())

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен!")
    dp.run_polling(bot)