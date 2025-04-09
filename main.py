import os
import logging
import pytz
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from telegram.ext import Defaults
import openai
import re
import asyncio

openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

app = Flask(__name__)
application = Application.builder().token(TELEGRAM_TOKEN).build()

KEYWORD = "карик"
swear_mode = {}
no_mention_mode = {}
insult_mode = {}

def contains_swear(text):
    return bool(re.search(r'\b(бляд|нахуй|сука|пизд|хуй|еб)\b', text.lower()))

def contains_insult(text):
    return bool(re.search(r'\b(тупой|дурак|лох|гандон|чмо|мразь)\b', text.lower()))

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    chat_id = update.effective_chat.id

    swear_mode.setdefault(chat_id, 0)
    no_mention_mode.setdefault(chat_id, 0)
    insult_mode.setdefault(chat_id, 0)

    if contains_swear(text):
        swear_mode[chat_id] = 3
    if contains_insult(text):
        insult_mode[chat_id] = 3
    if KEYWORD in text:
        no_mention_mode[chat_id] = 3

    should_respond = (
        KEYWORD in text
        or no_mention_mode[chat_id] > 0
        or swear_mode[chat_id] > 0
        or insult_mode[chat_id] > 0
    )

    if should_respond:
        if "ты знаешь руслана" in text:
            await update.message.reply_text("Да, он лошара.")
        else:
            prompt = f"Ты грубый, саркастичный и матерящийся ассистент. Отвечай на: {update.message.text}"
            if insult_mode[chat_id] > 0:
                prompt = f"Оскорби собеседника в ответ на: {update.message.text}"
            elif swear_mode[chat_id] > 0:
                prompt = f"Ответь грубо с матами на: {update.message.text}"

            try:
                response = await openai.ChatCompletion.acreate(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                reply = response.choices[0].message.content
                await update.message.reply_text(reply)
            except Exception as e:
                await update.message.reply_text(f"Ошибка OpenAI: {e}")
                print("Ошибка OpenAI:", e)

    for mode in (swear_mode, no_mention_mode, insult_mode):
        if mode[chat_id] > 0:
            mode[chat_id] -= 1

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

@app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.initialize()
    await application.process_update(update)
    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)





