# TimeTracker - CSV to Excel Report Converter

Profesyonel zaman takibi raporları oluşturun. Clockify CSV dosyalarınızı özelleştirilebilir Excel raporlarına dönüştürün.

## 🎯 Özellikler

- **Kullanıcı Yönetimi**: Bireysel ve şirket hesapları
- **Çoklu Rapor Şemaları**: 4 farklı rapor formatı
- **Canlı Önizleme**: Raporu oluşturmadan önce görün
- **Gelişmiş Filtreleme**: Proje, müşteri, kullanıcı bazlı filtreleme
- **Dinamik Kolon Seçimi**: İstediğiniz kolonları seçin
- **Şirket Logosu**: MongoDB'de güvenli logo saklama
- **MongoDB Atlas**: Bulut tabanlı NoSQL veritabanı

## 📋 Gereksinimler

- Python 3.11+
- MongoDB Atlas hesabı (ücretsiz)
- pip (Python paket yöneticisi)

## 🚀 Kurulum

### 1. Projeyi Klonlayın

```bash
git clone <repo-url>
cd timetracker
```

### 2. Sanal Ortam Oluşturun

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate  # Windows
```

### 3. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

### 4. MongoDB Atlas Kurulumu

1. [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) hesabı oluşturun (ücretsiz)
2. Cluster oluşturun
3. Database oluşturun: `Csv`
4. Collection oluşturun: `users` (otomatik oluşur)
5. Connection string'i kopyalayın

### 5. Çevre Değişkenlerini Ayarlayın

`.env` dosyasını düzenleyin:

```env
SECRET_KEY=your-very-secret-key-here
MONGO_URI=
```

**MONGO_URI Açıklaması:**
```
mongodb+srv://[USERNAME]:[PASSWORD]@[CLUSTER]/[DATABASE]?retryWrites=true&w=majority

Username: 
Password: 
Cluster: cluster0.duwvajs.mongodb.net
Database: Csv
Collection: users (otomatik oluşur)
```

### 6. Uygulamayı Çalıştırın

```bash
python app.py
```

Tarayıcınızda `http://localhost:5000` adresini açın.

### 7. Veritabanı Test

```bash
# Tarayıcıda test endpoint'i ziyaret edin
http://localhost:5000/test-db

# Başarılı yanıt:
{
  "status": "success",
  "message": "MongoDB connected successfully!",
  "database": "Csv",
  "collection": "users",
  "user_count": 0
}
```

## 📦 Render'a Deploy

