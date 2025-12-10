# tg.py - TeamDev Mirror Bot v5.0 (With Daily + Monthly Limits)
import telebot
import telebot.types import InputFile
import threading
import os
import shutil
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from pathlib import Path
import time
from datetime import date
import json
import random
import string

TOKEN = "7913272382:AAGnvD29s4bu_jmsejNmT5eWbl7HZnGy_OM"
ADMIN_ID = 8163739723  
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

os.makedirs("scraped", exist_ok=True)
os.makedirs("data", exist_ok=True)

USERS_DB = "data/users.json"

def load_json(file, default=None):
    if default is None:
        default = {}

    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)

    with open(file, "w") as f:
        json.dump(default, f, indent=4)

    return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

users = load_json(USERS_DB)
active_tasks = {}

def F(text): 
    return text.translate(str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789"
    ))

BOX = "╔═════◇◆◇═════╗\n"

# --------------------------------------
# LIMIT CHECK
# --------------------------------------
def check_limit(user_id):
    uid = str(user_id)

    if uid not in users:
        users[uid] = {
            "name": "",
            "scrapes_today": 0,
            "last_date": "",
            "cloud_month": 0,
            "last_month": ""
        }

    today = date.today().strftime("%Y-%m-%d")
    this_month = date.today().strftime("%Y-%m")

    if users[uid]["last_date"] != today:
        users[uid]["scrapes_today"] = 0
        users[uid]["last_date"] = today

    if users[uid]["last_month"] != this_month:
        users[uid]["cloud_month"] = 0
        users[uid]["last_month"] = this_month

    save_json(USERS_DB, users)

    return (
        users[uid]["scrapes_today"] < 5, 
        users[uid]["cloud_month"] < 2
    )

# --------------------------------------
# START COMMAND
# --------------------------------------
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)

    if uid not in users:
        users[uid] = {
            "name": m.from_user.first_name,
            "scrapes_today": 0,
            "last_date": "",
            "cloud_month": 0,
            "last_month": ""
        }
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


# --------------------------------------
# MIRROR CLASS
# --------------------------------------
class Mirror:
    def __init__(self, url, chat_id, msg_id, user_id):
        self.url = url.rstrip("/") + "/"
        self.user_id = str(user_id)
        self.chat_id = chat_id
        self.msg_id = msg_id
        self.cancelled = False
        self.file_count = 0

        free_daily, free_cloud = check_limit(user_id)

        if not free_daily:
            bot.edit_message_text(
                f"{BOX}ʟɪᴍɪᴛ ᴏᴠᴇʀ!\n5 sᴄʀᴀᴘᴇs ᴅᴀɪʟʏ ғɪɴɪsʜᴇᴅ\nᴄᴏᴍᴇ ᴛᴏᴍᴏʀʀᴏᴡ\n╚═════◇◆◇═════╝",
                chat_id,
                msg_id
            )
            return

        # Create folder
        num = len([d for d in os.listdir("scraped") if d.startswith(self.user_id + "_")]) + 1
        self.folder_num = num  # store original num
        self.dir = Path(f"scraped/{self.user_id}_{num}")
        self.dir.mkdir(parents=True, exist_ok=True)

        users[self.user_id]["scrapes_today"] += 1
        save_json(USERS_DB, users)

    # ----------------------------------------------------
    # FIXED: update_progress (You forgot to include it)
    # ----------------------------------------------------
    def update_progress(self, text):
        try:
            bot.edit_message_text(text, self.chat_id, self.msg_id)
        except:
            pass

    # ----------------------------------------------------
    # FIXED: Simple downloader (Your logic kept)
    # ----------------------------------------------------
    def download(self, url):
        try:
            r = requests.get(url, timeout=20)
        except:
            return

        soup = BeautifulSoup(r.text, "html.parser")
        links = soup.find_all("a")

        for link in links:
            href = link.get("href")
            if not href:
                continue

            full = urljoin(url, href)

            if full.endswith("/"):
                folder = self.dir / href.strip("/")
                folder.mkdir(exist_ok=True)
                self.download(full)
            else:
                try:
                    file_path = self.dir / href
                    content = requests.get(full).content
                    with open(file_path, "wb") as f:
                        f.write(content)
                    self.file_count += 1
                except:
                    pass

    # ----------------------------------------------------
    # FIXED MIRROR FUNCTION
    # ----------------------------------------------------
    def mirror(self):
        try:
            self.update_progress("Starting mirror...\n2-15 min lag sakta hai")

            # 1. Download website
            self.download(self.url)

            if self.cancelled:
                self.update_progress("Cancelled by user")
                return

            self.update_progress("Zipping files...")

            # 2. ZIP
            zip_path = f"{self.dir}.zip"
            shutil.make_archive(str(self.dir), 'zip', str(self.dir))

            # 3. Key
            key = ''.join(random.choices(string.ascii_letters + string.digits, k=20))

            # Cloud link MUST use original "folder_num"
            cloud_link = f"https://tg-ultimate-bot.onrender.com/scraped/{self.user_id}_{self.folder_num}?key={key}"

            with open(f"{self.dir}/key.txt", "w") as f:
                f.write(key)

            # 4. Cloud limit
            if users[self.user_id]["cloud_month"] < 2:
                users[self.user_id]["cloud_month"] += 1
                save_json(USERS_DB, users)

                cloud_text = f"ᴄʟᴏᴜᴅ ʟɪɴᴋ:\n<code>{cloud_link}</code>\nᴋᴇʏ: <code>{key}</code>"
            else:
                cloud_text = "ᴄʟᴏᴜᴅ ʟɪᴍɪᴛ ᴏᴠᴇʀ (2/ᴍᴏɴᴛʜ)"

            # 5. SEND ZIP
            with open(zip_path, 'rb') as f:
                bot.send_document(
                    self.chat_id,
                    InputFile(f,
                    filename="TeamDev.sbs.zip"),
                    caption=(
                        f"{BOX}ᴄʟᴏɴᴇᴅ!\n"
                        f"ғɪʟᴇs: {self.file_count}\n"
                        f"{cloud_text}\n"
                        "╚═════◇◆◇═════╝"
                    )
                )

        except Exception as e:
            bot.send_message(self.chat_id, f"Error: {e}")

        finally:
            # Release lock
            if self.user_id in active_tasks:
                del active_tasks[self.user_id]


# --------------------------------------
# HANDLE URL
# --------------------------------------
@bot.message_handler(func=lambda m: m.text and m.text.startswith("http"))
def handle(m):
    uid = str(m.from_user.id)

    if uid in active_tasks:
        bot.reply_to(m, "⏳ Wait, previous task still running...")
        return

    active_tasks[uid] = True

    msg = bot.reply_to(m, f"{BOX}ᴘʀᴏᴄᴇssɪɴɢ...\n╚═════◇◆◇═════╝")

    mirror = Mirror(m.text.strip(), m.chat.id, msg.message_id, m.from_user.id)
    threading.Thread(target=mirror.mirror, daemon=True).start()


print(f"{BOX}TeamDev Bot Ready!\n╚═════◇◆◇═════╝")
bot.infinity_polling()
