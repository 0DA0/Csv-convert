# MongoDB Atlas Kurulum Kılavuzu

## 🎯 Mevcut Bağlantı Bilgilerin

```
Username: ""
Password: ""
Cluster: ""
Database: Csv
Collection: users (otomatik oluşacak)
```

**Connection String:**
```

```

## ✅ Kontrol Listesi

### 1. MongoDB Atlas Ayarları

**Network Access:**
```
☐ MongoDB Atlas'a giriş yap
☐ Network Access → Add IP Address
☐ "Allow Access from Anywhere" seç (0.0.0.0/0)
☐ Confirm
```

**Database Access:**
```
☐ Database Access kontrol et
☐ Username: 
☐ Password: 
☐ Database Permissions: readWrite (Csv)
```

### 2. .env Dosyası

```bash
# .env dosyasını oluştur
touch .env

# İçeriğini düzenle
SECRET_KEY=
FLASK_ENV=
MONGO_URI=
```

### 3. Paketleri Yükle

```bash
# Sanal ortam
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Paketler
pip install -r requirements.txt
```

### 4. Test Et

```bash
# Uygulamayı çalıştır
python app.py

# Başka bir terminalde test et
curl http://localhost:5000/test-db

# Veya tarayıcıda:
# http://localhost:5000/test-db
```

**Başarılı Yanıt:**
```json
{
  "status": "success",
  "message": "MongoDB connected successfully!",
  "database": "Csv",
  "collection": "users",
  "user_count": 0
}
```

## 🔍 MongoDB Compass ile Kontrol

