from flask import Flask, render_template, request, flash, redirect, url_for, send_file, abort, session, jsonify, Response
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import CSRFProtect
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
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://localhost/timetracker')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# PostgreSQL URL düzeltmesi (Render için)
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

# ============== Eklentiler ==============
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

ALLOWED_EXTENSIONS = {'csv'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============== Veritabanı Modelleri ==============

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'individual' or 'company'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # İlişkiler
    individual_profile = db.relationship('IndividualProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    company_profile = db.relationship('CompanyProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class IndividualProfile(db.Model):
    __tablename__ = 'individual_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))

class CompanyProfile(db.Model):
    __tablename__ = 'company_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    logo_data = db.Column(db.LargeBinary)  # Logo verisini binary olarak sakla
    logo_mimetype = db.Column(db.String(50))  # MIME type (image/png, image/jpeg, vb.)
    
    def set_logo(self, file):
        """Logo dosyasını veritabanına kaydet"""
        if file and file.filename:
            self.logo_data = file.read()
            self.logo_mimetype = file.content_type
    
    def get_logo_base64(self):
        """Logo'yu base64 string olarak döndür (HTML img src için)"""
        if self.logo_data:
            encoded = base64.b64encode(self.logo_data).decode('utf-8')
            return f"data:{self.logo_mimetype};base64,{encoded}"
        return None
    
    def has_logo(self):
        """Logo var mı kontrol et"""
        return self.logo_data is not None

# ============== Login Manager ==============

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

# ============== Logo Servis Route ==============

@app.route('/logo/<int:user_id>')
@login_required
def serve_logo(user_id):
    """Veritabanından logo'yu servis et"""
    if current_user.id != user_id:
        abort(403)
    
    if current_user.user_type == 'company' and current_user.company_profile:
        profile = current_user.company_profile
        if profile.logo_data:
            return Response(profile.logo_data, mimetype=profile.logo_mimetype)
    
    abort(404)

# ============== Kimlik Doğrulama Routes ==============

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))
        
        user = User(email=email, user_type=user_type)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        if user_type == 'individual':
            profile = IndividualProfile(
                user_id=user.id,
                full_name=request.form.get('full_name'),
                phone=request.form.get('phone')
            )
            db.session.add(profile)
        else:
            profile = CompanyProfile(
                user_id=user.id,
                company_name=request.form.get('company_name'),
                contact_person=request.form.get('contact_person'),
                phone=request.form.get('phone'),
                address=request.form.get('address')
            )
            
            # Logo yükleme
            logo_file = request.files.get('logo')
            if logo_file and logo_file.filename and allowed_image(logo_file.filename):
                # Dosya boyutu kontrolü
                logo_file.seek(0, os.SEEK_END)
                file_size = logo_file.tell()
                logo_file.seek(0)
                
                if file_size <= 2 * 1024 * 1024:  # 2MB
                    profile.set_logo(logo_file)
                else:
                    flash('Logo file size must be less than 2MB.', 'error')
            
            db.session.add(profile)
        
        db.session.commit()
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
        user = User.query.filter_by(email=email).first()
        
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
        if current_user.user_type == 'individual':
            profile = current_user.individual_profile
            profile.full_name = request.form.get('full_name')
            profile.phone = request.form.get('phone')
        else:
            profile = current_user.company_profile
            profile.company_name = request.form.get('company_name')
            profile.contact_person = request.form.get('contact_person')
            profile.phone = request.form.get('phone')
            profile.address = request.form.get('address')
            
            # Logo güncelleme
            logo_file = request.files.get('logo')
            if logo_file and logo_file.filename and allowed_image(logo_file.filename):
                # Dosya boyutu kontrolü
                logo_file.seek(0, os.SEEK_END)
                file_size = logo_file.tell()
                logo_file.seek(0)
                
                if file_size <= 2 * 1024 * 1024:  # 2MB
                    profile.set_logo(logo_file)
                else:
                    flash('Logo file size must be less than 2MB.', 'error')
                    return redirect(url_for('profile'))
        
        db.session.commit()
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
        
        df["Duration (h)"].fillna("00:00:00", inplace=True)
        df["Billable"].fillna("No", inplace=True)
        
        # Filtreleri al
        selected_schema = request.form.get('schema', 'classic')
        selected_columns = request.form.getlist('selected_columns[]')
        selected_projects = request.form.getlist('projectSelect[]')
        selected_clients = request.form.getlist('clientSelect[]')
        selected_users = request.form.getlist('userSelect[]')
        format_choice = request.form.get('formatSelect', 'decimal')
        
        # Filtreleri uygula
        if selected_projects:
            df = df[df["Project"].isin(selected_projects)]
        if selected_clients:
            df = df[df["Client"].isin(selected_clients)]
        if selected_users:
            df = df[df["User"].isin(selected_users)]
        
        # Rapor bilgileri
        overall_projects = ", ".join(df["Project"].dropna().unique())
        overall_customers = ", ".join(df["Client"].dropna().unique())
        
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
        output = generate_excel_report(df, selected_schema, format_choice, report_period, overall_projects, overall_customers)
        
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

