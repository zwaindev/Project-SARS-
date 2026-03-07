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

# ── CONFIG ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GMAIL_USER     = os.environ.get("GMAIL_USER", "")
GMAIL_PASS     = os.environ.get("GMAIL_PASS", "")
ADMIN_PASS     = os.environ.get("ADMIN_PASS", "sars2026")
MIN_MAGNITUDE  = 4.0
DB_PATH        = "/tmp/sars.db"

# ── DATABASE ──────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT    UNIQUE NOT NULL,
            created_at TEXT    NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sent_quakes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            quake_id   TEXT    UNIQUE NOT NULL,
            magnitude  REAL,
            location   TEXT,
            sent_at    TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_emails():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT email FROM emails ORDER BY created_at DESC")
    result = [row[0] for row in c.fetchall()]
    conn.close()
    return result

def already_sent(quake_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM sent_quakes WHERE quake_id = ?", (quake_id,))
    found = c.fetchone() is not None
    conn.close()
    return found

def mark_sent(quake_id, magnitude, location):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO sent_quakes (quake_id, magnitude, location, sent_at) VALUES (?,?,?,?)",
        (quake_id, magnitude, location, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

# ── KANDİLLİ ─────────────────────────────────────────────────────────────────
def parse_kandilli():
    quakes = []
    try:
        url = "http://www.koeri.boun.edu.tr/scripts/lst0.asp"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        content = resp.read().decode("windows-1254", errors="ignore")

        for line in content.split("\n"):
            try:
                parts = line.split()
                if len(parts) < 9:
                    continue
                if not parts[0][:4].isdigit():
                    continue

                date     = parts[0]
                time_str = parts[1]
                depth    = float(parts[4])
                mag      = float(parts[6])
                location = " ".join(parts[8:]).strip()
                quake_id = f"{date}_{time_str}_{mag}"

                severity = (
                    "severe"   if mag >= 5.0 else
                    "moderate" if mag >= 4.0 else
                    "minor"
                )

                quakes.append({
                    "id":        quake_id,
                    "magnitude": mag,
                    "location":  location,
                    "depth":     depth,
                    "time":      f"{date} {time_str}",
                    "severity":  severity,
                })
            except Exception:
                continue

    except Exception as e:
        print(f"[Kandilli] {e}")

    return quakes

# ── GEMİNİ AI ────────────────────────────────────────────────────────────────
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

def get_ai_analysis(magnitude, location, depth):
    """
    Gemini 1.5 Flash ile deprem analizi üretir.
    GEMINI_API_KEY environment variable'ı yoksa None döner.
    """
    key = GEMINI_API_KEY
    if not key:
        print("[Gemini] GEMINI_API_KEY eksik — analiz atlandı.")
        return None

    prompt = (
        f"Türkiye'de {magnitude} büyüklüğünde bir deprem meydana geldi.\n"
        f"Bölge: {location}\n"
        f"Derinlik: {depth} km\n\n"
        "Lütfen bu deprem hakkında sade, anlaşılır Türkçe 2 cümlelik bir analiz yaz. "
        "Teknik terim kullanma. Halk için yaz: bu depremin ne anlama geldiğini ve "
        "insanların şu an ne yapması gerektiğini belirt."
    )

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 150,
        }
    }

    try:
        resp = requests.post(
            GEMINI_URL,
            params={"key": key},
            json=payload,
            timeout=12
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip()

    except requests.exceptions.HTTPError as e:
        # API hatası — key yanlış veya kota doldu
        print(f"[Gemini] HTTP {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as e:
        print(f"[Gemini] Hata: {e}")
        return None

# ── EMAIL ─────────────────────────────────────────────────────────────────────
def send_email(to_list, subject, body):
    if not GMAIL_USER or not GMAIL_PASS:
        print("[Email] GMAIL_USER veya GMAIL_PASS eksik.")
        return False
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            for to in to_list:
                msg            = MIMEText(body, "plain", "utf-8")
                msg["Subject"] = subject
                msg["From"]    = GMAIL_USER
                msg["To"]      = to
                server.sendmail(GMAIL_USER, to, msg.as_string())
        print(f"[Email] {len(to_list)} adrese gönderildi.")
        return True
    except Exception as e:
        print(f"[Email] Hata: {e}")
        return False

# ── ARKA PLAN WORKER ─────────────────────────────────────────────────────────
def check_and_notify():
    print("[Worker] Başlatıldı.")
    while True:
        try:
            quakes = parse_kandilli()
            for q in quakes:
                if q["magnitude"] >= MIN_MAGNITUDE and not already_sent(q["id"]):
                    ai_text = get_ai_analysis(q["magnitude"], q["location"], q["depth"])
                    emails  = get_emails()

                    if emails:
                        subject = f"⚠️ DEPREM | {q['magnitude']} Mw — {q['location']}"
                        body = (
                            f"SARS — Deprem Bildirimi\n"
                            f"{'='*44}\n\n"
                            f"Büyüklük : {q['magnitude']} Mw\n"
                            f"Konum    : {q['location']}\n"
                            f"Derinlik : {q['depth']} km\n"
                            f"Zaman    : {q['time']}\n\n"
                        )
                        if ai_text:
                            body += f"Yapay Zeka Analizi:\n{ai_text}\n\n"
                        body += (
                            f"{'='*44}\n"
                            f"Kaynak: Kandilli Rasathanesi — Boğaziçi Üniversitesi\n"
                            f"https://project-sars.onrender.com\n"
                        )
                        send_email(emails, subject, body)

                    mark_sent(q["id"], q["magnitude"], q["location"])

        except Exception as e:
            print(f"[Worker] Hata: {e}")

        time.sleep(60)

# ── ROUTES ────────────────────────────────────────────────────────────────────
@app.route("/api/quakes")
def api_quakes():
    quakes = parse_kandilli()[:10]
    for q in quakes:
        ai    = get_ai_analysis(q["magnitude"], q["location"], q["depth"])
        q["ai"] = ai if ai else "AI analizi şu an kullanılamıyor."
    return jsonify(quakes)

@app.route("/api/subscribe", methods=["POST"])
def subscribe():
    data  = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()

    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({"error": "Geçersiz e-posta adresi."}), 400

    try:
        conn = sqlite3.connect(DB_PATH)
        c    = conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO emails (email, created_at) VALUES (?, ?)",
            (email, datetime.now().isoformat())
        )
        inserted = c.rowcount
        conn.commit()
        conn.close()

        if inserted == 0:
            return jsonify({"error": "Bu e-posta zaten kayıtlı."}), 409
        return jsonify({"ok": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats")
def api_stats():
    conn  = sqlite3.connect(DB_PATH)
    c     = conn.cursor()
    c.execute("SELECT COUNT(*) FROM emails")
    count = c.fetchone()[0]
    conn.close()
    return jsonify({"subscribers": count})

@app.route("/api/admin/emails", methods=["GET"])
def admin_emails():
    if request.headers.get("X-Admin-Pass") != ADMIN_PASS:
        return jsonify({"error": "Yetkisiz."}), 401
    return jsonify(get_emails())

@app.route("/api/admin/delete", methods=["POST"])
def admin_delete():
    if request.headers.get("X-Admin-Pass") != ADMIN_PASS:
        return jsonify({"error": "Yetkisiz."}), 401
    data  = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    if not email:
        return jsonify({"error": "E-posta belirtilmedi."}), 400
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()
    c.execute("DELETE FROM emails WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/admin/test", methods=["POST"])
def admin_test():
    if request.headers.get("X-Admin-Pass") != ADMIN_PASS:
        return jsonify({"error": "Yetkisiz."}), 401
    emails = get_emails()
    if not emails:
        return jsonify({"error": "Kayıtlı e-posta yok."}), 400
    ok = send_email(
        emails,
        "SARS — Test Bildirimi",
        "Bu bir test mesajıdır. Sistem düzgün çalışıyor.\n\nhttps://project-sars.onrender.com"
    )
    return jsonify({"ok": ok, "sent": len(emails) if ok else 0})

@app.route("/api/gemini/test")
def gemini_test():
    """Gemini bağlantısını test eder — tarayıcıdan açılabilir."""
    if not GEMINI_API_KEY:
        return jsonify({"ok": False, "error": "GEMINI_API_KEY environment variable eksik."})
    result = get_ai_analysis(5.2, "İzmir (Bornova)", 8.0)
    if result:
        return jsonify({"ok": True, "sample": result})
    return jsonify({"ok": False, "error": "Gemini yanıt vermedi. Key'i kontrol et."})

@app.route("/")
def index():
    return open("index.html", encoding="utf-8").read()

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    t = threading.Thread(target=check_and_notify, daemon=True)
    t.start()
    app.run(
        host  = "0.0.0.0",
        port  = int(os.environ.get("PORT", 5000)),
        debug = False
    )
    
