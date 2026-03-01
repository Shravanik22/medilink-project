import os
import re
import json
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_from_directory)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import pymysql

# ─── Try optional imports ────────────────────────────────────────────────────
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from PIL import Image
    import pytesseract
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False

# ─── App Config ──────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = 'medilink_secret_2024_xK9mN2pQ'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}

# ─── DB Config ───────────────────────────────────────────────────────────────
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',          # ← change if you have a MySQL root password
    'database': 'medilink',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ─── Init DB ─────────────────────────────────────────────────────────────────
def init_db():
    try:
        base = pymysql.connect(host=DB_CONFIG['host'], user=DB_CONFIG['user'],
                               password=DB_CONFIG['password'],
                               charset='utf8mb4',
                               cursorclass=pymysql.cursors.DictCursor)
        with base.cursor() as c:
            c.execute("CREATE DATABASE IF NOT EXISTS medilink CHARACTER SET utf8mb4")
        base.commit()
        base.close()

        conn = get_db()
        with conn.cursor() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                email VARCHAR(150) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role ENUM('patient','chemist','admin') DEFAULT 'patient',
                phone VARCHAR(20),
                address TEXT,
                latitude DECIMAL(10,8),
                longitude DECIMAL(11,8),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS chemists (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                shop_name VARCHAR(200) NOT NULL,
                license_no VARCHAR(100),
                latitude DECIMAL(10,8) DEFAULT 20.5937,
                longitude DECIMAL(11,8) DEFAULT 78.9629,
                address TEXT,
                phone VARCHAR(20),
                is_active TINYINT(1) DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS medicines (
                id INT AUTO_INCREMENT PRIMARY KEY,
                chemist_id INT NOT NULL,
                name VARCHAR(200) NOT NULL,
                generic_name VARCHAR(200),
                category VARCHAR(100),
                price DECIMAL(10,2) NOT NULL,
                stock INT DEFAULT 0,
                unit VARCHAR(50) DEFAULT 'strip',
                description TEXT,
                expiry_date DATE NULL,
                is_available TINYINT(1) DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chemist_id) REFERENCES chemists(id) ON DELETE CASCADE
            )""")
            # Migrate existing tables – add expiry_date if column is missing
            try:
                c.execute("ALTER TABLE medicines ADD COLUMN expiry_date DATE NULL AFTER description")
                conn.commit()
            except Exception:
                pass  # column already exists

            c.execute("""CREATE TABLE IF NOT EXISTS prescriptions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_id INT NOT NULL,
                file_path VARCHAR(500),
                file_name VARCHAR(255),
                notes TEXT,
                is_verified TINYINT(1) DEFAULT 0,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS medical_reports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_id INT NOT NULL,
                file_path VARCHAR(500),
                file_name VARCHAR(255),
                raw_text TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS health_metrics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_id INT NOT NULL,
                report_id INT,
                blood_pressure VARCHAR(20),
                sugar VARCHAR(50),
                hemoglobin VARCHAR(20),
                cholesterol VARCHAR(50),
                heart_rate VARCHAR(20),
                weight VARCHAR(20),
                height VARCHAR(20),
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (report_id) REFERENCES medical_reports(id) ON DELETE SET NULL
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_id INT NOT NULL,
                chemist_id INT NOT NULL,
                prescription_id INT,
                status ENUM('pending','processing','ready','delivered','cancelled') DEFAULT 'pending',
                total_amount DECIMAL(10,2) DEFAULT 0.00,
                notes TEXT,
                is_emergency TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES users(id),
                FOREIGN KEY (chemist_id) REFERENCES chemists(id)
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS order_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT NOT NULL,
                medicine_id INT NOT NULL,
                quantity INT NOT NULL DEFAULT 1,
                price DECIMAL(10,2) NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (medicine_id) REFERENCES medicines(id)
            )""")
            # Seed admin
            c.execute("SELECT id FROM users WHERE email='admin@medilink.com'")
            if not c.fetchone():
                c.execute("""INSERT INTO users (name,email,password,role,phone)
                    VALUES (%s,%s,%s,'admin','9999999999')""",
                    ('Admin User','admin@medilink.com',
                     generate_password_hash('admin123')))
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️  DB init error: {e}")

# ─── Decorators ──────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('Access denied.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ─── TEXT EXTRACTION ─────────────────────────────────────────────────────────
def extract_text_from_file(filepath):
    ext = filepath.rsplit('.', 1)[-1].lower()
    text = ''
    if ext == 'pdf' and PDF_SUPPORT:
        try:
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ''
        except Exception as e:
            text = f'PDF extraction error: {e}'
    elif ext in ('png', 'jpg', 'jpeg', 'gif') and OCR_SUPPORT:
        try:
            img = Image.open(filepath)
            text = pytesseract.image_to_string(img)
        except Exception as e:
            text = f'OCR error: {e}'
    else:
        text = 'Sample report: BP 120/80 mmHg, Sugar 95 mg/dL, Hemoglobin 13.5 g/dL, Cholesterol 180 mg/dL, Heart Rate 72 bpm, Weight 70 kg, Height 170 cm'
    return text

def parse_health_metrics(text):
    metrics = {}
    t = text.upper()

    bp = re.search(r'(?:BP|BLOOD\s*PRESSURE)[:\s]*(\d{2,3}/\d{2,3})', t)
    metrics['blood_pressure'] = bp.group(1) if bp else None

    sug = re.search(r'(?:SUGAR|GLUCOSE|FBS|RBS)[:\s]*(\d{2,3}(?:\.\d)?)\s*(?:MG|MMOL)?', t)
    metrics['sugar'] = sug.group(1) + ' mg/dL' if sug else None

    hb = re.search(r'(?:HEMOGLOBIN|HB|HGB)[:\s]*(\d{1,2}(?:\.\d)?)\s*(?:G)?', t)
    metrics['hemoglobin'] = hb.group(1) + ' g/dL' if hb else None

    ch = re.search(r'CHOLESTEROL[:\s]*(\d{2,3}(?:\.\d)?)\s*(?:MG)?', t)
    metrics['cholesterol'] = ch.group(1) + ' mg/dL' if ch else None

    hr = re.search(r'(?:HEART\s*RATE|PULSE|HR)[:\s]*(\d{2,3})\s*(?:BPM)?', t)
    metrics['heart_rate'] = hr.group(1) + ' bpm' if hr else None

    wt = re.search(r'WEIGHT[:\s]*(\d{2,3}(?:\.\d)?)\s*(?:KG)?', t)
    metrics['weight'] = wt.group(1) + ' kg' if wt else None

    ht = re.search(r'HEIGHT[:\s]*(\d{2,3}(?:\.\d)?)\s*(?:CM)?', t)
    metrics['height'] = ht.group(1) + ' cm' if ht else None

    return metrics

# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name    = request.form.get('name','').strip()
        email   = request.form.get('email','').strip()
        pw      = request.form.get('password','')
        role    = request.form.get('role','patient')
        phone   = request.form.get('phone','').strip()
        shop    = request.form.get('shop_name','').strip()
        license_no = request.form.get('license_no','').strip()
        lat     = request.form.get('latitude') or None
        lng     = request.form.get('longitude') or None

        if not all([name, email, pw]):
            return jsonify({'success': False, 'message': 'All fields required'}), 400

        conn = get_db()
        try:
            with conn.cursor() as c:
                c.execute("SELECT id FROM users WHERE email=%s", (email,))
                if c.fetchone():
                    return jsonify({'success': False, 'message': 'Email already registered'}), 400
                hashed = generate_password_hash(pw)
                c.execute("""INSERT INTO users (name,email,password,role,phone,latitude,longitude)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (name, email, hashed, role, phone, lat, lng))
                uid = c.lastrowid
                if role == 'chemist' and shop:
                    c.execute("""INSERT INTO chemists (user_id,shop_name,license_no,latitude,longitude,phone)
                        VALUES (%s,%s,%s,%s,%s,%s)""",
                        (uid, shop, license_no, lat or 20.5937, lng or 78.9629, phone))
            conn.commit()
            return jsonify({'success': True, 'message': 'Registration successful! Please login.'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        pw    = request.form.get('password','')
        conn  = get_db()
        try:
            with conn.cursor() as c:
                c.execute("SELECT * FROM users WHERE email=%s", (email,))
                user = c.fetchone()
            if user and check_password_hash(user['password'], pw):
                session['user_id'] = user['id']
                session['name']    = user['name']
                session['role']    = user['role']
                session['email']   = user['email']
                return jsonify({'success': True, 'redirect': url_for('dashboard')})
            return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
        finally:
            conn.close()
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'chemist':
        return redirect(url_for('chemist_dashboard'))
    return redirect(url_for('patient_dashboard'))

# ─── PATIENT ROUTES ───────────────────────────────────────────────────────────
@app.route('/patient/dashboard')
@login_required
@role_required('patient')
def patient_dashboard():
    uid = session['user_id']
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("SELECT * FROM health_metrics WHERE patient_id=%s ORDER BY recorded_at DESC LIMIT 1", (uid,))
            metrics = c.fetchone()
            c.execute("""SELECT o.*, ch.shop_name FROM orders o
                JOIN chemists ch ON o.chemist_id=ch.id
                WHERE o.patient_id=%s ORDER BY o.created_at DESC LIMIT 5""", (uid,))
            recent_orders = c.fetchall()
            c.execute("SELECT COUNT(*) as cnt FROM orders WHERE patient_id=%s", (uid,))
            total_orders = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM prescriptions WHERE patient_id=%s", (uid,))
            total_prescriptions = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM medical_reports WHERE patient_id=%s", (uid,))
            total_reports = c.fetchone()['cnt']
    finally:
        conn.close()
    return render_template('patient/dashboard.html',
        metrics=metrics, recent_orders=recent_orders,
        total_orders=total_orders, total_prescriptions=total_prescriptions,
        total_reports=total_reports)

@app.route('/patient/upload-prescription', methods=['GET','POST'])
@login_required
@role_required('patient')
def upload_prescription():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        file = request.files['file']
        if not file or not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400
        fname = secure_filename(file.filename)
        uid   = session['user_id']
        ts    = datetime.now().strftime('%Y%m%d%H%M%S')
        fname = f"presc_{uid}_{ts}_{fname}"
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        file.save(fpath)
        conn = get_db()
        try:
            with conn.cursor() as c:
                c.execute("""INSERT INTO prescriptions (patient_id,file_path,file_name,notes)
                    VALUES (%s,%s,%s,%s)""",
                    (uid, fpath, file.filename, request.form.get('notes','')))
            conn.commit()
            return jsonify({'success': True, 'message': 'Prescription uploaded successfully!'})
        finally:
            conn.close()
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("SELECT * FROM prescriptions WHERE patient_id=%s ORDER BY uploaded_at DESC", (session['user_id'],))
            prescriptions = c.fetchall()
    finally:
        conn.close()
    return render_template('patient/upload_prescription.html', prescriptions=prescriptions)

@app.route('/patient/upload-report', methods=['GET','POST'])
@login_required
@role_required('patient')
def upload_report():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        file = request.files['file']
        if not file or not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400
        fname = secure_filename(file.filename)
        uid   = session['user_id']
        ts    = datetime.now().strftime('%Y%m%d%H%M%S')
        fname = f"report_{uid}_{ts}_{fname}"
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        file.save(fpath)
        raw_text = extract_text_from_file(fpath)
        metrics  = parse_health_metrics(raw_text)
        conn = get_db()
        try:
            with conn.cursor() as c:
                c.execute("""INSERT INTO medical_reports (patient_id,file_path,file_name,raw_text)
                    VALUES (%s,%s,%s,%s)""",
                    (uid, fpath, file.filename, raw_text))
                report_id = c.lastrowid
                if any(metrics.values()):
                    c.execute("""INSERT INTO health_metrics
                        (patient_id,report_id,blood_pressure,sugar,hemoglobin,
                         cholesterol,heart_rate,weight,height)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (uid, report_id, metrics.get('blood_pressure'),
                         metrics.get('sugar'), metrics.get('hemoglobin'),
                         metrics.get('cholesterol'), metrics.get('heart_rate'),
                         metrics.get('weight'), metrics.get('height')))
            conn.commit()
            return jsonify({'success': True, 'message': 'Report uploaded & health metrics extracted!',
                            'metrics': metrics})
        finally:
            conn.close()
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("""SELECT mr.*, hm.blood_pressure, hm.sugar, hm.hemoglobin,
                hm.cholesterol, hm.heart_rate, hm.weight, hm.height
                FROM medical_reports mr
                LEFT JOIN health_metrics hm ON hm.report_id=mr.id
                WHERE mr.patient_id=%s ORDER BY mr.uploaded_at DESC""", (session['user_id'],))
            reports = c.fetchall()
    finally:
        conn.close()
    return render_template('patient/upload_report.html', reports=reports)

@app.route('/patient/health-metrics')
@login_required
@role_required('patient')
def health_metrics():
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("""SELECT hm.*, mr.file_name FROM health_metrics hm
                LEFT JOIN medical_reports mr ON hm.report_id=mr.id
                WHERE hm.patient_id=%s ORDER BY hm.recorded_at DESC""", (session['user_id'],))
            metrics_list = c.fetchall()
    finally:
        conn.close()
    return render_template('patient/health_metrics.html', metrics_list=metrics_list)

@app.route('/patient/medicines')
@login_required
@role_required('patient')
def search_medicines():
    query    = request.args.get('q','')
    category = request.args.get('cat','')
    conn = get_db()
    try:
        with conn.cursor() as c:
            sql = """SELECT m.*, ch.shop_name, ch.address as chemist_address
                FROM medicines m JOIN chemists ch ON m.chemist_id=ch.id
                WHERE m.is_available=1"""
            params = []
            if query:
                sql += " AND (m.name LIKE %s OR m.generic_name LIKE %s OR m.category LIKE %s)"
                params += [f'%{query}%']*3
            if category:
                sql += " AND m.category=%s"
                params.append(category)
            sql += " ORDER BY m.name"
            c.execute(sql, params)
            medicines = c.fetchall()
            c.execute("SELECT DISTINCT category FROM medicines WHERE is_available=1 AND category IS NOT NULL")
            categories = [r['category'] for r in c.fetchall()]
    finally:
        conn.close()
    return render_template('patient/medicines.html',
        medicines=medicines, categories=categories, query=query, selected_cat=category)

@app.route('/patient/orders', methods=['GET','POST'])
@login_required
@role_required('patient')
def patient_orders():
    uid = session['user_id']
    if request.method == 'POST':
        data = request.get_json()
        chemist_id = data.get('chemist_id')
        items      = data.get('items', [])
        presc_id   = data.get('prescription_id')
        notes      = data.get('notes','')
        is_emerg   = data.get('is_emergency', 0)
        if not chemist_id or not items:
            return jsonify({'success': False, 'message': 'Missing order details'}), 400
        conn = get_db()
        try:
            with conn.cursor() as c:
                total = 0
                for item in items:
                    c.execute("SELECT price,stock FROM medicines WHERE id=%s AND chemist_id=%s",
                              (item['medicine_id'], chemist_id))
                    med = c.fetchone()
                    if med:
                        total += med['price'] * item['quantity']
                c.execute("""INSERT INTO orders (patient_id,chemist_id,prescription_id,
                    total_amount,notes,is_emergency) VALUES (%s,%s,%s,%s,%s,%s)""",
                    (uid, chemist_id, presc_id or None, total, notes, is_emerg))
                order_id = c.lastrowid
                for item in items:
                    c.execute("SELECT price FROM medicines WHERE id=%s", (item['medicine_id'],))
                    med = c.fetchone()
                    if med:
                        c.execute("""INSERT INTO order_items (order_id,medicine_id,quantity,price)
                            VALUES (%s,%s,%s,%s)""",
                            (order_id, item['medicine_id'], item['quantity'], med['price']))
            conn.commit()
            return jsonify({'success': True, 'message': 'Order placed successfully!', 'order_id': order_id})
        finally:
            conn.close()

    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("""SELECT o.*, ch.shop_name FROM orders o
                JOIN chemists ch ON o.chemist_id=ch.id
                WHERE o.patient_id=%s ORDER BY o.created_at DESC""", (uid,))
            orders = c.fetchall()
            c.execute("SELECT * FROM prescriptions WHERE patient_id=%s", (uid,))
            prescriptions = c.fetchall()
            c.execute("""SELECT ch.*, u.name as owner_name FROM chemists ch
                JOIN users u ON ch.user_id=u.id WHERE ch.is_active=1""")
            chemists = c.fetchall()
            c.execute("""SELECT m.*, ch.shop_name FROM medicines m
                JOIN chemists ch ON m.chemist_id=ch.id WHERE m.is_available=1 AND m.stock>0""")
            medicines = c.fetchall()
    finally:
        conn.close()
    return render_template('patient/orders.html',
        orders=orders, prescriptions=prescriptions,
        chemists=chemists, medicines=medicines)

@app.route('/patient/chemists-map')
@login_required
@role_required('patient')
def chemists_map():
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("""SELECT ch.*, u.name as owner_name, u.email
                FROM chemists ch JOIN users u ON ch.user_id=u.id
                WHERE ch.is_active=1""")
            chemists = c.fetchall()
    finally:
        conn.close()
    return render_template('patient/chemists_map.html', chemists=chemists,
                           chemists_json=json.dumps([{
                               'id': ch['id'], 'shop_name': ch['shop_name'],
                               'address': ch['address'] or 'N/A',
                               'phone': ch['phone'] or 'N/A',
                               'lat': float(ch['latitude'] or 20.5937),
                               'lng': float(ch['longitude'] or 78.9629)
                           } for ch in chemists]))

# ─── CHEMIST ROUTES ───────────────────────────────────────────────────────────
@app.route('/chemist/dashboard')
@login_required
@role_required('chemist')
def chemist_dashboard():
    uid = session['user_id']
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("SELECT * FROM chemists WHERE user_id=%s", (uid,))
            chemist = c.fetchone()
            if not chemist:
                flash('Chemist profile not found.', 'error')
                return redirect(url_for('logout'))
            cid = chemist['id']
            c.execute("SELECT COUNT(*) as cnt FROM medicines WHERE chemist_id=%s", (cid,))
            total_meds = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM medicines WHERE chemist_id=%s AND stock<=5", (cid,))
            low_stock  = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM orders WHERE chemist_id=%s AND status='pending'", (cid,))
            pending_orders = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM orders WHERE chemist_id=%s", (cid,))
            total_orders = c.fetchone()['cnt']
            c.execute("""SELECT o.*, u.name as patient_name, u.phone as patient_phone
                FROM orders o JOIN users u ON o.patient_id=u.id
                WHERE o.chemist_id=%s ORDER BY o.created_at DESC LIMIT 5""", (cid,))
            recent_orders = c.fetchall()
            c.execute("""SELECT * FROM medicines WHERE chemist_id=%s AND stock<=5
                ORDER BY stock ASC LIMIT 5""", (cid,))
            low_stock_meds = c.fetchall()
    finally:
        conn.close()
    return render_template('chemist/dashboard.html',
        chemist=chemist, total_meds=total_meds, low_stock=low_stock,
        pending_orders=pending_orders, total_orders=total_orders,
        recent_orders=recent_orders, low_stock_meds=low_stock_meds)

@app.route('/chemist/inventory', methods=['GET','POST'])
@login_required
@role_required('chemist')
def chemist_inventory():
    uid = session['user_id']
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("SELECT id FROM chemists WHERE user_id=%s", (uid,))
            chemist = c.fetchone()
            if not chemist:
                return redirect(url_for('logout'))
            cid = chemist['id']
            if request.method == 'POST':
                data = request.get_json() or {}
                action = data.get('action')
                if action == 'add':
                    c.execute("""INSERT INTO medicines
                        (chemist_id,name,generic_name,category,price,stock,unit,description,expiry_date)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (cid, data['name'], data.get('generic_name'),
                         data.get('category'), data['price'],
                         data.get('stock',0), data.get('unit','strip'),
                         data.get('description',''), data.get('expiry_date') or None))
                    conn.commit()
                    return jsonify({'success': True, 'message': 'Medicine added!'})
                elif action == 'update':
                    c.execute("""UPDATE medicines SET name=%s,generic_name=%s,category=%s,
                        price=%s,stock=%s,unit=%s,description=%s,expiry_date=%s,is_available=%s
                        WHERE id=%s AND chemist_id=%s""",
                        (data['name'], data.get('generic_name'),
                         data.get('category'), data['price'],
                         data.get('stock',0), data.get('unit','strip'),
                         data.get('description',''), data.get('expiry_date') or None,
                         data.get('is_available',1),
                         data['id'], cid))
                    conn.commit()
                    return jsonify({'success': True, 'message': 'Medicine updated!'})
                elif action == 'delete':
                    c.execute("DELETE FROM medicines WHERE id=%s AND chemist_id=%s", (data['id'], cid))
                    conn.commit()
                    return jsonify({'success': True, 'message': 'Medicine removed!'})
            c.execute("SELECT * FROM medicines WHERE chemist_id=%s ORDER BY name", (cid,))
            medicines = c.fetchall()
    finally:
        conn.close()
    return render_template('chemist/inventory.html', medicines=medicines, now=datetime.now())

@app.route('/chemist/orders')
@login_required
@role_required('chemist')
def chemist_orders():
    uid = session['user_id']
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("SELECT id FROM chemists WHERE user_id=%s", (uid,))
            chemist = c.fetchone()
            cid = chemist['id']
            c.execute("""SELECT o.*, u.name as patient_name, u.phone as patient_phone, u.email as patient_email
                FROM orders o JOIN users u ON o.patient_id=u.id
                WHERE o.chemist_id=%s ORDER BY o.created_at DESC""", (cid,))
            orders = c.fetchall()
    finally:
        conn.close()
    return render_template('chemist/orders.html', orders=orders)

@app.route('/chemist/orders/update', methods=['POST'])
@login_required
@role_required('chemist')
def update_order_status():
    data   = request.get_json()
    oid    = data.get('order_id')
    status = data.get('status')
    uid    = session['user_id']
    valid  = ['pending','processing','ready','delivered','cancelled']
    if status not in valid:
        return jsonify({'success': False, 'message': 'Invalid status'}), 400
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("SELECT id FROM chemists WHERE user_id=%s", (uid,))
            chemist = c.fetchone()
            c.execute("UPDATE orders SET status=%s WHERE id=%s AND chemist_id=%s",
                      (status, oid, chemist['id']))
        conn.commit()
        return jsonify({'success': True, 'message': f'Order status updated to {status}'})
    finally:
        conn.close()

@app.route('/chemist/orders/<int:order_id>/items')
@login_required
@role_required('chemist')
def order_items_detail(order_id):
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("""SELECT oi.*, m.name as medicine_name, m.unit
                FROM order_items oi JOIN medicines m ON oi.medicine_id=m.id
                WHERE oi.order_id=%s""", (order_id,))
            items = c.fetchall()
    finally:
        conn.close()
    return jsonify({'items': items})

# ─── ADMIN ROUTES ─────────────────────────────────────────────────────────────
@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) as cnt FROM users WHERE role='patient'")
            total_patients = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM users WHERE role='chemist'")
            total_chemists = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM orders")
            total_orders = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM orders WHERE status='pending'")
            pending_orders = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM medicines")
            total_meds = c.fetchone()['cnt']
            c.execute("""SELECT o.*, u.name as patient_name, ch.shop_name
                FROM orders o JOIN users u ON o.patient_id=u.id
                JOIN chemists ch ON o.chemist_id=ch.id
                ORDER BY o.created_at DESC LIMIT 10""")
            recent_orders = c.fetchall()
            c.execute("""SELECT name, email, role, created_at, phone
                FROM users ORDER BY created_at DESC LIMIT 10""")
            recent_users = c.fetchall()
            c.execute("""SELECT status, COUNT(*) as cnt FROM orders GROUP BY status""")
            order_stats = {r['status']: r['cnt'] for r in c.fetchall()}
    finally:
        conn.close()
    return render_template('admin/dashboard.html',
        total_patients=total_patients, total_chemists=total_chemists,
        total_orders=total_orders, pending_orders=pending_orders,
        total_meds=total_meds, recent_orders=recent_orders,
        recent_users=recent_users, order_stats=json.dumps(order_stats))

@app.route('/admin/users')
@login_required
@role_required('admin')
def admin_users():
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("SELECT * FROM users ORDER BY created_at DESC")
            users = c.fetchall()
    finally:
        conn.close()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/toggle', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user():
    data = request.get_json()
    uid  = data.get('user_id')
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("SELECT id FROM users WHERE id=%s AND role!='admin'", (uid,))
            if not c.fetchone():
                return jsonify({'success': False, 'message': 'User not found'}), 404
            c.execute("DELETE FROM users WHERE id=%s AND role!='admin'", (uid,))
        conn.commit()
        return jsonify({'success': True, 'message': 'User removed'})
    finally:
        conn.close()

@app.route('/admin/orders')
@login_required
@role_required('admin')
def admin_orders():
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("""SELECT o.*, u.name as patient_name, ch.shop_name, u.phone as patient_phone
                FROM orders o JOIN users u ON o.patient_id=u.id
                JOIN chemists ch ON o.chemist_id=ch.id
                ORDER BY o.created_at DESC""")
            orders = c.fetchall()
    finally:
        conn.close()
    return render_template('admin/orders.html', orders=orders)

# ─── API ─────────────────────────────────────────────────────────────────────
@app.route('/api/chemists')
def api_chemists():
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("""SELECT ch.id, ch.shop_name, ch.address, ch.phone,
                ch.latitude, ch.longitude, u.name as owner
                FROM chemists ch JOIN users u ON ch.user_id=u.id WHERE ch.is_active=1""")
            data = c.fetchall()
    finally:
        conn.close()
    return jsonify([{**r, 'latitude': float(r['latitude'] or 0), 'longitude': float(r['longitude'] or 0)} for r in data])

@app.route('/api/medicines')
def api_medicines():
    q = request.args.get('q','')
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("""SELECT m.id, m.name, m.price, m.stock, m.unit, ch.shop_name
                FROM medicines m JOIN chemists ch ON m.chemist_id=ch.id
                WHERE m.is_available=1 AND (m.name LIKE %s OR m.generic_name LIKE %s)
                LIMIT 20""", (f'%{q}%', f'%{q}%'))
            data = c.fetchall()
    finally:
        conn.close()
    return jsonify(data)

@app.route('/uploads/<path:filename>')
@login_required
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    init_db()
    app.run(debug=True, port=5000)
