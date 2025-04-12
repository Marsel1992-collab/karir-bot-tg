import os
import re
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from openai import AsyncOpenAI

# ==== Ключи ====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ==== Flask-приложение ====
app = Flask(__name__)

# ==== Telegram bot ====
application = Application.builder().token(TELEGRAM_TOKEN).build()

# ==== Обработчик сообщений ====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    text = update.message.text.lower()

    if "карик" not in text:
        print(">>> Сообщение без 'карик' — игнорируем.")
        return

    insult_words = ["тупой", "лох", "гандон", "чмо", "мразь", "идиот"]
    generate_keywords = ["сгенерируй", "нарисуй", "картинку", "фото", "изображение"]

    if any(word in text for word in insult_words):
        prompt = f"Ответь оскорбительно на: {update.message.text}"
    elif any(word in text for word in generate_keywords):
        await generate_image(update)
        return
    else:
        prompt = update.message.text

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content.strip()
        await update.message.reply_text(reply)
    except Exception as e:
        print(f"Ошибка OpenAI: {e}")
        await update.message.reply_text("Произошла ошибка при обращении к OpenAI.")


async def generate_image(update: Update):
    try:
        prompt = update.message.text.replace("карик", "").strip()
        image_response = await openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            n=1
        )
        image_url = image_response.data[0].url
        await update.message.reply_photo(photo=image_url)
    except Exception as e:
        print(f"Ошибка генерации изображения: {e}")
        await update.message.reply_text("Не удалось сгенерировать изображение.")


# ==== Регистрируем обработчик ====
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ==== Webhook для Telegram ====
@app.route("/webhook", methods=["POST"])
def webhook():
    print(">>> Входящий запрос от Telegram!")

    async def process():
        try:
            if not application._initialized:
                await application.initialize()
            update = Update.de_json(request.get_json(force=True), application.bot)
            print(f">>> Содержимое update:\n{update}")
            await application.process_update(update)
        except Exception as e:
            import traceback
            print(">>> ОШИБКА ВНУТРИ process():")
            traceback.print_exc()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(process())
    return "ok"


@app.route("/", methods=["GET"])
def index():
    return "Бот работает!"

# ==== Запуск сервера ====
if __name__ == "__main__":
    print("Сервер запущен. Ожидаем сообщения...")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


