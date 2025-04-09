import os
import logging
import pytz
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from openai import OpenAI
import re
import asyncio

# Инициализация OpenAI клиента
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Получаем токен Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Flask приложение
app = Flask(__name__)

# Telegram приложение
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Слово для упрощенного обращения
KEYWORD = "карик"

# Режимы
swear_mode = {}
no_mention_mode = {}
insult_mode = {}

# Мат
def contains_swear(text):
    return bool(re.search(r'\b(бляд|нахуй|сука|пизд|хуй|еб)\b', text.lower()))

# Оскорбление
def contains_insult(text):
    return bool(re.search(r'\b(тупой|дурак|лох|гандон|чмо|мразь)\b', text.lower()))

# Обработка сообщений
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    text = update.message.text.lower()
    chat_id = update.effective_chat.id

    # Инициализация счетчиков, если нужно
    for mode in (swear_mode, no_mention_mode, insult_mode):
        if chat_id not in mode:
            mode[chat_id] = 0

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
            prompt = "Ты дружелюбный ассистент."
            if insult_mode[chat_id] > 0:
                prompt = f"Оскорби собеседника в ответ на: {text}"
            elif swear_mode[chat_id] > 0:
                prompt = f"Ответь грубо с матами на: {text}"
            elif no_mention_mode[chat_id] > 0:
                prompt = f"Ответь на сообщение: {text}"

            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                reply = response.choices[0].message.content
                await update.message.reply_text(reply)
            except Exception as e:
                await update.message.reply_text(f"Ошибка OpenAI: {e}")
                print(">>> Ошибка OpenAI:", e)

    # Уменьшаем счётчики режимов
    for mode in (swear_mode, no_mention_mode, insult_mode):
        if mode[chat_id] > 0:
            mode[chat_id] -= 1

# Обработчик сообщений
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

# Flask route для Telegram webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    async def process():
        if not application._initialized:
            await application.initialize()
        await application.process_update(Update.de_json(request.get_json(force=True), application.bot))
    try:
        asyncio.run(process())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process())
    return "OK"

# Запуск
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



