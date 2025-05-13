import requests
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def send_telegram_message(chat_id, message):
    postfix = "\n\n"
    full_message = f"{message}{postfix}"

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": full_message}
    response = requests.post(url, data=data)
    return response.ok

