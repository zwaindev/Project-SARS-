<div align="center">

```
███████╗ █████╗ ██████╗ ███████╗
██╔════╝██╔══██╗██╔══██╗██╔════╝
███████╗███████║██████╔╝███████╗
╚════██║██╔══██║██╔══██╗╚════██║
███████║██║  ██║██║  ██║███████║
╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
```

# SARS — Sismik Ağ Raporlama Sistemi
### *Seismic Alert & Reporting System*

[![Live](https://img.shields.io/badge/🌐_Live-project--sars.onrender.com-blue?style=flat-square)](https://project-sars.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.x-green?style=flat-square&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-latest-lightgrey?style=flat-square&logo=flask)](https://flask.palletsprojects.com)
[![Render](https://img.shields.io/badge/Hosted_on-Render-purple?style=flat-square)](https://render.com)
[![Status](https://img.shields.io/badge/Status-🟢_Aktif-brightgreen?style=flat-square)]()

</div>

---

## 🇹🇷 Türkçe

### Proje Nedir?

**SARS**, Türkiye'deki depremleri gerçek zamanlı takip eden ve kayıtlı kullanıcılara otomatik e-posta bildirimi gönderen bir web servisidir. Kandilli Rasathanesi verilerini her 60 saniyede bir çeker, M≥4.0 büyüklüğündeki yeni depremleri tespit eder ve anında bildirim gönderir.

> "Bir deprem olduğunda sosyal medyadan öğrenmek zorunda kalma."

### Neden Yaptım?

Türkiye dünyanın en aktif deprem kuşaklarından birinde yer alıyor. 2023 Kahramanmaraş depreminden sonra insanların olayı çok geç öğrendiğini gördüm. Bunu değiştirmek istedim. Sıfır bütçeyle, sadece telefonumu kullanarak bu sistemi geliştirdim ve deploy ettim.

### Özellikler

- 📡 **Gerçek Zamanlı Veri** — Kandilli Rasathanesi'nden her 60 saniyede veri
- 📧 **Otomatik E-posta** — M≥4.0 depremlerde anında bildirim
- 🔁 **Tekrar Yok** — Aynı deprem için mükerrer bildirim yapılmaz
- 🌐 **Web Arayüzü** — Canlı deprem listesi, rehber, deprem çantası bilgisi
- 💾 **Hafif Mimari** — SQLite, sıfır bütçe, ücretsiz hosting

### Teknik Detaylar

| Bileşen | Teknoloji |
|---------|-----------|
| Backend | Python + Flask |
| Veritabanı | SQLite (`/tmp/sars.db`) |
| Veri Kaynağı | Kandilli Rasathanesi (Boğaziçi Üniversitesi) |
| E-posta | Gmail SMTP (SSL) |
| Hosting | Render.com (Free Tier) |
| Frontend | Vanilla HTML/CSS/JS |

### Nasıl Çalışır?

```
[Kandilli Rasathanesi]
        ↓  (her 60 sn)
  parse_kandilli()
        ↓
  M ≥ 4.0 mü?  →  Hayır → atla
        ↓  Evet
  Daha önce gönderildi mi?  →  Evet → atla
        ↓  Hayır
  E-posta gönder → mark_sent()
```

### Kurulum (Local)

```bash
git clone https://github.com/zwaindev/Project-SARS-
cd Project-SARS-
pip install -r requirements.txt

# Environment variables
export GMAIL_USER="senin@gmail.com"
export GMAIL_PASS="app-password"
export ADMIN_PASS="sifren"

python app.py
```

### API Endpointleri

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/` | GET | Ana sayfa |
| `/api/quakes` | GET | Son 10 deprem (JSON) |
| `/api/subscribe` | POST | E-posta kayıt |
| `/api/stats` | GET | Kayıtlı kullanıcı sayısı |
| `/api/admin/emails` | GET | E-posta listesi (admin) |
| `/api/admin/test` | POST | Test bildirimi gönder |
| `/api/admin/delete` | POST | E-posta sil |

---

## 🇬🇧 English

### What is SARS?

**SARS** (Seismic Alert & Reporting System) is a real-time earthquake monitoring and notification service for Turkey. It fetches data from Kandilli Observatory every 60 seconds, detects earthquakes with M≥4.0 magnitude, and instantly sends email alerts to registered users.

> "Don't find out about earthquakes from social media."

### Why I Built This

Turkey sits on one of the world's most active seismic zones. After the devastating 2023 Kahramanmaraş earthquake, I realized people were finding out about quakes way too late. I wanted to change that — so I built this system from scratch, with zero budget, using only my phone.

### Features

- 📡 **Real-time Data** — Fetches from Kandilli Observatory every 60 seconds
- 📧 **Auto Email Alerts** — Instant notifications for M≥4.0+ earthquakes
- 🔁 **No Duplicates** — Each earthquake triggers only one notification
- 🌐 **Web Interface** — Live earthquake list, safety guide, emergency kit info
- 💾 **Lightweight** — SQLite database, zero cost, free hosting

### Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python + Flask |
| Database | SQLite (`/tmp/sars.db`) |
| Data Source | Kandilli Observatory (Boğaziçi University) |
| Email | Gmail SMTP (SSL) |
| Hosting | Render.com (Free Tier) |
| Frontend | Vanilla HTML/CSS/JS |

### How It Works

```
[Kandilli Observatory]
        ↓  (every 60s)
  parse_kandilli()
        ↓
  Magnitude ≥ 4.0?  →  No → skip
        ↓  Yes
  Already notified?  →  Yes → skip
        ↓  No
  Send email → mark_sent()
```

### Setup (Local)

```bash
git clone https://github.com/zwaindev/Project-SARS-
cd Project-SARS-
pip install -r requirements.txt

# Environment variables
export GMAIL_USER="your@gmail.com"
export GMAIL_PASS="app-password"
export ADMIN_PASS="yourpassword"

python app.py
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main page |
| `/api/quakes` | GET | Latest 10 earthquakes (JSON) |
| `/api/subscribe` | POST | Register email |
| `/api/stats` | GET | Subscriber count |
| `/api/admin/emails` | GET | List emails (admin) |
| `/api/admin/test` | POST | Send test notification |
| `/api/admin/delete` | POST | Delete email |

---

## 👤 Geliştirici / Developer

<div align="center">

### Tunahan — Zwain

*Bilişim öğrencisi / Informatics Student*
*Pınarbaşı Mesleki ve Teknik Anadolu Lisesi*

| Platform | Link |
|----------|------|
| 📸 Instagram | [@zwain.dev](https://instagram.com/zwain.dev) |
| 💻 GitHub | [github.com/zwaindev](https://github.com/zwaindev) |
| ✉️ E-posta / Email | zwaindev99@gmail.com |

</div>

---

## 📄 Lisans / License

Bu proje açık kaynaklıdır. Kullanabilir, değiştirebilirsin — kaynak göstermen yeterli.

This project is open source. Feel free to use and modify — just give credit.

---

<div align="center">

**🌍 [project-sars.onrender.com](https://project-sars.onrender.com)**

*Veri Kaynağı / Data Source: [Kandilli Rasathanesi — Boğaziçi Üniversitesi](http://www.koeri.boun.edu.tr)*

Made with 🧡 by **Zwain** — from Turkey

</div>
