from flask import Flask, render_template, request, flash, redirect, url_for, send_file, abort, session, jsonify, Response
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import CSRFProtect
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
import pandas as pd
from io import BytesIO
import os
import re
import traceback
from datetime import datetime
import calendar
from functools import wraps
import base64

# PDF imports
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image as RLImage
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ============== Flask Yapılandırması ==============
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

# MongoDB Configuration
app.config['MONGO_URI'] = os.environ.get('MONGO_URI', 'mongodb+srv://Admin:O3oTRp9cyo63ZHy3@cluster0.duwvajs.mongodb.net/Csv?retryWrites=true&w=majority')

# ============== Eklentiler ==============
mongo = PyMongo(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

ALLOWED_EXTENSIONS = {'csv'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============== User Class for Flask-Login ==============

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.email = user_data['email']
        self.password_hash = user_data['password_hash']
        self.user_type = user_data['user_type']
        self.created_at = user_data.get('created_at', datetime.utcnow())
        
        # Profile data
        if self.user_type == 'individual':
            self.individual_profile = user_data.get('individual_profile', {})
        else:
            self.company_profile = user_data.get('company_profile', {})
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def get_by_id(user_id):
        try:
            user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            if user_data:
                return User(user_data)
        except:
            pass
        return None
    
    @staticmethod
    def get_by_email(email):
        user_data = mongo.db.users.find_one({'email': email})
        if user_data:
            return User(user_data)
        return None
    
    def has_logo(self):
        """Check if company has logo"""
        if self.user_type == 'company':
            return self.company_profile.get('logo_data') is not None
        return False
    
    def get_logo_base64(self):
        """Get logo as base64 string for HTML display"""
        if self.user_type == 'company' and self.has_logo():
            logo_data = self.company_profile.get('logo_data')
            logo_mimetype = self.company_profile.get('logo_mimetype', 'image/png')
            encoded = base64.b64encode(logo_data).decode('utf-8')
            return f"data:{logo_mimetype};base64,{encoded}"
        return None

# ============== Login Manager ==============

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

# ============== Yardımcı Fonksiyonlar ==============

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def safe_filename(name):
    return re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)

def replace_turkish_characters(text):
    replacements = {
        "ç": "c", "Ç": "C", "ğ": "g", "Ğ": "G", "ı": "i", "İ": "I",
        "ö": "o", "Ö": "O", "ş": "s", "Ş": "S", "ü": "u", "Ü": "U"
    }
    for turkish_char, ascii_char in replacements.items():
        text = text.replace(turkish_char, ascii_char)
    return text

def sanitize_excel_cell(value):
    if pd.isna(value) or value is None:
        return ""
    value = str(value)
    if value and value[0] in ('=', '+', '-', '@'):
        return "'" + value
    return value

def parse_duration_to_seconds(d_str):
    try:
        h, m, s = map(int, d_str.split(":"))
        return h * 3600 + m * 60 + s
    except:
        return 0

def round_to_nearest_minute(seconds):
    minutes = seconds / 60
    rounded_minutes = round(minutes)
    return rounded_minutes * 60

# ============== Routes ==============

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# ============== Kimlik Doğrulama Routes ==============

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        
        # Check if user exists
        if mongo.db.users.find_one({'email': email}):
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))
        
        # Create user document
        user_doc = {
            'email': email,
            'password_hash': generate_password_hash(password),
            'user_type': user_type,
            'created_at': datetime.utcnow()
        }
        
        if user_type == 'individual':
            user_doc['individual_profile'] = {
                'full_name': request.form.get('full_name'),
                'phone': request.form.get('phone', '')
            }
        else:
            company_profile = {
                'company_name': request.form.get('company_name'),
                'contact_person': request.form.get('contact_person', ''),
                'phone': request.form.get('phone', ''),
                'address': request.form.get('address', '')
            }
            
            # Logo yükleme
            logo_file = request.files.get('logo')
            if logo_file and logo_file.filename and allowed_image(logo_file.filename):
                # Dosya boyutu kontrolü
                logo_file.seek(0, os.SEEK_END)
                file_size = logo_file.tell()
                logo_file.seek(0)
                
                if file_size <= 2 * 1024 * 1024:  # 2MB
                    company_profile['logo_data'] = logo_file.read()
                    company_profile['logo_mimetype'] = logo_file.content_type
                else:
                    flash('Logo file size must be less than 2MB.', 'error')
            
            user_doc['company_profile'] = company_profile
        
        # Insert user
        mongo.db.users.insert_one(user_doc)
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.get_by_email(email)
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        
        flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# ============== Dashboard ==============

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# ============== Profil Yönetimi ==============

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        user_id = ObjectId(current_user.id)
        
        if current_user.user_type == 'individual':
            update_data = {
                'individual_profile.full_name': request.form.get('full_name'),
                'individual_profile.phone': request.form.get('phone', '')
            }
        else:
            update_data = {
                'company_profile.company_name': request.form.get('company_name'),
                'company_profile.contact_person': request.form.get('contact_person', ''),
                'company_profile.phone': request.form.get('phone', ''),
                'company_profile.address': request.form.get('address', '')
            }
            
            # Logo güncelleme
            logo_file = request.files.get('logo')
            if logo_file and logo_file.filename and allowed_image(logo_file.filename):
                # Dosya boyutu kontrolü
                logo_file.seek(0, os.SEEK_END)
                file_size = logo_file.tell()
                logo_file.seek(0)
                
                if file_size <= 2 * 1024 * 1024:  # 2MB
                    update_data['company_profile.logo_data'] = logo_file.read()
                    update_data['company_profile.logo_mimetype'] = logo_file.content_type
                else:
                    flash('Logo file size must be less than 2MB.', 'error')
                    return redirect(url_for('profile'))
        
        # Update user
        mongo.db.users.update_one(
            {'_id': user_id},
            {'$set': update_data}
        )
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html')

