
import os
import random
import sqlite3
from datetime import date
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

TOKEN = os.environ["BOT_TOKEN"]
DB = "dark_temptation.db"

def setup():
    with sqlite3.connect(DB) as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY,
            name TEXT,
            coins INTEGER DEFAULT 100,
            daily TEXT DEFAULT '',
            games INTEGER DEFAULT 0
        )
        """)

def player(uid, name):
    with sqlite3.connect(DB) as c:
        c.execute(
            "INSERT OR IGNORE INTO players(id,name) VALUES(?,?)",
            (uid, name)
        )
        c.execute("UPDATE players SET name=? WHERE id=?", (name, uid))

def add_coins(uid, amount):
    with sqlite3.connect(DB) as c:
        c.execute(
            "UPDATE players SET coins=coins+? WHERE id=?",
            (amount, uid)
        )

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 بازی تاس", callback_data="dice"),
         InlineKeyboardButton("🔢 حدس عدد", callback_data="guess")],
        [InlineKeyboardButton("🎁 جایزه روزانه", callback_data="daily"),
         InlineKeyboardButton("👤 پروفایل", callback_data="profile")],
        [InlineKeyboardButton("🏆 رتبه‌بندی", callback_data="top")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    player(u.id, u.first_name)
    await update.effective_message.reply_text(
        "🖤 به بازی Dark Temptation خوش اومدی!\n"
        "🪙 موجودی اولیه: ۱۰۰ سکه مجازی\n"
        "از منوی زیر انتخاب کن:",
        reply_markup=menu()
    )

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    player(u.id, u.first_name)
    with sqlite3.connect(DB) as c:
        row = c.execute(
            "SELECT daily FROM players WHERE id=?", (u.id,)
        ).fetchone()
        if row[0] == date.today().isoformat():
            msg = "⏳ جایزه امروزت رو قبلاً گرفتی!"
        else:
            c.execute(
                "UPDATE players SET coins=coins+50,daily=? WHERE id=?",
                (date.today().isoformat(), u.id)
            )
            msg = "🎁 ۵۰ سکه مجازی دریافت کردی!"
    await update.effective_message.reply_text(msg)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    player(u.id, u.first_name)
    with sqlite3.connect(DB) as c:
        coins, games = c.execute(
            "SELECT coins,games FROM players WHERE id=?", (u.id,)
        ).fetchone()
    await update.effective_message.reply_text(
        f"👤 {u.first_name}\n🪙 سکه: {coins}\n🎮 بازی‌ها: {games}"
    )

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with sqlite3.connect(DB) as c:
        rows = c.execute(
            "SELECT name,coins FROM players ORDER BY coins DESC LIMIT 10"
        ).fetchall()
    text = "🏆 رتبه‌بندی Dark Temptation\n\n"
    text += "\n".join(
        f"{i}. {name}: {coins} 🪙"
        for i, (name, coins) in enumerate(rows, 1)
    ) or "هنوز بازیکنی ثبت نشده."
    await update.effective_message.reply_text(text)

async def gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if len(context.args) != 2 or not context.args[0].startswith("@"):
        await update.effective_message.reply_text(
            "روش استفاده:\n/gift @username 20"
        )
        return
    try:
        amount = int(context.args[1])
    except ValueError:
        amount = 0
    if amount < 1 or amount > 1000:
        await update.effective_message.reply_text(
            "مقدار هدیه باید بین ۱ تا ۱۰۰۰ سکه باشه."
        )
        return
    with sqlite3.connect(DB) as c:
        sender = c.execute(
            "SELECT coins FROM players WHERE id=?", (u.id,)
        ).fetchone()
        recipient = c.execute(
            "SELECT id FROM players WHERE lower(name)=lower(?)",
            (context.args[0][1:],)
        ).fetchone()
        if not sender or sender[0] < amount:
            msg = "سکه کافی نداری!"
        elif not recipient or recipient[0] == u.id:
            msg = "گیرنده باید قبلاً ربات رو شروع کرده باشه."
        else:
            c.execute("UPDATE players SET coins=coins-? WHERE id=?",
                      (amount, u.id))
            c.execute("UPDATE players SET coins=coins+? WHERE id=?",
                      (amount, recipient[0]))
            msg = f"🎁 {amount} سکه به {context.args[0]} هدیه شد!"
    await update.effective_message.reply_text(msg)

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = q.from_user
    player(u.id, u.first_name)

    if q.data == "daily":
        with sqlite3.connect(DB) as c:
            row = c.execute(
                "SELECT daily FROM players WHERE id=?", (u.id,)
            ).fetchone()
            if row[0] == date.today().isoformat():
                msg = "جایزه امروزت رو قبلاً گرفتی."
            else:
                c.execute(
                    "UPDATE players SET coins=coins+50,daily=? WHERE id=?",
                    (date.today().isoformat(), u.id)
                )
                msg = "🎁 ۵۰ سکه گرفتی!"
        await q.edit_message_text(msg, reply_markup=menu())

    elif q.data == "profile":
        with sqlite3.connect(DB) as c:
            coins, games = c.execute(
                "SELECT coins,games FROM players WHERE id=?", (u.id,)
            ).fetchone()
        await q.edit_message_text(
            f"👤 {u.first_name}\n🪙 سکه: {coins}\n🎮 بازی‌ها: {games}",
            reply_markup=menu()
        )

    elif q.data == "top":
        with sqlite3.connect(DB) as c:
            rows = c.execute(
                "SELECT name,coins FROM players ORDER BY coins DESC LIMIT 10"
            ).fetchall()
        msg = "🏆 رتبه‌بندی\n\n" + "\n".join(
            f"{i}. {n}: {v} 🪙"
            for i, (n, v) in enumerate(rows, 1)
        )
        await q.edit_message_text(msg, reply_markup=menu())

    elif q.data == "dice":
        result = await context.bot.send_dice(
            chat_id=q.message.chat_id, emoji="🎲"
        )
        value = result.dice.value
        reward = value * 5
        add_coins(u.id, reward)
        with sqlite3.connect(DB) as c:
            c.execute("UPDATE players SET games=games+1 WHERE id=?", (u.id,))
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text=f"🎲 {u.first_name} عدد {value} آورد و {reward} سکه جایزه گرفت!"
        )

    elif q.data == "guess":
        context.user_data["guess"] = random.randint(1, 5)
        await q.edit_message_text(
            "🔢 یه عدد بین ۱ تا ۵ حدس بزن:\n/guess 3",
            reply_markup=menu()
        )

async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    player(u.id, u.first_name)
    if not context.args or not context.args[0].isdigit():
        await update.effective_message.reply_text("مثال: /guess 3")
        return
    if "guess" not in context.user_data:
        context.user_data["guess"] = random.randint(1, 5)
    answer = context.user_data.pop("guess")
    try:
        n = int(context.args[0])
    except ValueError:
        n = 0
    if n == answer:
        add_coins(u.id, 25)
        msg = "درست حدس زدی! 🎉 ۲۵ سکه جایزه گرفتی."
    else:
        msg = f"عدد درست {answer} بود. دفعه بعد تلاش کن!"
    with sqlite3.connect(DB) as c:
        c.execute("UPDATE players SET games=games+1 WHERE id=?", (u.id,))
    await update.effective_message.reply_text(msg)

def main():
    setup()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("bazi", start))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("gift", gift))
    app.add_handler(CommandHandler("guess", guess))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling()

if __name__ == "__main__":
    main()
  
