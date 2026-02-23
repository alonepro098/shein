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
BOT_TOKEN = "8061483201:AAExBhXJhj2LEmAWwG_kJAaiX8a38v4P_VU"

OWNER_ID = 5311223486

CHANNEL_1 = "@tmm_bots"          # FrozenTools
CHANNEL_2 = "@tmm_bots"  # Giveaway (REPLACE)

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
    join_date TEXT
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
        "INSERT OR IGNORE INTO users VALUES (?, ?, 0, 0, ?)",
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
# /START
# ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_new = get_user(user.id) is None

    add_user(user.id, user.username or "None")

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
            InlineKeyboardButton("1️⃣ FrozenTools", url="https://t.me/jsks"),
            InlineKeyboardButton("2️⃣ Giveaway", url="https://t.me/js;₹js"),
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

    joined_1 = await check_join(update, context, CHANNEL_1)
    joined_2 = await check_join(update, context, CHANNEL_2)

    if not (joined_1 and joined_2):
        await query.message.reply_text(
            "❗ Please Join our channel then tap on Joined ✅"
        )
        return

    keyboard = ReplyKeyboardMarkup(
        [
            ["👤 Profile", "🎁 Refer & Earn"],
            ["🎟 Withdraw Voucher", "💰 Balance"]
        ],
        resize_keyboard=True
    )

    await query.message.reply_text(
        "✅ Access Granted!",
        reply_markup=keyboard
    )

# ========================
# PROFILE
# ========================
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)

    await update.message.reply_text(
        f"👤 Profile Details\n\n"
        f"ID: {user[0]}\n"
        f"User: @{user[1]}\n"
        f"Total Referrals: {user[3]}\n"
        f"Join Date: {user[4]}"
    )

# ========================
# REFER & EARN
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
    user = get_user(update.effective_user.id)

    if user[2] < 2:
        await update.message.reply_text(
            "❌ Insufficient Points!\n"
            "You need at least 2 points to withdraw."
        )
        return

    coupon = generate_coupon()

    cur.execute(
        "UPDATE users SET points = points - 2 WHERE user_id=?",
        (user[0],)
    )
    conn.commit()

    await update.message.reply_text(
        "🎉 Withdrawal Successful!\n\n"
        "Amount: ₹500\n\n"
        f"Code: `{coupon}`\n\n"
        "Use this on the SHEIN checkout page.",
        parse_mode="Markdown"
    )

# ========================
# BALANCE
# ========================
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)

    await update.message.reply_text(
        "💳 Your Wallet\n\n"
        f"Points balance: {user[2]}\n\n"
        "• 2 Pts → ₹500\n"
        "• 5 Pts → ₹1000\n"
        "• 10 Pts → ₹2000"
    )

# ========================
# BROADCAST (OWNER ONLY)
# ========================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "❗ Usage:\n/broadcast Your message here"
        )
        return

    message = " ".join(context.args)

    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()

    sent = 0
    for uid in users:
        try:
            await context.bot.send_message(uid[0], message)
            sent += 1
        except:
            pass

    await update.message.reply_text(f"✅ Broadcast sent to {sent} users.")

# ========================
# MAIN
# ========================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CallbackQueryHandler(joined_check, pattern="joined_check"))

app.add_handler(MessageHandler(filters.Regex("^👤 Profile$"), profile))
app.add_handler(MessageHandler(filters.Regex("^🎁 Refer & Earn$"), refer))
app.add_handler(MessageHandler(filters.Regex("^🎟 Withdraw Voucher$"), withdraw))
app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))

app.run_polling()