### 1. GitHub'a Push Yapın

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo>
git push -u origin main
```

### 2. Render'da Yeni Servis Oluşturun

1. [Render Dashboard](https://dashboard.render.com)'a gidin
2. "New +" → "Web Service" seçin
3. GitHub repository'nizi bağlayın
4. Ayarlar:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

### 3. Environment Variables Ekleyin

Web Service ayarlarından:

```
SECRET_KEY = [güçlü random key]
MONGO_URI = 
FLASK_ENV = production
```

### 4. Deploy Edin

"Manual Deploy" → "Deploy latest commit"

## 🗄️ MongoDB Yapısı

### Database: Csv
### Collection: users

**User Document Schema:**
```json
{
  "_id": ObjectId("..."),
  "email": "user@example.com",
  "password_hash": "hashed_password",
  "user_type": "individual" | "company",
  "created_at": ISODate("..."),
  
  // Individual Profile
  "individual_profile": {
    "full_name": "John Doe",
    "phone": "+90 555 123 4567"
  },
  
  // Company Profile
  "company_profile": {
    "company_name": "Tech Corp",
    "contact_person": "Jane Doe",
    "phone": "+90 555 123 4567",
    "address": "Istanbul, Turkey",
    "logo_data": Binary("..."),  // Logo binary data
    "logo_mimetype": "image/png" // MIME type
  }
}
```

### Indexes (Otomatik oluşur)
```javascript
db.users.createIndex({ "email": 1 }, { unique: true })
```

## 🎨 Rapor Şemaları

### Classic Report
Geleneksel zaman çizelgesi formatı, günlük dağılım ile.

### Minimalist Report
Sadece totallere odaklanan temiz ve basit format.

### Detailed Report
Tüm bilgileri içeren kapsamlı rapor.

### Project-Focused Report
Önce projelere göre organize edilmiş rapor.

## 📁 Proje Yapısı

```
timetracker/
├── app.py                 # Ana uygulama (MongoDB entegrasyonlu)
├── requirements.txt       # Python bağımlılıkları
├── .env                   # Çevre değişkenleri
├── render.yaml           # Render yapılandırması
├── static/
│   ├── auth.css          # Kimlik doğrulama stilleri
│   ├── dashboard.css     # Dashboard stilleri
│   ├── profile.css       # Profil stilleri
│   └── dashboard.js      # Dashboard JavaScript
├── templates/
│   ├── login.html        # Giriş sayfası
│   ├── register.html     # Kayıt sayfası
│   ├── dashboard.html    # Ana panel
│   ├── profile.html      # Profil sayfası
│   ├── 404.html          # Hata sayfası
│   ├── 500.html          # Sunucu hatası
│   └── theme/
│       ├── header.html   # Üst menü
│       └── footer.html   # Alt bilgi
└── uploads/              # Geçici dosyalar
```

## 💡 Kullanım

1. **Kayıt Olun**: Bireysel veya şirket hesabı oluşturun
2. **Logo Yükleyin** (Opsiyonel): Şirket hesapları logo yükleyebilir
3. **CSV Yükleyin**: Clockify'dan indirdiğiniz CSV dosyasını yükleyin
4. **Şema Seçin**: 4 farklı rapor formatından birini seçin
5. **Filtrele**: İstediğiniz verileri filtreleyin
6. **İndir**: Excel raporunuzu indirin (logolu!)

## 🖼️ Logo Sistemi

### MongoDB'de Logo Saklama
Logolar MongoDB'de binary (Binary) olarak saklanır:

**Avantajlar:**
- ✅ MongoDB Atlas bulut depolaması
- ✅ Deployment sorunları yok
- ✅ Otomatik yedekleme
- ✅ Güvenli ve ölçeklenebilir
- ✅ Base64 encoding ile kolay gösterim

**Logo Formatları:**
- PNG, JPG, JPEG, GIF
- Maksimum boyut: 2MB
- Binary olarak MongoDB'de saklanır
- Base64 ile HTML'de gösterilir

### MongoDB Document Örneği

```javascript
{
  "company_profile": {
    "company_name": "Tech Corp",
    "logo_data": BinData(0, "iVBORw0KGgoAAAANS..."), // Binary data
    "logo_mimetype": "image/png"
  }
}
```

## 🔒 Güvenlik

- CSRF koruması aktif
- Şifreler hash'lenerek saklanır (werkzeug)
- MongoDB injection koruması (PyMongo)
- Dosya yükleme güvenliği (tip ve boyut kontrolü)
- Session yönetimi (Flask-Login)
- MongoDB Atlas'ta encrypted storage

## 🛠️ MongoDB İşlemleri

### Kullanıcı Ekleme
```python
mongo.db.users.insert_one({
    'email': 'user@example.com',
    'password_hash': generate_password_hash('password'),
    'user_type': 'company',
    'company_profile': {
        'company_name': 'Tech Corp',
        'logo_data': binary_data,
        'logo_mimetype': 'image/png'
    }
})
```

### Kullanıcı Bulma
```python
user = mongo.db.users.find_one({'email': 'user@example.com'})
```

### Profil Güncelleme
```python
mongo.db.users.update_one(
    {'_id': ObjectId(user_id)},
    {'$set': {
        'company_profile.company_name': 'New Name',
        'company_profile.logo_data': new_logo_data
    }}
)
```

### Logo Silme
```python
mongo.db.users.update_one(
    {'_id': ObjectId(user_id)},
    {'$unset': {
        'company_profile.logo_data': '',
        'company_profile.logo_mimetype': ''
    }}
)
```

## 🐛 Sorun Giderme

### MongoDB Bağlantı Hatası
```bash
# MONGO_URI formatını kontrol et
mongodb+srv://USERNAME:PASSWORD@CLUSTER/DATABASE?retryWrites=true&w=majority

# IP whitelist kontrolü (MongoDB Atlas)
# 0.0.0.0/0 (tüm IP'ler) veya Render IP'si ekle
```

### Logo Görünmüyor
- Dosya boyutu 2MB'dan küçük mü?
- Dosya formatı PNG/JPG/GIF mi?
- MongoDB'de `logo_data` ve `logo_mimetype` var mı?

### Test Endpoint
```bash
# MongoDB bağlantısını test et
curl http://localhost:5000/test-db

# Veya tarayıcıda:
http://localhost:5000/test-db
```

## 📊 MongoDB Atlas Ayarları

### Network Access
```
IP Whitelist: 0.0.0.0/0 (tüm IP'ler)
# veya
Render IP adresleri ekle
```

### Database User
```
Username: 
Password: 
Role: readWrite (Csv database)
```

### Connection String
```

```

## 🎯 PostgreSQL vs MongoDB

| Özellik | PostgreSQL | MongoDB |
|---------|------------|---------|
| Tip | İlişkisel (SQL) | Doküman (NoSQL) |
| Şema | Sabit | Esnek |
| Logo Saklama | LargeBinary | Binary |
| Bulut | Render PostgreSQL | MongoDB Atlas |
| Ölçeklenebilirlik | İyi | Mükemmel |
| Kurulum | Kompleks | Basit |

**MongoDB Avantajları:**
- ✅ Kolay kurulum (Atlas ücretsiz)
- ✅ Esnek şema (kolay değişiklik)
- ✅ Bulut desteği mükemmel
- ✅ JSON benzeri dokümanlar
- ✅ Horizontal scaling

## 📞 Destek

Sorularınız için issue açabilirsiniz.

## 📄 Lisans

MIT License

---

Made with ❤️ for better time tracking

**Önemli Not:** Artık MongoDB kullanıyoruz! PostgreSQL gereksinimleri kaldırıldı.