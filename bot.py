import logging
import re
from io import BytesIO
from datetime import datetime, timedelta
from PIL import Image
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI
from googleapiclient.discovery import build
import yt_dlp
from deep_translator import GoogleTranslator

# ------------------- CONFIG -------------------
BOT_TOKEN = "8255581378:AAE8_9JzwrfStRNhMh5sBuCLB0S7_7i8Buc"
OPENAI_API_KEY = "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"
GOOGLE_API_KEY = "AIzaSyB88amZV9eF7ygX79XUIBOwe-fUOhH_j_w"
CSE_ID = "5777c0fc3e0b44a82"

client = OpenAI(api_key=OPENAI_API_KEY)
user_memory = {}
last_question = {}

# ------------------- LOGGING -------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ------------------- HELPERS -------------------
def highlight_terms(text, terms):
    for term in terms:
        escaped_term = re.escape(term)
        text = re.sub(f"\\b({escaped_term})\\b", r"<b>\\1</b>", text, flags=re.IGNORECASE)
    return text

def google_search(query, num_results=5):
    service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
    res = service.cse().list(q=query, cx=CSE_ID, num=num_results).execute()
    snippets = []
    if "items" in res:
        for item in res["items"]:
            snippet = item.get("snippet") or item.get("title")
            if snippet:
                snippets.append(snippet)
    return "\n".join(snippets)

# ------------------- CHATGPT + GOOGLE -------------------
async def abby_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("❓ Please provide a question after /abby.")
        return

    # Creator questions
    creator_questions = [
        "who owned you", "who created your code", "which company own you",
        "please tell me truth who created you"
    ]
    if any(q in query.lower() for q in creator_questions):
        await update.message.reply_text("I am created by @WuwaRoccia 🤖")
        return
    if "you are still tell lie" in query.lower():
        await update.message.reply_text("No, I am not telling a lie. I am created by @WuwaRoccia 🤖")
        return

    # Remember last question
    last_question[user_id] = query
    user_memory.setdefault(user_id, []).append({"role": "user", "content": query})

    # Step 1: Google search
    search_results = google_search(query)
    system_prompt = (
        f"Summarize the following Google search results concisely:\n{search_results}"
        if search_results else "Summarize this query concisely."
    )

    # Step 2: ChatGPT summary
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}] + user_memory[user_id],
        max_tokens=300
    )
    answer = response.choices[0].message.content
    user_memory[user_id].append({"role": "assistant", "content": answer})

    # Step 3: Highlight
    query_words = set(re.findall(r"\w+", query))
    answer = highlight_terms(answer, query_words)
    await update.message.reply_html(answer)

# ------------------- TRANSLATION -------------------
async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text and update.message.reply_to_message:
        text = update.message.reply_to_message.text or update.message.reply_to_message.caption
    if not text:
        await update.message.reply_text("🌐 Provide text or reply to a message to translate.")
        return
    translated = GoogleTranslator(source="auto", target="en").translate(text)
    await update.message.reply_text(f"🌐 Translation: {translated}")

# ------------------- MAIN -------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("abby", abby_handler))
    app.add_handler(CommandHandler("translate", translate))

    app.run_polling()

if __name__ == "__main__":
    main()

