import os
import re
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from openai import AsyncOpenAI

# Инициализация
app = Flask(__name__)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

application = Application.builder().token(TELEGRAM_TOKEN).build()
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Флаг матерного ответа
swear_mode = {}

# Проверка на мат
def contains_swear(text):
    return bool(re.search(r'\b(бляд|нахуй|сука|пизд|хуй|еб)\b', text.lower()))

# Обработчик Telegram-сообщений
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    chat_id = update.effective_chat.id

    use_swear = False

    if contains_swear(text):
        swear_mode[chat_id] = 1

    if "карик" not in text and swear_mode.get(chat_id, 0) == 0:
        return

    if swear_mode.get(chat_id, 0):
        prompt = f"Ответь грубо и с матами: {text}"
        swear_mode[chat_id] = 0
    else:
        prompt = f"Ты дерзкий бот. Ответь на: {text}"

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content.strip()
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка при обращении к OpenAI.")
        print(f"OpenAI error: {e}")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

# Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.create_task(application.process_update(update))
    return "ok"

# Главная страница
@app.route("/")
def index():
    return "Бот работает."

# Запуск Flask
if __name__ == "__main__":
    import threading
    import logging
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()

    def run_flask():
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    loop.run_until_complete(application.initialize())
