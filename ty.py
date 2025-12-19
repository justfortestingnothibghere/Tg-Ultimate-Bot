import telebot
import threading
import os
import shutil
import zipfile
import requests
from urllib.parse import urljoin, urlparse, unquote
from bs4 import BeautifulSoup
from pathlib import Path
import time
import logging
from datetime import datetime, date
import json
import psutil
import math

# ================= CONFIG =================
TOKEN = "7913272382:AAGnvD29s4bu_jmsejNmT5eWbl7HZnGy_OM"
bot = telebot.TeleBot(TOKEN)

# ADMIN ID
ADMIN_ID = 8163739723

DB_FILE = "users.json"
DEFAULT_DAILY_LIMIT = 2
MAX_SIZE_MB = 45
HEADERS = {'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-S906N) AppleWebKit/537.36'}

active_tasks = {}
progress_messages = {}

# =============== JSON DB ===============
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_db(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=4)

def get_user_data(user_id):
    db = load_db()
    user_id = str(user_id)
    if user_id not in db:
        db[user_id] = {
            "accepted_tc": False,
            "daily_used": 0,
            "last_date": None,
            "custom_limit": DEFAULT_DAILY_LIMIT,
            "is_premium": False,
            "joined_date": datetime.now().isoformat()
        }
        save_db(db)
    return db[user_id]

def accept_tc(user_id):
    user_id = str(user_id)
    db = load_db()
    db[user_id]["accepted_tc"] = True
    save_db(db)

def reset_daily_if_needed(user_id):
    user_id = str(user_id)
    data = get_user_data(user_id)
    today = date.today().isoformat()
    if data.get("last_date") != today:
        data["daily_used"] = 0
        data["last_date"] = today
        db = load_db()
        db[user_id].update(data)
        save_db(db)
    return data

def increment_usage(user_id):
    user_id = str(user_id)
    data = reset_daily_if_needed(user_id)
    data["daily_used"] += 1
    db = load_db()
    db[user_id].update(data)
    save_db(db)

def set_user_limit(user_id, limit, premium=False):
    user_id = str(user_id)
    db = load_db()
    if user_id not in db:
        db[user_id] = {"accepted_tc": True}
    db[user_id]["custom_limit"] = limit
    db[user_id]["is_premium"] = premium
    save_db(db)

# =============== STYLISH T&C ===============
def send_tc_message(chat_id):
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(telebot.types.InlineKeyboardButton("✅ I Accept T&C & Privacy Policy", callback_data="accept_tc"))
    markup.add(telebot.types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_tc"))

    tc_text = (
        "✨ *Terms & Conditions | Privacy Policy* ✨\n\n"
        "By using this bot, you agree to:\n\n"
        "• Only mirror *public websites*\n"
        "• No login/private data scraping\n"
        "• No illegal or harmful usage\n"
        "• Max file size: 45MB\n"
        "• Daily limit: 2 (upgradable)\n"
        "• We store only your Telegram ID & usage stats\n"
        "• All files deleted after delivery\n\n"
        "Your data is safe • No logs • Fully private\n\n"
        "Made with ❤️ by @MR_ARMAN_08"
    )

    bot.send_photo(
        chat_id,
        "https://graph.org/file/6bdddbc4b335597a86632-bbfc6792edbf4e2b21.jpg",
        caption=tc_text,
        parse_mode='Markdown',
        reply_markup=markup
    )

# =============== CALLBACKS ===============
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "accept_tc":
        accept_tc(call.from_user.id)
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption="✅ *Accepted!* Now you can use the bot!\n\nSend /start to begin",
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id, "Welcome! 🚀")
    elif call.data == "cancel_tc":
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption="❌ You declined T&C.\nBot will not work until accepted.",
            parse_mode='Markdown'
        )

# =============== KEYBOARDS ===============
def main_keyboard():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("👥 Group", url="https://t.me/team_x_og"),
        telebot.types.InlineKeyboardButton("🌐 Website", url="https://teamdev.sbs")
    )
    markup.add(telebot.types.InlineKeyboardButton("📊 My Stats", callback_data="my_stats"))
    return markup

