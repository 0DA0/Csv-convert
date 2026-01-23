from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
import pandas as pd
from io import BytesIO
import os
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
                    summary_sheet.insert_image(table_start_row, 4, "logo", {
                        'image_data': temp_logo,
                        'x_scale': 0.25, 'y_scale': 0.25,
                        'x_offset': 10, 'y_offset': 5,
                        'positioning': 1
                    })
                    for i in range(table_start_row, row):
                        summary_sheet.write(i, 4, "", info_value_format)
                except:
                    pass
            
            row += 1
        
        # Rapor Bilgileri
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
            
            summary_sheet.merge_range(row, 0, row, 3, sanitize_excel_cell(f"User: {user}"), user_header_format)
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
                
                desc_length = len(combined_description)
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
        
        summary_sheet.set_column(0, 0, 16)
        summary_sheet.set_column(1, 1, 60)
        summary_sheet.set_column(2, 2, 10)
        summary_sheet.set_column(3, 3, 12)
        summary_sheet.set_column(4, 4, 12)
        
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
                    
                    # Satır yüksekliği
                    desc_length = len(desc_text)
                    lines_needed = max(1, (desc_length // 50) + 1)
                    row_height = 18 * lines_needed
                    detail_sheet.set_row(detail_row, row_height)
                    
                    detail_row += 1
                
                detail_row += 1
            
            detail_row += 1
        
        # Kolon genişlikleri
        detail_sheet.set_column(0, 0, 12)  # Start Time
        detail_sheet.set_column(1, 1, 12)  # End Time
        detail_sheet.set_column(2, 2, 12)  # Duration
        detail_sheet.set_column(3, 3, 50)  # Description
        detail_sheet.set_column(4, 4, 10)  # Billable
        detail_sheet.set_column(5, 5, 12)  # Logo column
    
    output.seek(0)
    return output

# ============== AUTH ENDPOINTS ==============

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Kullanıcı kaydı"""
    try:
        data = request.get_json()
        
        if mongo.db.users.find_one({'email': data['email']}):
            return jsonify({'error': 'Email already registered'}), 400
        
        user_doc = {
            'email': data['email'],
            'password_hash': generate_password_hash(data['password']),
            'user_type': data['user_type'],
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
            'user_type': user['user_type']
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
            'user_type': user['user_type']
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
    """Profil güncelleme"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        update_data = {}
        
        if user['user_type'] == 'individual':
            update_data = {
                'individual_profile.full_name': data['full_name'],
                'individual_profile.phone': data.get('phone', '')
            }
        else:
            update_data = {
                'company_profile.company_name': data['company_name'],
                'company_profile.contact_person': data.get('contact_person', ''),
                'company_profile.phone': data.get('phone', ''),
                'company_profile.address': data.get('address', '')
            }
            
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
        api_key = request.headers.get('X-Clockify-Api-Key')
        if not api_key:
            return jsonify({'error': 'Clockify API key required'}), 400
        
        headers = {'X-Api-Key': api_key}
        response = requests.get('https://api.clockify.me/api/v1/workspaces', headers=headers)
        
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
        api_key = request.headers.get('X-Clockify-Api-Key')
        workspace_id = request.args.get('workspace_id')
        
        if not api_key or not workspace_id:
            return jsonify({'error': 'API key and workspace_id required'}), 400
        
        headers = {'X-Api-Key': api_key}
        response = requests.get(
            f'https://api.clockify.me/api/v1/workspaces/{workspace_id}/projects',
            headers=headers
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch projects'}), 400
        
        return jsonify(response.json()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clockify/time-entries', methods=['POST'])
@jwt_required()
def get_clockify_time_entries():
    """Clockify time entries'leri getir ve CSV formatına dönüştür"""
    try:
        user_id = get_jwt_identity()
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        
        data = request.get_json()

        app.logger.info(f"Received data: {data}")

        api_key = data.get('api_key')
        workspace_id = data.get('workspace_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        project_ids = data.get('project_ids', [])
        
        if not all([api_key, workspace_id, start_date, end_date]):
            missing = []
            if not api_key: missing.append('api_key')
            if not workspace_id: missing.append('workspace_id')
            if not start_date: missing.append('start_date')
            if not end_date: missing.append('end_date')
            return jsonify({'error': f'Missing required parameters: {", ".join(missing)}'}), 400
        
        headers = {'X-Api-Key': api_key, 'Content-Type': 'application/json'}
        
        # Clockify'dan time entries al
        url = f'https://api.clockify.me/api/v1/workspaces/{workspace_id}/user/me'
        user_response = requests.get(url, headers=headers)
        
        if user_response.status_code != 200:
            return jsonify({'error': 'Failed to get user info'}), 400
        
        clockify_user = user_response.json()
        clockify_user_id = clockify_user['id']
        
        # Time entries getir
        url = f'https://api.clockify.me/api/v1/workspaces/{workspace_id}/user/{clockify_user_id}/time-entries'
        params = {
            'start': start_date,
            'end': end_date,
            'page-size': 5000
        }
        
        entries_response = requests.get(url, headers=headers, params=params)
        
        if entries_response.status_code != 200:
            return jsonify({'error': 'Failed to fetch time entries'}), 400
        
        time_entries = entries_response.json()
        
        # Project bilgilerini çek
        projects_url = f'https://api.clockify.me/api/v1/workspaces/{workspace_id}/projects'
        projects_response = requests.get(projects_url, headers=headers)
        projects = {p['id']: p for p in projects_response.json()}
        
        # Client bilgilerini çek
        clients_url = f'https://api.clockify.me/api/v1/workspaces/{workspace_id}/clients'
        clients_response = requests.get(clients_url, headers=headers)
        clients = {c['id']: c for c in clients_response.json()}
        
        # CSV formatına dönüştür
        csv_data = []
        for entry in time_entries:
            if project_ids and entry.get('projectId') not in project_ids:
                continue
            
            project = projects.get(entry.get('projectId', ''), {})
            client = clients.get(project.get('clientId', ''), {})
            
            # Süreyi hesapla
            start_time = datetime.fromisoformat(entry['timeInterval']['start'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(entry['timeInterval']['end'].replace('Z', '+00:00')) if entry['timeInterval'].get('end') else datetime.utcnow()
            duration = end_time - start_time
            
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            seconds = int(duration.total_seconds() % 60)
            
            csv_data.append({
                'Project': project.get('name', 'Unknown'),
                'Client': client.get('name', 'Unknown'),
                'User': clockify_user.get('name', 'Unknown'),
                'Description': entry.get('description', ''),
                'Start Date': start_time.strftime('%d/%m/%Y'),
                'Start Time': start_time.strftime('%H:%M:%S'),
                'End Time': end_time.strftime('%H:%M:%S'),
                'Duration (h)': f"{hours:02d}:{minutes:02d}:{seconds:02d}",
                'Billable': 'Yes' if entry.get('billable') else 'No'
            })
        
        if not csv_data:
            return jsonify({'error': 'No time entries found for selected criteria'}), 400
        
        # DataFrame oluştur
        df = pd.DataFrame(csv_data)
        
        # Filtreleri al
        selected_projects = data.get('projects', ['all'])
        selected_clients = data.get('clients', ['all'])
        selected_users = data.get('users', ['all'])
        format_choice = data.get('format', 'decimal')
        
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
        filename = f"Clockify_Report_{timestamp}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        app.logger.error(f"Error in clockify time entries: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clockify/save-api-key', methods=['POST'])
@jwt_required()
def save_clockify_api_key():
    """Clockify API key'i kaydet"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'clockify_api_key': data['api_key']}}
        )
        
        return jsonify({'message': 'API key saved successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clockify/get-api-key', methods=['GET'])
@jwt_required()
def get_clockify_api_key():
    """Kayıtlı Clockify API key'i getir"""
    try:
        user_id = get_jwt_identity()
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        
        api_key = user.get('clockify_api_key', '')
        return jsonify({'api_key': api_key}), 200
        
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