# VarAz — Əmlak və Nəqliyyat Elanları Platforması

Bina.az və Turbo.az-ın funksionallığını birləşdirən, tam işlək **backend + verilənlər bazası**
olan elanlar saytı. Python/Flask + SQLite üzərində qurulub, orijinal marka dizaynı ilə.

## Xüsusiyyətlər

- İki elan növü: **Əmlak** (mənzil, həyət evi, ofis, torpaq, qaraj) və **Nəqliyyat** (minik, suv, moto, kommersiya)
- Qeydiyyat / giriş (parol hash-lənir, sessiya ilə autentifikasiya)
- Elan yerləşdirmə — hər növ üçün fərqli sahələr (mənzil üçün otaq/sahə/mərtəbə, avtomobil üçün marka/model/il/yürüş və s.)
- Şəkil yükləmə (bir neçə fayl, avtomatik adlandırma)
- Axtarış + filtrlər: növ, kateqoriya, şəhər, qiymət aralığı, açar söz, (əmlak üçün) əməliyyat növü, (nəqliyyat üçün) minimum il
- Sıralama: ən yeni / qiymət artan / qiymət azalan
- Sevimlilər (AJAX ilə əlavə/çıxar)
- "Elanlarım" — öz elanlarını idarə etmə və silmə
- Bənzər elanlar bloku, baxış sayğacı

## Texniki quruluş

```
varaz/
├── app.py              # Flask tətbiqi — bütün marşrutlar (routes)
├── schema.sql           # Verilənlər bazası sxemi
├── seed.py               # Bazanı yaradır və nümunə elanlarla doldurur
├── varaz.db              # SQLite bazası (artıq yaradılıb, hazır demo data ilə)
├── templates/            # Jinja2 HTML şablonları
├── static/css/style.css  # Dizayn sistemi (rənglər, tipoqrafiya, komponentlər)
├── static/js/main.js     # Sevimlilər AJAX, dinamik forma sahələri
├── static/img/           # Orijinal SVG illüstrasiyalar (elan şəkli olmadıqda)
└── static/uploads/       # İstifadəçilərin yüklədiyi şəkillər
```

**Verilənlər bazası sxemi:** `users`, `listings` (ortaq sahələr), `property_details` və
`vehicle_details` (növə görə ayrı cədvəllər, 1-ə-1 əlaqə), `listing_images`, `favorites`, `cities`.

## Quraşdırma və işə salma

Tələb olunur: Python 3.9+

```bash
cd varaz
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install flask

# Baza artıq yaradılıb (varaz.db). Sıfırdan yaratmaq/data-nı təzələmək üçün:
python3 seed.py

python3 app.py
```

Sonra brauzerdə: **http://127.0.0.1:5000**

### Demo hesab
- Telefon: `0501234567`
- Şifrə: `parol123`

(Digər demo istifadəçilər: `0552345678` və `0703456789`, eyni şifrə ilə.)

## Deploy (real sayta çevirmək üçün)

Bu, development server ilə işləyir (`app.run(debug=True)`) — bu, yalnız test üçündür.
Canlı mühitə çıxarmaq üçün:

1. `app.config["SECRET_KEY"]` üçün mühit dəyişəni ilə güclü, təsadüfi açar təyin edin
   (`VARAZ_SECRET_KEY`), `debug=False` edin.
2. Production WSGI server istifadə edin: `gunicorn -w 4 -b 0.0.0.0:8000 app:app`
3. SQLite kiçik/orta trafik üçün kifayətdir; böyüdükdə PostgreSQL-ə keçid tövsiyə olunur
   (sorğuların çoxu standart SQL-dir, keçid nisbətən asandır).
4. Şəkilləri `static/uploads` yerinə S3 / obyekt anbarına yönləndirin ki, server restart-larında itməsin.
5. Nginx və ya oxşar reverse proxy arxasında, HTTPS ilə işə salın.

## Növbəti addımlar üçün fikirlər

- Elanları redaktə etmə (hazırda yalnız yaratmaq/silmək var)
- Admin panel (moderasiya, spam elanların bağlanması)
- SMS/e-poçt təsdiqi qeydiyyatda
- Xəritə üzərində əmlak yerləşməsi
- Bildirişlər (qiymət düşəndə, yeni bənzər elan çıxanda)
