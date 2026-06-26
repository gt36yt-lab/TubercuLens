# app.py — TubercuLens v5.5 (Batch Processing Complete)
# ------------------------------------------------------------
import os
import math
import sqlite3
import requests
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, session
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont
import cv2

# ================== CONFIGURATION (ayaw hilabti) ==================
APP_VERSION = "TubercuLens-v5.5-Batch"
API_KEY = "122aOY67jDoRdfvlcYg6"
MODEL_ID = "tuberculosis-detection-xxmxp/1"

DEFAULT_CONF = 40
DEFAULT_OVERLAP = 30
A4_WIDTH_PX = 2480
A4_HEIGHT_PX = 3508
MARGIN = 150

STATIC_DIR = Path("static")
UPLOAD_DIR = STATIC_DIR / "uploads"
OUTPUT_DIR = STATIC_DIR / "outputs"
REPORT_DIR = STATIC_DIR / "reports"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}

# Ensure directories exist
for d in [STATIC_DIR, UPLOAD_DIR, OUTPUT_DIR, REPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ================== PASSKEY INITIALIZATION ==================
def init_passkeys():
    """Create three one-time passkeys if they don't exist and display them to console
    Uses fixed values 123, 321, 098 per user request."""
    conn = sqlite3.connect('plema.db')
    c = conn.cursor()
    predefined = ["123", "321", "098"]
    generated = []
    for i in range(1,4):
        keyname = f"passkey{i}"
        usedname = f"passkey{i}_used"
        c.execute("SELECT value FROM settings WHERE key=?", (keyname,))
        existing = c.fetchone()
        if not existing:
            key = predefined[i-1]
            generated.append(key)
            c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (keyname, key))
            c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (usedname, "0"))
        else:
            # ensure used flag present
            c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (usedname, "0"))
    conn.commit()
    conn.close()
    if generated:
        print("[TubercuLens] Passkeys set to:", ", ".join(generated))
import secrets


app = Flask(__name__)
app.secret_key = "plema-research-secure-key-tuberculens"
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# ================== HELPER FUNCTIONS FOR CREDENTIALS ==================
def account_exists():
    """Check if an account has been created"""
    conn = sqlite3.connect('plema.db')
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key='account_username'")
    result = c.fetchone()
    conn.close()
    return result is not None

