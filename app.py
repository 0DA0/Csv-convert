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

# ============== Rapor Şemaları ==============

REPORT_SCHEMAS = {
    'classic': {
        'name': 'Classic Report',
        'description': 'Traditional timesheet format with daily breakdown',
        'columns': ['Day', 'Total Duration', 'Projects'],
        'show_details': True
    },
    'minimalist': {
        'name': 'Minimalist Report',
        'description': 'Clean and simple format focusing on totals',
        'columns': ['Day', 'Total Duration'],
        'show_details': False
    },
    'detailed': {
        'name': 'Detailed Report',
        'description': 'Comprehensive report with all information',
        'columns': ['Day', 'Total Duration', 'Projects', 'Descriptions', 'Billable Status'],
        'show_details': True
    },
    'project_focused': {
        'name': 'Project-Focused Report',
        'description': 'Organized by projects first',
        'columns': ['Project', 'Day', 'Duration', 'Description'],
        'show_details': True
    }
}

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
    return render_template('dashboard.html', schemas=REPORT_SCHEMAS)

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
        selected_schema = request.form.get('schema', 'classic')
        selected_columns = request.form.getlist('selected_columns[]')
        selected_projects = request.form.getlist('projectSelect[]')
        selected_clients = request.form.getlist('clientSelect[]')
        selected_users = request.form.getlist('userSelect[]')
        format_choice = request.form.get('formatSelect', 'decimal')
        
        # "All" seçeneklerini filtrele
        selected_projects = [p for p in selected_projects if p and 'All' not in p]
        selected_clients = [c for c in selected_clients if c and 'All' not in c]
        selected_users = [u for u in selected_users if u and 'All' not in u]
        
        # Filtreleri uygula
        original_df = df.copy()
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
        
        # Logo bilgisini hazırla
        logo_data = None
        if current_user.user_type == 'company' and current_user.has_logo():
            logo_data = {
                'data': current_user.company_profile.get('logo_data'),
                'mimetype': current_user.company_profile.get('logo_mimetype', 'image/png')
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
        
        # Excel oluşturma
        output = generate_excel_report(df, selected_schema, format_choice, report_period, 
                                      overall_projects, overall_customers, logo_data)
        
        # Dosya adı
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Report_{timestamp}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        app.logger.error(f"Error in convert: {str(e)}\n{traceback.format_exc()}")
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('dashboard'))
    
