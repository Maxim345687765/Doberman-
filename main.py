import logging
import os
import aiosqlite

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("8717308248:AAFXVNrIyWud2ikQIUteoCYp7blOAKemWSU")

MASTERS = [803343644]  # добавь ID мастеров

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DB = "orders.db"


# ---------------- DB ----------------
async def init_db():
    async with aiosqlite.connect(DB) as db:
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


# ---------------- CREATE ORDER ----------------
@dp.message_handler(commands=['new'])
async def new_order(message: types.Message):
    try:
        _, desc, addr = message.text.split("|")
    except:
        await message.reply("Формат: /new услуга|адрес")
        return

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "INSERT INTO orders (description, address, status) VALUES (?, ?, ?)",
            (desc, addr, "new")
        )
        order_id = cur.lastrowid
        await db.commit()

    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🚕 Взять заказ", callback_data=f"take_{order_id}")
    )

    text = f"🔥 Заказ #{order_id}\n{desc}\n📍 {addr}"

    for m in MASTERS:
        await bot.send_message(m, text, reply_markup=kb)


# ---------------- TAKE ORDER ----------------
@dp.callback_query_handler(lambda c: c.data.startswith("take_"))
async def take(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT status FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()

        if not row or row[0] != "new":
            await callback.answer("Уже взят", show_alert=True)
            return

        await db.execute(
            "UPDATE orders SET status='taken', master_id=? WHERE id=?",
            (callback.from_user.id, order_id)
        )
        await db.commit()

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📍 Еду", callback_data=f"onway_{order_id}"),
        InlineKeyboardButton("🏁 Завершить", callback_data=f"done_{order_id}")
    )

    await callback.message.answer("✅ Заказ твой")
    await callback.answer()


# ---------------- ON WAY ----------------
@dp.callback_query_handler(lambda c: c.data.startswith("onway_"))
async def onway(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE orders SET status='on_way' WHERE id=?",
            (order_id,)
        )
        await db.commit()

    await callback.message.answer("🚕 Ты в пути")
    await callback.answer()


# ---------------- DONE ----------------
@dp.callback_query_handler(lambda c: c.data.startswith("done_"))
async def done(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])

    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE orders SET status='done' WHERE id=?",
            (order_id,)
        )
        await db.commit()

    await callback.message.answer("🏁 Заказ завершён")
    await callback.answer()


# ---------------- START ----------------
async def on_startup(dp):
    await init_db()
    print("BOT STARTED")


if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup)