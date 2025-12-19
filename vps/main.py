# ================================================
# main.py - Premium VPS Seller Bot (Single File)
# FIXED & WORKING 100% - December 2025
# ================================================

import telebot
import sqlite3
import os
import time
import threading
import random
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import scrypt
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

# ===================== CONFIG =====================
BOT_TOKEN = "7913272382:AAGnvD29s4bu_jmsejNmT5eWbl7HZnGy_OM"           # Change
ADMIN_ID = 7618637244                        # Your Telegram ID

UPI_ID = "yourname@upi"                     # Your UPI ID
UPI_NAME = "Premium VPS"

PLANS = {
    "7d":  {"name": "7 Days Trial",    "price": 149,  "days": 7},
    "15d": {"name": "15 Days Pro",     "price": 349,  "days": 15},
    "30d": {"name": "30 Days Elite",   "price": 599,  "days": 30},
    "365d":{"name": "1 Year God Mode", "price": 9999, "days": 365}
}

# Folders
os.makedirs("payments", exist_ok=True)
os.makedirs("vps", exist_ok=True)
os.makedirs("images", exist_ok=True)

# ===================== ENCRYPTION =====================
KEY_FILE = "secret.key"
def get_key():
    if os.path.exists(KEY_FILE):
        return open(KEY_FILE, "rb").read()
    key = scrypt(b"vps2025_secure", get_random_bytes(16), 32, N=2**14, r=8, p=1)
    with open(KEY_FILE, "wb") as f: f.write(key)
    return key
KEY = get_key()

def encrypt(text): 
    cipher = AES.new(KEY, AES.MODE_CBC)
    ct = cipher.encrypt(pad(text.encode(), 16))
    return cipher.iv.hex() + ":" + ct.hex()

def decrypt(enc):
    try:
        iv, ct = [bytes.fromhex(x) for x in enc.split(":")]
        cipher = AES.new(KEY, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(ct), 16).decode()
    except: 
        return "ERROR"

