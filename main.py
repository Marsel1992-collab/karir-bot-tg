import os
import logging
import pytz
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
import openai
import re
import asyncio

# Настройка логов (по желанию)
logging.basicConfig(level=logging.INFO)

# Ключи из переменных среды
openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Flask-приложение
app = Flask(__name__)

# Telegram Application
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Инициализация состояний
KEYWORD = "карик"
swear_mode = {}
no_mention_mode = {}
insult_mode = {}

# Фильтр мата
def contains_swear(text):
    return bool(re.search(r'\b(бляд|нахуй|сука|пизд|хуй|еб)\b', text.lower()))

# Фильтр оскорблений
def contains_insult(text):
    return bool(re.search(r'\b(тупой|дурак|лох|гандон|чмо|мразь)\b', text.lower()))

# Основной обработчик сообщений
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    print(">>> Получено сообщение:", update.message.text)
    print(">>> Полный апдейт:", update)

    chat_id = update.effective_chat.id
    text = update.message.text.lower()

    # Обнуление режимов
    swear_mode.setdefault(chat_id, 0)
    no_mention_mode.setdefault(chat_id, 0)
    insult_mode.setdefault(chat_id, 0)

    # Включение режимов
    if contains_swear(text):
        swear_mode[chat_id] = 3
    if contains_insult(text):
        insult_mode[chat_id] = 3
    if KEYWORD in text:
        no_mention_mode[chat_id] = 3

    # Нужно ли отвечать
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
            # Выбираем тон ответа
            if insult_mode[chat_id] > 0:
                prompt = f"Оскорби собеседника в ответ на: {update.message.text}"
            elif swear_mode[chat_id] > 0:
                prompt = f"Ответь грубо с матами на: {update.message.text}"
            else:
                prompt = f"Ты грубый, саркастичный и матерящийся ассистент. Отвечай на: {update.message.text}"

            try:
                response = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                reply = response.choices[0].message.content
                await update.message.reply_text(reply)
            except Exception as e:
                print(">>> Ошибка OpenAI:", e)
                await update.message.reply_text(f"Ошибка OpenAI: {e}")

    # Уменьшаем счётчики
    no_mention_mode[chat_id] = max(0, no_mention_mode[chat_id] - 1)
    swear_mode[chat_id] = max(0, swear_mode[chat_id] - 1)
    insult_mode[chat_id] = max(0, insult_mode[chat_id] - 1)

# Регистрируем обработчик
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

# Webhook обработчик
@app.route("/webhook", methods=["POST"])
def webhook():
    async def process():
        if not application._initialized:
            await application.initialize()
        await application.process_update(Update.de_json(request.get_json(force=True), application.bot))

    asyncio.run(process())
    return "OK"

# Запуск Flask на Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



