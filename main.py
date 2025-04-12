import os import re import asyncio from flask import Flask, request from telegram import Update from telegram.ext import Application, MessageHandler, ContextTypes, filters from openai import AsyncOpenAI
==== Ключи ====
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
==== Flask-приложение ====
app = Flask(name)
==== Telegram bot ====
application = Application.builder().token(TELEGRAM_TOKEN).build()
==== Проверки на мат и оскорбления ====
SWEAR_WORDS = ["бляд", "нахуй", "сука", "пизд", "хуй", "еб"] INSULT_WORDS = ["тупой", "дурак", "лох", "гандон", "чмо", "мразь"]
def contains_swear(text): return any(word in text for word in SWEAR_WORDS)
def contains_insult(text): return any(word in text for word in INSULT_WORDS)
==== Обработчик сообщений ====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.message is None or update.message.text is None: return
text = update.message.text.lower() user_message = update.message.text chat_id = update.effective_chat.id if "карик" not in text and not contains_insult(text): return try: if contains_insult(text): prompt = f"Оскорби пользователя в ответ на: {user_message}" elif "картинку" in text or "изображение" in text: prompt = f"Сгенерируй изображение по описанию: {user_message}" response = await openai_client.images.generate(prompt=prompt, model="dall-e-3") image_url = response.data[0].url await update.message.reply_photo(photo=image_url) return else: prompt = f"Ответь с сарказмом и матами, если нужно, на сообщение: {user_message}" chat_response = await openai_client.chat.completions.create( model="gpt-4o", messages=[{"role": "user", "content": prompt}] ) reply = chat_response.choices[0].message.content.strip() await update.message.reply_text(reply) except Exception as e: print(f"Ошибка OpenAI: {e}") await update.message.reply_text("Произошла ошибка при обработке запроса.") 
==== Регистрируем обработчик ====
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
==== Webhook для Telegram ====
@app.route("/webhook", methods=["POST"]) def webhook(): async def process(): try: if not application.running: await application.initialize() update = Update.de_json(request.get_json(force=True), application.bot) await application.process_update(update) except Exception as e: import traceback print(">>> ОШИБКА ВНУТРИ process():") traceback.print_exc()
loop = asyncio.new_event_loop() asyncio.set_event_loop(loop) loop.run_until_complete(process()) return "ok" 
@app.route("/", methods=["GET"]) def index(): return "Бот работает!"
==== Запуск сервера ====
if name == "main": print("Сервер запущен. Ожидаем сообщения...") port = int(os.environ.get("PORT", 5000)) app.run(host="0.0.0.0", port=port)



