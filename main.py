import os
import re
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from openai import AsyncOpenAI

# Load tokens from environment
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Initialize Flask app
app = Flask(name)

# Initialize Telegram bot
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Check for offensive language
def contains_insult(text):
    return bool(re.search(r'\b(idiot|moron|dumb|asshole|stupid|fuck|shit|bitch)\b', text.lower()))

# Check for image generation request
def wants_image(text):
    return "generate image" in text.lower() or "create picture" in text.lower()

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    text = update.message.text.lower()
    if "karik" not in text:
        return

    prompt = update.message.text

    try:
        if contains_insult(text):
            insult_reply = f"You said: '{update.message.text}'. That's not very nice. Here's some sarcasm for you."
            response = await openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": insult_reply}]
            )
        elif wants_image(text):
            image_response = await openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                n=1,
                size="1024x1024"
            )
            image_url = image_response.data[0].url
            await update.message.reply_photo(photo=image_url)
            return
        else:
            response = await openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            )

        reply = response.choices[0].message.content
        await update.message.reply_text(reply)

    except Exception as e:
        print("OpenAI error:", e)
        await update.message.reply_text("OpenAI error: " + str(e))


application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    async def process():
        try:
            await application.initialize()
            update = Update.de_json(request.get_json(force=True), application.bot)
            await application.process_update(update)
        except Exception as e:
            import traceback
            print("Webhook error:")
            traceback.print_exc()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(process())
    return "OK"

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!"

if name == "main":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



