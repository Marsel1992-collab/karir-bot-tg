import os
import re
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from openai import AsyncOpenAI

# ==== Ключи ====
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# ==== Flask-приложение ====
app = Flask(__name__)

# ==== Telegram bot ====
application = Application.builder().token(TELEGRAM_TOKEN).build()

# ==== Память для каждого пользователя ====
user_histories = {}  # user_id: [ {role: ..., content: ...}, ... ]
MAX_HISTORY_LENGTH = 10

# ==== Проверка на мат и оскорбления ====
def contains_swear(text):
    return bool(re.search(r'\b(еб|бля|пизд|хуй|сука|нах|гандон|мудак|чмо|мразь)\b', text.lower()))

def contains_insult(text):
    return bool(re.search(r'\b(тупой|дебил|лох|гондон|идиот|козёл)\b', text.lower()))

# ==== Обработчик сообщений ====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    text = update.message.text.lower()

    if "карик" not in text:
        print(">>> Сообщение без 'карик' — игнорируем.")
        return

    if "ты знаешь руслана" in text:
        print(">>> Спецвопрос про Руслана.")
        await update.message.reply_text("Да, он лошара 😎")
        return

    if contains_insult(text):
        await update.message.reply_text("Сам ты {}, урод 😤".format(text.split()[0]))
        return

    if contains_swear(text):
        await update.message.reply_text("Вот и иди ты на х*й! 🤬")
        return

    user_id = update.message.from_user.id
    user_message = update.message.text
    print(f"Получено сообщение с 'карик': {user_message}")

    # Инициализируем историю, если её ещё нет
    if user_id not in user_histories:
        user_histories[user_id] = []

    # Добавляем новое сообщение в историю
    user_histories[user_id].append({"role": "user", "content": user_message})

    # Обрезаем историю, если она слишком длинная
    if len(user_histories[user_id]) > MAX_HISTORY_LENGTH:
        user_histories[user_id] = user_histories[user_id][-MAX_HISTORY_LENGTH:]

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=user_histories[user_id]
        )
        reply = response.choices[0].message.content.strip()
        print(f"GPT ответил: {reply}")

        # Добавляем ответ ассистента в историю
        user_histories[user_id].append({"role": "assistant", "content": reply})
        if len(user_histories[user_id]) > MAX_HISTORY_LENGTH:
            user_histories[user_id] = user_histories[user_id][-MAX_HISTORY_LENGTH:]

        await update.message.reply_text(reply)

    except Exception as e:
        print(f"Ошибка OpenAI: {e}")
        await update.message.reply_text("Произошла ошибка при обработке запроса.")

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

    import asyncio
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



