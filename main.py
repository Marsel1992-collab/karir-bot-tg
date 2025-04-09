import os
import re
import pytz
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from openai import AsyncOpenAI

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

app = Flask(__name__)
application = Application.builder().token(TELEGRAM_TOKEN).build()

KEYWORD = "карик"
insult_once = set()

def contains_insult(text):
    return bool(re.search(r'\b(тупой|дурак|лох|гандон|чмо|мразь|идиот|дебил)\b', text.lower()))

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if KEYWORD not in text:
        return  # Не реагируем без обращения

    if "ты знаешь руслана" in text:
        await update.message.reply_text("Да, он лошара.")
        return

    # Если есть оскорбление — добавляем юзера в set
    is_insult = contains_insult(text)
    if is_insult and user_id not in insult_once:
        prompt = f"Оскорби собеседника в ответ на: {update.message.text}"
        insult_once.add(user_id)
    else:
        prompt = f"Ты грубый, дерзкий, но сдержанный ассистент. Ответь на: {update.message.text}"

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"Ошибка OpenAI: {e}")
        print(">>> Ошибка OpenAI:", e)

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

@app.route("/webhook", methods=["POST"])
async def webhook():
    if not application._initialized:
        await application.initialize()
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)




