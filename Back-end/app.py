from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
import pandas as pd
from io import BytesIO
import os
from cryptography.fernet import Fernet
import re
import base64
from datetime import datetime, timedelta
import calendar
import traceback
import requests

# ============== Flask Yapılandırması ==============
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MONGO_URI'] = os.environ.get('MONGO_URI')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

# CORS - Angular için (Render URL'ini ekle)
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:4200",  # Local development
            "https://csv-convert-front.onrender.com",  # Render production
            "https://*.onrender.com"  # Tüm Render subdomain'leri
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Clockify-Api-Key"],  # BU SATIRI GÜNCELLEDİK
        "supports_credentials": True
    }
})
mongo = PyMongo(app)
jwt = JWTManager(app)

# Encryption key - Environment variable'dan al veya generate et
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key()
    print(f"WARNING: Generated new encryption key. Add this to your environment: ENCRYPTION_KEY={ENCRYPTION_KEY.decode()}")
else:
    ENCRYPTION_KEY = ENCRYPTION_KEY.encode()

cipher_suite = Fernet(ENCRYPTION_KEY)

# ============== Yardımcı Fonksiyonlar ==============

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

def generate_excel_report(df, format_choice, report_period, projects, customers, logo_data=None, company_info=None):
    """Excel raporu oluşturur - Summary ve Detailed Report ile"""
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
    
    # Start Time ve End Time kolonlarını ekle (yoksa)
    if "Start Time" not in df.columns:
        df["Start Time"] = ""
    if "End Time" not in df.columns:
        df["End Time"] = ""
    
    all_days = pd.date_range(start=df['ParsedDate'].min(), end=df['ParsedDate'].max(), freq='D') if not df['ParsedDate'].dropna().empty else pd.date_range(start="2025-01-01", periods=1)
    all_days_str = [d.strftime("%d (%A)") for d in all_days]
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # ============== FORMAT TANIMLARI ==============
        header_format = workbook.add_format({
            'bold': True, 'border': 1, 'bg_color': '#4472C4', 
            'font_color': 'white', 'align': 'center', 'valign': 'vcenter'
        })
        
        info_label_format = workbook.add_format({
            'bold': True, 'border': 1, 'bg_color': '#4472C4',
            'font_color': 'white', 'align': 'left', 'valign': 'vcenter'
        })
        
        info_value_format = workbook.add_format({
            'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True
        })
        
        cell_format = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})
        cell_wrap_format = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'top', 'text_wrap': True})
        cell_center_format = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        
        number_format = workbook.add_format({'num_format': '0.00', 'border': 1, 'align': 'right', 'valign': 'vcenter'})
        time_format = workbook.add_format({'num_format': '[h]:mm', 'border': 1, 'align': 'right', 'valign': 'vcenter'})
        
        yellow_format = workbook.add_format({'bg_color': '#FFEB9C', 'border': 1, 'bold': True, 'align': 'center', 'valign': 'vcenter'})
        yellow_number_format = workbook.add_format({'bg_color': '#FFEB9C', 'border': 1, 'bold': True, 'num_format': '0.00', 'align': 'right', 'valign': 'vcenter'})
        yellow_time_format = workbook.add_format({'bg_color': '#FFEB9C', 'border': 1, 'bold': True, 'num_format': '[h]:mm', 'align': 'right', 'valign': 'vcenter'})
        
        green_format = workbook.add_format({'bg_color': '#C6EFCE', 'border': 1, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_color': '#006100'})
        green_number_format = workbook.add_format({'bg_color': '#C6EFCE', 'border': 1, 'bold': True, 'num_format': '0.00', 'align': 'right', 'valign': 'vcenter', 'font_color': '#006100'})
        green_time_format = workbook.add_format({'bg_color': '#C6EFCE', 'border': 1, 'bold': True, 'num_format': '[h]:mm', 'align': 'right', 'valign': 'vcenter', 'font_color': '#006100'})
        
        red_format = workbook.add_format({'bg_color': '#FFC7CE', 'border': 1, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_color': '#9C0006'})
        red_number_format = workbook.add_format({'bg_color': '#FFC7CE', 'border': 1, 'bold': True, 'num_format': '0.00', 'align': 'right', 'valign': 'vcenter', 'font_color': '#9C0006'})
        red_time_format = workbook.add_format({'bg_color': '#FFC7CE', 'border': 1, 'bold': True, 'num_format': '[h]:mm', 'align': 'right', 'valign': 'vcenter', 'font_color': '#9C0006'})
        
        user_header_format = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#4472C4', 'font_color': 'white', 'align': 'left', 'valign': 'vcenter', 'font_size': 12})
        
        # Detailed Report için formatlar
        detail_header_format = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#667eea', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'font_size': 11})
        detail_date_header_format = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#4472C4', 'font_color': 'white', 'align': 'left', 'font_size': 12, 'valign': 'vcenter'})
        detail_cell_format = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_size': 10})
        detail_cell_wrap = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'top', 'font_size': 10, 'text_wrap': True})
        detail_cell_center = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 10})
        detail_number_format = workbook.add_format({'num_format': '0.00', 'border': 1, 'align': 'right', 'valign': 'vcenter', 'font_size': 10})
        detail_time_format = workbook.add_format({'num_format': '[h]:mm', 'border': 1, 'align': 'right', 'valign': 'vcenter', 'font_size': 10})
        
        # ============== SAYFA 1: ÖZET RAPOR ==============
        summary_sheet = workbook.add_worksheet("Summary Report")
        summary_sheet.fit_to_pages(1, 0)
        summary_sheet.set_landscape()
        summary_sheet.set_paper(9)
        
        row = 0
        
        # Logo ve Şirket Bilgileri
        if company_info or logo_data:
            table_start_row = row
            
            if company_info:
                summary_sheet.write(row, 0, "Company:", info_label_format)
                summary_sheet.merge_range(row, 1, row, 4, sanitize_excel_cell(company_info.get('company_name', '')), info_value_format)
                summary_sheet.set_row(row, 18)
                row += 1
                
                if company_info.get('contact_person'):
                    summary_sheet.write(row, 0, "Contact:", info_label_format)
                    summary_sheet.merge_range(row, 1, row, 4, sanitize_excel_cell(company_info.get('contact_person', '')), info_value_format)
                    summary_sheet.set_row(row, 18)
                    row += 1
                
                if company_info.get('phone'):
                    summary_sheet.write(row, 0, "Phone:", info_label_format)
                    summary_sheet.merge_range(row, 1, row, 4, sanitize_excel_cell(company_info.get('phone', '')), info_value_format)
                    summary_sheet.set_row(row, 18)
                    row += 1
                
                if company_info.get('address'):
                    summary_sheet.write(row, 0, "Address:", info_label_format)
                    summary_sheet.merge_range(row, 1, row, 4, sanitize_excel_cell(company_info.get('address', '')), info_value_format)
                    summary_sheet.set_row(row, 18)
                    row += 1
            
            if logo_data is not None:
                try:
                    temp_logo = BytesIO(logo_data['data'])
                    summary_sheet.insert_image(table_start_row, 5, "logo", {
                        'image_data': temp_logo,
                        'x_scale': 0.25, 'y_scale': 0.25,
                        'x_offset': 10, 'y_offset': 5,
                        'positioning': 1
                    })
                    for i in range(table_start_row, row):
                        summary_sheet.write(i, 5, "", info_value_format)
                except:
                    pass
            
            row += 1
        
        # Rapor Bilgileri
        summary_sheet.write(row, 0, "Period:", info_label_format)
        summary_sheet.merge_range(row, 1, row, 4, sanitize_excel_cell(report_period), info_value_format)
        if logo_data:
            summary_sheet.write(row, 5, "", info_value_format)
        summary_sheet.set_row(row, 18)
        row += 1
        
        summary_sheet.write(row, 0, "Projects:", info_label_format)
        summary_sheet.merge_range(row, 1, row, 4, sanitize_excel_cell(projects), info_value_format)
        if logo_data:
            summary_sheet.write(row, 5, "", info_value_format)
        summary_sheet.set_row(row, 18)
        row += 1
        
        summary_sheet.write(row, 0, "Customers:", info_label_format)
        summary_sheet.merge_range(row, 1, row, 4, sanitize_excel_cell(customers), info_value_format)
        if logo_data:
            summary_sheet.write(row, 5, "", info_value_format)
        summary_sheet.set_row(row, 18)
        row += 2
        
        # Kullanıcı bazında özet
        for user in sorted(df["User"].dropna().unique()):
            user_df = df[df["User"] == user].copy()
            
            summary_sheet.merge_range(row, 0, row, 4, sanitize_excel_cell(f"User: {user}"), user_header_format)
            summary_sheet.set_row(row, 20)
            row += 1
            
            # YENİ: Başlık satırı - Billable ve Free Duration olarak ayrıldı
            summary_sheet.write(row, 0, "Day", header_format)
            summary_sheet.write(row, 1, "Description", header_format)
            summary_sheet.write(row, 2, "Billable Duration", header_format)
            summary_sheet.write(row, 3, "Free Duration", header_format)
            summary_sheet.write(row, 4, "Total Duration", header_format)
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
                
                # YENİ: Billable ve Non-billable süreleri ayrı hesapla
                billable_duration = day_df[day_df["Billable"] == "Yes"]["formatted_duration"].sum()
                free_duration = day_df[day_df["Billable"] == "No"]["formatted_duration"].sum()
                total_duration = day_df["formatted_duration"].sum()
                
                summary_sheet.write(row, 0, sanitize_excel_cell(day), cell_format)
                summary_sheet.write(row, 1, sanitize_excel_cell(combined_description), cell_wrap_format)
                
                # Billable Duration
                if format_choice == "hours":
                    summary_sheet.write_number(row, 2, billable_duration, time_format)
                else:
                    summary_sheet.write_number(row, 2, billable_duration, number_format)
                
                # Free Duration
                if format_choice == "hours":
                    summary_sheet.write_number(row, 3, free_duration, time_format)
                else:
                    summary_sheet.write_number(row, 3, free_duration, number_format)
                
                # Total Duration
                if format_choice == "hours":
                    summary_sheet.write_number(row, 4, total_duration, time_format)
                else:
                    summary_sheet.write_number(row, 4, total_duration, number_format)
                
                desc_length = len(combined_description)
                lines_needed = max(1, (desc_length // 120) + 1)
                row_height = 18 * lines_needed
                summary_sheet.set_row(row, row_height)
                row += 1
            
            row += 1
            
            billable_df = user_df[user_df["Billable"] == "Yes"]
            non_billable_df = user_df[user_df["Billable"] == "No"]
            
            total_billable = billable_df["formatted_duration"].sum()
            total_non_billable = non_billable_df["formatted_duration"].sum()
            total_overall = user_df["formatted_duration"].sum()
            
            summary_sheet.merge_range(row, 0, row, 1, "BILLABLE TOTAL", green_format)
            if format_choice == "hours":
                summary_sheet.write_number(row, 2, total_billable, green_time_format)
            else:
                summary_sheet.write_number(row, 2, total_billable, green_number_format)
            summary_sheet.write(row, 3, "", green_format)
            summary_sheet.write(row, 4, "", green_format)
            summary_sheet.set_row(row, 20)
            row += 1
            
            summary_sheet.merge_range(row, 0, row, 1, "FREE TOTAL", red_format)
            summary_sheet.write(row, 2, "", red_format)
            if format_choice == "hours":
                summary_sheet.write_number(row, 3, total_non_billable, red_time_format)
            else:
                summary_sheet.write_number(row, 3, total_non_billable, red_number_format)
            summary_sheet.write(row, 4, "", red_format)
            summary_sheet.set_row(row, 20)
            row += 1
            
            summary_sheet.merge_range(row, 0, row, 1, "GRAND TOTAL", yellow_format)
            summary_sheet.write(row, 2, "", yellow_format)
            summary_sheet.write(row, 3, "", yellow_format)
            if format_choice == "hours":
                summary_sheet.write_number(row, 4, total_overall, yellow_time_format)
            else:
                summary_sheet.write_number(row, 4, total_overall, yellow_number_format)
            summary_sheet.set_row(row, 20)
            row += 3
        
        # YENİ: Kolon genişlikleri - landscape A4'e sığacak şekilde optimize edildi
        summary_sheet.set_column(0, 0, 14)   # Day
        summary_sheet.set_column(1, 1, 100)   # Description
        summary_sheet.set_column(2, 2, 12)   # Billable Duration
        summary_sheet.set_column(3, 3, 12)   # Free Duration
        summary_sheet.set_column(4, 4, 12)   # Total Duration
        summary_sheet.set_column(5, 5, 12)   # Logo column
        
        # ============== SAYFA 2: DETAYLI RAPOR ==============
        detail_sheet = workbook.add_worksheet("Detailed Report")
        detail_sheet.fit_to_pages(1, 0)
        detail_sheet.set_landscape()
        detail_sheet.set_paper(9)
        
        detail_row = 0
        
        # Başlık
        detail_sheet.merge_range(detail_row, 0, detail_row, 4, "Detailed Time Report", header_format)
        detail_sheet.set_row(detail_row, 22)
        detail_row += 1
        
        # Logo ve Şirket Bilgileri
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
                        'x_scale': 0.25, 'y_scale': 0.25,
                        'x_offset': 10, 'y_offset': 5,
                        'positioning': 1
                    })
                    for i in range(table_start_row, detail_row):
                        detail_sheet.write(i, 5, "", info_value_format)
                except:
                    pass
            
            detail_row += 1
        
        # Rapor Bilgileri
        detail_sheet.write(detail_row, 0, "Period:", info_label_format)
        detail_sheet.merge_range(detail_row, 1, detail_row, 4, sanitize_excel_cell(report_period), info_value_format)
        detail_sheet.set_row(detail_row, 18)
        detail_row += 1
        
        detail_sheet.write(detail_row, 0, "Projects:", info_label_format)
        detail_sheet.merge_range(detail_row, 1, detail_row, 4, sanitize_excel_cell(projects), info_value_format)
        detail_sheet.set_row(detail_row, 18)
        detail_row += 1
        
        detail_sheet.write(detail_row, 0, "Clients:", info_label_format)
        detail_sheet.merge_range(detail_row, 1, detail_row, 4, sanitize_excel_cell(customers), info_value_format)
        detail_sheet.set_row(detail_row, 18)
        detail_row += 2
        
        # Kullanıcı ve tarih bazında detaylı veriler
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
                
                # Başlık satırı
                headers = ["Start Time", "End Time", "Duration", "Description", "Billable"]
                for col_idx, header in enumerate(headers):
                    detail_sheet.write(detail_row, col_idx, header, detail_header_format)
                detail_sheet.set_row(detail_row, 18)
                detail_row += 1
                
                # Veri satırları
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
                    
                    # Satır yüksekliği - daha kompakt
                    desc_length = len(desc_text)
                    lines_needed = max(1, (desc_length // 60) + 1)
                    row_height = 16 * lines_needed
                    detail_sheet.set_row(detail_row, row_height)
                    
                    detail_row += 1
                
                detail_row += 1
            
            detail_row += 1
        
        # YENİ: Kolon genişlikleri - landscape A4'e tam sığacak şekilde optimize edildi
        detail_sheet.set_column(0, 0, 10)   # Start Time
        detail_sheet.set_column(1, 1, 10)   # End Time
        detail_sheet.set_column(2, 2, 10)   # Duration
        detail_sheet.set_column(3, 3, 84)   # Description
        detail_sheet.set_column(4, 4, 8)    # Billable
        detail_sheet.set_column(5, 5, 12)   # Logo column
    
    output.seek(0)
    return output

def encrypt_api_key(api_key):
    """API key'i şifrele"""
    if not api_key:
        return None
    return cipher_suite.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key):
    """API key'i çöz"""
    if not encrypted_key:
        return None
    try:
        return cipher_suite.decrypt(encrypted_key.encode()).decode()
    except:
        return None

# ============== AUTH ENDPOINTS ==============

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Kullanıcı kaydı - Data Source seçimi ile"""
    try:
        data = request.get_json()
        
        if mongo.db.users.find_one({'email': data['email']}):
            return jsonify({'error': 'Email already registered'}), 400
        
        user_doc = {
            'email': data['email'],
            'password_hash': generate_password_hash(data['password']),
            'user_type': data['user_type'],
            'data_source': data.get('data_source', 'csv'),  # YENİ: csv veya clockify
            'created_at': datetime.utcnow()
        }
        
        if data['user_type'] == 'individual':
            user_doc['individual_profile'] = {
                'full_name': data['full_name'],
                'phone': data.get('phone', '')
            }
        else:
            company_profile = {
                'company_name': data['company_name'],
                'contact_person': data.get('contact_person', ''),
                'phone': data.get('phone', ''),
                'address': data.get('address', '')
            }
            
            if 'logo_base64' in data and data['logo_base64']:
                logo_data = base64.b64decode(data['logo_base64'].split(',')[1])
                company_profile['logo_data'] = logo_data
                company_profile['logo_mimetype'] = data.get('logo_mimetype', 'image/png')
            
            user_doc['company_profile'] = company_profile
        
        # Eğer Clockify seçilmişse ve API key varsa, şifrele ve kaydet
        if data.get('data_source') == 'clockify' and data.get('clockify_api_key'):
            encrypted_key = encrypt_api_key(data['clockify_api_key'])
            user_doc['clockify_api_key'] = encrypted_key
        
        result = mongo.db.users.insert_one(user_doc)
        
        return jsonify({
            'message': 'User registered successfully',
            'user_id': str(result.inserted_id)
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Kullanıcı girişi"""
    try:
        data = request.get_json()
        user = mongo.db.users.find_one({'email': data['email']})
        
        if not user or not check_password_hash(user['password_hash'], data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        access_token = create_access_token(identity=str(user['_id']))
        
        user_info = {
            'id': str(user['_id']),
            'email': user['email'],
            'user_type': user['user_type'],
            'data_source': user.get('data_source', 'csv')  # YENİ
        }
        
        if user['user_type'] == 'individual':
            user_info['profile'] = user.get('individual_profile', {})
        else:
            profile = user.get('company_profile', {})
            if 'logo_data' in profile:
                logo_base64 = base64.b64encode(profile['logo_data']).decode('utf-8')
                profile['logo_base64'] = f"data:{profile.get('logo_mimetype', 'image/png')};base64,{logo_base64}"
                del profile['logo_data']
            user_info['profile'] = profile
        
        return jsonify({
            'access_token': access_token,
            'user': user_info
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Mevcut kullanıcı bilgileri"""
    try:
        user_id = get_jwt_identity()
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user_info = {
            'id': str(user['_id']),
            'email': user['email'],
            'user_type': user['user_type'],
            'data_source': user.get('data_source', 'csv')  # YENİ
        }
        
        if user['user_type'] == 'individual':
            user_info['profile'] = user.get('individual_profile', {})
        else:
            profile = user.get('company_profile', {})
            if 'logo_data' in profile:
                logo_base64 = base64.b64encode(profile['logo_data']).decode('utf-8')
                profile['logo_base64'] = f"data:{profile.get('logo_mimetype', 'image/png')};base64,{logo_base64}"
                del profile['logo_data']
            user_info['profile'] = profile
        
        return jsonify(user_info), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============== PROFILE ENDPOINTS ==============

@app.route('/api/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Profil güncelleme - Data Source değişimi ile"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        update_data = {}
        
        # Data source güncelleme
        if 'data_source' in data:
            update_data['data_source'] = data['data_source']
            
            # Eğer Clockify'a geçiş yapılıyorsa ve API key varsa
            if data['data_source'] == 'clockify' and data.get('clockify_api_key'):
                # Boş string veya maskelenmiş değer değilse şifrele
                api_key = data['clockify_api_key']
                if api_key and not '*' in api_key:
                    encrypted_key = encrypt_api_key(api_key)
                    update_data['clockify_api_key'] = encrypted_key
        
        # Eğer sadece API key güncellemesi yapılıyorsa
        if data.get('clockify_api_key') and not '*' in data.get('clockify_api_key', ''):
            encrypted_key = encrypt_api_key(data['clockify_api_key'])
            update_data['clockify_api_key'] = encrypted_key
        
        if user['user_type'] == 'individual':
            update_data['individual_profile.full_name'] = data['full_name']
            update_data['individual_profile.phone'] = data.get('phone', '')
        else:
            update_data['company_profile.company_name'] = data['company_name']
            update_data['company_profile.contact_person'] = data.get('contact_person', '')
            update_data['company_profile.phone'] = data.get('phone', '')
            update_data['company_profile.address'] = data.get('address', '')
            
            if 'logo_base64' in data and data['logo_base64']:
                logo_data = base64.b64decode(data['logo_base64'].split(',')[1])
                update_data['company_profile.logo_data'] = logo_data
                update_data['company_profile.logo_mimetype'] = data.get('logo_mimetype', 'image/png')
        
        mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_data}
        )
        
        return jsonify({'message': 'Profile updated successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============== CSV PROCESSING ENDPOINTS ==============

@app.route('/api/csv/preview', methods=['POST'])
@jwt_required()
def preview_csv():
    """CSV önizleme"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        df = pd.read_csv(file)
        
        columns = df.columns.tolist()
        sample_data = df.head(10).to_dict('records')
        
        unique_values = {}
        for col in ['Project', 'Client', 'User']:
            if col in df.columns:
                unique_values[col] = df[col].dropna().unique().tolist()
        
        return jsonify({
            'columns': columns,
            'sample_data': sample_data,
            'unique_values': unique_values,
            'total_rows': len(df)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/csv/convert', methods=['POST'])
@jwt_required()
def convert_csv():
    """CSV'yi Excel'e dönüştür"""
    try:
        user_id = get_jwt_identity()
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        df = pd.read_csv(file)
        
        # Zorunlu kolonları kontrol et
        required_columns = ["Project", "Client", "User", "Start Date", "Duration (h)"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({'error': f'Missing columns: {", ".join(missing_columns)}'}), 400
        
        # Eksik kolonları ekle
        if "Billable" not in df.columns:
            df["Billable"] = "No"
        if "Description" not in df.columns:
            df["Description"] = ""
        
        df["Duration (h)"].fillna("00:00:00", inplace=True)
        df["Billable"].fillna("No", inplace=True)
        
        # Filtreleri al
        selected_projects = request.form.getlist('projects[]')
        selected_clients = request.form.getlist('clients[]')
        selected_users = request.form.getlist('users[]')
        format_choice = request.form.get('format', 'decimal')
        
        # Filtreleri uygula
        if selected_projects and 'all' not in [p.lower() for p in selected_projects]:
            df = df[df["Project"].isin(selected_projects)]
        if selected_clients and 'all' not in [c.lower() for c in selected_clients]:
            df = df[df["Client"].isin(selected_clients)]
        if selected_users and 'all' not in [u.lower() for u in selected_users]:
            df = df[df["User"].isin(selected_users)]
        
        if df.empty:
            return jsonify({'error': 'No data matches filters'}), 400
        
        # Rapor bilgileri
        overall_projects = ", ".join(df["Project"].dropna().unique())
        overall_customers = ", ".join(df["Client"].dropna().unique())
        
        # Logo ve şirket bilgilerini hazırla
        logo_data = None
        company_info = None
        
        if user['user_type'] == 'company':
            profile = user.get('company_profile', {})
            if 'logo_data' in profile:
                logo_data = {
                    'data': profile['logo_data'],
                    'mimetype': profile.get('logo_mimetype', 'image/png')
                }
            company_info = {
                'company_name': profile.get('company_name', ''),
                'contact_person': profile.get('contact_person', ''),
                'phone': profile.get('phone', ''),
                'address': profile.get('address', '')
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
        
        # Excel oluştur
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = generate_excel_report(df, format_choice, report_period, 
                                      overall_projects, overall_customers, logo_data, company_info)
        filename = f"Report_{timestamp}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        app.logger.error(f"Error in convert: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clockify/workspaces', methods=['GET'])
@jwt_required()
def get_clockify_workspaces():
    """Clockify workspace'lerini getir"""
    try:
        user_id = get_jwt_identity()
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        
        # API key'i header'dan veya database'den al
        api_key = request.headers.get('X-Clockify-Api-Key')
        
        if not api_key or api_key == '':
            # Database'den al ve decrypt et
            encrypted_key = user.get('clockify_api_key', '')
            api_key = decrypt_api_key(encrypted_key) if encrypted_key else None
        
        if not api_key:
            return jsonify({'error': 'Clockify API key required'}), 400
        
        headers = {'X-Api-Key': api_key}
        response = requests.get('https://api.clockify.me/api/v1/workspaces', headers=headers, timeout=10)
        
        if response.status_code != 200:
            return jsonify({'error': 'Invalid Clockify API key'}), 401
        
        workspaces = response.json()
        return jsonify(workspaces), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clockify/projects', methods=['GET'])
@jwt_required()
def get_clockify_projects():
    """Clockify projelerini getir"""
    try:
        user_id = get_jwt_identity()
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        
        workspace_id = request.args.get('workspace_id')
        
        # API key'i header'dan veya database'den al
        api_key = request.headers.get('X-Clockify-Api-Key')
        
        if not api_key or api_key == '':
            encrypted_key = user.get('clockify_api_key', '')
            api_key = decrypt_api_key(encrypted_key) if encrypted_key else None
        
        if not api_key or not workspace_id:
            return jsonify({'error': 'API key and workspace_id required'}), 400
        
        headers = {'X-Api-Key': api_key}
        response = requests.get(
            f'https://api.clockify.me/api/v1/workspaces/{workspace_id}/projects',
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch projects'}), 400
        
        return jsonify(response.json()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clockify/time-entries', methods=['POST'])
@jwt_required()
def get_clockify_time_entries():
    """Clockify time entries'leri getir ve Excel'e dönüştür"""
    try:
        user_id = get_jwt_identity()
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        
        data = request.get_json()
        workspace_id = data.get('workspace_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        project_ids = data.get('project_ids', [])
        
        # API key'i al ve decrypt et
        api_key = data.get('api_key')
        if not api_key:
            encrypted_key = user.get('clockify_api_key', '')
            api_key = decrypt_api_key(encrypted_key) if encrypted_key else None
        
        if not all([api_key, workspace_id, start_date, end_date]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        headers = {
            'X-Api-Key': api_key,
            'Content-Type': 'application/json'
        }
        
        # Kullanıcı doğrulama
        try:
            user_response = requests.get(
                'https://api.clockify.me/api/v1/user',
                headers=headers,
                timeout=10
            )
            
            if user_response.status_code != 200:
                return jsonify({'error': 'Invalid Clockify API key'}), 400
                
            clockify_user = user_response.json()
        except Exception as e:
            app.logger.error(f"Auth error: {str(e)}")
            return jsonify({'error': 'Failed to authenticate with Clockify'}), 400
        
        # Time entries al
        try:
            report_url = f'https://reports.api.clockify.me/v1/workspaces/{workspace_id}/reports/detailed'
            
            report_payload = {
                "dateRangeStart": start_date,
                "dateRangeEnd": end_date,
                "detailedFilter": {
                    "page": 1,
                    "pageSize": 1000
                }
            }
            
            if project_ids and len(project_ids) > 0:
                report_payload["detailedFilter"]["projects"] = {
                    "ids": project_ids,
                    "contains": "CONTAINS"
                }
            
            report_response = requests.post(
                report_url,
                headers=headers,
                json=report_payload,
                timeout=30
            )
            
            if report_response.status_code != 200:
                app.logger.error(f"API Error: {report_response.text}")
                return jsonify({'error': f'Clockify API error: {report_response.text}'}), 400
            
            report_data = report_response.json()
            time_entries = report_data.get('timeentries', [])
            
            if not time_entries:
                return jsonify({'error': 'No time entries found'}), 400
            
        except Exception as e:
            app.logger.error(f"Fetch error: {str(e)}\n{traceback.format_exc()}")
            return jsonify({'error': f'Failed to fetch time entries: {str(e)}'}), 400
        
        # CSV formatına dönüştür
        csv_data = []
        for entry in time_entries:
            try:
                project_name = entry.get('projectName', 'No Project') or 'No Project'
                client_name = entry.get('clientName', 'No Client') or 'No Client'
                user_name = entry.get('userName', 'Unknown')
                description = entry.get('description', '')
                
                time_interval = entry.get('timeInterval', {})
                start_str = time_interval.get('start')
                end_str = time_interval.get('end')
                duration_seconds = time_interval.get('duration', 0)
                
                if not start_str:
                    continue
                
                start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                
                if end_str:
                    end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                else:
                    end_time = start_time + timedelta(seconds=duration_seconds)
                
                total_seconds = duration_seconds if duration_seconds > 0 else (end_time - start_time).total_seconds()
                
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                seconds = int(total_seconds % 60)
                
                csv_data.append({
                    'Project': project_name,
                    'Client': client_name,
                    'User': user_name,
                    'Description': description,
                    'Start Date': start_time.strftime('%d/%m/%Y'),
                    'Start Time': start_time.strftime('%H:%M:%S'),
                    'End Time': end_time.strftime('%H:%M:%S'),
                    'Duration (h)': f"{hours:02d}:{minutes:02d}:{seconds:02d}",
                    'Billable': 'Yes' if entry.get('billable', False) else 'No'
                })
            except Exception as e:
                app.logger.warning(f"Error processing entry: {str(e)}")
                continue
        
        if not csv_data:
            return jsonify({'error': 'No valid time entries found'}), 400
        
        df = pd.DataFrame(csv_data)
        
        overall_projects = ", ".join(df["Project"].dropna().unique())
        overall_customers = ", ".join(df["Client"].dropna().unique())
        
        logo_data = None
        company_info = None
        
        if user and user.get('user_type') == 'company':
            profile = user.get('company_profile', {})
            if 'logo_data' in profile:
                logo_data = {
                    'data': profile['logo_data'],
                    'mimetype': profile.get('logo_mimetype', 'image/png')
                }
            company_info = {
                'company_name': profile.get('company_name', ''),
                'contact_person': profile.get('contact_person', ''),
                'phone': profile.get('phone', ''),
                'address': profile.get('address', '')
            }
        
        df['ParsedDate'] = pd.to_datetime(df['Start Date'], format='%d/%m/%Y', errors='coerce')
        
        if not df['ParsedDate'].dropna().empty:
            min_date = df['ParsedDate'].min()
            max_date = df['ParsedDate'].max()
            if min_date.month == max_date.month and min_date.year == max_date.year:
                report_period = min_date.strftime("%B %Y")
            else:
                report_period = f"{min_date.strftime('%B %Y')} - {max_date.strftime('%B %Y')}"
        else:
            report_period = "All Data"
        
        format_choice = data.get('format', 'decimal')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = generate_excel_report(df, format_choice, report_period, 
                                      overall_projects, overall_customers, logo_data, company_info)
        filename = f"Clockify_Report_{timestamp}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        app.logger.error(f"Error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clockify/save-api-key', methods=['POST'])
@jwt_required()
def save_clockify_api_key():
    """Clockify API key'i kaydet - Şifreli"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        encrypted_key = encrypt_api_key(data['api_key'])
        
        mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'clockify_api_key': encrypted_key}}
        )
        
        return jsonify({'message': 'API key saved successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clockify/get-api-key', methods=['GET'])
@jwt_required()
def get_clockify_api_key():
    """Kayıtlı Clockify API key'i getir - Maskelenmiş"""
    try:
        user_id = get_jwt_identity()
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        
        encrypted_key = user.get('clockify_api_key', '')
        
        if encrypted_key:
            # API key var ama güvenlik için maskelenmiş göster
            decrypted_key = decrypt_api_key(encrypted_key)
            if decrypted_key and len(decrypted_key) > 8:
                # İlk 4 ve son 4 karakteri göster, ortası yıldız
                masked_key = decrypted_key[:4] + '*' * (len(decrypted_key) - 8) + decrypted_key[-4:]
                return jsonify({
                    'api_key': masked_key,
                    'has_key': True
                }), 200
            
        return jsonify({
            'api_key': '',
            'has_key': False
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============== HEALTH CHECK ==============

@app.route('/api/health', methods=['GET'])
def health_check():
    """API sağlık kontrolü"""
    try:
        mongo.db.command('ping')
        return jsonify({
            'status': 'healthy',
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/')
def index():
    """Root endpoint"""
    return jsonify({
        'message': 'TimeTracker API',
        'version': '1.0.0',
        'endpoints': {
            'auth': '/api/auth/*',
            'profile': '/api/profile',
            'csv': '/api/csv/*',
            'health': '/api/health'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)