def generate_excel_report(df, schema, format_choice, report_period, projects, customers, logo_data=None):
    """Excel raporu oluşturur - Hem özet hem detaylı sayfa ile"""
    output = BytesIO()
    
    # Süreleri hesapla
    df["raw_seconds"] = df["Duration (h)"].apply(parse_duration_to_seconds)
    df["rounded_seconds"] = df["raw_seconds"].apply(round_to_nearest_minute)
    
    # Format seçimine göre süreleri dönüştür
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
        
        info_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'bold': False
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
        
        # Detay sayfası için formatlar
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
        summary_sheet.set_margins(left=0.5, right=0.5, top=0.75, bottom=0.75)
        summary_sheet.repeat_rows(0, 3)
        
        row = 0
        
        # Logo varsa ekle (F kolonuna)
        if logo_data is not None:
            try:
                temp_logo = BytesIO(logo_data['data'])
                summary_sheet.insert_image(row, 5, "logo", {
                    'image_data': temp_logo,
                    'x_scale': 0.3,
                    'y_scale': 0.3,
                    'x_offset': 10,
                    'y_offset': 5
                })
            except Exception as e:
                app.logger.error(f"Error inserting logo: {str(e)}")
        
        # Genel Rapor bilgileri - SADECE EN BAŞTA BİR KERE
        summary_sheet.write(row, 0, "Projects:", header_format)
        summary_sheet.merge_range(row, 1, row, 4, sanitize_excel_cell(projects), info_format)
        summary_sheet.set_row(row, 20)
        row += 1
        
        summary_sheet.write(row, 0, "Customers:", header_format)
        summary_sheet.merge_range(row, 1, row, 4, sanitize_excel_cell(customers), info_format)
        summary_sheet.set_row(row, 20)
        row += 1
        
        summary_sheet.write(row, 0, "Period:", header_format)
        summary_sheet.merge_range(row, 1, row, 4, sanitize_excel_cell(report_period), info_format)
        summary_sheet.set_row(row, 20)
        row += 2
        
        # Kullanıcı bazında özet - SADECE USER VE TABLO
        for user in sorted(df["User"].dropna().unique()):
            user_df = df[df["User"] == user].copy()
            
            # Kullanıcı başlığı (A-D kolonları arası)
            summary_sheet.merge_range(row, 0, row, 3, sanitize_excel_cell(f"User: {user}"), user_header_format)
            summary_sheet.set_row(row, 24)
            row += 1
            
            # Tablo başlıkları
            summary_sheet.write(row, 0, "Day", header_format)
            summary_sheet.write(row, 1, "Description", header_format)
            summary_sheet.write(row, 2, "Billable", header_format)
            summary_sheet.write(row, 3, "Duration", header_format)
            summary_sheet.set_row(row, 20)
            row += 1
            
            # Günlük detaylar
            for day in all_days_str:
                day_df = user_df[user_df["Day"] == day]
                
                if day_df.empty:
                    continue
                
                # Benzersiz description'ları al
                unique_descriptions = []
                for desc in day_df["Description"].tolist():
                    desc_str = str(desc).strip()
                    if desc_str and desc_str not in unique_descriptions and desc_str != 'nan':
                        unique_descriptions.append(desc_str)
                
                combined_description = " | ".join(unique_descriptions) if unique_descriptions else ""
                
                # Billable durumu
                billable_count = (day_df["Billable"] == "Yes").sum()
                non_billable_count = (day_df["Billable"] == "No").sum()
                
                if billable_count > 0 and non_billable_count > 0:
                    billable_status = "Mixed"
                elif billable_count > 0:
                    billable_status = "Yes"
                else:
                    billable_status = "No"
                
                total_duration = day_df["formatted_duration"].sum()
                
                # Satıra yaz
                summary_sheet.write(row, 0, sanitize_excel_cell(day), cell_format)
                summary_sheet.write(row, 1, sanitize_excel_cell(combined_description), cell_wrap_format)
                summary_sheet.write(row, 2, sanitize_excel_cell(billable_status), cell_center_format)
                
                if format_choice == "hours":
                    summary_sheet.write_number(row, 3, total_duration, time_format)
                else:
                    summary_sheet.write_number(row, 3, total_duration, number_format)
                
                # Satır yüksekliği
                desc_length = len(combined_description)
                if desc_length > 100:
                    summary_sheet.set_row(row, 60)
                elif desc_length > 50:
                    summary_sheet.set_row(row, 40)
                else:
                    summary_sheet.set_row(row, 20)
                
                row += 1
            
            # Kullanıcı için toplamlar
            row += 1
            
            billable_df = user_df[user_df["Billable"] == "Yes"]
            non_billable_df = user_df[user_df["Billable"] == "No"]
            
            total_billable = billable_df["formatted_duration"].sum()
            total_non_billable = non_billable_df["formatted_duration"].sum()
            total_overall = user_df["formatted_duration"].sum()
            
            # Billable Total
            summary_sheet.merge_range(row, 0, row, 2, "BILLABLE TOTAL", green_format)
            if format_choice == "hours":
                summary_sheet.write_number(row, 3, total_billable, green_time_format)
            else:
                summary_sheet.write_number(row, 3, total_billable, green_number_format)
            summary_sheet.set_row(row, 22)
            row += 1
            
            # Non-Billable Total
            summary_sheet.merge_range(row, 0, row, 2, "NON-BILLABLE TOTAL", red_format)
            if format_choice == "hours":
                summary_sheet.write_number(row, 3, total_non_billable, red_time_format)
            else:
                summary_sheet.write_number(row, 3, total_non_billable, red_number_format)
            summary_sheet.set_row(row, 22)
            row += 1
            
            # Grand Total
            summary_sheet.merge_range(row, 0, row, 2, "GRAND TOTAL", yellow_format)
            if format_choice == "hours":
                summary_sheet.write_number(row, 3, total_overall, yellow_time_format)
            else:
                summary_sheet.write_number(row, 3, total_overall, yellow_number_format)
            summary_sheet.set_row(row, 22)
            row += 3  # Sonraki user için boşluk
        
        # Yazdırma alanı (A-E kolonları)
        summary_sheet.print_area(0, 0, row - 1, 4)
        
        # Kolon genişlikleri
        summary_sheet.set_column(0, 0, 18)  # Day
        summary_sheet.set_column(1, 1, 55)  # Description
        summary_sheet.set_column(2, 2, 10)  # Billable
        summary_sheet.set_column(3, 3, 12)  # Duration
        summary_sheet.set_column(4, 4, 2)   # Boşluk
        
        # ============== SAYFA 2: DETAYLI RAPOR ==============
        detail_sheet = workbook.add_worksheet("Detailed Report")
        
        # Yazdırma ayarları
        detail_sheet.fit_to_pages(1, 0)
        detail_sheet.set_landscape()
        detail_sheet.set_paper(9)
        detail_sheet.center_horizontally()
        detail_sheet.set_margins(left=0.5, right=0.5, top=0.75, bottom=0.75)
        detail_sheet.repeat_rows(0, 2)
        
        detail_row = 0
        
        # Başlık
        detail_sheet.merge_range(detail_row, 0, detail_row, 4, "Detailed Time Report", header_format)
        detail_sheet.set_row(detail_row, 25)
        detail_row += 1
        
        detail_sheet.merge_range(detail_row, 0, detail_row, 4, sanitize_excel_cell(f"Period: {report_period}"), info_format)
        detail_sheet.set_row(detail_row, 20)
        detail_row += 2
        
        # Verileri tarihe ve kullanıcıya göre grupla
        df_sorted = df.sort_values(['ParsedDate', 'User', 'Start Time'])
        
        # Tarihe göre grupla
        for date_value in df_sorted['DayFull'].unique():
            if pd.isna(date_value) or date_value == "Unknown":
                continue
                
            date_df = df_sorted[df_sorted['DayFull'] == date_value]
            
            # Tarih başlığı (A-E kolonları arası)
            detail_sheet.merge_range(detail_row, 0, detail_row, 4, sanitize_excel_cell(f"Date: {date_value}"), detail_date_header_format)
            detail_sheet.set_row(detail_row, 22)
            detail_row += 1
            
            # Bu tarihteki tüm projeler ve clientlar
            date_projects = ", ".join(sorted(date_df["Project"].dropna().unique()))
            date_clients = ", ".join(sorted(date_df["Client"].dropna().unique()))
            
            # Project bilgisi - Summary ile aynı formatta
            detail_sheet.write(detail_row, 0, "Projects:", header_format)
            detail_sheet.merge_range(detail_row, 1, detail_row, 4, sanitize_excel_cell(date_projects), info_format)
            detail_sheet.set_row(detail_row, 20)
            detail_row += 1
            
            # Client bilgisi - Summary ile aynı formatta
            detail_sheet.write(detail_row, 0, "Clients:", header_format)
            detail_sheet.merge_range(detail_row, 1, detail_row, 4, sanitize_excel_cell(date_clients), info_format)
            detail_sheet.set_row(detail_row, 20)
            detail_row += 1
            
            # User'dan önce boşluk
            detail_row += 1
            
            # Bu tarihteki kullanıcılara göre grupla
            for user_value in date_df['User'].unique():
                if pd.isna(user_value):
                    continue
                    
                user_df = date_df[date_df['User'] == user_value]
                
                # Kullanıcı başlığı (A-E kolonları arası)
                detail_sheet.merge_range(detail_row, 0, detail_row, 4, sanitize_excel_cell(f"User: {user_value}"), user_header_format)
                detail_sheet.set_row(detail_row, 22)
                detail_row += 1
                
                # Tablo başlıkları
                headers = ["Start Time", "End Time", "Duration", "Description", "Billable"]
                for col_idx, header in enumerate(headers):
                    detail_sheet.write(detail_row, col_idx, header, detail_header_format)
                
                detail_sheet.set_row(detail_row, 20)
                detail_row += 1
                
                # Bu kullanıcının bu tarihteki tüm kayıtları
                for idx, row_data in user_df.iterrows():
                    detail_sheet.write(detail_row, 0, sanitize_excel_cell(str(row_data.get('Start Time', ''))), detail_cell_center)
                    detail_sheet.write(detail_row, 1, sanitize_excel_cell(str(row_data.get('End Time', ''))), detail_cell_center)
                    
                    # Duration formatı
                    if format_choice == "hours":
                        detail_sheet.write_number(detail_row, 2, row_data['formatted_duration'], detail_time_format)
                    else:
                        detail_sheet.write_number(detail_row, 2, row_data['formatted_duration'], detail_number_format)
                    
                    # Description
                    desc_text = sanitize_excel_cell(str(row_data.get('Description', '')))
                    detail_sheet.write(detail_row, 3, desc_text, detail_cell_wrap)
                    
                    detail_sheet.write(detail_row, 4, sanitize_excel_cell(str(row_data.get('Billable', 'No'))), detail_cell_center)
                    
                    # Satır yüksekliği
                    desc_length = len(desc_text)
                    if desc_length > 100:
                        detail_sheet.set_row(detail_row, 60)
                    elif desc_length > 50:
                        detail_sheet.set_row(detail_row, 40)
                    else:
                        detail_sheet.set_row(detail_row, 20)
                    
                    detail_row += 1
                
                # Kullanıcı için boş satır
                detail_row += 1
            
            # Tarih için boş satır
            detail_row += 1
        
        # Yazdırma alanı (A-E kolonları)
        detail_sheet.print_area(0, 0, detail_row - 1, 4)
        
        # Kolon genişlikleri
        detail_sheet.set_column(0, 0, 12)  # Start Time
        detail_sheet.set_column(1, 1, 12)  # End Time
        detail_sheet.set_column(2, 2, 12)  # Duration
        detail_sheet.set_column(3, 3, 50)  # Description
        detail_sheet.set_column(4, 4, 10)  # Billable
    
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
        # Test connection
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