def generate_excel_report(df, schema, format_choice, report_period, projects, customers):
    """Excel raporu oluşturur"""
    output = BytesIO()
    
    # Süreleri hesapla
    df["raw_seconds"] = df["Duration (h)"].apply(parse_duration_to_seconds)
    df["rounded_seconds"] = df["raw_seconds"].apply(round_to_nearest_minute)
    
    if format_choice == "decimal":
        df["formatted_duration"] = (df["rounded_seconds"] / 3600).round(2)
    else:
        df["formatted_duration"] = df["rounded_seconds"] / 86400
    
    df['ParsedDate'] = pd.to_datetime(df['Start Date'], format='%d/%m/%Y', errors='coerce')
    df["Day"] = df["ParsedDate"].apply(lambda d: d.strftime("%d (%A)") if pd.notnull(d) else "Unknown")
    
    all_days = pd.date_range(start=df['ParsedDate'].min(), end=df['ParsedDate'].max(), freq='D') if not df['ParsedDate'].dropna().empty else pd.date_range(start="2025-01-01", periods=1)
    all_days_str = [d.strftime("%d (%A)") for d in all_days]
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Format tanımlamaları
        header_format = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#4472C4', 'font_color': 'white'})
        cell_format = workbook.add_format({'border': 1})
        number_format = workbook.add_format({'num_format': '0.00', 'border': 1})
        time_format = workbook.add_format({'num_format': '[h]:mm', 'border': 1})
        yellow_format = workbook.add_format({'bg_color': 'yellow', 'border': 1, 'bold': True})
        
        # Rapor sayfası
        report_sheet = workbook.add_worksheet("Report")
        
        # Kullanıcı/Şirket bilgisi
        row = 0
        if current_user.user_type == 'company':
            profile = current_user.company_profile
            report_sheet.write(row, 0, sanitize_excel_cell(f"Company: {profile.company_name}"), header_format)
            
            # Logo ekleme - veritabanından
            if profile.has_logo():
                try:
                    # Logo verisini geçici dosyaya yaz
                    temp_logo = BytesIO(profile.logo_data)
                    report_sheet.insert_image(row, 7, "logo", {
                        'image_data': temp_logo,
                        'x_scale': 0.5,
                        'y_scale': 0.5
                    })
                except Exception as e:
                    app.logger.error(f"Error inserting logo: {str(e)}")
        else:
            profile = current_user.individual_profile
            report_sheet.write(row, 0, sanitize_excel_cell(f"Name: {profile.full_name}"), header_format)
        
        row += 1
        report_sheet.write(row, 0, sanitize_excel_cell(f"Projects: {projects}"), cell_format)
        row += 1
        report_sheet.write(row, 0, sanitize_excel_cell(f"Customers: {customers}"), cell_format)
        row += 1
        report_sheet.write(row, 0, sanitize_excel_cell(f"Period: {report_period}"), cell_format)
        row += 2
        
        # Kullanıcı bazında rapor
        for user in df["User"].dropna().unique():
            user_df = df[df["User"] == user].copy()
            
            report_sheet.write(row, 0, sanitize_excel_cell(f"User: {user}"), header_format)
            row += 1
            
            # Günlük özet
            grouped = user_df.groupby("Day")["formatted_duration"].sum().reindex(all_days_str, fill_value=0)
            
            report_sheet.write(row, 0, "Day", header_format)
            report_sheet.write(row, 1, "Duration", header_format)
            row += 1
            
            for day, duration in grouped.items():
                report_sheet.write(row, 0, sanitize_excel_cell(day), cell_format)
                if format_choice == "hours":
                    report_sheet.write_number(row, 1, duration, time_format)
                else:
                    report_sheet.write_number(row, 1, duration, number_format)
                row += 1
            
            # Total
            total = grouped.sum()
            report_sheet.write(row, 0, "TOTAL", yellow_format)
            if format_choice == "hours":
                report_sheet.write_number(row, 1, total, yellow_format)
            else:
                report_sheet.write_number(row, 1, total, yellow_format)
            row += 2
    
    output.seek(0)
    return output

# ============== Hata Yönetimi ==============

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

# ============== Veritabanı Oluşturma ==============

@app.cli.command()
def init_db():
    """Veritabanını oluşturur"""
    db.create_all()
    print("Database initialized!")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)