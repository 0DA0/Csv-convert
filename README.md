# TimeTracker - CSV to Excel Report Converter

Profesyonel zaman takibi raporları oluşturun. Clockify CSV dosyalarınızı özelleştirilebilir Excel raporlarına dönüştürün.

## 🎯 Özellikler

- **Kullanıcı Yönetimi**: Bireysel ve şirket hesapları
- **Çoklu Rapor Şemaları**: 4 farklı rapor formatı
- **Canlı Önizleme**: Raporu oluşturmadan önce görün
- **Gelişmiş Filtreleme**: Proje, müşteri, kullanıcı bazlı filtreleme
- **Dinamik Kolon Seçimi**: İstediğiniz kolonları seçin
- **Şirket Logosu**: Veritabanında güvenli logo saklama
- **PostgreSQL Veritabanı**: Güvenli veri saklama

## 📋 Gereksinimler

- Python 3.11+
- PostgreSQL 12+
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

### 4. Çevre Değişkenlerini Ayarlayın

`.env` dosyasını düzenleyin:

```env
SECRET_KEY=your-very-secret-key-here
DATABASE_URL=postgresql://username:password@localhost:5432/timetracker
```

### 5. Veritabanını Oluşturun

```bash
# PostgreSQL'e bağlanın
psql -U postgres

# Veritabanını oluşturun
CREATE DATABASE timetracker;
\q

# Tabloları oluşturun
flask init-db
```

### 6. Uygulamayı Çalıştırın

```bash
python app.py
```

Tarayıcınızda `http://localhost:5000` adresini açın.

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

### 3. PostgreSQL Veritabanı Ekleyin

1. "New +" → "PostgreSQL" seçin
2. Database adı: `timetracker-db`
3. Oluşturulduktan sonra **Internal Database URL**'yi kopyalayın

### 4. Environment Variables Ekleyin

Web Service ayarlarından:

- `DATABASE_URL`: Internal Database URL'nizi yapıştırın
- `SECRET_KEY`: Güçlü bir random key girin (örn: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `FLASK_ENV`: `production`

### 5. Deploy Edin

"Manual Deploy" → "Deploy latest commit"

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
├── app.py                 # Ana uygulama
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

### Veritabanında Logo Saklama
Logolar artık dosya sistemi yerine PostgreSQL veritabanında binary (LargeBinary) olarak saklanır:

**Avantajlar:**
- ✅ Deployment sorunları yok (Render ephemeral filesystem)
- ✅ Yedekleme ve migration kolay
- ✅ Güvenli ve merkezi saklama
- ✅ Otomatik encoding/decoding

**Logo Formatları:**
- PNG, JPG, JPEG, GIF
- Maksimum boyut: 2MB
- Base64 encoding ile HTML'de görüntüleme
- Excel'de binary olarak ekleme

### Teknik Detaylar

```python
# Logo kaydetme
profile.set_logo(file)  # Otomatik binary'ye çevirir

# Logo gösterme (HTML)
profile.get_logo_base64()  # data:image/png;base64,... döner

# Logo kontrolü
profile.has_logo()  # True/False
```

## 🔒 Güvenlik

- CSRF koruması aktif
- Şifreler hash'lenerek saklanır (werkzeug)
- SQL injection koruması (SQLAlchemy ORM)
- Dosya yükleme güvenliği (tip ve boyut kontrolü)
- Session yönetimi (Flask-Login)
- Logo verileri encrypted storage

## 🛠️ Geliştirme

### Yeni Şema Eklemek

`app.py` dosyasındaki `REPORT_SCHEMAS` dict'ine yeni şema ekleyin:

```python
REPORT_SCHEMAS['my_schema'] = {
    'name': 'My Custom Schema',
    'description': 'Description here',
    'columns': ['Column1', 'Column2'],
    'show_details': True
}
```

### Veritabanı Schema Değişikliği

```bash
# Değişiklik yaptıktan sonra
flask init-db  # Sadece ilk kurulumda

# Veya PostgreSQL'de manuel
psql -U postgres timetracker
DROP TABLE IF EXISTS company_profiles CASCADE;
DROP TABLE IF EXISTS individual_profiles CASCADE;
DROP TABLE IF EXISTS users CASCADE;
\q
flask init-db
```

### Logo Test Etme

```python
# Python shell'de test
from app import app, db
from app import CompanyProfile

with app.app_context():
    profile = CompanyProfile.query.first()
    if profile and profile.has_logo():
        print(f"Logo MIME type: {profile.logo_mimetype}")
        print(f"Logo size: {len(profile.logo_data)} bytes")
        print(f"Base64 preview: {profile.get_logo_base64()[:100]}...")
```

## 🐛 Sorun Giderme

### Logo Görünmüyor
- Dosya boyutu 2MB'dan küçük mü?
- Dosya formatı PNG/JPG/GIF mi?
- Veritabanında `logo_data` ve `logo_mimetype` dolu mu?

### PostgreSQL Bağlantı Hatası
```bash
# DATABASE_URL formatını kontrol et
postgresql://username:password@host:port/database

# Render'da otomatik sağlanır, sadece kopyala-yapıştır
```

### Excel'de Logo Görünmüyor
- Logo boyutu çok büyük olabilir
- `xlsxwriter` versiyonu güncel mi?
- Log'larda hata var mı kontrol et

## 📞 Destek

Sorularınız için issue açabilirsiniz.

## 📄 Lisans

MIT License

---

Made with ❤️ for better time tracking

**Önemli Not:** Logolar artık dosya sisteminde değil, veritabanında saklanır. `static/logos/` klasörüne gerek yok!