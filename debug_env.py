import os, requests
from dotenv import load_dotenv
load_dotenv()
tok = os.getenv("TELEGRAM_BOT_TOKEN")
cid = os.getenv("TELEGRAM_CHAT_ID")
print("Token suffix:", (tok or "")[-6:], " ChatID:", cid)
r1 = requests.get(f"https://api.telegram.org/bot{tok}/getMe")
print("getMe:", r1.status_code, r1.text[:150])
r2 = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                   data={"chat_id": cid, "text": "✅ Test z debug skriptu"})
print("sendMessage:", r2.status_code, r2.text[:200])
