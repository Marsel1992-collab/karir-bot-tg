import os
import re
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from openai import AsyncOpenAI

# Инициализация OpenAI клиента
openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Токен Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Flask приложение
app = Flask(name)

# Telegram приложение
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Регистрация обработчика
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: handle_message(u, c)))

# Проверка на оскорбление
def contains_insult(text):
    return bool(re.search(r'\b(идиот|тупой|лох|мразь|гандон|чмо)\b', text.lower()))

# Обработка сообщения
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    text = update.message.text.lower()

    # Обращение к боту по ключевому слову
    if "карик" not in text and not contains_insult(text):
        return

    prompt = ""
    insult_reply = False
    image_request = False

    if contains_insult(text):
        insult_reply = True
        prompt = f"Оскорби собеседника в ответ на: {update.message.text}"
    elif "сгенерируй" in text or "нарисуй" in text or "создай" in text:
        image_request = True
        prompt = re.sub(r"карик[, ]*", "", text)
    else:
        prompt = f"Отвечай с сарказмом и матами на: {update.message.text}"

    try:
        if image_request:
            response = await openai.images.generate(
                model="dall-e-3",
                prompt=prompt,
                n=1,
                size="1024x1024"
            )
            image_url = response.data[0].url
            await update.message.reply_photo(image_url)
        else:
            completion = await openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            )
            reply = completion.choices[0].message.content
            await update.message.reply_text(reply)

    except Exception as e:
        print(f"Ошибка OpenAI: {e}")
        await update.message.reply_text("Ошибка OpenAI: " + str(e))


# Webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    async def process():
        if not application.running:
            await application.initialize()
        await application.process_update(Update.de_json(request.get_json(force=True), application.bot))

    asyncio.run(process())
    return "ok"


@app.route("/", methods=["GET"])
def index():
    return "Бот работает!"

# Запуск Flask-сервера
if name == "main":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

