from flask import Flask, jsonify, request
import requests
import smtplib
import sqlite3
import os
from email.mime.text import MIMEText
from datetime import datetime
import threading
import time
import urllib.request

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_PASS = os.environ.get("GMAIL_PASS", "")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "sars2025")
MIN_MAGNITUDE = 4.0

def init_db():
    conn = sqlite3.connect("sars.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS emails
                 (id INTEGER PRIMARY KEY, email TEXT UNIQUE, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS sent_quakes
                 (id INTEGER PRIMARY KEY, quake_id TEXT UNIQUE, magnitude REAL, location TEXT, sent_at TEXT)""")
    conn.commit()
    conn.close()

def get_emails():
    conn = sqlite3.connect("sars.db")
    c = conn.cursor()
    c.execute("SELECT email FROM emails")
    emails = [row[0] for row in c.fetchall()]
    conn.close()
    return emails

def already_sent(quake_id):
    conn = sqlite3.connect("sars.db")
    c = conn.cursor()
    c.execute("SELECT id FROM sent_quakes WHERE quake_id=?", (quake_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def mark_sent(quake_id, magnitude, location):
    conn = sqlite3.connect("sars.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO sent_quakes (quake_id, magnitude, location, sent_at) VALUES (?,?,?,?)",
              (quake_id, magnitude, location, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def parse_kandilli():
    quakes = []
    try:
        url = "http://www.koeri.boun.edu.tr/scripts/lst0.asp"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=15)
        content = response.read().decode('windows-1254', errors='ignore')
        lines = content.split('\n')
        for line in lines:
            try:
                parts = line.split()
                if len(parts) < 9:
                    continue
                if not parts[0][0:4].isdigit():
                    continue
                mag = float(parts[6])
                location = ' '.join(parts[8:])
                depth = float(parts[4])
                date = parts[0]
                time_str = parts[1]
                quake_id = f"{date}_{time_str}_{mag}"
                quakes.append({
                    'id': quake_id,
                    'magnitude': mag,
                    'location': location,
                    'depth': depth,
                    'time': f"{date} {time_str}",
                    'severity': 'severe' if mag >= 5 else 'moderate' if mag >= 4 else 'minor'
                })
            except:
                continue
    except Exception as e:
        print(f"Kandilli hata: {e}")
    return quakes

def get_ai_analysis(magnitude, location, depth):
    if not GEMINI_API_KEY:
        return "AI analizi için API anahtarı gerekli."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""Türkiye'de {magnitude} büyüklüğünde, {location} bölgesinde, {depth} km derinlikte deprem oldu.
Kısa ve sade Türkçe analiz yaz. Max 3 cümle. Teknik değil, halk için yaz.
Büyüklük ne anlama gelir, ne yapmalılar, tehlike var mı?"""
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = requests.post(url, json=body, timeout=10)
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "AI analizi şu an kullanılamıyor."

def send_email(to_list, subject, body):
    if not GMAIL_USER or not GMAIL_PASS:
        return False
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            for to in to_list:
                msg = MIMEText(body, "plain", "utf-8")
                msg["Subject"] = subject
                msg["From"] = GMAIL_USER
                msg["To"] = to
                server.sendmail(GMAIL_USER, to, msg.as_string())
        return True
    except Exception as e:
        print(f"Email hata: {e}")
        return False

def check_and_notify():
    while True:
        try:
            quakes = parse_kandilli()
            for q in quakes:
                if q["magnitude"] >= MIN_MAGNITUDE and not already_sent(q["id"]):
                    ai = get_ai_analysis(q["magnitude"], q["location"], q["depth"])
                    emails = get_emails()
                    if emails:
                        subject = f"⚠️ DEPREM | {q['magnitude']} Mw - {q['location']}"
                        body = f"""SARS - Deprem Bildirimi

Büyüklük: {q['magnitude']} Mw
Konum: {q['location']}
Derinlik: {q['depth']} km
Zaman: {q['time']}

AI Analiz:
{ai}

---
Kaynak: Kandilli Rasathanesi"""
                        send_email(emails, subject, body)
                    mark_sent(q["id"], q["magnitude"], q["location"])
        except Exception as e:
            print(f"Notify hata: {e}")
        time.sleep(60)

@app.route("/api/quakes")
def api_quakes():
    quakes = parse_kandilli()
    result = []
    for q in quakes[:10]:
        q["ai"] = get_ai_analysis(q["magnitude"], q["location"], q["depth"])
        result.append(q)
    return jsonify(result)

@app.route("/api/subscribe", methods=["POST"])
def subscribe():
    email = request.json.get("email", "").strip()
    if not email or "@" not in email:
        return jsonify({"error": "Geçersiz email"}), 400
    try:
        conn = sqlite3.connect("sars.db")
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO emails (email, created_at) VALUES (?,?)",
                  (email, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({"ok": True})
    except:
        return jsonify({"error": "Hata"}), 500

@app.route("/api/admin/emails", methods=["GET"])
def admin_emails():
    if request.headers.get("X-Admin-Pass") != ADMIN_PASS:
        return jsonify({"error": "Yetkisiz"}), 401
    return jsonify(get_emails())

@app.route("/api/admin/test", methods=["POST"])
def admin_test():
    if request.headers.get("X-Admin-Pass") != ADMIN_PASS:
        return jsonify({"error": "Yetkisiz"}), 401
    emails = get_emails()
    if not emails:
        return jsonify({"error": "Kayıtlı email yok"}), 400
    send_email(emails, "SARS Test Bildirimi", "Bu bir test mesajıdır. Sistem çalışıyor.")
    return jsonify({"ok": True, "sent": len(emails)})

@app.route("/")
def index():
    return open('index.html', encoding='utf-8').read()

if __name__ == "__main__":
    init_db()
    t = threading.Thread(target=check_and_notify, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
