import os
import logging
import pytz
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
import openai
import re

# Настройки
openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Flask-приложение
app = Flask(__name__)

# Telegram-приложение
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Слово для активации Карика
KEYWORD = "карик"
swear_mode = {}
no_mention_mode = {}
insult_mode = {}

# Проверка на мат
def contains_swear(text):
    return bool(re.search(r'\b(бляд|нахуй|сука|пизд|хуй|еб)\b', text.lower()))

def contains_insult(text):
    return bool(re.search(r'\b(тупой|дурак|лох|гандон|чмо|мразь)\b', text.lower()))

# Обработчик сообщений
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.lower()

    # Состояния
    if chat_id not in swear_mode:
        swear_mode[chat_id] = 0
    if chat_id not in no_mention_mode:
        no_mention_mode[chat_id] = 0
    if chat_id not in insult_mode:
        insult_mode[chat_id] = 0

    # Режим мата
    if contains_swear(text):
        swear_mode[chat_id] = 3

    # Режим оскорблений
    if contains_insult(text):
        insult_mode[chat_id] = 3

    # Упоминание "карик"
    if KEYWORD in text:
        no_mention_mode[chat_id] = 3

    # Условие реакции
    should_respond = KEYWORD in text or no_mention_mode[chat_id] > 0 or swear_mode[chat_id] > 0 or insult_mode[chat_id] > 0

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
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                reply = response["choices"][0]["message"]["content"]
                await update.message.reply_text(reply)
            except Exception as e:
                await update.message.reply_text(f"Ошибка OpenAI: {e}")

    # Уменьшаем счётчики режимов
    if no_mention_mode[chat_id] > 0:
        no_mention_mode[chat_id] -= 1
    if swear_mode[chat_id] > 0:
        swear_mode[chat_id] -= 1
    if insult_mode[chat_id] > 0:
        insult_mode[chat_id] -= 1

# Добавляем обработчик
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

# Flask route
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK"

# Запуск приложения на нужном порту
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))     # ← порт от Render
    app.run(host="0.0.0.0", port=port)            # ← правильный запуск