# =============== PROGRESS BAR ===============
def create_progress_bar(percentage, length=20):
    filled = "█" 
    empty = "░"
    filled_count = int(length * percentage // 100)
    bar = filled * filled_count + empty * (length - filled_count)
    return f"{bar} {percentage}%"

# =============== ADMIN PANEL ===============
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "⛔ *Access Denied!* Only admin can use this.", parse_mode='Markdown')
    
    text = (
        "🔧 *Admin Panel*\n\n"
        "👥 Total Users: `{}`\n"
        "🗂 DB Size: `{:.2f} KB`\n"
        "💾 RAM Usage: `{:.1f}%`\n\n"
        "*Commands:*\n"
        "/users - List all users\n"
        "/broadcast - Send message to all\n"
        "/stats - Bot statistics\n"
        "/limit <id> <limit> - Set user limit\n"
        "/premium <id> - Make premium\n"
        "/resetuser <id> - Reset usage"
    ).format(
        len(load_db()),
        os.path.getsize(DB_FILE)/1024 if os.path.exists(DB_FILE) else 0,
        psutil.virtual_memory().percent
    )
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id != ADMIN_ID: return
    db = load_db()
    premium = sum(1 for u in db.values() if u.get("is_premium"))
    bot.reply_to(message, f"📊 *Bot Stats*\n\nTotal Users: {len(db)}\nPremium Users: {premium}\nActive Tasks: {len(active_tasks)}", parse_mode='Markdown')

