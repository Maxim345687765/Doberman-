import asyncio
import logging
import aiosqlite

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

TOKEN = "8717308248:AAFXVNrIyWud2ikQIUteoCYp7blOAKemWSU"

# ID чатов мастеров (вставь сюда)
MASTERS = [803343644]

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DB_NAME = "orders.db"


# --- База данных ---
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            address TEXT,
            status TEXT,
            master_id INTEGER
        )
        """)
        await db.commit()


# --- Создание заказа ---
@dp.message_handler(commands=['new'])
async def create_order(message: types.Message):
    try:
        _, description, address = message.text.split("|")
    except:
        await message.reply("Формат: /new описание|адрес")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO orders (description, address, status) VALUES (?, ?, ?)",
            (description, address, "new")
        )
        order_id = cursor.lastrowid
        await db.commit()

    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Взять заказ", callback_data=f"take_{order_id}")
    )

    text = f"🔥 Новый заказ #{order_id}\n{description}\n📍 {address}"

    for master in MASTERS:
        await bot.send_message(master, text, reply_markup=keyboard)

    await message.reply("Заявка отправлена мастерам")


# --- Взять заказ ---
@dp.callback_query_handler(lambda c: c.data.startswith("take_"))
async def take_order(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT status FROM orders WHERE id=?",
            (order_id,)
        )
        row = await cursor.fetchone()

        if not row or row[0] != "new":
            await callback.answer("Заказ уже взят", show_alert=True)
            return

        await db.execute(
            "UPDATE orders SET status=?, master_id=? WHERE id=?",
            ("taken", callback.from_user.id, order_id)
        )
        await db.commit()

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Я на месте", callback_data=f"arrived_{order_id}"),
        InlineKeyboardButton("Завершить", callback_data=f"done_{order_id}")
    )

    await callback.message.answer(f"✅ Ты взял заказ #{order_id}", reply_markup=keyboard)
    await callback.answer()


# --- Я на месте ---
@dp.callback_query_handler(lambda c: c.data.startswith("arrived_"))
async def arrived(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE orders SET status=? WHERE id=?",
            ("in_progress", order_id)
        )
        await db.commit()

    await callback.message.answer(f"📍 Заказ #{order_id}: ты на месте")
    await callback.answer()


# --- Завершить ---
@dp.callback_query_handler(lambda c: c.data.startswith("done_"))
async def done(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE orders SET status=? WHERE id=?",
            ("done", order_id)
        )
        await db.commit()

    await callback.message.answer(f"🏁 Заказ #{order_id} завершён")
    await callback.answer()


# --- Запуск ---
async def on_startup(dp):
    await init_db()
    print("Бот запущен")

if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup)