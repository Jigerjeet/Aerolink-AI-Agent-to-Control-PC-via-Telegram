import os
import time
import webbrowser
import pyautogui
import psutil
import cv2
import ollama
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from AppOpener import open as open_app
import re

# -- CONFIG ---
TOKEN = "your_token"
MY_CHAT_ID = "@example"  # Replace with your ID from @userinfobot
MODEL_NAME = 'gemma:2b'


# --- ACTION LOGIC ---
def run_local_task(intent_summary):
    cmd = intent_summary.lower()

    # 1. System Stats (CPU/RAM)
    if "stats" in cmd or "health" in cmd:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory().percent
        return f"📊 System Health:\nCPU Usage: {cpu}%\nRAM Usage: {ram}%"

    # 2. Webcam Snapshot
    elif "webcam" in cmd or "camera" in cmd or "photo" in cmd:
        cam = cv2.VideoCapture(0)
        ret, frame = cam.read()
        if ret:
            cv2.imwrite("webcam_shot.png", frame)
            cam.release()
            return "SEND_FILE:webcam_shot.png"
        cam.release()
        return "❌ Failed to access webcam."

    # 3. Volume Control
    elif "volume up" in cmd:
        for _ in range(5): pyautogui.press('volumeup')
        return "🔊 Volume turned up."
    elif "volume down" in cmd:
        for _ in range(5): pyautogui.press('volumedown')
        return "🔉 Volume turned down."

    # 4. File Management (List Downloads)
    elif "list files" in cmd or "downloads" in cmd:
        download_path = os.path.expanduser("~/Downloads")
        files = os.listdir(download_path)
        file_list = "\n".join(files[:15])  # Show first 15 files
        return f"📂 Recent Downloads:\n{file_list}"

    # 5. Lock PC
    elif "lock" in cmd:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return "🔒 PC has been locked."

    # 6. Existing Features (YouTube/Screenshot/Google)
    elif "youtube" in cmd:
        search = cmd.split("search")[-1].strip() if "search" in cmd else "music"
        webbrowser.open(f"https://www.youtube.com/results?search_query={search}")
        return f"🎬 Searching YouTube for {search}."

    elif "screenshot" in cmd:
        pyautogui.screenshot("screen.png")
        return "SEND_FILE:screen.png"


    elif "open" in cmd:

        # 1. Gemma might be too wordy. Let's find the word after 'action' or 'open'

        # This splits the string and looks for the last word which is usually the app name

        parts = cmd.split()

        app_to_open = parts[-1].strip()

        # If the AI says "open google chrome", we want "google chrome"

        if "open" in cmd:
            app_to_open = cmd.split("open")[-1].strip()

        try:

            # We use match_closest to handle things like "excel" vs "microsoft excel"

            open_app(app_to_open, match_closest=True, output=False)

            return f"🚀 Command sent to Windows: {app_to_open}"

        except Exception as e:

            return f"❌ AppOpener Error: {str(e)}"


    return "✅ Instruction processed: " + intent_summary


# --- TELEGRAM HANDLER ---
async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # SECURITY: Ignore anyone who isn't YOU

    user_text = update.message.text
    await update.message.reply_text("🧠 Gemma 2B is thinking...")

    # ASKING GEMMA: We give Gemma a strict "System Prompt" to act as a parser
    system_prompt = (
        "You are a computer controller. Translate the user request into a short "
        "instruction like 'YouTube search [topic]' or 'Take screenshot'. "
        "User says: "
    )

    response = ollama.generate(model='gemma:2b', prompt=system_prompt + user_text)
    ai_interpretation = response['response'].strip()

    # EXECUTE
    status = run_local_task(ai_interpretation)

    # REPLY
    if status.startswith("SEND_FILE:"):
        file_path = status.split(":")[1]
        await update.message.reply_photo(photo=open(file_path, 'rb'), caption="Here is your screen!")
    else:
        await update.message.reply_text(status)


if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_request))
    print("🚀 TelePath AI is running locally...")
    app.run_polling()