# ===================== DATABASE =====================
DB = "vps_bot.db"
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, name TEXT, join_date TEXT, banned INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS vps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT, username TEXT, password_enc TEXT, pem_path TEXT,
            assigned_to INTEGER, expiry TEXT, status TEXT DEFAULT 'available'
        );
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY, user_id INTEGER, plan TEXT, amount INTEGER,
            status TEXT DEFAULT 'PENDING', proof_path TEXT, created_at TEXT
        );
    ''')
    conn.commit()
    conn.close()
init_db()

# ===================== BOT SETUP =====================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ===================== KEYBOARDS =====================
def main_menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("Buy VPS", "My VPS")
    m.add("Orders", "Plans", "Support")
    return m

def plans_kb():
    k = InlineKeyboardMarkup(row_width=1)
    for code, p in PLANS.items():
        k.add(InlineKeyboardButton(f"{p['name']} — ₹{p['price']}", callback_data=f"plan_{code}"))
    return k

# ===================== HELPERS =====================
def log(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, ?)", 
              (user_id, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

def generate_order_id():
    return f"ORD{datetime.now().strftime('%Y%m%d')}{random.randint(1000,9999)}"

def get_available_vps():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, ip, username, password_enc, pem_path FROM vps WHERE status='available' LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row

def assign_vps(vps_id, user_id, days):
    expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE vps SET assigned_to=?, expiry=?, status='assigned' WHERE id=?", (user_id, expiry, vps_id))
    conn.commit()
    conn.close()
    return expiry

def progress_animation(msg):
    bars = ["10%", "40%", "70%", "100% Done!"]
    for i, bar in enumerate(bars):
        try:
            bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id,
                text=f"<b>Activating your VPS...</b>\n\n<code>{'▓' * (i+1)*2 + '░' * (8-(i+1)*2)} {bar}</code>")
            time.sleep(2)
        except: pass
    bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id,
        text="VPS Activated! Details below")

# ===================== HANDLERS =====================
@bot.message_handler(commands=['start'])
def start(m):
    log(m.from_user.id)
    photo_path = "images/start.jpg"
    if os.path.exists(photo_path):
        bot.send_photo(m.chat.id, open(photo_path, "rb"),
            caption="Welcome to <b>Premium VPS Seller</b>\nInstant • Root • 24/7\nChoose below:", reply_markup=main_menu())
    else:
        bot.send_message(m.chat.id, "Welcome to <b>Premium VPS</b>\nGet your server now!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "Buy VPS")
def buy_vps(m):
    photo_path = "images/plans.jpg"
    if os.path.exists(photo_path):
        bot.send_photo(m.chat.id, open(photo_path, "rb"), reply_markup=plans_kb())
    else:
        bot.send_message(m.chat.id, "<b>Select Your Plan</b>", reply_markup=plans_kb())

@bot.message_handler(func=lambda m: m.text == "My VPS")
def my_vps(m):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT ip, username, password_enc, pem_path, expiry FROM vps WHERE assigned_to=? AND status='assigned'", (m.from_user.id,))
    vps = c.fetchone()
    conn.close()
    if not vps:
        bot.send_message(m.chat.id, "No active VPS.\nBuy now!", reply_markup=main_menu())
        return

    ip, user, pass_enc, pem, exp = vps
    password = decrypt(pass_enc)
    text = f"""<b>VPS ACTIVATED</b>
━━━━━━━━━━━━━━━
IP: <code>{ip}</code>
Username: <code>{user}</code>
Password: <code>{password}</code>
Expires: <code>{exp}</code>
━━━━━━━━━━━━━━━
SSH: <code>ssh {user}@{ip}</code>"""

    photo_path = "images/activated.jpg"
    if os.path.exists(photo_path):
        bot.send_photo(m.chat.id, open(photo_path, "rb"), caption=text)
    else:
        bot.send_message(m.chat.id, text)

    if pem and os.path.exists(pem):
        bot.send_document(m.chat.id, open(pem, "rb"), caption="Your .pem Key File")

@bot.message_handler(func=lambda m: m.text in ["Plans", "Orders", "Support"])
def simple_pages(m):
    if m.text == "Plans":
        txt = "<b>Available Plans</b>\n\n"
        for p in PLANS.values():
            txt += f"• {p['name']} → ₹{p['price']}\n"
    elif m.text == "Orders":
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT order_id, plan, amount, status FROM orders WHERE user_id=? ORDER BY created_at DESC", (m.from_user.id,))
        rows = c.fetchall()
        conn.close()
        txt = "<b>Your Orders</b>\n\n" if rows else "No orders yet.\n"
        for o in rows:
            status = "Pending" if o[3]=="PENDING" else "Approved" if o[3]=="APPROVED" else "Rejected"
            txt += f"{status} <code>{o[0]}</code> • ₹{o[2]}\n"
    else:
        txt = "<b>Support</b>\nAfter payment, send screenshot here.\nAdmin will activate instantly!"

    bot.send_message(m.chat.id, txt, reply_markup=main_menu())

# ===================== CALLBACKS =====================
@bot.callback_query_handler(func=lambda call: call.data.startswith("plan_"))
def plan_selected(call):
    plan_key = call.data.split("_")[1]
    plan = PLANS[plan_key]
    order_id = generate_order_id()
    user_id = call.from_user.id  # FIXED: was c.from_user.id

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO orders (order_id, user_id, plan, amount, created_at) VALUES (?,?,?,?,?)",
              (order_id, user_id, plan_key, plan["price"], datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

    payment_text = f"""<b>Payment Required</b>
━━━━━━━━━━━━━━━
Amount: <b>₹{plan['price']}</b>
Plan: {plan['name']}
Order ID: <code>{order_id}</code>

UPI ID: <code>{UPI_ID}</code>

<b>Send payment screenshot here after paying</b>"""

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=payment_text)

    try:
        bot.send_message(ADMIN_ID, f"New Order!\nUser: {call.from_user.first_name} (@{call.from_user.username or 'NoUser'})\nOrder: <code>{order_id}</code>\nPlan: {plan['name']}\nAmount: ₹{plan['price']}")
    except: pass

# ===================== PAYMENT PROOF =====================
@bot.message_handler(content_types=['photo'])
def receive_proof(m):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT order_id FROM orders WHERE user_id=? AND status='PENDING'", (m.from_user.id,))
    order = cur.fetchone()
    conn.close()

    if not order:
        bot.reply_to(m, "You have no pending order.")
        return

    file = bot.get_file(m.photo[-1].file_id)
    downloaded = bot.download_file(file.file_path)
    proof_path = f"payments/{order[0]}_{m.from_user.id}.jpg"
    with open(proof_path, "wb") as f:
        f.write(downloaded)

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("UPDATE orders SET proof_path=? WHERE order_id=?", (proof_path, order[0]))
    conn.commit()
    conn.close()

    bot.reply_to(m, f"Proof received!\nOrder <code>{order[0]}</code>\nWaiting for admin approval...")
    bot.forward_message(ADMIN_ID, m.chat.id, m.message_id)
    bot.send_message(ADMIN_ID, f"New Proof\nOrder: <code>{order[0]}</code>\nUser: {m.from_user.first_name}")

# ===================== ADMIN COMMANDS =====================
@bot.message_handler(commands=['pending', 'approve', 'reject', 'stats'])
def admin_commands(m):
    if m.from_user.id != ADMIN_ID: return

    if m.text.startswith("/pending"):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT order_id, user_id, plan, amount FROM orders WHERE status='PENDING'")
        orders = c.fetchall()
        conn.close()
        if not orders:
            bot.reply_to(m, "No pending orders.")
            return
        txt = "<b>Pending Orders</b>\n\n"
        for o in orders:
            txt += f"<code>{o[0]}</code> | User {o[1]} | ₹{o[3]}\n/approve {o[0]}  /reject {o[0]}\n\n"
        bot.reply_to(m, txt)

    elif m.text.startswith("/approve"):
        try:
            order_id = m.text.split()[1].upper()
        except:
            bot.reply_to(m, "Usage: /approve ORDER_ID")
            return

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT user_id, plan FROM orders WHERE order_id=? AND status='PENDING'", (order_id,))
        order = c.fetchone()
        if not order:
            bot.reply_to(m, "Not found or already processed.")
            conn.close()
            return

        user_id, plan_key = order
        vps = get_available_vps()
        if not vps:
            bot.reply_to(m, "No VPS in stock!")
            conn.close()
            return

        vps_id, ip, username, pass_enc, pem_path = vps
        days = PLANS[plan_key]["days"]
        expiry = assign_vps(vps_id, user_id, days)
        password = decrypt(pass_enc)

        c.execute("UPDATE orders SET status='APPROVED' WHERE order_id=?", (order_id,))
        conn.commit()
        conn.close()

        msg = bot.send_message(user_id, "Activating your VPS...")
        threading.Thread(target=progress_animation, args=(msg,)).start()

        time.sleep(8)
        delivery = f"""<b>VPS ACTIVATED SUCCESSFULLY!</b>
━━━━━━━━━━━━━━━
IP: <code>{ip}</code>
Username: <code>{username}</code>
Password: <code>{password}</code>
Expires: <code>{expiry}</code>
━━━━━━━━━━━━━━━
Enjoy full root access!"""

        bot.send_message(user_id, delivery)
        if pem_path and os.path.exists(pem_path):
            bot.send_document(user_id, open(pem_path, "rb"), caption="Your .pem Key")

        bot.reply_to(m, f"Approved & Delivered {order_id}")

    elif m.text.startswith("/reject"):
        try:
            order_id = m.text.split()[1]
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("UPDATE orders SET status='REJECTED' WHERE order_id=?", (order_id,))
            conn.commit()
            conn.close()
            bot.reply_to(m, f"Rejected {order_id}")
        except: pass

    elif "/stats" in m.text:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users"); users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM orders WHERE status='APPROVED'"); sales = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM vps WHERE status='available'"); stock = c.fetchone()[0]
        conn.close()
        bot.reply_to(m, f"<b>Bot Stats</b>\nUsers: {users}\nSales: {sales}\nStock: {stock}")

# ===================== START =====================
if __name__ == "__main__":
    print("Premium VPS Bot Started - Single File (FIXED)")
    print("Ready for production!")
    bot.infinity_polling()
