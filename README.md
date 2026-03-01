# 💊 MediLink – Smart Telemedicine & Pharmacy Connection System

A full-stack healthcare platform connecting **Patients**, **Chemists**, and **Admins**. Built with Flask, MySQL, and Vanilla JS.

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.10+
- MySQL 8.0+
- (Optional) Tesseract OCR — for image-based report reading

### Setup

```bash
# 1. Clone the project
git clone <your-repo-url>
cd MediLink

# 2. Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your MySQL credentials

# 5. Run
python app.py
```

App runs at **http://localhost:5000**

---

## 🔑 Default Login

| Role    | Email                  | Password   |
|---------|------------------------|------------|
| Admin   | admin@medilink.com     | admin123   |
| Chemist | Register at /register  | Your choice |
| Patient | Register at /register  | Your choice |

---

## 🌐 Deploy to Render

### 1. Push to GitHub

```bash
git add .
git commit -m "Production ready"
git push origin main
```

### 2. Create Web Service on Render
- Go to [render.com](https://render.com) → **New → Web Service**
- Connect your GitHub repository
- Set:
  - **Build Command:** `pip install -r requirements.txt`
  - **Start Command:** `gunicorn app:app`
  - **Runtime:** Python 3

### 3. Set Environment Variables on Render

| Variable      | Value                        |
|---------------|------------------------------|
| `SECRET_KEY`  | A long random string         |
| `DB_HOST`     | Your MySQL host              |
| `DB_USER`     | Your MySQL user              |
| `DB_PASSWORD` | Your MySQL password          |
| `DB_NAME`     | `medilink`                   |
| `FLASK_DEBUG` | `false`                      |

> 💡 Render sets `PORT` automatically — do not set it manually.

### 4. Database on Render
Use **PlanetScale**, **Railway**, or **Aiven** for a free hosted MySQL instance. Set the connection details as env vars above.

---

## 🧬 Features

### Patient Portal
- 🏥 Dashboard with health overview
- 📋 Upload prescriptions (PDF/image)
- 📄 Upload medical reports → auto-extract health metrics via OCR
- 💊 Search medicines by name/category
- 🛒 Place and track orders
- 🗺️ Find nearby chemists (Leaflet.js + OpenStreetMap)
- ❤️ Health Metrics & AI Wellbeing Insights

### Chemist Portal
- 📦 Manage medicine inventory (stock, price, expiry dates)
- 🔴 Expiry date tracking with color-coded badges
- 📬 View and update incoming orders

### Admin Panel
- 👥 View and manage all users
- 📦 Monitor all platform orders
- 📊 System analytics dashboard

---

## 🔬 OCR Behaviour

The app handles OCR gracefully in all environments:

| Environment         | Tesseract Status  | Upload Result                    |
|---------------------|-------------------|----------------------------------|
| Local with Tesseract| ✅ Available       | File saved + metrics extracted   |
| Render (no binary)  | ⚠️ Unavailable    | File saved + friendly message    |
| Any OCR runtime error | 🔴 Error        | File saved + friendly message    |

**The upload never fails.** Only metric extraction is skipped when OCR is unavailable.

---

## 📁 Project Structure

```
MediLink/
├── app.py                  # Flask backend (all routes)
├── requirements.txt        # Python dependencies
├── Procfile                # Gunicorn start command
├── .env.example            # Environment variable template
├── render.yaml             # Render.com deployment blueprint
├── schema.sql              # Database schema reference
├── static/
│   ├── css/style.css       # Design system & all styles
│   └── js/main.js          # Toast, Modal, Table utilities
├── templates/
│   ├── layout.html         # Shared sidebar layout
│   ├── index.html          # Landing page
│   ├── login.html          # Login page
│   ├── register.html       # Registration page
│   ├── admin/              # Admin panel templates
│   ├── chemist/            # Chemist portal templates
│   └── patient/            # Patient portal templates
└── uploads/                # Uploaded files (gitignored)
```

---

## ⚙️ Environment Variables Reference

| Variable         | Required | Default       | Description                              |
|------------------|----------|---------------|------------------------------------------|
| `SECRET_KEY`     | Yes      | dev fallback  | Flask session encryption key             |
| `DB_HOST`        | Yes      | `localhost`   | MySQL server hostname                    |
| `DB_USER`        | Yes      | `root`        | MySQL username                           |
| `DB_PASSWORD`    | Yes      | *(empty)*     | MySQL password                           |
| `DB_NAME`        | Yes      | `medilink`    | MySQL database name                      |
| `FLASK_DEBUG`    | No       | `false`       | Enable debug mode (never `true` in prod) |
| `PORT`           | No       | `5000`        | Server port (Render sets automatically)  |
| `UPLOAD_FOLDER`  | No       | `./uploads`   | Where uploaded files are stored          |
| `TESSERACT_CMD`  | No       | *(auto)*      | Path to tesseract binary (Windows only)  |

---

## 🛡️ Security Notes

- All passwords hashed with `werkzeug.security` (PBKDF2-SHA256)
- Session data encrypted with `SECRET_KEY`
- File uploads validated by extension and size (16 MB max)
- Admin account protected from deletion
- SQL injection protected via parameterized queries (PyMySQL)
