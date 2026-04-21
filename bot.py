import os
import logging
import json
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# Setup Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration (Koyeb Environment Variables) ---
TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN", "8766546977:AAEOp-KzpLAOKI3pNO4j-ADcedOrQuZdKOY")
GEMINI_API_KEY = os.getenv("GEMINI_KEY", "AIzaSyAV-QZ9MwrBQmedkkPSWGA3JhmEJ3ybLBA")
ADMIN_CHAT_ID = 5994570683 

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

user_conversations = defaultdict(list)
user_photos = defaultdict(list)

SYSTEM_PROMPT = """Tu Supreme X App ka expert customer support agent hai.
Tujhe natural Hinglish me baat karni hai. Robotic mat ban.
Kill Issue: Username, Match ID, SS maang.
Payment Issue: Payment SS, QR SS, Username maang.
Withdrawal: Username maang aur bol 24 hours me ho jayega.
Match ID Guide: # wala code Match ID hai.
Jab details mil jayein toh end me ye tag laga: [COMPLAINT_READY]
Data: [COMPLAINT_DATA]{"username":"...", "issue":"...", "match_id":"...", "details":"..."}[/COMPLAINT_DATA]"""

async def get_ai_reply(user_id, user_message):
    history = user_conversations[user_id]
    chat = model.start_chat(history=[])
    try:
        # History ko combine karke context bhejna
        context = f"{SYSTEM_PROMPT}\n\nPrevious Chat: {history}\nUser: {user_message}\nAssistant:"
        response = chat.send_message(context)
        reply = response.text.strip()
        # History update karna (Memory ke liye)
        history.append(f"User: {user_message}")
        history.append(f"Assistant: {reply}")
        if len(history) > 10: history[:] = history[-10:]
        return reply
    except Exception as e:
        logger.error(f"Error: {e}")
        return "Sir server busy hai, thoda wait karke msg karein."

def extract_complaint(reply):
    clean_reply = reply.split("[COMPLAINT_READY]")[0].split("[COMPLAINT_DATA]")[0].strip()
    data = None
    if "[COMPLAINT_DATA]" in reply:
        try:
            json_str = reply.split("[COMPLAINT_DATA]")[1].split("[/COMPLAINT_DATA]")[0].strip()
            data = json.loads(json_str)
        except: pass
    return data, clean_reply

async def forward_to_admin(context, update, data, photos):
    user = update.effective_user
    msg = f"🚨 *NEW COMPLAINT*\n👤 Name: {user.full_name}\n🆔 ID: `{user.id}`\n"
    if data:
        for k,v in data.items(): msg += f"• {k.title()}: {v}\n"
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")
    for p in photos:
        await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=p, caption=f"Proof for {user.id}")

async def handle_msg(update: Update, context):
    user_id = update.effective_user.id
    msg_text = update.message.text or update.message.caption or ""
    if update.message.photo:
        user_photos[user_id].append(update.message.photo[-1].file_id)
        msg_text = f"[USER SENT A PHOTO] {msg_text}"
    
    reply = await get_ai_reply(user_id, msg_text)
    data, clean_reply = extract_complaint(reply)
    await update.message.reply_text(clean_reply)
    
    if "[COMPLAINT_READY]" in reply:
        await forward_to_admin(context, update, data, user_photos[user_id])
        user_photos[user_id] = []

async def start(update, context):
    user_conversations[update.effective_user.id] = []
    await update.message.reply_text("Namaste sir! Supreme X Support me swagat hai. Kya problem hai?")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_msg))
    app.run_polling()

if __name__ == "__main__":
    main()
