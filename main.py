
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from openai import OpenAI
import asyncio
import os
import traceback
import pytz

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)
application = Application.builder().token(TELEGRAM_TOKEN).build()
application.job_queue.scheduler.configure(timezone=pytz.UTC)

# Сохраняем память в user_data
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    user_id = update.message.from_user.id
    text = update.message.text.lower()

    # если сообщение содержит слово "карик"
    if "карик" not in text:
        return

    # спецответ про Руслана
    if "ты знаешь руслана" in text:
        await update.message.reply_text("Да, он лошара 😎")
        return

    # генерация картинки по фразе
    if "нарисуй" in text or "сделай картинку" in text:
        prompt = update.message.text.replace("карик", "").replace("нарисуй", "").strip()
        try:
            image = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )
            image_url = image.data[0].url
            await update.message.reply_photo(photo=image_url)
        except Exception as e:
            print("Ошибка генерации изображения:", e)
            await update.message.reply_text("Не удалось сгенерировать изображение.")
        return

    # История сообщений (память)
    history = context.user_data.get("history", [])
    history.append({"role": "user", "content": update.message.text})
    history = history[-5:]  # сохраняем последние 5 сообщений

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=history
        )
        reply = response.choices[0].message.content.strip()
        await update.message.reply_text(reply)

        history.append({"role": "assistant", "content": reply})
        context.user_data["history"] = history

    except Exception as e:
        print("Ошибка OpenAI:", e)
        await update.message.reply_text("Произошла ошибка при обработке запроса.")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route("/webhook", methods=["POST"])
def webhook():
    async def process():
        try:
            await application.initialize()
            update = Update.de_json(request.get_json(force=True), application.bot)
            await application.process_update(update)
        except Exception as e:
            print(">>> ОШИБКА ВНУТРИ process():")
            traceback.print_exc()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(process())
    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "Карик-бот онлайн!"

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