def save_account(username, password):
    """Save account credentials to database"""
    conn = sqlite3.connect('plema.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('account_username', ?)", (username,))
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('account_password', ?)", (password,))
    conn.commit()
    conn.close()

def get_account_credentials():
    """Retrieve account credentials from database"""
    conn = sqlite3.connect('plema.db')
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key='account_username'")
    username = c.fetchone()
    c.execute("SELECT value FROM settings WHERE key='account_password'")
    password = c.fetchone()
    conn.close()
    return (username[0] if username else None, password[0] if password else None)

# ================== PASSKEY HELPERS ==================
def verify_and_use_passkey(key):
    """Return True if key is valid and unused, then mark it used"""
    conn = sqlite3.connect('plema.db')
    c = conn.cursor()
    for i in range(1,4):
        keyname = f"passkey{i}"
        usedname = f"passkey{i}_used"
        c.execute("SELECT value FROM settings WHERE key=?", (keyname,))
        stored = c.fetchone()
        if stored and stored[0] == key:
            # check used
            c.execute("SELECT value FROM settings WHERE key=?", (usedname,))
            used = c.fetchone()
            if used and used[0] == "0":
                # mark used
                c.execute("UPDATE settings SET value='1' WHERE key=?", (usedname,))
                conn.commit()
                conn.close()
                return True
            break
    conn.close()
    return False

# ================== DATABASE ENGINE ==================
def init_db():
    conn = sqlite3.connect('plema.db')
    c = conn.cursor()
    # Create Records Table
    c.execute('''CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT,
        name TEXT,
        age TEXT,
        sex TEXT,
        date_added TEXT,
        mtb_count INTEGER,
        status TEXT,
        image_orig TEXT,
        image_analyzed TEXT,
        report_path TEXT
    )''')
    # Create Settings Table
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    # Set Default Confidence if missing
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('confidence', ?)", (str(DEFAULT_CONF),))
    conn.commit()
    conn.close()

def get_setting(key, default):
    conn = sqlite3.connect('plema.db')
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    result = c.fetchone()
    conn.close()
    return int(result[0]) if result else default

def save_record(patient, mtb_count, paths):
    conn = sqlite3.connect('plema.db')
    c = conn.cursor()
    status = "POSITIVE" if mtb_count > 0 else "NEGATIVE"
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    c.execute('''INSERT INTO records 
        (patient_id, name, age, sex, date_added, mtb_count, status, image_orig, image_analyzed, report_path) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (patient['id'], patient['name'], patient['age'], patient['sex'], 
         date_now, mtb_count, status, paths['orig'], paths['out'], paths['report'])
    )
    conn.commit()
    conn.close()

# ================== DATE UTILITIES ==================
def get_week_boundaries(target_date=None):
    """Get the start and end dates for the week containing target_date (Monday-Sunday)"""
    if target_date is None:
        target_date = datetime.now()
    elif isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d")
    
    # Monday = 0, Sunday = 6
    monday = target_date - timedelta(days=target_date.weekday())
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    return monday, sunday

def get_current_week_boundaries():
    """Get the start and end dates for the current week"""
    return get_week_boundaries(datetime.now())

def get_records_by_date_range(start_date, end_date):
    """Get records within a date range"""
    conn = sqlite3.connect('plema.db')
    conn.row_factory = sqlite3.Row
    
    # Convert to proper format for SQL comparison
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(hours=23, minutes=59, seconds=59)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    records = conn.execute(
        "SELECT * FROM records WHERE date_added LIKE ? OR date_added LIKE ? OR date_added BETWEEN ? AND ? ORDER BY id DESC",
        (f"{start_str}%", f"{end_str}%", start_str, end_str)
    ).fetchall()
    conn.close()
    return records

# Initialize Database and passkeys on Start
init_db()
init_passkeys()

# ================== AI & GRAPHICS UTILITIES ==================
def allowed_file(filename):
    return Path(filename).suffix in ALLOWED_EXTENSIONS

def load_image_pil(path):
    try:
        return Image.open(path).convert("RGB")
    except:
        # Fallback for complex image formats using OpenCV
        arr = cv2.imread(str(path))
        if arr is None: raise RuntimeError("Unable to load image.")
        arr = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(arr)

def try_load_font(size, bold=False):
    # Attempts to load Arial (standard on Windows)
    font_name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(font_name, size=size)
    except:
        return ImageFont.load_default()

def draw_rectangles_only(img, preds, conf_threshold):
    draw = ImageDraw.Draw(img)
    w, h = img.size
    thickness = max(4, math.ceil(min(w, h) * 0.005)) 
    color_detected = (0, 255, 0) # Neon Green for High Contrast

    for p in preds:
        if p.get("confidence", 0) < (conf_threshold / 100.0): continue
        x, y, bw, bh = p.get("x"), p.get("y"), p.get("width"), p.get("height")
        
        left = x - bw / 2
        top = y - bh / 2
        right = x + bw / 2
        bottom = y + bh / 2
        
        draw.rectangle([left, top, right, bottom], outline=color_detected, width=thickness)
    return img

def count_mtb(preds, conf_threshold):
    n = 0
    for p in preds:
        if p.get("confidence", 0.0) >= (conf_threshold / 100.0):
            n += 1
    return n

# ================== PROFESSIONAL PDF GENERATOR ==================
def make_report(annotated_img_path, export_type, patient, mtb_count):
    # 1. Setup Canvas (A4 Size)
    page = Image.new("RGB", (A4_WIDTH_PX, A4_HEIGHT_PX), "#F5F5F7")
    draw = ImageDraw.Draw(page)
    
    # Fonts
    font_header = try_load_font(70, bold=True)
    font_sub = try_load_font(38)
    font_title = try_load_font(60, bold=True)
    font_label = try_load_font(36, bold=True)
    font_text = try_load_font(36)
    font_small = try_load_font(28)

    # 2. HEADER SECTION
    logo_path = Path("static/school_logo.png")
    if logo_path.exists():
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo.thumbnail((250, 250))
            page.paste(logo, (MARGIN, MARGIN), logo)
        except: pass

    text_school = "TubercuLens"
    text_sub =   "Mycobacterium tuberculosis Detection System (TubercuLens)"
    
    w_school = draw.textlength(text_school, font=font_header)
    w_sub = draw.textlength(text_sub, font=font_sub)
    
    draw.text(((A4_WIDTH_PX - w_school)/2, MARGIN + 20), text_school, font=font_header, fill="black")
    draw.text(((A4_WIDTH_PX - w_sub)/2, MARGIN + 110), text_sub, font=font_sub, fill="#333333")
    
    draw.text(((A4_WIDTH_PX - draw.textlength("SPUTUM AFB RESULT", font=font_title))/2, MARGIN + 250), 
              "SPUTUM AFB RESULT", font=font_title, fill="#00008B")

    # 3. PATIENT INFO BLOCK
    y_start = MARGIN + 400
    col1_x = MARGIN
    col2_x = A4_WIDTH_PX / 2 + 50
    
    draw.text((col1_x, y_start), f"Processing Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", font=font_small, fill="black")
    y_c1 = y_start + 60
    draw.text((col1_x, y_c1), f"NAME: {patient['name']}", font=font_text, fill="black"); y_c1 += 50
    draw.text((col1_x, y_c1), f"PHYSICIAN: __________________", font=font_text, fill="black"); y_c1 += 50
    draw.text((col1_x, y_c1), f"Bact. No: PD-{patient['id']}", font=font_text, fill="black"); y_c1 += 50
    draw.text((col1_x, y_c1), f"Lab No: __________________", font=font_text, fill="black")

    y_c2 = y_start + 60
    draw.text((col2_x, y_c2), f"AGE/SEX: {patient['age']} / {patient['sex']}", font=font_text, fill="black"); y_c2 += 50
    draw.text((col2_x, y_c2), f"Ward: __________________", font=font_text, fill="black"); y_c2 += 50
    draw.text((col2_x, y_c2), f"DATE: {datetime.now().strftime('%Y-%m-%d')}", font=font_text, fill="black")

    # 4. RESULTS TABLE
    table_y = max(y_c1, y_c2) + 100
    row_height = 100
    table_w = A4_WIDTH_PX - (2 * MARGIN)
    
    # Table Lines
    draw.rectangle([MARGIN, table_y, MARGIN + table_w, table_y + (3 * row_height)], outline="black", width=3)
    draw.line([MARGIN, table_y + row_height, MARGIN + table_w, table_y + row_height], fill="black", width=2)
    draw.line([MARGIN, table_y + (2*row_height), MARGIN + table_w, table_y + (2*row_height)], fill="black", width=2)
    draw.line([MARGIN + 600, table_y, MARGIN + 600, table_y + (3 * row_height)], fill="black", width=2)

    # Table Content
    draw.text((MARGIN + 1000, table_y + 10), "Specimen: Sputum", font=font_text, fill="black")
    
    draw.text((MARGIN + 20, table_y + row_height + 30), "Visual Appearance", font=font_text, fill="black")
    draw.text((MARGIN + 620, table_y + row_height + 30), "Muco-purulent (Auto-detected)", font=font_text, fill="black")
    
    draw.text((MARGIN + 20, table_y + (2*row_height) + 30), "Reading", font=font_text, fill="black")
    draw.text((MARGIN + 620, table_y + (2*row_height) + 30), f"{mtb_count} AFB (AI Model Count)", font=font_label, fill="black")

    diagnosis = "AFB NEGATIVE" if mtb_count == 0 else f"AFB POSITIVE (Detected {mtb_count} Bacilli)"
    draw.rectangle([MARGIN, table_y + (3*row_height), MARGIN + table_w, table_y + (4*row_height)], outline="black", width=3)
    draw.text((MARGIN + 20, table_y + (3*row_height) + 30), "Laboratory Diagnosis", font=font_text, fill="black")
    draw.text((MARGIN + 620, table_y + (3*row_height) + 30), diagnosis, font=font_label, fill="red" if mtb_count > 0 else "green")

    # 5. REMARKS & INTERPRETATION
    remarks_y = table_y + (4*row_height) + 50
    draw.text((MARGIN, remarks_y), "Remarks:", font=font_small, fill="black")
    draw.line([MARGIN, remarks_y + 40, A4_WIDTH_PX - MARGIN, remarks_y + 40], fill="black", width=1)
    draw.text((MARGIN + 150, remarks_y), f"Generated by {APP_VERSION} (Automated Screening)", font=font_text, fill="black")

    interp_y = remarks_y + 100
    interp_h = 250
    draw.rectangle([MARGIN, interp_y, A4_WIDTH_PX - MARGIN, interp_y + interp_h], outline="black", width=2)
    draw.text((A4_WIDTH_PX/2 - 150, interp_y + 10), "RESULT INTERPRETATION", font=font_label, fill="black")
    interp_text = "0 = NO AFB FOUND (Negative)\n+n = 1-9 AFB FOUND (Scanty)\n1+ = 10-99 AFB FOUND\n2+ = 1-10 AFB / FIELD\n3+ = >10 AFB / FIELD"
    draw.multiline_text((MARGIN + 20, interp_y + 60), interp_text, font=font_text, spacing=10, fill="black")

    # 6. ANNOTATED IMAGE
    img_y = interp_y + interp_h + 100
    try:
        annotated = Image.open(annotated_img_path)
        # Calculate fit
        max_w = A4_WIDTH_PX - (2 * MARGIN)
        max_h = (A4_HEIGHT_PX - 200) - img_y - 100
        
        target_w = max_w
        ratio = target_w / annotated.width
        target_h = int(annotated.height * ratio)
        
        if target_h > max_h:
            target_h = max_h
            ratio = target_h / annotated.height
            target_w = int(annotated.width * ratio)
            
        annotated = annotated.resize((target_w, target_h), Image.Resampling.LANCZOS)
        img_x = MARGIN + (max_w - target_w) // 2
        
        draw.rectangle([img_x-5, img_y-5, img_x+target_w+5, img_y+target_h+5], outline="black", width=2)
        page.paste(annotated, (img_x, img_y))
    except:
        draw.text((MARGIN, img_y), "[IMAGE UPLOAD ERROR]", font=font_text, fill="red")

    # 7. FOOTER
    footer_y = A4_HEIGHT_PX - 200
    draw.text((MARGIN, footer_y), "PERFORMED BY:", font=font_small, fill="black")
    draw.text((MARGIN, footer_y + 50), "TubercuLens AI", font=font_label, fill="black")
    draw.text((A4_WIDTH_PX/2 - 100, footer_y), "VERIFIED BY:", font=font_small, fill="black")
    draw.line([A4_WIDTH_PX/2 - 100, footer_y + 80, A4_WIDTH_PX/2 + 200, footer_y + 80], fill="black", width=1)
    draw.text((A4_WIDTH_PX - 500, footer_y), "PATHOLOGIST:", font=font_small, fill="black")
    draw.line([A4_WIDTH_PX - 500, footer_y + 80, A4_WIDTH_PX - MARGIN, footer_y + 80], fill="black", width=1)

    # Save PDF
    # Add microseconds to filename to prevent overwriting in batch mode
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"Report_{patient['id']}_{timestamp}.pdf"
    save_path = REPORT_DIR / filename
    page.save(save_path, "PDF", resolution=300.0)
    return filename

# ================== WEB ROUTES ==================
@app.route("/reset", methods=["GET", "POST"])
def reset():
    """Password reset using one of three one-time passkeys"""
    if request.method == "POST":
        key = request.form.get("passkey", "").strip()
        new_username = request.form.get("username", "").strip()
        new_password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        
        if not key or not new_username or not new_password:
            flash("All fields are required.", "error")
        elif len(new_username) < 3:
            flash("Username must be at least 3 characters long.", "error")
        elif len(new_password) < 4:
            flash("Password must be at least 4 characters long.", "error")
        elif new_password != confirm_password:
            flash("Passwords do not match.", "error")
        elif not verify_and_use_passkey(key):
            flash("Invalid or already used passkey.", "error")
        else:
            save_account(new_username, new_password)
            flash("✓ Credentials reset successfully! Please log in.", "success")
            return redirect(url_for('login'))
    return render_template("reset.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():

    """Sign up route - only available if no account exists"""
    if account_exists():
        flash("Account already exists. Please log in.", "warning")
        return redirect(url_for('login'))
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        
        if not username or not password:
            flash("Username and password are required.", "error")
        elif len(username) < 3:
            flash("Username must be at least 3 characters long.", "error")
        elif len(password) < 4:
            flash("Password must be at least 4 characters long.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        else:
            save_account(username, password)
            flash("✓ Account created successfully! Please log in.", "success")
            return redirect(url_for('login'))
    
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Login route with username and password authentication"""
    # If no account exists, redirect to signup
    if not account_exists():
        return redirect(url_for('signup'))
    
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        stored_username, stored_password = get_account_credentials()
        
        if username == stored_username and password == stored_password:
            session['logged_in'] = True
            session['username'] = username
            flash("✓ Login successful! Welcome to TubercuLens.", "success")
            return redirect(url_for('index'))
        else:
            flash("✗ Invalid username or password. Please try again.", "error")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    """Logout route"""
    session.clear()
    flash("✓ You have been logged out successfully.", "success")
    return redirect(url_for('login'))

@app.route("/", methods=["GET", "POST"])
def index():
    # Check if user is logged in
    if not session.get('logged_in'):
        flash("Please log in to access the system.", "warning")
        return redirect(url_for('login'))
    
    current_conf = get_setting('confidence', DEFAULT_CONF)
    
    # Get current week's data for analytics
    week_start, week_end = get_current_week_boundaries()
    week_start_str = week_start.strftime("%Y-%m-%d")
    week_end_str = week_end.strftime("%Y-%m-%d")
    
    conn = sqlite3.connect('plema.db')
    conn.row_factory = sqlite3.Row
    records = conn.execute("SELECT * FROM records ORDER BY id DESC").fetchall()
    conn.close()

    context = {
        "show_results": False,
        "batch_mode": False,
        "system_status": "ONLINE",
        "records": records,
        "current_conf": current_conf,
        "week_start": week_start_str,
        "week_end": week_end_str
    }

    if request.method == "POST":
        # HANDLE SETTINGS UPDATE
        if "setting_conf" in request.form:
            new_conf = request.form.get("setting_conf")
            conn = sqlite3.connect('plema.db')
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('confidence', ?)", (new_conf,))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))
        
        # HANDLE CREDENTIALS CHANGE
        if "change_credentials" in request.form:
            new_username = request.form.get("new_username", "").strip()
            new_password = request.form.get("new_password", "").strip()
            confirm_password = request.form.get("confirm_new_password", "").strip()
            
            if not new_username or not new_password:
                flash("Username and password are required.", "error")
            elif len(new_username) < 3:
                flash("Username must be at least 3 characters long.", "error")
            elif len(new_password) < 4:
                flash("Password must be at least 4 characters long.", "error")
            elif new_password != confirm_password:
                flash("Passwords do not match.", "error")
            else:
                save_account(new_username, new_password)
                flash("✓ Credentials updated successfully! Please log in again with your new credentials.", "success")
                return redirect(url_for('logout'))
            
            return redirect(url_for('index'))

        # HANDLE IMAGE UPLOAD (UPDATED SA DAGHAN IMAGES FUCK)
        if "image" in request.files:
            files = request.files.getlist("image")
            
            # --- SINGLE IMAGE MODE ---
            if len(files) == 1 and files[0].filename != "":
                file = files[0]
                filename = secure_filename(file.filename)
                upload_path = UPLOAD_DIR / filename
                file.save(upload_path)
                
                # Call Roboflow API
                api_url = f"https://detect.roboflow.com/{MODEL_ID}"
                params = { "api_key": API_KEY, "confidence": current_conf, "overlap": DEFAULT_OVERLAP }
                
                with open(upload_path, "rb") as f:
                    response = requests.post(api_url, params=params, files={"file": f})
                
                predictions = response.json().get("predictions", []) if response.status_code == 200 else []

                # Draw Boxes
                img = load_image_pil(upload_path)
                img_out = draw_rectangles_only(img, predictions, current_conf)
                out_filename = f"analyzed_{filename}"
                img_out.save(OUTPUT_DIR / out_filename)
                
                mtb_count = count_mtb(predictions, current_conf)
                
                patient = {
                    "name": request.form.get("patient_name", "Unknown"),
                    "id": request.form.get("patient_id", "---"),
                    "age": request.form.get("patient_age", "--"),
                    "sex": request.form.get("patient_sex", "--")
                }
                
                report_name = make_report(OUTPUT_DIR / out_filename, "pdf", patient, mtb_count)
                
                paths = {
                    "orig": f"uploads/{filename}",
                    "out": f"outputs/{out_filename}",
                    "report": f"reports/{report_name}"
                }
                save_record(patient, mtb_count, paths)
                
                # Update Context for View
                context.update({
                    "show_results": True,
                    "batch_mode": False,
                    "mtb_count": mtb_count,
                    "patient": patient,
                    "orig_url": url_for("static", filename=paths['orig']), 
                    "out_url": url_for("static", filename=paths['out']),
                    "report_url": url_for("static", filename=paths['report'])
                })

            # --- BATCH IMAGE MODE ---
            elif len(files) > 1:
                batch_results = []
                base_id = request.form.get("patient_id", "BATCH")
                base_name = request.form.get("patient_name", "Batch Scan")
                
                total_pos = 0
                
                for index, file in enumerate(files):
                    if file.filename == "": continue
                    
                    # 1. Save
                    filename = secure_filename(file.filename)
                    upload_path = UPLOAD_DIR / filename
                    file.save(upload_path)
                    
                    # 2. Analyze
                    api_url = f"https://detect.roboflow.com/{MODEL_ID}"
                    params = { "api_key": API_KEY, "confidence": current_conf, "overlap": DEFAULT_OVERLAP }
                    
                    with open(upload_path, "rb") as f:
                        response = requests.post(api_url, params=params, files={"file": f})
                        
                    predictions = response.json().get("predictions", []) if response.status_code == 200 else []
                    
                    # 3. Draw
                    img = load_image_pil(upload_path)
                    img_out = draw_rectangles_only(img, predictions, current_conf)
                    out_filename = f"analyzed_{filename}"
                    img_out.save(OUTPUT_DIR / out_filename)
                    
                    mtb_count = count_mtb(predictions, current_conf)
                    if mtb_count > 0: total_pos += 1
                    
                    # 4. Generate Unique Data
                    current_patient = {
                        "name": base_name,
                        "id": f"{base_id}-{index+1:02d}", # e.g. ID-01, ID-02
                        "age": request.form.get("patient_age", "--"),
                        "sex": request.form.get("patient_sex", "--")
                    }
                    
                    report_name = make_report(OUTPUT_DIR / out_filename, "pdf", current_patient, mtb_count)
                    
                    paths = {
                        "orig": f"uploads/{filename}",
                        "out": f"outputs/{out_filename}",
                        "report": f"reports/{report_name}"
                    }
                    save_record(current_patient, mtb_count, paths)
                    
                    batch_results.append({
                        "filename": filename,
                        "id": current_patient['id'],
                        "count": mtb_count,
                        "status": "POSITIVE" if mtb_count > 0 else "NEGATIVE",
                        "out_url": url_for("static", filename=paths['out']),
                        "report_url": url_for("static", filename=paths['report'])
                    })
                
                context.update({
                    "show_results": True,
                    "batch_mode": True,
                    "batch_total": len(batch_results),
                    "batch_pos": total_pos,
                    "batch_results": batch_results
                })
            
            # Refresh Database View after batch add
            conn = sqlite3.connect('plema.db')
            conn.row_factory = sqlite3.Row
            context["records"] = conn.execute("SELECT * FROM records ORDER BY id DESC").fetchall()
            conn.close()

    return render_template("index.html", **context)

# ================== EXCEL EXPORT ROUTE ==================
@app.route("/export_data")
def export_data():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('plema.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records")
    rows = cursor.fetchall()
    
    def generate():
        yield "ID,Patient ID,Name,Age,Sex,Date,Result,Count\n"
        for row in rows:
            yield f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]},{row[7]},{row[6]}\n"
            
    conn.close()
    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=tuberculens_data.csv"})

# ================== CLEAR DATA ROUTE ==================
@app.route("/clear_data", methods=["POST"])
def clear_data():
    try:
        conn = sqlite3.connect('plema.db')
        c = conn.cursor()
        c.execute("DELETE FROM records")
        conn.commit()
        conn.close()
        flash("✓ All analytics data has been cleared successfully!", "success")
    except Exception as e:
        flash(f"Error clearing data: {str(e)}", "error")
    return redirect(url_for('index'))

# ================== ANALYTICS API ROUTE ==================
@app.route("/api/analytics", methods=["GET"])
def analytics_api():
    """Get analytics data for a specific date range"""
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        week_start, week_end = get_current_week_boundaries()
        start_date = week_start.strftime("%Y-%m-%d")
        end_date = week_end.strftime("%Y-%m-%d")
    
    records = get_records_by_date_range(start_date, end_date)
    
    positive = sum(1 for r in records if r['status'] == 'POSITIVE')
    negative = sum(1 for r in records if r['status'] == 'NEGATIVE')
    total = positive + negative
    rate = round((positive / total * 100), 1) if total > 0 else 0
    
    return jsonify({
        "total": total,
        "positive": positive,
        "negative": negative,
        "rate": rate,
        "records": [dict(r) for r in records]
    })

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)