### Kurulum
1. [MongoDB Compass](https://www.mongodb.com/try/download/compass) indir
2. Kur ve aç

### Bağlan
```
Connection String:

```

### Kontroller
```
☐ Csv database görünüyor mu?
☐ users collection oluştu mu? (ilk kayıt sonrası)
☐ Dokümanları görebiliyor musun?
```

## 📊 MongoDB Doküman Yapısı

### Individual User
```json
{
  "_id": ObjectId("674a7e3b8f9c2d1e4a5b6c7d"),
  "email": "john@example.com",
  "password_hash": "$2b$12$...",
  "user_type": "individual",
  "created_at": ISODate("2024-12-07T10:30:00Z"),
  "individual_profile": {
    "full_name": "John Doe",
    "phone": "+90 555 123 4567"
  }
}
```

### Company User (Logo ile)
```json
{
  "_id": ObjectId("674a7e3b8f9c2d1e4a5b6c7e"),
  "email": "tech@example.com",
  "password_hash": "$2b$12$...",
  "user_type": "company",
  "created_at": ISODate("2024-12-07T10:35:00Z"),
  "company_profile": {
    "company_name": "Tech Corp",
    "contact_person": "Jane Doe",
    "phone": "+90 555 987 6543",
    "address": "Istanbul, Turkey",
    "logo_data": Binary("iVBORw0KGgoAAAANS..."),
    "logo_mimetype": "image/png"
  }
}
```

## 🚀 Çalışma Akışı

### 1. Kayıt (Register)
```python
# MongoDB'ye yeni user eklenir
mongo.db.users.insert_one({
    'email': email,
    'password_hash': hashed_password,
    'user_type': 'company',
    'company_profile': {
        'company_name': 'Tech Corp',
        'logo_data': binary_logo_data,
        'logo_mimetype': 'image/png'
    }
})
```

### 2. Giriş (Login)
```python
# Email ile user bulunur
user = mongo.db.users.find_one({'email': email})

# Şifre kontrol edilir
if check_password_hash(user['password_hash'], password):
    login_user(User(user))
```

### 3. Profil Güncelleme
```python
# Profil güncellenir
mongo.db.users.update_one(
    {'_id': ObjectId(user_id)},
    {'$set': {
        'company_profile.company_name': 'New Name',
        'company_profile.logo_data': new_logo
    }}
)
```

### 4. Logo Gösterme
```python
# MongoDB'den logo alınır
logo_data = user['company_profile']['logo_data']
logo_mimetype = user['company_profile']['logo_mimetype']

# Base64'e çevrilir
encoded = base64.b64encode(logo_data).decode('utf-8')
data_url = f"data:{logo_mimetype};base64,{encoded}"

# HTML'de gösterilir
<img src="{{ data_url }}" alt="Logo">
```

## 🔧 Önemli MongoDB Komutları

### Python Shell'de Test
```python
python

>>> from app import app, mongo
>>> with app.app_context():
...     # Test connection
...     mongo.db.command('ping')
...     
...     # User count
...     count = mongo.db.users.count_documents({})
...     print(f"Total users: {count}")
...     
...     # Tüm userları listele
...     users = mongo.db.users.find()
...     for user in users:
...         print(user['email'])
```

### MongoDB Shell Komutları
```javascript
// MongoDB Compass veya mongosh

// Database seç
use Csv

// Collection'ları listele
show collections

// Tüm userları listele
db.users.find().pretty()

// Email ile ara
db.users.find({ "email": "user@example.com" })

// Company userları listele
db.users.find({ "user_type": "company" })

// Logo olan userlar
db.users.find({ "company_profile.logo_data": { $exists: true } })

// User sayısı
db.users.countDocuments()

// User sil
db.users.deleteOne({ "email": "user@example.com" })

// Tüm userları sil (DİKKAT!)
db.users.deleteMany({})
```

## 🛡️ Güvenlik Best Practices

### IP Whitelist
```
Geliştirme: 0.0.0.0/0 (tüm IP'ler)
Production: Sadece Render IP'leri
```

### Password Güvenliği
```python
# ASLA plain text şifre saklama!
❌ user['password'] = 'password123'

# Her zaman hash kullan
✅ user['password_hash'] = generate_password_hash('password123')
```

### Connection String
```bash
# .env dosyasında sakla
✅ MONGO_URI=mongodb+srv://...

# Kod içinde hardcode etme!
❌ mongo_uri = "mongodb+srv://Admin:pass@..."

# .gitignore'a ekle
echo ".env" >> .gitignore
```

## 🐛 Yaygın Hatalar ve Çözümleri

### 1. Connection Timeout
```
Error: connection timeout

Çözüm:
☐ MongoDB Atlas Network Access kontrol et
☐ IP whitelist'e 0.0.0.0/0 ekle
☐ Firewall kontrolü yap
```

### 2. Authentication Failed
```
Error: Authentication failed

Çözüm:
☐ Username/password doğru mu?
☐ Database adı doğru mu? (Csv)
☐ User permissions kontrol et (readWrite)
```

### 3. Database Not Found
```
Error: Database Csv not found

Çözüm:
☐ İlk doküman eklenince otomatik oluşur
☐ İlk kayıt yap, database oluşacak
```

### 4. dnspython Hatası
```
Error: dnspython must be installed

Çözüm:
pip install dnspython
```

## 📈 Performans İpuçları

### Index Oluşturma
```python
# Email için unique index (otomatik olmalı)
mongo.db.users.create_index('email', unique=True)

# User type için index
mongo.db.users.create_index('user_type')

# Created_at için index (sorting için)
mongo.db.users.create_index('created_at')
```

### Query Optimizasyonu
```python
# Sadece gerekli alanları çek
user = mongo.db.users.find_one(
    {'email': email},
    {'password_hash': 1, 'user_type': 1}
)

# Logo'yu sonra çek (gerekirse)
if user['user_type'] == 'company':
    logo = mongo.db.users.find_one(
        {'_id': user['_id']},
        {'company_profile.logo_data': 1}
    )
```

## 🎉 Başarılı Kurulum Kontrolü

```bash
✅ MongoDB Atlas'a bağlanıldı
✅ Network Access ayarlandı (0.0.0.0/0)
✅ .env dosyası oluşturuldu
✅ Paketler yüklendi
✅ /test-db endpoint çalışıyor
✅ Kayıt yapılabiliyor
✅ Login çalışıyor
✅ Logo yüklenebiliyor
✅ Profil güncellenebiliyor
```

Tebrikler! MongoDB entegrasyonu tamamlandı! 🎊