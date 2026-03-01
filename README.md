# MediLink – Smart Telemedicine & Pharmacy Connection System

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- MySQL Server (XAMPP/MySQL Workbench)
- Tesseract OCR (optional, for image reports)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup MySQL
Start MySQL and ensure it's running on `localhost:3306`.
- Default config: user=`root`, password=`` (empty)
- The app **auto-creates** the database and tables on first run.
- To change credentials, edit `DB_CONFIG` in `app.py`.

Optional – import schema manually:
```bash
mysql -u root -p < schema.sql
```

### 3. Run the App
```bash
python app.py
```

Open: [http://localhost:5000](http://localhost:5000)

---

## 🔑 Default Admin Login
- **Email:** `admin@medilink.com`
- **Password:** `admin123`

---

## 👥 User Roles

| Role | Portal | Key Features |
|------|--------|--------------|
| Patient | `/patient/dashboard` | Upload reports, order medicines, view health metrics, find chemists |
| Chemist | `/chemist/dashboard` | Manage inventory, process orders, low stock alerts |
| Admin | `/admin/dashboard` | User management, order monitoring, analytics |

---

## 📁 Project Structure
```
MediLink/
├── app.py              # Flask backend
├── schema.sql          # Database schema
├── requirements.txt    # Python dependencies
├── templates/
│   ├── base.html       # Base template
│   ├── layout.html     # Authenticated layout with sidebar
│   ├── index.html      # Landing page
│   ├── login.html      # Login page
│   ├── register.html   # Registration page
│   ├── patient/        # Patient templates
│   ├── chemist/        # Chemist templates
│   └── admin/          # Admin templates
├── static/
│   ├── css/style.css   # Main stylesheet
│   └── js/main.js      # Interactive JS
└── uploads/            # Uploaded files
```

---

## 🧬 Medical Report Extraction
- Upload PDF or image (JPG/PNG) medical reports
- System auto-extracts: **BP, Sugar, Hemoglobin, Cholesterol, Heart Rate, Weight, Height**
- Uses PyPDF2 (PDF) + pytesseract (images)
- Results stored in `health_metrics` table
- No manual entry required

## 🗺️ Map Feature
- Uses **OpenStreetMap + Leaflet.js** (free, no API key needed)
- Shows all registered chemists on map
- Click marker → see details
- Auto-detects user location

---

## 🎨 Design System
- Color: `#2563EB` (Primary Blue) + `#10B981` (Accent Green)
- Fonts: Inter + Outfit (Google Fonts)
- Glass-effect cards, gradient sidebar
- Smooth animations + count-up effects
- Toast notifications, modals, sortable tables
- Mobile responsive
