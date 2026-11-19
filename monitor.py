import os
import json
import smtplib
import urllib.parse
from email.message import EmailMessage
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PORTAL_URL = "https://results3.jntuh.ac.in/"
LOGIN_URL = "https://results3.jntuh.ac.in/login"
SEEN_FILE = "seen_notices.json"

# Matches all B.Tech Regular, Supply, and Revaluation notices
REQUIRED_WORD = "BTECH"
EXAM_KEYWORDS = ["R22", "REGULAR", "SUPPLY", "SUPPLEMENTARY", "IV-I", "IV-II", "III-II", "I-II", "RC", "RV"]

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_seen(seen_list):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen_list, f, indent=2)

def fetch_notices():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(PORTAL_URL, headers=headers, timeout=15, verify=False)
        resp.raise_for_status()
    except Exception as e:
        print(f"Portal temporarily busy or unreachable: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    notices = []
    for tag in soup.find_all(["li", "p", "div", "a", "td"]):
        text = " ".join(tag.get_text(" ", strip=True).split())
        if "RESULTS PUBLISHED" in text.upper() and len(text) < 350:
            if text not in notices:
                notices.append(text)
    return notices

def send_whatsapp(message_text):
    phone = os.environ.get("WHATSAPP_PHONE", "").strip()
    apikey = os.environ.get("WHATSAPP_APIKEY", "").strip()
    if not phone or not apikey:
        return
    encoded_msg = urllib.parse.quote(message_text)
    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_msg}&apikey={apikey}"
    try:
        r = requests.get(url, timeout=15)
        print("WhatsApp alert status:", r.status_code)
    except Exception as e:
        print("WhatsApp failed:", e)

def send_gmail(subject, body):
    gmail_user = os.environ.get("GMAIL_USER", "").strip()
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    if not gmail_user or not gmail_pass:
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = gmail_user
    msg.set_content(body)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(gmail_user, gmail_pass)
            server.send_message(msg)
        print("Gmail alert sent.")
    except Exception as e:
        print("Gmail failed:", e)

def main():
    seen = load_seen()
    first_run = not os.path.exists(SEEN_FILE)
    notices = fetch_notices()

    if not notices:
        return

    # On very first run, baseline existing old notices so you don't get spammed
    if first_run:
        save_seen(notices)
        print(f"Baseline saved with {len(notices)} existing notices.")
        return

    new_found = False
    for notice in notices:
        upper_notice = notice.upper()
        if notice not in seen:
            seen.append(notice)
            new_found = True

            if REQUIRED_WORD in upper_notice and any(k in upper_notice for k in EXAM_KEYWORDS):
                alert_msg = (
                    f"🚨 *JNTUH RESULT OUT NOW!* 🚨\n\n"
                    f"{notice}\n\n"
                    f"⚡ *Direct Login (Beat Traffic):*\n{LOGIN_URL}"
                )
                send_whatsapp(alert_msg)
                send_gmail(f"[JNTUH RESULT OUT] {notice[:65]}", alert_msg)

    if new_found:
        save_seen(seen)

if __name__ == "__main__":
    main()
