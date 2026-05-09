import logging
import os
import sqlite3
from contextlib import closing

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# =========================================================
# НАСТРОЙКИ
# =========================================================

TOKEN = "8717308248:AAGgsU2W2jNPYrYAeGDySVCYMw0-CmSpf98"

# ID мастеров
MASTERS = [
    803343644,
]

DB_NAME = "orders.db"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# =========================================================
# БАЗА ДАННЫХ
# =========================================================

def init_db():
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                description TEXT,
                address TEXT,
                status TEXT,
                master_id INTEGER
            )
            """)

# =========================================================
# КНОПКИ
# =========================================================

def take_order_keyboard(order_id):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(
            "🚕 Взять заказ",
            callback_data=f"take_{order_id}"
        )
    )
    return kb


def active_order_keyboard(order_id):
    kb = InlineKeyboardMarkup(row_width=2)

    kb.add(
        InlineKeyboardButton(
            "🚗 Еду",
            callback_data=f"onway_{order_id}"
        ),
        InlineKeyboardButton(
            "📍 На месте",
            callback_data=f"arrived_{order_id}"
        )
    )

    kb.add(
        InlineKeyboardButton(
            "🏁 Завершить",
            callback_data=f"done_{order_id}"
        )
    )

    return kb

# =========================================================
# СОЗДАНИЕ ЗАКАЗА
# =========================================================

@dp.message_handler(commands=["new"])
async def create_order(message: types.Message):

    """
    Формат:
    /new Описание|Адрес
    """

    try:
        data = message.text.replace("/new ", "", 1)

        description, address = data.split("|")

        description = description.strip()
        address = address.strip()

    except Exception:
        await message.reply(
            "❌ Неверный формат\n\n"
            "Пример:\n"
            "/new Починить кран|Ленина 15"
        )
        return

    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            cursor = conn.execute("""
            INSERT INTO orders (
                client_id,
                description,
                address,
                status
            )
            VALUES (?, ?, ?, ?)
            """, (
                message.from_user.id,
                description,
                address,
                "new"
            ))

            order_id = cursor.lastrowid

    text = (
        f"🔥 Новый заказ #{order_id}\n\n"
        f"🛠 Услуга: {description}\n"
        f"📍 Адрес: {address}"
    )

    for master_id in MASTERS:
        try:
            await bot.send_message(
                master_id,
                text,
                reply_markup=take_order_keyboard(order_id)
            )
        except Exception as e:
            logging.error(f"Ошибка отправки мастеру: {e}")

    await message.reply("✅ Заказ создан и отправлен мастерам")

# =========================================================
# ВЗЯТЬ ЗАКАЗ
# =========================================================

@dp.callback_query_handler(lambda c: c.data.startswith("take_"))
async def take_order(callback: types.CallbackQuery):

    order_id = int(callback.data.split("_")[1])

    with closing(sqlite3.connect(DB_NAME)) as conn:

        cursor = conn.execute("""
        SELECT status
        FROM orders
        WHERE id = ?
        """, (order_id,))

        order = cursor.fetchone()

        if not order:
            await callback.answer(
                "❌ Заказ не найден",
                show_alert=True
            )
            return

        if order[0] != "new":
            await callback.answer(
                "⚠️ Заказ уже взят",
                show_alert=True
            )
            return

        with conn:
            conn.execute("""
            UPDATE orders
            SET status = ?, master_id = ?
            WHERE id = ?
            """, (
                "taken",
                callback.from_user.id,
                order_id
            ))

    await callback.message.answer(
        f"✅ Ты взял заказ #{order_id}",
        reply_markup=active_order_keyboard(order_id)
    )

    await callback.answer()

# =========================================================
# ЕДУ
# =========================================================

@dp.callback_query_handler(lambda c: c.data.startswith("onway_"))
async def on_way(callback: types.CallbackQuery):

    order_id = int(callback.data.split("_")[1])

    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("""
            UPDATE orders
            SET status = ?
            WHERE id = ?
            """, (
                "on_way",
                order_id
            ))

    await callback.answer("🚗 Статус: еду")
    await callback.message.answer(
        f"🚗 Ты выехал на заказ #{order_id}"
    )

# =========================================================
# НА МЕСТЕ
# =========================================================

@dp.callback_query_handler(lambda c: c.data.startswith("arrived_"))
async def arrived(callback: types.CallbackQuery):

    order_id = int(callback.data.split("_")[1])

    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("""
            UPDATE orders
            SET status = ?
            WHERE id = ?
            """, (
                "arrived",
                order_id
            ))

    await callback.answer("📍 Ты на месте")
    await callback.message.answer(
        f"📍 Ты прибыл на заказ #{order_id}"
    )

# =========================================================
# ЗАВЕРШИТЬ
# =========================================================

@dp.callback_query_handler(lambda c: c.data.startswith("done_"))
async def complete_order(callback: types.CallbackQuery):

    order_id = int(callback.data.split("_")[1])

    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("""
            UPDATE orders
            SET status = ?
            WHERE id = ?
            """, (
                "done",
                order_id
            ))

    await callback.answer("🏁 Заказ завершён")

    await callback.message.answer(
        f"🏁 Заказ #{order_id} завершён"
    )

# =========================================================
# СТАРТ
# =========================================================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):

    text = (
        "👋 Добро пожаловать в систему заказов Doberman\n\n"
        "Для создания заказа используй:\n"
        "/new услуга|адрес"
    )

    await message.answer(text)

# =========================================================
# ЗАПУСК
# =========================================================

async def on_startup(_):
    init_db()
    logging.info("BOT STARTED")


if __name__ == "__main__":
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup
    )