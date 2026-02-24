import sqlite3
import random
import string
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ========================
# CONFIG
# ========================
BOT_TOKEN = "YOUR_NEW_TOKEN_HERE"

OWNER_ID = 5311223486

CHANNEL_1 = "@tmm_bots"
CHANNEL_2 = "@tmm_bots"

# ========================
# DATABASE
# ========================
conn = sqlite3.connect("users.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    points INTEGER DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    join_date TEXT,
    referred_by INTEGER
)
""")
conn.commit()

# ========================
# HELPERS
# ========================
def get_user(user_id):
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cur.fetchone()

def add_user(user_id, username):
    join_date = datetime.now().strftime("%Y-%m-%d")
    cur.execute(
        """INSERT OR IGNORE INTO users
        (user_id, username, points, referrals, join_date, referred_by)
        VALUES (?, ?, 0, 0, ?, NULL)""",
        (user_id, username, join_date)
    )
    conn.commit()

def generate_coupon():
    chars = string.ascii_uppercase + string.digits
    return "SVC" + "".join(random.choices(chars, k=12))

async def check_join(update, context, channel):
    try:
        member = await context.bot.get_chat_member(channel, update.effective_user.id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ========================
# /START + REFERRAL + NOTIFICATIONS
# ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or "None"

    existing_user = get_user(user_id)
    is_new = existing_user is None

    add_user(user_id, username)

    # ---------- REFERRAL LOGIC ----------
    if is_new and context.args:
        try:
            referrer_id = int(context.args[0])

            if referrer_id != user_id:
                cur.execute("SELECT referred_by FROM users WHERE user_id=?", (user_id,))
                already = cur.fetchone()[0]

                if already is None:
                    # Save referral
                    cur.execute(
                        "UPDATE users SET referred_by=? WHERE user_id=?",
                        (referrer_id, user_id)
                    )
                    cur.execute(
                        "UPDATE users SET points = points + 1, referrals = referrals + 1 WHERE user_id=?",
                        (referrer_id,)
                    )
                    conn.commit()

                    # Notify referrer
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=
                        "🎉 New Referral Joined!\n\n"
                        f"User ID: {user_id}\n"
                        "You earned +1 point."
                    )

                    # Notify new user
                    await update.message.reply_text(
                        "✅ Referral Applied!\n\n"
                        f"You were referred by User ID: {referrer_id}"
                    )
        except:
            pass

    # ---------- OWNER NOTIFICATION ----------
    if is_new:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=
            "🆕 New User Started The Bot\n\n"
            f"Name: {user.full_name}\n"
            f"Username: @{user.username}\n"
            f"UserID: {user.id}"
        )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1️⃣ FrozenTools", url="https://t.me/FrozenTools"),
            InlineKeyboardButton("2️⃣ Giveaway", url="https://t.me/+-kOlLYQkVAI3YmU1"),
        ],
        [
            InlineKeyboardButton("Joined ✅", callback_data="joined_check")
        ]
    ])

    await update.message.reply_text(
        "👋 Welcome!\nTo continue, please join our channels.",
        reply_markup=keyboard
    )

# ========================
# JOIN CHECK
# ========================
async def joined_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not (await check_join(update, context, CHANNEL_1) and await check_join(update, context, CHANNEL_2)):
        await query.message.reply_text("❗ Please Join our channel then tap on Joined ✅")
        return

    keyboard = ReplyKeyboardMarkup(
        [["👤 Profile", "🎁 Refer & Earn"],
         ["🎟 Withdraw Voucher", "💰 Balance"]],
        resize_keyboard=True
    )

    await query.message.reply_text("✅ Access Granted!", reply_markup=keyboard)

# ========================
# PROFILE
# ========================
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    await update.message.reply_text(
        f"👤 Profile Details\n\n"
        f"ID: {u[0]}\n"
        f"User: @{u[1]}\n"
        f"Total Referrals: {u[3]}\n"
        f"Join Date: {u[4]}"
    )

# ========================
# REFER
# ========================
async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = f"https://t.me/{context.bot.username}?start={update.effective_user.id}"
    await update.message.reply_text(
        "🎁 Referral Program\n\n"
        "Earn 1 Point for every friend who joins!\n\n"
        f"🔗 Your Link:\n{link}"
    )

# ========================
# WITHDRAW
# ========================
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    if u[2] < 2:
        await update.message.reply_text("❌ Insufficient Points!\nYou need at least 2 points to withdraw.")
        return

    code = generate_coupon()
    cur.execute("UPDATE users SET points = points - 2 WHERE user_id=?", (u[0],))
    conn.commit()

    await update.message.reply_text(
        f"🎉 Withdrawal Successful!\n\n"
        f"Amount: ₹500\n\n"
        f"Code: `{code}`\n\n"
        "Use this on the SHEIN checkout page.",
        parse_mode="Markdown"
    )

# ========================
# BALANCE
# ========================
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    await update.message.reply_text(
        f"💳 Your Wallet\n\nPoints balance: {u[2]}\n\n"
        "• 2 Pts → ₹500\n"
        "• 5 Pts → ₹1000\n"
        "• 10 Pts → ₹2000"
    )

# ========================
# OWNER ADD / DEDUCT
# ========================
async def add_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    try:
        pts, uid = int(context.args[0]), int(context.args[1])
        cur.execute("UPDATE users SET points = points + ? WHERE user_id=?", (pts, uid))
        conn.commit()
        await update.message.reply_text(f"✅ Added {pts} points to User ID {uid}")
    except:
        await update.message.reply_text("❗ Usage: /add {points} {userid}")

async def deduct_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    try:
        pts, uid = int(context.args[0]), int(context.args[1])
        cur.execute("UPDATE users SET points = MAX(points - ?, 0) WHERE user_id=?", (pts, uid))
        conn.commit()
        await update.message.reply_text(f"✅ Deducted {pts} points from User ID {uid}")
    except:
        await update.message.reply_text("❗ Usage: /deduct {points} {userid}")

# ========================
# BROADCAST
# ========================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if not context.args:
        await update.message.reply_text("❗ Usage:\n/broadcast Your message here")
        return

    message = " ".join(context.args)
    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()

    sent = 0
    for u in users:
        try:
            await context.bot.send_message(u[0], message)
            sent += 1
        except:
            pass

    await update.message.reply_text(f"✅ Broadcast sent to {sent} users.")

# ========================
# MAIN
# ========================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add_points))
app.add_handler(CommandHandler("deduct", deduct_points))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CallbackQueryHandler(joined_check, pattern="joined_check"))

app.add_handler(MessageHandler(filters.Regex("^👤 Profile$"), profile))
app.add_handler(MessageHandler(filters.Regex("^🎁 Refer & Earn$"), refer))
app.add_handler(MessageHandler(filters.Regex("^🎟 Withdraw Voucher$"), withdraw))
app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))

app.run_polling()
