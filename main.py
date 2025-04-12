import os
import re
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from openai import AsyncOpenAI

# Инициализация
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Простые фильтры
def contains_swear(text: str) -> bool:
    return bool(re.search(r"\b(хуй|бля|пизд|еб|нахуй|сука)\b", text.lower()))

def contains_insult(text: str) -> bool:
    return bool(re.search(r"\b(тупой|лох|чмо|гандон|долбоёб|мразь)\b", text.lower()))

def wants_image(text: str) -> bool:
    return any(word in text.lower() for word in ["нарисуй", "изобрази", "сгенерируй"])

# Обработчик сообщений
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip().lower()
    chat_id = update.effective_chat.id

    if "карик" not in text:
        return  # Только обращение с "карик"

    try:
        # Генерация изображения
        if wants_image(text):
            image_response = await openai_client.images.generate(
                model="dall-e-3",
                prompt=update.message.text,
                n=1,
                size="1024x1024"
            )
            image_url = image_response.data[0].url
            await update.message.reply_photo(photo=image_url)
            return

        # Подготовка промпта
        prompt = "Ты грубый, колкий, язвительный ассистент. Отвечай на вопрос:\n"
        if contains_insult(text):
            prompt = "Оскорби собеседника в ответ:\n"
        elif contains_swear(text):
            prompt = "Ответь с использованием мата:\n"

        prompt += update.message.text

        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content.strip()
        await update.message.reply_text(reply)

    except Exception as e:
        print(f"Ошибка OpenAI: {e}")
        await update.message.reply_text("Произошла ошибка при обращении к OpenAI.")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

# Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    async def process():
        await application.initialize()
        await application.process_update(Update.de_json(request.get_json(force=True), application.bot))
    asyncio.run(process())
    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "Бот работает!"

# Запуск
if name == "main":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

