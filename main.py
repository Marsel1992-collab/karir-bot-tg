import os
import re
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from openai import OpenAI

# Инициализация OpenAI и Telegram
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

app = Flask(name)
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Обработчик сообщений
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    text = update.message.text.lower()
    if "карик" not in text:
        return

    prompt = f"Ответь с сарказмом и матами, если нужно, на сообщение: {update.message.text}"

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content.strip()
        await update.message.reply_text(reply)

    except Exception as e:
        print("Ошибка OpenAI:", e)
        await update.message.reply_text("Произошла ошибка при обращении к ChatGPT.")

# Регистрируем обработчик
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

# Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    async def process():
        await application.initialize()
        await application.process_update(Update.de_json(request.get_json(force=True), application.bot))

    asyncio.run(process())
    return "ok"

# Главная страница
@app.route("/", methods=["GET"])
def index():
    return "Бот работает!"

# Запуск
if name == "main":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