# ============== CSV Önizleme API ==============

@app.route('/api/preview-csv', methods=['POST'])
@login_required
def preview_csv():
    file = request.files.get('csv_file')
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400
    
    try:
        df = pd.read_csv(file)
        
        # Sütun bilgilerini çıkar
        columns = df.columns.tolist()
        sample_data = df.head(5).to_dict('records')
        
        # Özet bilgiler
        unique_values = {}
        for col in ['Project', 'Client', 'User']:
            if col in df.columns:
                unique_values[col] = df[col].dropna().unique().tolist()
        
        return jsonify({
            'columns': columns,
            'sample_data': sample_data,
            'unique_values': unique_values,
            'total_rows': len(df)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============== Rapor Dönüştürme ==============

@app.route('/convert', methods=['POST'])
@login_required
def convert():
    file = request.files.get('csv_file')
    if not file or not allowed_file(file.filename):
        flash('Please upload a valid CSV file.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # CSV'yi oku
        df = pd.read_csv(file)
        
        # Zorunlu kolonları kontrol et
        required_columns = ["Project", "Client", "User", "Start Date", "Duration (h)"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            flash(f"Missing required columns: {', '.join(missing_columns)}", 'error')
            return redirect(url_for('dashboard'))
        
        # Eksik kolonları ekle
        if "Billable" not in df.columns:
            df["Billable"] = "No"
        if "Description" not in df.columns:
            df["Description"] = ""
        if "Start Time" not in df.columns:
            df["Start Time"] = ""
        if "End Time" not in df.columns:
            df["End Time"] = ""
        
        df["Duration (h)"].fillna("00:00:00", inplace=True)
        df["Billable"].fillna("No", inplace=True)
        
        # Filtreleri al
        selected_projects = request.form.getlist('projectSelect[]')
        selected_clients = request.form.getlist('clientSelect[]')
        selected_users = request.form.getlist('userSelect[]')
        format_choice = request.form.get('formatSelect', 'decimal')
        export_format = request.form.get('exportFormat', 'excel')  # excel veya pdf
        
        # "All" seçeneklerini filtrele
        selected_projects = [p for p in selected_projects if p and 'All' not in p]
        selected_clients = [c for c in selected_clients if c and 'All' not in c]
        selected_users = [u for u in selected_users if u and 'All' not in u]
        
        # Filtreleri uygula
        if selected_projects:
            df = df[df["Project"].isin(selected_projects)]
        if selected_clients:
            df = df[df["Client"].isin(selected_clients)]
        if selected_users:
            df = df[df["User"].isin(selected_users)]
        
        # Eğer filtre sonrası veri yoksa uyarı ver
        if df.empty:
            flash('No data matches the selected filters.', 'warning')
            return redirect(url_for('dashboard'))
        
        # Rapor bilgileri
        overall_projects = ", ".join(df["Project"].dropna().unique())
        overall_customers = ", ".join(df["Client"].dropna().unique())
        
        # Logo ve şirket bilgilerini hazırla
        logo_data = None
        company_info = None
        
        if current_user.user_type == 'company':
            if current_user.has_logo():
                logo_data = {
                    'data': current_user.company_profile.get('logo_data'),
                    'mimetype': current_user.company_profile.get('logo_mimetype', 'image/png')
                }
            
            company_info = {
                'company_name': current_user.company_profile.get('company_name', ''),
                'contact_person': current_user.company_profile.get('contact_person', ''),
                'phone': current_user.company_profile.get('phone', ''),
                'address': current_user.company_profile.get('address', '')
            }
        
        # Tarihleri parse et
        df['ParsedDate'] = pd.to_datetime(df['Start Date'], format='%d/%m/%Y', errors='coerce')
        
        # Rapor periyodu
        if not df['ParsedDate'].dropna().empty:
            min_date = df['ParsedDate'].min()
            max_date = df['ParsedDate'].max()
            if min_date.month == max_date.month and min_date.year == max_date.year:
                report_period = min_date.strftime("%B %Y")
            else:
                report_period = f"{min_date.strftime('%B %Y')} - {max_date.strftime('%B %Y')}"
        else:
            report_period = "All Data"
        
        # Format seçimine göre rapor oluştur
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_format == 'pdf':
            # PDF oluştur
            output = generate_pdf_report(df, format_choice, report_period, 
                                        overall_projects, overall_customers, logo_data, company_info)
            filename = f"Report_{timestamp}.pdf"
            mimetype = 'application/pdf'
        else:
            # Excel oluştur (default)
            output = generate_excel_report(df, format_choice, report_period, 
                                          overall_projects, overall_customers, logo_data, company_info)
            filename = f"Report_{timestamp}.xlsx"
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        return send_file(
            output,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        app.logger.error(f"Error in convert: {str(e)}\n{traceback.format_exc()}")
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# ============== EXCEL RAPOR OLUŞTURMA ==============

def generate_excel_report(df, format_choice, report_period, projects, customers, logo_data=None, company_info=None):
    """Excel raporu oluşturur - Düzeltilmiş versiyon"""
    output = BytesIO()
    
    # Süreleri hesapla
    df["raw_seconds"] = df["Duration (h)"].apply(parse_duration_to_seconds)
    df["rounded_seconds"] = df["raw_seconds"].apply(round_to_nearest_minute)
    
    if format_choice == "hours":
        df["formatted_duration"] = df["rounded_seconds"] / 86400
    else:
        df["formatted_duration"] = (df["rounded_seconds"] / 3600).round(2)
    
    # Tarihleri parse et
    df['Start Date'] = df['Start Date'].astype(str)
    df['ParsedDate'] = pd.to_datetime(df['Start Date'], format='%d/%m/%Y', errors='coerce')
    df["Day"] = df["ParsedDate"].apply(lambda d: d.strftime("%d (%A)") if pd.notnull(d) else "Unknown")
    df["DayFull"] = df["ParsedDate"].apply(lambda d: d.strftime("%d %B %Y (%A)") if pd.notnull(d) else "Unknown")
    
    all_days = pd.date_range(start=df['ParsedDate'].min(), end=df['ParsedDate'].max(), freq='D') if not df['ParsedDate'].dropna().empty else pd.date_range(start="2025-01-01", periods=1)
    all_days_str = [d.strftime("%d (%A)") for d in all_days]
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Format tanımlamaları
        header_format = workbook.add_format({
            'bold': True, 
            'border': 1, 
            'bg_color': '#4472C4', 
            'font_color': 'white', 
            'align': 'center', 
            'valign': 'vcenter'
        })
        
        info_label_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'align': 'left',
            'valign': 'vcenter'
        })
        
        info_value_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'text_wrap': True
        })
        
        cell_format = workbook.add_format({
            'border': 1, 
            'align': 'left', 
            'valign': 'vcenter'
        })
        
        cell_wrap_format = workbook.add_format({
            'border': 1, 
            'align': 'left', 
            'valign': 'top',
            'text_wrap': True
        })
        
        cell_center_format = workbook.add_format({
            'border': 1, 
            'align': 'center', 
            'valign': 'vcenter'
        })
        
        number_format = workbook.add_format({
            'num_format': '0.00', 
            'border': 1, 
            'align': 'right',
            'valign': 'vcenter'
        })
        
        time_format = workbook.add_format({
            'num_format': '[h]:mm', 
            'border': 1, 
            'align': 'right',
            'valign': 'vcenter'
        })
        
        yellow_format = workbook.add_format({
            'bg_color': '#FFEB9C', 
            'border': 1, 
            'bold': True,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        yellow_number_format = workbook.add_format({
            'bg_color': '#FFEB9C', 
            'border': 1, 
            'bold': True,
            'num_format': '0.00',
            'align': 'right',
            'valign': 'vcenter'
        })
        
        yellow_time_format = workbook.add_format({
            'bg_color': '#FFEB9C', 
            'border': 1, 
            'bold': True,
            'num_format': '[h]:mm',
            'align': 'right',
            'valign': 'vcenter'
        })
        
        green_format = workbook.add_format({
            'bg_color': '#C6EFCE',
            'border': 1,
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': '#006100'
        })
        
        green_number_format = workbook.add_format({
            'bg_color': '#C6EFCE',
            'border': 1,
            'bold': True,
            'num_format': '0.00',
            'align': 'right',
            'valign': 'vcenter',
            'font_color': '#006100'
        })
        
        green_time_format = workbook.add_format({
            'bg_color': '#C6EFCE',
            'border': 1,
            'bold': True,
            'num_format': '[h]:mm',
            'align': 'right',
            'valign': 'vcenter',
            'font_color': '#006100'
        })
        
        red_format = workbook.add_format({
            'bg_color': '#FFC7CE',
            'border': 1,
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': '#9C0006'
        })
        
        red_number_format = workbook.add_format({
            'bg_color': '#FFC7CE',
            'border': 1,
            'bold': True,
            'num_format': '0.00',
            'align': 'right',
            'valign': 'vcenter',
            'font_color': '#9C0006'
        })
        
        red_time_format = workbook.add_format({
            'bg_color': '#FFC7CE',
            'border': 1,
            'bold': True,
            'num_format': '[h]:mm',
            'align': 'right',
            'valign': 'vcenter',
            'font_color': '#9C0006'
        })
        
        user_header_format = workbook.add_format({
            'bold': True, 
            'border': 1, 
            'bg_color': '#4472C4', 
            'font_color': 'white', 
            'align': 'center', 
            'valign': 'vcenter',
            'font_size': 12
        })
        
        detail_header_format = workbook.add_format({
            'bold': True, 
            'border': 1, 
            'bg_color': '#667eea', 
            'font_color': 'white', 
            'align': 'center', 
            'valign': 'vcenter',
            'font_size': 11
        })
        
        detail_date_header_format = workbook.add_format({
            'bold': True, 
            'border': 1, 
            'bg_color': '#4472C4',
            'font_color': 'white',
            'align': 'left',
            'font_size': 12,
            'valign': 'vcenter'
        })
        
        detail_cell_format = workbook.add_format({
            'border': 1, 
            'align': 'left', 
            'valign': 'vcenter',
            'font_size': 10
        })
        
        detail_cell_wrap = workbook.add_format({
            'border': 1, 
            'align': 'left', 
            'valign': 'top',
            'font_size': 10,
            'text_wrap': True
        })
        
        detail_cell_center = workbook.add_format({
            'border': 1, 
            'align': 'center', 
            'valign': 'vcenter',
            'font_size': 10
        })
        
        detail_number_format = workbook.add_format({
            'num_format': '0.00', 
            'border': 1, 
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 10
        })
        
        detail_time_format = workbook.add_format({
            'num_format': '[h]:mm', 
            'border': 1, 
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 10
        })
        
        # ============== SAYFA 1: ÖZET RAPOR ==============
        summary_sheet = workbook.add_worksheet("Summary Report")
        
        # Yazdırma ayarları
        summary_sheet.fit_to_pages(1, 0)
        summary_sheet.set_landscape()
        summary_sheet.set_paper(9)
        summary_sheet.center_horizontally()
        summary_sheet.set_margins(left=0.3, right=0.3, top=0.5, bottom=0.5)
        
        row = 0
        
        # Logo ve Şirket Bilgileri Tablosu
        if company_info or logo_data:
            table_start_row = row
            
            if company_info:
                summary_sheet.write(row, 0, "Company:", info_label_format)
                summary_sheet.merge_range(row, 1, row, 3, sanitize_excel_cell(company_info.get('company_name', '')), info_value_format)
                summary_sheet.set_row(row, 18)
                row += 1
                
                if company_info.get('contact_person'):
                    summary_sheet.write(row, 0, "Contact:", info_label_format)
                    summary_sheet.merge_range(row, 1, row, 3, sanitize_excel_cell(company_info.get('contact_person', '')), info_value_format)
                    summary_sheet.set_row(row, 18)
                    row += 1
                
                if company_info.get('phone'):
                    summary_sheet.write(row, 0, "Phone:", info_label_format)
                    summary_sheet.merge_range(row, 1, row, 3, sanitize_excel_cell(company_info.get('phone', '')), info_value_format)
                    summary_sheet.set_row(row, 18)
                    row += 1
                
                if company_info.get('address'):
                    summary_sheet.write(row, 0, "Address:", info_label_format)
                    summary_sheet.merge_range(row, 1, row, 3, sanitize_excel_cell(company_info.get('address', '')), info_value_format)
                    summary_sheet.set_row(row, 18)
                    row += 1
            
            if logo_data is not None:
                try:
                    temp_logo = BytesIO(logo_data['data'])
                    logo_rows = row - table_start_row if row > table_start_row else 4
                    
                    summary_sheet.insert_image(table_start_row, 4, "logo", {
                        'image_data': temp_logo,
                        'x_scale': 0.25,
                        'y_scale': 0.25,
                        'x_offset': 10,
                        'y_offset': 5,
                        'positioning': 1
                    })
                    
                    for i in range(table_start_row, row):
                        summary_sheet.write(i, 4, "", info_value_format)
                except Exception as e:
                    pass
            
            row += 1
        
        # Rapor Bilgileri Tablosu (Period eklendi, D'ye kadar genişletildi)
        summary_sheet.write(row, 0, "Period:", info_label_format)
        summary_sheet.merge_range(row, 1, row, 3, sanitize_excel_cell(report_period), info_value_format)
        if logo_data:
            summary_sheet.write(row, 4, "", info_value_format)
        summary_sheet.set_row(row, 18)
        row += 1
        
        summary_sheet.write(row, 0, "Projects:", info_label_format)
        summary_sheet.merge_range(row, 1, row, 3, sanitize_excel_cell(projects), info_value_format)
        if logo_data:
            summary_sheet.write(row, 4, "", info_value_format)
        summary_sheet.set_row(row, 18)
        row += 1
        
        summary_sheet.write(row, 0, "Customers:", info_label_format)
        summary_sheet.merge_range(row, 1, row, 3, sanitize_excel_cell(customers), info_value_format)
        if logo_data:
            summary_sheet.write(row, 4, "", info_value_format)
        summary_sheet.set_row(row, 18)
        row += 2
        
        # Kullanıcı bazında özet
        for user in sorted(df["User"].dropna().unique()):
            user_df = df[df["User"] == user].copy()
            
            summary_sheet.merge_range(row, 0, row, 4, sanitize_excel_cell(f"User: {user}"), user_header_format)
            summary_sheet.set_row(row, 20)
            row += 1
            
            summary_sheet.write(row, 0, "Day", header_format)
            summary_sheet.write(row, 1, "Description", header_format)
            summary_sheet.write(row, 2, "Billable", header_format)
            summary_sheet.write(row, 3, "Duration", header_format)
            summary_sheet.set_row(row, 18)
            row += 1
            
            for day in all_days_str:
                day_df = user_df[user_df["Day"] == day]
                
                if day_df.empty:
                    continue
                
                unique_descriptions = []
                for desc in day_df["Description"].tolist():
                    desc_str = str(desc).strip()
                    if desc_str and desc_str not in unique_descriptions and desc_str != 'nan':
                        unique_descriptions.append(desc_str)
                
                combined_description = " | ".join(unique_descriptions) if unique_descriptions else ""
                
                billable_count = (day_df["Billable"] == "Yes").sum()
                non_billable_count = (day_df["Billable"] == "No").sum()
                
                if billable_count > 0 and non_billable_count > 0:
                    billable_status = "Mixed"
                elif billable_count > 0:
                    billable_status = "Yes"
                else:
                    billable_status = "No"
                
                total_duration = day_df["formatted_duration"].sum()
                
                summary_sheet.write(row, 0, sanitize_excel_cell(day), cell_format)
                summary_sheet.write(row, 1, sanitize_excel_cell(combined_description), cell_wrap_format)
                summary_sheet.write(row, 2, sanitize_excel_cell(billable_status), cell_center_format)
                
                if format_choice == "hours":
                    summary_sheet.write_number(row, 3, total_duration, time_format)
                else:
                    summary_sheet.write_number(row, 3, total_duration, number_format)
                
                # Satır yüksekliğini içerik uzunluğuna göre ayarla (sadece sığmazsa)
                desc_length = len(combined_description)
                # Kolon genişliği yaklaşık 60 karakter, her 60 karakter için 1 satır
                lines_needed = max(1, (desc_length // 60) + 1)
                row_height = 18 * lines_needed
                summary_sheet.set_row(row, row_height)
                
                row += 1
            
            row += 1
            
            billable_df = user_df[user_df["Billable"] == "Yes"]
            non_billable_df = user_df[user_df["Billable"] == "No"]
            
            total_billable = billable_df["formatted_duration"].sum()
            total_non_billable = non_billable_df["formatted_duration"].sum()
            total_overall = user_df["formatted_duration"].sum()
            
            summary_sheet.merge_range(row, 0, row, 2, "BILLABLE TOTAL", green_format)
            if format_choice == "hours":
                summary_sheet.write_number(row, 3, total_billable, green_time_format)
            else:
                summary_sheet.write_number(row, 3, total_billable, green_number_format)
            summary_sheet.set_row(row, 20)
            row += 1
            
            summary_sheet.merge_range(row, 0, row, 2, "NON-BILLABLE TOTAL", red_format)
            if format_choice == "hours":
                summary_sheet.write_number(row, 3, total_non_billable, red_time_format)
            else:
                summary_sheet.write_number(row, 3, total_non_billable, red_number_format)
            summary_sheet.set_row(row, 20)
            row += 1
            
            summary_sheet.merge_range(row, 0, row, 2, "GRAND TOTAL", yellow_format)
            if format_choice == "hours":
                summary_sheet.write_number(row, 3, total_overall, yellow_time_format)
            else:
                summary_sheet.write_number(row, 3, total_overall, yellow_number_format)
            summary_sheet.set_row(row, 20)
            row += 3
        
        summary_sheet.print_area(0, 0, row - 1, 4)
        
        # Kolon genişlikleri (Description otomatik genişlik için artırıldı)
        summary_sheet.set_column(0, 0, 16)   # Day
        summary_sheet.set_column(1, 1, 60)   # Description - genişletildi
        summary_sheet.set_column(2, 2, 10)   # Billable
        summary_sheet.set_column(3, 3, 12)   # Duration
        summary_sheet.set_column(4, 4, 12)   # Logo column
        
        # ============== SAYFA 2: DETAYLI RAPOR ==============
        detail_sheet = workbook.add_worksheet("Detailed Report")
        
        detail_sheet.fit_to_pages(1, 0)
        detail_sheet.set_landscape()
        detail_sheet.set_paper(9)
        detail_sheet.center_horizontally()
        detail_sheet.set_margins(left=0.3, right=0.3, top=0.5, bottom=0.5)
        
        detail_row = 0
        
        detail_sheet.merge_range(detail_row, 0, detail_row, 5, "Detailed Time Report", header_format)
        detail_sheet.set_row(detail_row, 22)
        detail_row += 1
        
        if company_info:
            table_start_row = detail_row
            
            detail_sheet.write(detail_row, 0, "Company:", info_label_format)
            detail_sheet.merge_range(detail_row, 1, detail_row, 4, sanitize_excel_cell(company_info.get('company_name', '')), info_value_format)
            detail_sheet.set_row(detail_row, 18)
            detail_row += 1
            
            if company_info.get('contact_person'):
                detail_sheet.write(detail_row, 0, "Contact:", info_label_format)
                detail_sheet.merge_range(detail_row, 1, detail_row, 4, sanitize_excel_cell(company_info.get('contact_person', '')), info_value_format)
                detail_sheet.set_row(detail_row, 18)
                detail_row += 1
            
            if company_info.get('phone'):
                detail_sheet.write(detail_row, 0, "Phone:", info_label_format)
                detail_sheet.merge_range(detail_row, 1, detail_row, 4, sanitize_excel_cell(company_info.get('phone', '')), info_value_format)
                detail_sheet.set_row(detail_row, 18)
                detail_row += 1
            
            if company_info.get('address'):
                detail_sheet.write(detail_row, 0, "Address:", info_label_format)
                detail_sheet.merge_range(detail_row, 1, detail_row, 4, sanitize_excel_cell(company_info.get('address', '')), info_value_format)
                detail_sheet.set_row(detail_row, 18)
                detail_row += 1
            
            if logo_data is not None:
                try:
                    temp_logo = BytesIO(logo_data['data'])
                    
                    detail_sheet.insert_image(table_start_row, 5, "logo", {
                        'image_data': temp_logo,
                        'x_scale': 0.25,
                        'y_scale': 0.25,
                        'x_offset': 10,
                        'y_offset': 5,
                        'positioning': 1
                    })
                    
                    for i in range(table_start_row, detail_row):
                        detail_sheet.write(i, 5, "", info_value_format)
                except Exception as e:
                    pass
            
            detail_row += 1
        
        # Rapor bilgileri (E'ye kadar genişletildi)
        detail_sheet.write(detail_row, 0, "Period:", info_label_format)
        detail_sheet.merge_range(detail_row, 1, detail_row, 4, sanitize_excel_cell(report_period), info_value_format)
        if logo_data:
            detail_sheet.write(detail_row, 5, "", info_value_format)
        detail_sheet.set_row(detail_row, 18)
        detail_row += 1
        
        detail_sheet.write(detail_row, 0, "Projects:", info_label_format)
        detail_sheet.merge_range(detail_row, 1, detail_row, 4, sanitize_excel_cell(projects), info_value_format)
        if logo_data:
            detail_sheet.write(detail_row, 5, "", info_value_format)
        detail_sheet.set_row(detail_row, 18)
        detail_row += 1
        
        detail_sheet.write(detail_row, 0, "Clients:", info_label_format)
        detail_sheet.merge_range(detail_row, 1, detail_row, 4, sanitize_excel_cell(customers), info_value_format)
        if logo_data:
            detail_sheet.write(detail_row, 5, "", info_value_format)
        detail_sheet.set_row(detail_row, 18)
        detail_row += 2
        
        df_sorted = df.sort_values(['User', 'ParsedDate', 'Start Time'])
        
        for user_value in sorted(df_sorted['User'].dropna().unique()):
            user_df = df_sorted[df_sorted['User'] == user_value]
            
            detail_sheet.merge_range(detail_row, 0, detail_row, 4, sanitize_excel_cell(f"User: {user_value}"), user_header_format)
            detail_sheet.set_row(detail_row, 22)
            detail_row += 1
            
            for date_value in user_df['DayFull'].unique():
                if pd.isna(date_value) or date_value == "Unknown":
                    continue
                    
                date_df = user_df[user_df['DayFull'] == date_value]
                
                detail_sheet.merge_range(detail_row, 0, detail_row, 4, sanitize_excel_cell(f"Date: {date_value}"), detail_date_header_format)
                detail_sheet.set_row(detail_row, 20)
                detail_row += 1
                
                headers = ["Start Time", "End Time", "Duration", "Description", "Billable"]
                for col_idx, header in enumerate(headers):
                    detail_sheet.write(detail_row, col_idx, header, detail_header_format)
                
                detail_sheet.set_row(detail_row, 18)
                detail_row += 1
                
                for idx, row_data in date_df.iterrows():
                    detail_sheet.write(detail_row, 0, sanitize_excel_cell(str(row_data.get('Start Time', ''))), detail_cell_center)
                    detail_sheet.write(detail_row, 1, sanitize_excel_cell(str(row_data.get('End Time', ''))), detail_cell_center)
                    
                    if format_choice == "hours":
                        detail_sheet.write_number(detail_row, 2, row_data['formatted_duration'], detail_time_format)
                    else:
                        detail_sheet.write_number(detail_row, 2, row_data['formatted_duration'], detail_number_format)
                    
                    desc_text = sanitize_excel_cell(str(row_data.get('Description', '')))
                    detail_sheet.write(detail_row, 3, desc_text, detail_cell_wrap)
                    
                    detail_sheet.write(detail_row, 4, sanitize_excel_cell(str(row_data.get('Billable', 'No'))), detail_cell_center)
                    
                    # Satır yüksekliğini içerik uzunluğuna göre ayarla
                    desc_length = len(desc_text)
                    lines_needed = max(1, (desc_length // 50) + 1)
                    row_height = 18 * lines_needed
                    detail_sheet.set_row(detail_row, row_height)
                    
                    detail_row += 1
                
                detail_row += 1
            
            detail_row += 1
        
        detail_sheet.print_area(0, 0, detail_row - 1, 5)
        
        # Kolon genişlikleri
        detail_sheet.set_column(0, 0, 12)  # Start Time
        detail_sheet.set_column(1, 1, 12)  # End Time
        detail_sheet.set_column(2, 2, 12)  # Duration
        detail_sheet.set_column(3, 3, 50)  # Description - genişletildi
        detail_sheet.set_column(4, 4, 10)  # Billable
        detail_sheet.set_column(5, 5, 12)  # Logo column
    
    output.seek(0)
    return output


# ============== PDF RAPOR OLUŞTURMA (Düzeltilmiş) ==============

def generate_pdf_report(df, format_choice, report_period, projects, customers, logo_data=None, company_info=None):
    """PDF raporu oluşturur - Hem Summary hem Detailed"""
    output = BytesIO()
    
    # Süreleri hesapla
    df["raw_seconds"] = df["Duration (h)"].apply(parse_duration_to_seconds)
    df["rounded_seconds"] = df["raw_seconds"].apply(round_to_nearest_minute)
    
    if format_choice == "hours":
        df["formatted_duration"] = df["rounded_seconds"] / 86400
    else:
        df["formatted_duration"] = (df["rounded_seconds"] / 3600).round(2)
    
    df['ParsedDate'] = pd.to_datetime(df['Start Date'], format='%d/%m/%Y', errors='coerce')
    df["Day"] = df["ParsedDate"].apply(lambda d: d.strftime("%d (%A)") if pd.notnull(d) else "Unknown")
    df["DayFull"] = df["ParsedDate"].apply(lambda d: d.strftime("%d %B %Y (%A)") if pd.notnull(d) else "Unknown")
    
    all_days = pd.date_range(start=df['ParsedDate'].min(), end=df['ParsedDate'].max(), freq='D') if not df['ParsedDate'].dropna().empty else pd.date_range(start="2025-01-01", periods=1)
    all_days_str = [d.strftime("%d (%A)") for d in all_days]
    
    # PDF oluştur
    doc = SimpleDocTemplate(output, pagesize=landscape(A4),
                           topMargin=0.5*inch, bottomMargin=0.5*inch,
                           leftMargin=0.5*inch, rightMargin=0.5*inch)
    
    story = []
    styles = getSampleStyleSheet()
    
    # UTF-8 desteği için font kaydetme
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    
    # Helvetica zaten mevcuttur, UTF-8 için DejaVu kullanabiliriz
    # Ama basit çözüm: Türkçe karakterleri düzelt
    def fix_turkish(text):
        """Türkçe karakterleri düzelt"""
        if isinstance(text, str):
            replacements = {
                'ç': 'c', 'Ç': 'C', 'ğ': 'g', 'Ğ': 'G',
                'ı': 'i', 'İ': 'I', 'ö': 'o', 'Ö': 'O',
                'ş': 's', 'Ş': 'S', 'ü': 'u', 'Ü': 'U'
            }
            for tr_char, en_char in replacements.items():
                text = text.replace(tr_char, en_char)
        return text
    
    # Stil tanımlamaları
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#4472C4'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=15,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )
    # ============== SUMMARY REPORT ==============

    story.append(Paragraph("Time Tracking Report - Summary", title_style))
    story.append(Spacer(1, 0.2*inch))

    # Şirket bilgileri ve logo
    if company_info:
        if logo_data:
            try:
                logo_img = BytesIO(logo_data['data'])
                img = RLImage(logo_img, width=1.5*inch, height=0.75*inch)
                story.append(img)
                story.append(Spacer(1, 0.2*inch))
            except:
                pass
        
        info_data = []
        if company_info.get('company_name'):
            info_data.append(['Company:', fix_turkish(company_info.get('company_name', ''))])
        if company_info.get('contact_person'):
            info_data.append(['Contact:', fix_turkish(company_info.get('contact_person', ''))])
        if company_info.get('phone'):
            info_data.append(['Phone:', company_info.get('phone', '')])
        if company_info.get('address'):
            info_data.append(['Address:', fix_turkish(company_info.get('address', ''))])
        
        if info_data:
            info_table = Table(info_data, colWidths=[1.5*inch, 5*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.2*inch))

    # Rapor bilgileri
    report_info_data = [
        ['Period:', fix_turkish(report_period)],
        ['Projects:', fix_turkish(projects)],
        ['Customers:', fix_turkish(customers)]
    ]

    report_info_table = Table(report_info_data, colWidths=[1.5*inch, 5*inch])
    report_info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(report_info_table)
    story.append(Spacer(1, 0.3*inch))

    # Kullanıcı bazında özet
    for user in sorted(df["User"].dropna().unique()):
        user_df = df[df["User"] == user].copy()
        
        story.append(Paragraph(f"<b>User: {fix_turkish(user)}</b>", subtitle_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Günlük tablo
        table_data = [['Day', 'Description', 'Billable', 'Duration']]
        
        for day in all_days_str:
            day_df = user_df[user_df["Day"] == day]
            
            if day_df.empty:
                continue
            
            unique_descriptions = []
            for desc in day_df["Description"].tolist():
                desc_str = str(desc).strip()
                if desc_str and desc_str not in unique_descriptions and desc_str != 'nan':
                    unique_descriptions.append(desc_str)
            
            combined_description = " | ".join(unique_descriptions) if unique_descriptions else ""
            if len(combined_description) > 80:
                combined_description = combined_description[:77] + "..."
            
            billable_count = (day_df["Billable"] == "Yes").sum()
            non_billable_count = (day_df["Billable"] == "No").sum()
            
            if billable_count > 0 and non_billable_count > 0:
                billable_status = "Mixed"
            elif billable_count > 0:
                billable_status = "Yes"
            else:
                billable_status = "No"
            
            total_duration = day_df["formatted_duration"].sum()
            
            if format_choice == "hours":
                duration_str = f"{int(total_duration * 24)}:{int((total_duration * 24 * 60) % 60):02d}"
            else:
                duration_str = f"{total_duration:.2f}"
            
            table_data.append([
                fix_turkish(day),
                fix_turkish(combined_description),
                billable_status,
                duration_str
            ])
        
        # Toplamlar
        billable_df = user_df[user_df["Billable"] == "Yes"]
        non_billable_df = user_df[user_df["Billable"] == "No"]
        
        total_billable = billable_df["formatted_duration"].sum()
        total_non_billable = non_billable_df["formatted_duration"].sum()
        total_overall = user_df["formatted_duration"].sum()
        
        if format_choice == "hours":
            billable_str = f"{int(total_billable * 24)}:{int((total_billable * 24 * 60) % 60):02d}"
            non_billable_str = f"{int(total_non_billable * 24)}:{int((total_non_billable * 24 * 60) % 60):02d}"
            overall_str = f"{int(total_overall * 24)}:{int((total_overall * 24 * 60) % 60):02d}"
        else:
            billable_str = f"{total_billable:.2f}"
            non_billable_str = f"{total_non_billable:.2f}"
            overall_str = f"{total_overall:.2f}"
        
        table_data.append(['', 'BILLABLE TOTAL', '', billable_str])
        table_data.append(['', 'NON-BILLABLE TOTAL', '', non_billable_str])
        table_data.append(['', 'GRAND TOTAL', '', overall_str])
        
        # Tablo oluştur (genişlikler düzeltildi)
        t = Table(table_data, colWidths=[1.3*inch, 4.2*inch, 0.9*inch, 1.1*inch])
        t.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('FONTSIZE', (0, 1), (-1, -4), 8),
            ('GRID', (0, 0), (-1, -4), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),  # Duration sağa hizalı
            
            # Totals
            ('BACKGROUND', (0, -3), (-1, -3), colors.HexColor('#C6EFCE')),
            ('BACKGROUND', (0, -2), (-1, -2), colors.HexColor('#FFC7CE')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FFEB9C')),
            ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -3), (-1, -1), 9),
            ('GRID', (0, -3), (-1, -1), 0.5, colors.grey),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(t)
        story.append(Spacer(1, 0.3*inch))

    # ============== DETAILED REPORT ==============

    story.append(PageBreak())
    story.append(Paragraph("Time Tracking Report - Detailed", title_style))
    story.append(Spacer(1, 0.2*inch))

    # Şirket bilgileri tekrar (detailed için)
    if company_info:
        if logo_data:
            try:
                logo_img = BytesIO(logo_data['data'])
                img = RLImage(logo_img, width=1.5*inch, height=0.75*inch)
                story.append(img)
                story.append(Spacer(1, 0.2*inch))
            except:
                pass
        
        info_data = []
        if company_info.get('company_name'):
            info_data.append(['Company:', fix_turkish(company_info.get('company_name', ''))])
        if company_info.get('contact_person'):
            info_data.append(['Contact:', fix_turkish(company_info.get('contact_person', ''))])
        if company_info.get('phone'):
            info_data.append(['Phone:', company_info.get('phone', '')])
        if company_info.get('address'):
            info_data.append(['Address:', fix_turkish(company_info.get('address', ''))])
        
        if info_data:
            info_table = Table(info_data, colWidths=[1.5*inch, 5*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.2*inch))

    # Rapor bilgileri
    story.append(report_info_table)
    story.append(Spacer(1, 0.3*inch))

    # Detaylı kayıtlar
    df_sorted = df.sort_values(['User', 'ParsedDate', 'Start Time'])

    for user_value in sorted(df_sorted['User'].dropna().unique()):
        user_df = df_sorted[df_sorted['User'] == user_value]
        
        story.append(Paragraph(f"<b>User: {fix_turkish(user_value)}</b>", subtitle_style))
        story.append(Spacer(1, 0.1*inch))
        
        for date_value in sorted(user_df['DayFull'].unique()):
            if pd.isna(date_value) or date_value == "Unknown":
                continue
                
            date_df = user_df[user_df['DayFull'] == date_value]
            
            story.append(Paragraph(f"Date: {fix_turkish(date_value)}", 
                                ParagraphStyle('DateStyle', fontSize=11, textColor=colors.HexColor('#4472C4'), 
                                            fontName='Helvetica-Bold', spaceAfter=8)))
            
            # Detaylı tablo
            detail_data = [['Start Time', 'End Time', 'Duration', 'Description', 'Billable']]
            
            for idx, row_data in date_df.iterrows():
                if format_choice == "hours":
                    duration_str = f"{int(row_data['formatted_duration'] * 24)}:{int((row_data['formatted_duration'] * 24 * 60) % 60):02d}"
                else:
                    duration_str = f"{row_data['formatted_duration']:.2f}"
                
                desc_text = fix_turkish(str(row_data.get('Description', '')))
                if len(desc_text) > 60:
                    desc_text = desc_text[:57] + "..."
                
                detail_data.append([
                    str(row_data.get('Start Time', '')),
                    str(row_data.get('End Time', '')),
                    duration_str,
                    desc_text,
                    str(row_data.get('Billable', 'No'))
                ])
            
            detail_table = Table(detail_data, colWidths=[0.9*inch, 0.9*inch, 0.9*inch, 3.5*inch, 0.8*inch])
            detail_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 1), (2, -1), 'CENTER'),  # Time ve Duration center
                ('ALIGN', (2, 1), (2, -1), 'RIGHT'),   # Duration sağa
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            
            story.append(detail_table)
            story.append(Spacer(1, 0.15*inch))
        
        story.append(Spacer(1, 0.2*inch))

    # PDF'i oluştur
    doc.build(story)
    output.seek(0)
    return output


# ============== Hata Yönetimi ==============

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

# ============== Test Route ==============

@app.route('/test-db')
def test_db():
    """Test MongoDB connection"""
    try:
        mongo.db.command('ping')
        user_count = mongo.db.users.count_documents({})
        return jsonify({
            'status': 'success',
            'message': 'MongoDB connected successfully!',
            'database': 'Csv',
            'collection': 'users',
            'user_count': user_count
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)