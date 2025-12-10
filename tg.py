# tg.py - TeamDev Mirror Bot v5.0 (With Daily + Monthly Limits)
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
import random
import string

TOKEN = "7913272382:AAGnvD29s4bu_jmsejNmT5eWbl7HZnGy_OM"
ADMIN_ID = 8163739723  # ← Apna ID
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

os.makedirs("scraped", exist_ok=True)
os.makedirs("data", exist_ok=True)

USERS_DB = "data/users.json"

def load_json(file, default={}):
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    with open(file, 'w') as f:
        json.dump(default, f)
    return default

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

users = load_json(USERS_DB)
active_tasks = {}

# Fancy Font
def F(text): 
    return text.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", 
                                       "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789"))

BOX = "╔═════◇◆◇═════╗\n"

# Daily & Monthly Limits
def check_limit(user_id):
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"name": "", "scrapes_today": 0, "last_date": "", "cloud_month": 0, "last_month": ""}
    
    today = date.today().strftime("%Y-%m-%d")
    this_month = date.today().strftime("%Y-%m")
    
    # Reset daily
    if users[uid]["last_date"] != today:
        users[uid]["scrapes_today"] = 0
        users[uid]["last_date"] = today
    
    # Reset monthly cloud links
    if users[uid]["last_month"] != this_month:
        users[uid]["cloud_month"] = 0
        users[uid]["last_month"] = this_month
    
    free_daily = users[uid]["scrapes_today"] < 5
    free_cloud = users[uid]["cloud_month"] < 2
    
    save_json(USERS_DB, users)
    return free_daily, free_cloud

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in users:
        users[uid] = {"name": m.from_user.first_name, "scrapes_today": 0, "last_date": "", "cloud_month": 0, "last_month": ""}
        save_json(USERS_DB, users)
    
    free_daily, free_cloud = check_limit(m.from_user.id)
    
    text = f"""{BOX}
{F("HELLO")} <b>{m.from_user.first_name}</b>!

{F("FREE LIMITS")}:
• 5 sᴄʀᴀᴘᴇs/ᴅᴀʏ
• 2 ᴄʟᴏᴜᴅ ʟɪɴᴋs/ᴍᴏɴᴛʜ

{F("TODAY")}: {5 - users[uid]["scrapes_today"]} ʟᴇғᴛ
{F("THIS MONTH")}: {2 - users[uid]["cloud_month"]} ᴄʟᴏᴜᴅ ʟɪɴᴋs ʟᴇғᴛ

sᴇɴᴅ ᴜʀʟ ᴏʀ ᴄʟɪᴄᴋ ʙᴜᴛᴛᴏɴ
╚═════◇◆◇═════╝"""
    bot.send_message(m.chat.id, text)

class Mirror:
    def __init__(self, url, chat_id, msg_id, user_id):
        self.url = url.rstrip("/") + "/"
        self.user_id = str(user_id)
        self.chat_id = chat_id
        self.msg_id = msg_id
        
        free_daily, free_cloud = check_limit(user_id)
        if not free_daily and self.user_id not in ["premium_list"]:
            bot.edit_message_text(f"{BOX}ʟɪᴍɪᴛ ᴏᴠᴇʀ!\n5 sᴄʀᴀᴘᴇs/ᴅᴀʏ ғɪɴɪsʜᴇᴅ\nᴄᴏᴍᴇ ᴛᴏᴍᴏʀʀᴏᴡ\n╚═════◇◆◇═════╝", chat_id, msg_id)
            return
        
        # Create folder
        num = len([d for d in os.listdir("scraped") if d.startswith(self.user_id + "_")]) + 1
        self.dir = Path(f"scraped/{self.user_id}_{num}")
        self.dir.mkdir(parents=True, exist_ok=True)
        
        self.file_count = 0
        users[self.user_id]["scrapes_today"] += 1
        save_json(USERS_DB, users)

    def generate_key(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=20))

    def mirror(self):
        try:
            self.update_progress("Starting mirror...\n2-15 min lag sakta hai")

        # Start download
            self.download(self.url)

            if self.cancelled:
                self.update_progress("Cancelled by user")
                return

            self.update_progress("Zipping files...")

        # Create ZIP
            zip_path = f"{self.dir}.zip"
            shutil.make_archive(str(self.dir), 'zip', str(self.dir))

        # Generate secure key
            key = self.generate_key()

        # You used 'num' but never defined -> FIXED
            num = str(int(time.time()))  # unique ID based on timestamp

            cloud_link = f"https://tg-ultimate-bot.onrender.com/scraped/{self.user_id}_{num}?key={key}"

        # Save key inside directory
            with open(f"{self.dir}/key.txt", "w") as f:
                f.write(key)

        # Cloud monthly limit
            if users[self.user_id]["cloud_month"] < 2:
                users[self.user_id]["cloud_month"] += 1
                save_json(USERS_DB, users)
                cloud_text = (
                    f"ᴄʟᴏᴜᴅ ʟɪɴᴋ:\n<code>{cloud_link}</code>\n"
                    f"ᴋᴇʏ: <code>{key}</code>"
                )
            else:
                cloud_text = "ᴄʟᴏᴜᴅ ʟɪᴍɪᴛ ᴏᴠᴇʀ (2/ᴍᴏɴᴛʜ)"

        # Send ZIP to Telegram
            with open(zip_path, 'rb') as f:
                bot.send_document(
                    self.chat_id,
                    f,
                    filename="TeamDev.sbs.zip",
                    caption=(
                        f"{BOX}ᴄʟᴏɴᴇᴅ!\n"
                        f"ғɪʟᴇs: {self.file_count}\n"
                        f"{cloud_text}\n"
                        "╚═════◇◆◇═════╝"
                    )
                )

        except Exception as e:
            bot.send_message(self.chat_id, f"Error: {e}")
        
@bot.message_handler(func=lambda m: m.text and m.text.startswith("http"))
def handle(m):
    if str(m.from_user.id) in active_tasks:
        return
    active_tasks[str(m.from_user.id)] = True
    
    msg = bot.reply_to(m, f"{BOX}ᴘʀᴏᴄᴇssɪɴɢ...\n╚═════◇◆◇═════╝")
    
    mirror = Mirror(m.text.strip(), m.chat.id, msg.message_id, m.from_user.id)
    threading.Thread(target=mirror.mirror, daemon=True).start()

print(f"{BOX}TeamDev Bot + Website Ready!\n{F('LIVE ON PORT 5000')}\n╚═════◇◆◇═════╝")
bot.infinity_polling()
