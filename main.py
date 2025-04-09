import os
import re
import pytz
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from openai import AsyncOpenAI

# ======= Переменные окружения =======
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ======= Инициализация клиентов =======
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
application = Application.builder().token(TELEGRAM_TOKEN).build()

# ======= Flask-приложение =======
app = Flask(__name__)

# ======= Флаг — один раз оскорбить =======
insulted_chats = set()

# ======= Обработчик сообщений =======
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    text = update.message.text.lower()

    if "карик" not in text:
        print(">>> Сообщение без упоминания 'карик' — игнорируем.")
        return

    print(f">>> Сообщение с 'карик': {text}")

    # Специальный ответ на фразу
    if "ты знаешь руслана" in text:
        await update.message.reply_text("Да, он лошара 😎")
        return

    # Если сообщение содержит оскорбление — оскорбляем один раз
    if re.search(r'\b(тупой|дурак|лох|гандон|чмо|мразь|еблан|идиот)\b', text):
        chat_id = update.effective_chat.id
        if chat_id not in insulted_chats:
            insulted_chats.add(chat_id)
            await update.message.reply_text("Сам такой, убогий 🤡")
            return

    # Отправляем запрос в OpenAI
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": update.message.text}]
        )
        reply = response.choices[0].message.content.strip()
        await update.message.reply_text(reply)
    except Exception as e:
        import traceback
        traceback.print_exc()
        await update.message.reply_text(f"Ошибка OpenAI: {e}")

# ======= Регистрируем обработчик =======
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ======= Webhook для Telegram =======
@app.route("/webhook", methods=["POST"])
def webhook():
    print(">>> Входящий запрос от Telegram!")

    async def process():
        try:
            await application.initialize()
            update = Update.de_json(request.get_json(force=True), application.bot)
            print(f">>> Содержимое update:\n{update}")
            await application.process_update(update)
        except Exception as e:
            import traceback
            print(">>> ОШИБКА ВНУТРИ process():")
            traceback.print_exc()

    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(process())
    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "Бот работает!"

# ======= Запуск =======
if __name__ == "__main__":
    print(">>> Запускаем сервер Flask...")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