@bot.message_handler(commands=['premium'])
def make_premium(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        user_id = int(message.text.split()[1])
        set_user_limit(user_id, 50, premium=True)
        bot.reply_to(message, f"✅ User {user_id} is now *Premium* (50/day)", parse_mode='Markdown')
    except: bot.reply_to(message, "Usage: /premium user_id")

# =============== COMMANDS ===============
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if not get_user_data(user_id).get("accepted_tc", False):
        send_tc_message(message.chat.id)
        return

    caption = (
        "🌟 *Website Mirror Bot - LIVE & FAST!* 🌟\n\n"
        "🔥 Main kisi bhi public website ko *full offline clone* banata hoon!\n"
        "Just send URL → Get ZIP\n\n"
        "✨ Example: `https://httpbin.org`\n"
        "⚡ Max Size: 45MB | Daily Limit: 2 (Upgradable)\n\n"
        "Made with ❤️ by @MR_ARMAN_08"
    )

    bot.send_photo(
        message.chat.id,
        "https://graph.org/file/6bdddbc4b335597a86632-bbfc6792edbf4e2b21.jpg",
        caption=caption,
        parse_mode='Markdown',
        reply_markup=main_keyboard()
    )

@bot.message_handler(commands=['cancel'])
def cancel_task(message):
    user_id = message.from_user.id
    if user_id in active_tasks:
        active_tasks[user_id]['cancelled'] = True
        bot.reply_to(message, "🛑 *Task Cancelled Successfully!*", parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ No active task to cancel.")

# =============== MAIN MIRROR HANDLER ===============
@bot.message_handler(func=lambda m: True)
def handle_url(message):
    user_id = message.from_user.id
    if not get_user_data(user_id).get("accepted_tc", False):
        send_tc_message(message.chat.id)
        return

    url = message.text.strip()
    if not url.startswith(('http://', 'https://')):
        return bot.reply_to(message, "❌ Please send a valid URL!\nExample: https://example.com")

    if user_id in active_tasks:
        return bot.reply_to(message, "⏳ *One task at a time!* Please wait...", parse_mode='Markdown')

    data = reset_daily_if_needed(user_id)
    limit = 50 if data.get("is_premium") else data.get("custom_limit", DEFAULT_DAILY_LIMIT)
    if data["daily_used"] >= limit:
        return bot.reply_to(message, f"🚫 *Daily Limit Exceeded!* ({data['daily_used']}/{limit})\nTry tomorrow or ask admin for upgrade!", parse_mode='Markdown')

    # Start Progress
    progress_msg = bot.reply_to(message, 
        "🚀 *Starting Mirror...*\n\n"
        "⏳ Please wait 2-15 minutes...\n"
        "You will get ZIP when done!",
        parse_mode='Markdown'
    )
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"mirrors/user_{user_id}_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    mirror = WebsiteMirror(url, output_dir, message.chat.id, progress_msg.message_id, user_id)
    active_tasks[user_id] = {'cancelled': False, 'mirror': mirror}

    def run_mirror():
        try:
            mirror.run()
            if not active_tasks[user_id]['cancelled']:
                increment_usage(user_id)
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Error: {str(e)}")
        finally:
            active_tasks.pop(user_id, None)

    threading.Thread(target=run_mirror, daemon=True).start()

# =============== UPGRADED MIRROR CLASS ===============
class WebsiteMirror:
    def __init__(self, url, output_dir, chat_id, msg_id, user_id):
        self.url = url.rstrip("/") + "/"
        self.domain = urlparse(url).netloc
        self.base_dir = Path(output_dir)
        self.output_dir = self.base_dir / self.domain
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.visited = set()
        self.file_count = 0
        self.total_files = 0
        self.chat_id = chat_id
        self.msg_id = msg_id
        self.user_id = user_id
        self.start_time = time.time()

    def update_progress(self, status="", percentage=0):
        if self.user_id not in active_tasks or active_tasks[self.user_id]['cancelled']:
            return
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)
        bar = create_progress_bar(percentage)
        
        text = (
            f"🔄 *Mirroring in Progress...*\n\n"
            f"{bar}\n"
            f"📊 Files: `{self.file_count}`\n"
            f"⏱ Time: `{mins}m {secs}s`\n"
            f"🌐 Domain: `{self.domain}`\n\n"
            f"Status: {status or 'Downloading assets...'}"
        )
        try:
            bot.edit_message_text(text, self.chat_id, self.msg_id, parse_mode='Markdown')
        except: pass

    def save_file(self, content, file_path):
        full_path = self.output_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'wb') as f:
            f.write(content)
        self.file_count += 1

    def run(self):
        try:
            self.update_progress("Initializing...", 5)
            self.download(self.url)
            
            if active_tasks[self.user_id]['cancelled']:
                self.update_progress("❌ Cancelled by user", 100)
                return

            self.update_progress("Compressing files...", 90)
            zip_path = f"{self.base_dir}_{self.domain}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(self.output_dir):
                    for file in files:
                        if active_tasks[self.user_id]['cancelled']: break
                        fp = os.path.join(root, file)
                        zf.write(fp, os.path.relpath(fp, self.base_dir))

            if active_tasks[self.user_id]['cancelled']: return

            size_mb = os.path.getsize(zip_path) / (1024*1024)
            if size_mb > MAX_SIZE_MB:
                self.update_progress(f"❌ Too large ({size_mb:.1f}MB)", 100)
                bot.send_message(self.chat_id, "❌ Website too big! Try smaller site.")
                return

            self.update_progress("Uploading to Telegram...", 95)
            with open(zip_path, 'rb') as f:
                bot.send_document(
                    self.chat_id,
                    f,
                    caption=(
                        f"✅ *Website Cloned Successfully!*\n\n"
                        f"📦 Files: `{self.file_count}`\n"
                        f"💾 Size: `{size_mb:.2f} MB`\n"
                        f"🔗 URL: `{self.url}`\n"
                        f"⏰ Time: `{int(time.time()-self.start_time)}s`\n\n"
                        f"Now works 100% offline! 🔥"
                    ),
                    parse_mode='Markdown'
                )
            bot.send_message(self.chat_id, "🎉 *Done!* Your offline website is ready!", parse_mode='Markdown')
            
        except Exception as e:
            bot.send_message(self.chat_id, f"❌ Failed: {str(e)}")
        finally:
            shutil.rmtree(self.base_dir, ignore_errors=True)
            for f in os.listdir('.'):
                if f.endswith('.zip') and self.domain in f:
                    try: os.remove(f)
                    except: pass

    def download(self, url):
        if self.user_id not in active_tasks or active_tasks[self.user_id]['cancelled']:
            return
        if url in self.visited: return
        self.visited.add(url)

        try:
            time.sleep(0.3)
            r = requests.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
            r.raise_for_status()
            path = self.normalize_path(r.url)

            self.update_progress(f"Downloading: {Path(path).name[:30]}...", 
                              min(85, 10 + len(self.visited)*5))

            if 'text/html' in r.headers.get('Content-Type', '') or not Path(path).suffix:
                self.save_file(r.content, path)
                soup = BeautifulSoup(r.text, 'html.parser')
                for tag in soup.find_all(['a', 'link', 'script', 'img', 'source']):
                    link = tag.get('href') or tag.get('src')
                    if link and not link.startswith(('mailto:', 'tel:', 'javascript:', '#')):
                        abs_url = urljoin(url, link.split('#')[0].split('?')[0])
                        if urlparse(abs_url).netloc == self.domain:
                            self.download(abs_url)
            else:
                self.save_file(r.content, path)
        except: pass

    def normalize_path(self, url):
        parsed = urlparse(url)
        path = unquote(parsed.path)
        if not path or path.endswith('/'):
            path = path + 'index.html' if path else 'index.html'
        return path.lstrip('/')

# =============== START BOT ===============
if not os.path.exists("mirrors"):
    os.makedirs("mirrors")

print("🚀 Ultimate Mirror Bot v2.0 - Running with Style!")
bot.infinity_polling(none_stop=True)
