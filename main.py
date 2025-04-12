import os
import re
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from openai import AsyncOpenAI

app = Flask(name)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI client
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Telegram bot
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Грубость, оскорбления, генерация
def has_swear(text):
    return re.search(r"\b(бляд|сука|хуй|пизд|ебан|нахуй)\b", text.lower())

def has_insult(text):
    return re.search(r"\b(лох|тупой|дебил|гандон|чмо|мразь)\b", text.lower())

def ask_for_image(text):
    return "сгенерируй" in text.lower() and "картин" in text.lower()

# Обработчик сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    user_text = update.message.text.lower()
    user_message = update.message.text
    prompt = user_message

    try:
        # Если есть просьба сгенерировать изображение
        if ask_for_image(user_text):
            image = await openai_client.images.generate(
                model="dall-e-3",
                prompt=user_message,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            await update.message.reply_photo(photo=image.data[0].url)
            return

        # Грубый, матерящийся или оскорбительный режим
        if has_insult(user_text):
            prompt = f"Оскорби собеседника, ответив на: {user_message}"
        elif has_swear(user_text):
            prompt = f"Ответь грубо с матами на: {user_message}"
        else:
            prompt = f"Ты резкий ассистент, ответь на: {user_message}"

        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)

    except Exception as e:
        print(">>> OpenAI error:", e)
        await update.message.reply_text("Произошла ошибка при обращении к OpenAI.")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    async def process():
        if not application.running:
            await application.initialize()
        await application.process_update(Update.de_json(request.get_json(force=True), application.bot))

    asyncio.run(process())
    return "ok"

# Проверка, что бот работает
@app.route("/", methods=["GET"])
def index():
    return "Бот запущен!"

# Запуск
if name == "main":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

