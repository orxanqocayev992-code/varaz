"""VarVar.az -- verilenler bazasini yaradir ve numune elanlarla doldurur."""
import sqlite3
import os
from werkzeug.security import generate_password_hash

import random

CITY_COORDS = {
    "Bakı": (40.4093, 49.8671),
    "Gəncə": (40.6828, 46.3606),
    "Sumqayıt": (40.5897, 49.6686),
    "Mingəçevir": (40.7699, 47.0500),
    "Naxçıvan": (39.2089, 45.4122),
    "Şəki": (41.2000, 47.1700),
    "Lənkəran": (38.7537, 48.8511),
    "Şirvan": (39.9333, 48.9333),
    "Qəbələ": (40.9800, 47.8500),
    "Quba": (41.3600, 48.5100),
    "Xaçmaz": (41.4650, 48.8000),
    "Qax": (41.4200, 46.9200),
    "Xırdalan": (40.4500, 49.7333),
}

DISTRICT_COORDS = {
    "Yasamal": (40.3800, 49.8090),
    "Nərimanov": (40.4090, 49.8850),
    "Xəzər": (40.4700, 50.1000),
    "Nəsimi": (40.3923, 49.8288),
    "Kəpəz": (40.6828, 46.3606),
}


def get_coords(city, district):
    base = DISTRICT_COORDS.get(district) or CITY_COORDS.get(city) or CITY_COORDS["Bakı"]
    rnd = random.Random(f"{city}{district}")
    jitter = lambda: (rnd.random() - 0.5) * 0.02
    return base[0] + jitter(), base[1] + jitter()


DB_PATH = os.path.join(os.path.dirname(__file__), "varaz.db")

CITIES = [
    "Bakı", "Gəncə", "Sumqayıt", "Mingəçevir", "Naxçıvan",
    "Şəki", "Lənkəran", "Şirvan", "Qəbələ", "Quba", "Xaçmaz", "Qax"
]

USERS = [
    ("Elvin Məmmədov", "0501234567", "elvin@example.com", "parol123"),
    ("Aysel Quliyeva", "0552345678", "aysel@example.com", "parol123"),
    ("Rəşad Əliyev", "0703456789", "resad@example.com", "parol123"),
    ("VarVar.az Admin", "0702773533", "azvar2026@gmail.com", "danger352943"),
]
ADMIN_USER_INDEX = 3

PROPERTY_LISTINGS = [
    dict(user=0, category="mənzil", title="8 mikrorayonda 3 otaqlı mənzil, təmirli",
         description="Günəşli, geniş balkonlu, metroya yaxın 3 otaqlı mənzil. Yeni təmir, mətbəx mebeli qalır.",
         price=185000, city="Bakı", district="Yasamal", address="8-ci mikrorayon",
         rooms=3, area_m2=98, floor=7, floors_total=16, building_type="yeni tikili",
         repair_status="təmirli", deal_type="satılır"),
    dict(user=1, category="mənzil", title="Nərimanovda kirayə 2 otaqlı mənzil",
         description="Ailəyə və ya tələbəyə uyğun, məişət texnikası ilə təchiz olunub.",
         price=650, city="Bakı", district="Nərimanov", address="H.Zərdabi pr.",
         rooms=2, area_m2=64, floor=3, floors_total=9, building_type="yeni tikili",
         repair_status="təmirli", deal_type="kirayə"),
    dict(user=2, category="həyət evi/bağ evi", title="Novxanıda 2 mərtəbəli həyət evi, bağı ilə",
         description="6 sot torpaq sahəsində, bağçalı, tam kommunikasiyalı həyət evi.",
         price=245000, city="Bakı", district="Xəzər", address="Novxanı qəsəbəsi",
         rooms=5, area_m2=210, floor=1, floors_total=2, building_type="fərdi",
         repair_status="təmirli", deal_type="satılır"),
    dict(user=0, category="ofis", title="28 May metrosu yaxınlığında ofis sahəsi",
         description="Biznes mərkəzin 5-ci mərtəbəsində, ayrıca girişli ofis otağı.",
         price=1200, city="Bakı", district="Nəsimi", address="28 May",
         rooms=4, area_m2=140, floor=5, floors_total=12, building_type="yeni tikili",
         repair_status="təmirli", deal_type="kirayə"),
    dict(user=1, category="torpaq", title="Xırdalanda 10 sot torpaq sahəsi",
         description="Kənd təsərrüfatı və ya tikinti üçün əlverişli, yol kənarında.",
         price=45000, city="Xırdalan", district="", address="Xırdalan, Bakı yolu",
         rooms=None, area_m2=1000, floor=None, floors_total=None, building_type="torpaq",
         repair_status="", deal_type="satılır"),
    dict(user=2, category="mənzil", title="Gəncədə yeni tikili 1 otaqlı mənzil",
         description="Şəhər mərkəzində, yeni tikilən binada rahat planlaşdırma.",
         price=52000, city="Gəncə", district="Kəpəz", address="Atatürk prospekti",
         rooms=1, area_m2=45, floor=4, floors_total=9, building_type="yeni tikili",
         repair_status="təmirsiz", deal_type="satılır"),
    dict(user=1, category="mənzil", title="Nəsimi rayonunda köhnə tikili 3 otaqlı mənzil",
         description="Sərfəli qiymət, əsaslı təmirə ehtiyacı var, yaxşı lokasiya.",
         price=112000, city="Bakı", district="Nəsimi", address="Ə.Əlizadə küç.",
         rooms=3, area_m2=76, floor=2, floors_total=5, building_type="köhnə tikili",
         repair_status="təmirsiz", deal_type="satılır"),
    dict(user=0, category="obyekt", title="Yasamalda ticarət obyekti, yol kənarı",
         description="Fəaliyyət göstərən market, yüksək keçidli ünvanda, uzunmüddətli kirayəçi mümkündür.",
         price=310000, city="Bakı", district="Yasamal", address="H.Cavid pr.",
         rooms=None, area_m2=180, floor=1, floors_total=1, building_type="fərdi",
         repair_status="təmirli", deal_type="satılır"),
    dict(user=1, category="mənzil", title="Sea Breeze kompleksində 2 otaqlı mənzil, dəniz mənzərəli",
         description="Sea Breeze yaşayış kompleksində, hovuz və çimərlik girişinə yaxın, tam mebelli mənzil.",
         price=192000, city="Bakı", district="Xəzər", address="Novxanı qəsəbəsi, Sea Breeze",
         rooms=2, area_m2=78, floor=9, floors_total=22, building_type="yeni tikili",
         repair_status="təmirli", deal_type="satılır", residence_slug="sea-breeze"),
    dict(user=2, category="mənzil", title="Port Baku Residence-də 3 otaqlı mənzil, buxta mənzərəli",
         description="Port Baku Residence-də, tam təmirli, panoramik pəncərəli geniş mənzil.",
         price=435000, city="Bakı", district="Nəsimi", address="Neftçilər prospekti, Port Baku",
         rooms=3, area_m2=140, floor=15, floors_total=24, building_type="yeni tikili",
         repair_status="təmirli", deal_type="satılır", residence_slug="port-baku-residence"),
]

VEHICLE_LISTINGS = [
    dict(user=0, category="minik", title="Mercedes-Benz E 200, 2019",
         description="Salon vəziyyətində, vurulmayıb, boyasız. Servis tarixçəsi mövcuddur.",
         price=58000, city="Bakı", district="", address="",
         make="Mercedes-Benz", model="E 200", year=2019, mileage_km=62000,
         engine_volume=2.0, fuel_type="benzin", transmission="avtomat",
         color="qara", body_type="sedan", condition_status="vurulmayıb"),
    dict(user=1, category="suv", title="Hyundai Tucson, 2021",
         description="Tam suraetli, arxa görüntü kamerası, yeni şinlər.",
         price=44500, city="Bakı", district="", address="",
         make="Hyundai", model="Tucson", year=2021, mileage_km=38000,
         engine_volume=2.0, fuel_type="benzin", transmission="avtomat",
         color="ağ", body_type="offroader", condition_status="vurulmayıb"),
    dict(user=2, category="minik", title="Lada (VAZ) 2107, 2010",
         description="Ehtiyat hissə kimi və ya gündəlik istifadə üçün əlverişli.",
         price=6200, city="Sumqayıt", district="", address="",
         make="Lada (VAZ)", model="2107", year=2010, mileage_km=210000,
         engine_volume=1.6, fuel_type="benzin", transmission="manual",
         color="gümüşü", body_type="sedan", condition_status="sürücülü"),
    dict(user=0, category="moto", title="Yamaha MT-07, 2022",
         description="Az yürüş, orijinal boya, heç bir problemi yoxdur.",
         price=17500, city="Bakı", district="", address="",
         make="Yamaha", model="MT-07", year=2022, mileage_km=4200,
         engine_volume=0.7, fuel_type="benzin", transmission="manual",
         color="mavi", body_type="motosiklet", condition_status="vurulmayıb"),
    dict(user=1, category="suv", title="Kia Sportage, 2023",
         description="Zavod zəmanəti davam edir, tam avadanlıqlı.",
         price=61000, city="Bakı", district="", address="",
         make="Kia", model="Sportage", year=2023, mileage_km=12000,
         engine_volume=1.6, fuel_type="benzin", transmission="avtomat",
         color="boz", body_type="offroader", condition_status="vurulmayıb"),
    dict(user=2, category="minik", title="Chevrolet Malibu, 2017",
         description="Rahat sürüş, yaxşı yanacaq sərfiyyatı, ailə avtomobili.",
         price=23800, city="Gəncə", district="", address="",
         make="Chevrolet", model="Malibu", year=2017, mileage_km=95000,
         engine_volume=1.5, fuel_type="benzin", transmission="avtomat",
         color="qırmızı", body_type="sedan", condition_status="vurulmayıb"),
    dict(user=0, category="pikap", title="Toyota Hilux, 2020",
         description="4x4, kuza örtüklü, tikinti və təsərrüfat işləri üçün ideal.",
         price=52000, city="Bakı", district="", address="",
         make="Toyota", model="Hilux", year=2020, mileage_km=71000,
         engine_volume=2.8, fuel_type="dizel", transmission="avtomat",
         color="ağ", body_type="pikap", condition_status="vurulmayıb"),
    dict(user=1, category="furqon", title="Ford Transit, 2019",
         description="Furqon kuzov, soyuducu qurğu yoxdur, biznes üçün əlverişli.",
         price=34500, city="Sumqayıt", district="", address="",
         make="Ford", model="Transit", year=2019, mileage_km=140000,
         engine_volume=2.2, fuel_type="dizel", transmission="manual",
         color="ağ", body_type="furqon", condition_status="vurulmayıb"),
    dict(user=0, category="ehtiyat hissələri", title="BMW E90 üçün ön fara dəsti (orijinal)",
         description="BMW 3 Series (E90) 2008-2011 üçün orijinal ön fara dəsti, tam işlək, sınıq yoxdur.",
         price=280, city="Bakı", district="Yasamal", address="",
         make="BMW", model="3 Series (E90)", year=None, mileage_km=None,
         engine_volume=None, fuel_type=None, transmission=None,
         color=None, body_type=None, condition_status="işlənmiş"),
    dict(user=2, category="ehtiyat hissələri", title="Mercedes-Benz üçün tormoz kolodkaları (yeni)",
         description="Bütün Mercedes-Benz C/E-Class modelləri üçün uyğun, orijinal qablaşdırmada, yeni.",
         price=95, city="Bakı", district="", address="",
         make="Mercedes-Benz", model="", year=None, mileage_km=None,
         engine_volume=None, fuel_type=None, transmission=None,
         color=None, body_type=None, condition_status="yeni"),
    dict(user=0, category="minik", title="Hyundai Elantra, 2022 — gündəlik icarə", deal_type="kirayə",
         description="Gündəlik/həftəlik icarəyə verilir, tam sığortalı, limitsiz kilometraj.",
         price=65, city="Bakı", district="", address="",
         make="Hyundai", model="Elantra", year=2022, mileage_km=28000,
         engine_volume=1.6, fuel_type="benzin", transmission="avtomat",
         color="ağ", body_type="sedan", condition_status="vurulmayıb"),
    dict(user=1, category="suv", title="Kia Sorento, 2023 — icarəyə verilir", deal_type="kirayə",
         description="Toy, ezamiyyət və gündəlik istifadə üçün icarəyə verilir, sürücü ilə də mümkündür.",
         price=95, city="Bakı", district="", address="",
         make="Kia", model="Sorento", year=2023, mileage_km=15000,
         engine_volume=2.2, fuel_type="dizel", transmission="avtomat",
         color="qara", body_type="offroader", condition_status="vurulmayıb"),
]


COMPANIES = [
    dict(slug="sea-breeze", name="Sea Breeze", city="Bakı", founded_year=2016,
         about="Sea Breeze — Xəzər dənizi sahilində premium yaşayış kompleksləri quran aparıcı tikinti şirkətidir.",
         website="seabreeze.az", phone="0125550101"),
    dict(slug="kristal-abseron", name="Kristal Abşeron", city="Bakı", founded_year=2012,
         about="Kristal Abşeron — Abşeron yarımadası boyunca müasir yaşayış kompleksləri inşa edən etibarlı developer.",
         website="kristalabseron.az", phone="0125550104"),
    dict(slug="melissa-group", name="Melissa Group", city="Bakı", founded_year=2014,
         about="Melissa Group — rahat və funksional yaşayış mühiti yaradan ailə dostu layihələr üzrə ixtisaslaşıb.",
         website="melissagroup.az", phone="0125550105"),
    dict(slug="pilot-construction", name="Pilot Construction", city="Bakı", founded_year=2010,
         about="Pilot Construction — Bakının müxtəlif rayonlarında keyfiyyətli tikinti həyata keçirən təcrübəli şirkət.",
         website="pilotconstruction.az", phone="0125550106"),
    dict(slug="white-city", name="White City", city="Bakı", founded_year=2018,
         about="White City — müasir arxitektura və geniş infrastrukturu birləşdirən iri miqyaslı yaşayış layihələri quran şirkət.",
         website="whitecity.az", phone="0125550107"),
    dict(slug="grand-hayat", name="Grand Hayat", city="Bakı", founded_year=2015,
         about="Grand Hayat — premium seqmentdə yüksək keyfiyyətli tikinti standartları ilə tanınan developer.",
         website="grandhayat.az", phone="0125550108"),
    dict(slug="olympic-star", name="Olympic Star", city="Bakı", founded_year=2013,
         about="Olympic Star — idman infrastrukturuna yaxın, aktiv həyat tərzi üçün yaşayış kompleksləri quran şirkət.",
         website="olympicstar.az", phone="0125550109"),
    dict(slug="knightsbridge", name="Knightsbridge", city="Bakı", founded_year=2019,
         about="Knightsbridge — beynəlxalq standartlara uyğun lüks yaşayış kompleksləri inşa edən premium developer.",
         website="knightsbridge.az", phone="0125550110"),
    dict(slug="park-azure", name="Park Azure", city="Bakı", founded_year=2017,
         about="Park Azure — geniş yaşıllıq zolaqları və park ərazilərinə inteqrasiya olunmuş layihələr quran şirkət.",
         website="parkazure.az", phone="0125550111"),
    dict(slug="port-baku-group", name="Port Baku", city="Bakı", founded_year=2009,
         about="Port Baku — şəhər mərkəzində ikonik, çoxfunksiyalı kompleks layihələri ilə tanınan aparıcı developer.",
         website="portbaku.az", phone="0125550102"),
    dict(slug="yasamal-group", name="Yasamal Group", city="Bakı", founded_year=2011,
         about="Yasamal Group — dağətəyi ərazilərdə sakit, ailəvi mühitli yaşayış kompleksləri quran şirkət.",
         website="yasamalgroup.az", phone="0125550103"),
    dict(slug="crescent-development", name="Crescent Development", city="Bakı", founded_year=2020,
         about="Crescent Development — sahilyanı ərazilərdə müasir konsepsiyalı yaşayış layihələri inşa edən yeni nəsil developer.",
         website="crescentdev.az", phone="0125550112"),
    dict(slug="green-line-group", name="Green Line Group", city="Bakı", founded_year=2016,
         about="Green Line Group — ekoloji, yaşıl sahələrə üstünlük verən davamlı yaşayış layihələri quran şirkət.",
         website="greenlinegroup.az", phone="0125550113"),
    dict(slug="riviera-group", name="Riviera Group", city="Bakı", founded_year=2014,
         about="Riviera Group — Aralıq dənizi üslubunda arxitektura ilə fərqlənən yaşayış kompleksləri quran developer.",
         website="rivieragroup.az", phone="0125550114"),
    dict(slug="bakixanov-tikinti", name="Bakıxanov Tikinti", city="Bakı", founded_year=2008,
         about="Bakıxanov Tikinti — sərfəli qiymətlərlə etibarlı yaşayış kompleksləri quran köklü tikinti şirkəti.",
         website="bakixanovtikinti.az", phone="0125550115"),
]

RESIDENCES = [
    dict(slug="sea-breeze", name="Sea Breeze", company_slug="sea-breeze", city="Bakı",
         district="Xəzər r., Novxanı", address="Xəzər rayonu, Novxanı qəsəbəsi, dəniz sahili",
         price_from=139000, deadline="2027", rating=4.9, accent="teal",
         description="Sea Breeze — Xəzər dənizi sahilində, müasir infrastrukturlu yaşayış kompleksidir. "
                      "Kompleks geniş yaşıllıq zolağı, şəxsi çimərlik girişi və tam təhlükəsizlik sistemi ilə təchiz olunub.",
         amenities="Bassein, Fitnes zalı, 24/7 təhlükəsizlik, Yeraltı parkinq, Uşaq meydançası, Yaşıl ərazi, Çimərlik girişi, Videomüşahidə",
         contact_name="Sea Breeze Satış Ofisi", contact_phone="0125550101"),
    dict(slug="white-city", name="White City", company_slug="white-city", city="Bakı",
         district="Xətai r.", address="Xətai rayonu, Salyan yolu",
         price_from=142000, deadline="2027", rating=4.8, accent="brass",
         description="White City — geniş ərazidə, müasir arxitektura və tam infrastrukturla inşa olunan iri yaşayış kompleksidir.",
         amenities="Bassein, Fitnes zalı, Ticarət mərkəzi, Yeraltı parkinq, Uşaq bağçası, 24/7 təhlükəsizlik",
         contact_name="White City Satış Ofisi", contact_phone="0125550107"),
    dict(slug="port-baku-residence", name="Port Baku Residence", company_slug="port-baku-group", city="Bakı",
         district="Nəsimi r.", address="Nəsimi rayonu, Neftçilər prospekti",
         price_from=310000, deadline="2026", rating=4.9, accent="brass",
         description="Port Baku Residence — şəhərin mərkəzində, Bakı buxtasının mənzərəsi ilə premium yaşayış kompleksi.",
         amenities="Bassein, Spa mərkəzi, Fitnes zalı, Yeraltı parkinq, Concierge xidməti, 24/7 təhlükəsizlik, Panoramik mənzərə",
         contact_name="Port Baku Satış Ofisi", contact_phone="0125550102"),
    dict(slug="yasamal-hills", name="Yasamal Hills", company_slug="yasamal-group", city="Bakı",
         district="Yasamal r.", address="Yasamal rayonu, dağətəyi ərazi",
         price_from=98000, deadline="2028", rating=4.6, accent="ink",
         description="Yasamal Hills — şəhərin yaşıllıq zolağına yaxın, sakit və ailəvi mühitdə yeni nəsil yaşayış kompleksi.",
         amenities="Uşaq meydançası, Yaşıl ərazi, Yeraltı parkinq, 24/7 təhlükəsizlik, İdman meydançası",
         contact_name="Yasamal Hills Satış Ofisi", contact_phone="0125550103"),
    dict(slug="kristal-abseron", name="Kristal Abşeron", company_slug="kristal-abseron", city="Bakı",
         district="Xəzər r., Bilgəh", address="Xəzər rayonu, Bilgəh qəsəbəsi",
         price_from=115000, deadline="2027", rating=4.7, accent="teal",
         description="Kristal Abşeron — Abşeron yarımadasının sakit guşəsində, təbiətlə iç-içə müasir yaşayış kompleksi.",
         amenities="Bassein, Yaşıl ərazi, Uşaq meydançası, 24/7 təhlükəsizlik, Yeraltı parkinq",
         contact_name="Kristal Abşeron Satış Ofisi", contact_phone="0125550104"),
    dict(slug="melissa-park", name="Melissa Park", company_slug="melissa-group", city="Bakı",
         district="Binəqədi r.", address="Binəqədi rayonu",
         price_from=89000, deadline="2026", rating=4.5, accent="ink",
         description="Melissa Park — ailələr üçün rahat planlaşdırma və geniş yaşıl sahələrlə yeni nəsil yaşayış kompleksi.",
         amenities="Uşaq bağçası, Yaşıl ərazi, Uşaq meydançası, Yeraltı parkinq, 24/7 təhlükəsizlik",
         contact_name="Melissa Park Satış Ofisi", contact_phone="0125550105"),
    dict(slug="pilot-residence", name="Pilot Residence", company_slug="pilot-construction", city="Bakı",
         district="Nərimanov r.", address="Nərimanov rayonu, H.Zərdabi pr.",
         price_from=126000, deadline="2026", rating=4.6, accent="brass",
         description="Pilot Residence — metroya yaxın, nəqliyyat qovşağında rahat yerləşən müasir yaşayış kompleksi.",
         amenities="Fitnes zalı, Yeraltı parkinq, 24/7 təhlükəsizlik, Videomüşahidə",
         contact_name="Pilot Residence Satış Ofisi", contact_phone="0125550106"),
    dict(slug="grand-hayat", name="Grand Hayat", company_slug="grand-hayat", city="Bakı",
         district="Səbail r.", address="Səbail rayonu, şəhər mərkəzi",
         price_from=285000, deadline="2025", rating=4.9, accent="brass",
         description="Grand Hayat — şəhər mərkəzində, yüksək keyfiyyət standartları ilə inşa olunan premium kompleks.",
         amenities="Bassein, Spa mərkəzi, Fitnes zalı, Concierge xidməti, Yeraltı parkinq, 24/7 təhlükəsizlik",
         contact_name="Grand Hayat Satış Ofisi", contact_phone="0125550108"),
    dict(slug="crescent-bay", name="Crescent Bay", company_slug="crescent-development", city="Bakı",
         district="Xəzər r., Türkan", address="Xəzər rayonu, Türkan qəsəbəsi, sahil xətti",
         price_from=168000, deadline="2028", rating=4.8, accent="teal",
         description="Crescent Bay — dəniz sahilində, yarımay formalı arxitekturası ilə fərqlənən müasir kompleks.",
         amenities="Bassein, Çimərlik girişi, Fitnes zalı, Yaşıl ərazi, 24/7 təhlükəsizlik",
         contact_name="Crescent Bay Satış Ofisi", contact_phone="0125550112"),
    dict(slug="park-azure", name="Park Azure", company_slug="park-azure", city="Bakı",
         district="Xətai r.", address="Xətai rayonu, park ərazisi yaxınlığı",
         price_from=155000, deadline="2027", rating=4.7, accent="ink",
         description="Park Azure — geniş park ərazisinə bitişik, yaşıllıqla əhatələnmiş rahat yaşayış kompleksi.",
         amenities="Yaşıl ərazi, Uşaq meydançası, Yeraltı parkinq, Fitnes zalı, 24/7 təhlükəsizlik",
         contact_name="Park Azure Satış Ofisi", contact_phone="0125550111"),
    dict(slug="knightsbridge-residence", name="Knightsbridge Residence", company_slug="knightsbridge", city="Bakı",
         district="Səbail r.", address="Səbail rayonu, Bulvar yaxınlığı",
         price_from=395000, deadline="2026", rating=5.0, accent="brass",
         description="Knightsbridge Residence — Bakı Bulvarına yaxın, beynəlxalq standartlarda lüks yaşayış kompleksi.",
         amenities="Bassein, Spa mərkəzi, Fitnes zalı, Concierge xidməti, Valet parkinq, 24/7 təhlükəsizlik, Panoramik mənzərə",
         contact_name="Knightsbridge Satış Ofisi", contact_phone="0125550110"),
    dict(slug="olympic-star", name="Olympic Star", company_slug="olympic-star", city="Bakı",
         district="Binəqədi r.", address="Binəqədi rayonu, Olimpiya kompleksi yaxınlığı",
         price_from=104000, deadline="2027", rating=4.6, accent="teal",
         description="Olympic Star — idman infrastrukturuna yaxın, aktiv həyat tərzi sevənlər üçün yaşayış kompleksi.",
         amenities="İdman meydançası, Fitnes zalı, Yaşıl ərazi, Yeraltı parkinq, 24/7 təhlükəsizlik",
         contact_name="Olympic Star Satış Ofisi", contact_phone="0125550109"),
    dict(slug="green-ville", name="Green Ville", company_slug="green-line-group", city="Bakı",
         district="Suraxanı r.", address="Suraxanı rayonu",
         price_from=82000, deadline="2029", rating=4.5, accent="ink",
         description="Green Ville — ekoloji baxımdan təmiz ərazidə, geniş yaşıllıq zolaqları ilə davamlı yaşayış layihəsi.",
         amenities="Yaşıl ərazi, Uşaq meydançası, Velosiped yolu, Yeraltı parkinq, 24/7 təhlükəsizlik",
         contact_name="Green Ville Satış Ofisi", contact_phone="0125550113"),
    dict(slug="riviera-residence", name="Riviera Residence", company_slug="riviera-group", city="Bakı",
         district="Xəzər r., Mərdəkan", address="Xəzər rayonu, Mərdəkan qəsəbəsi",
         price_from=178000, deadline="2028", rating=4.8, accent="brass",
         description="Riviera Residence — Mərdəkanın sakit bağ ərazisində, Aralıq dənizi üslubunda arxitektura ilə kompleks.",
         amenities="Bassein, Yaşıl ərazi, Fitnes zalı, Uşaq meydançası, 24/7 təhlükəsizlik",
         contact_name="Riviera Satış Ofisi", contact_phone="0125550114"),
    dict(slug="bakixanov-residence", name="Bakıxanov Residence", company_slug="bakixanov-tikinti", city="Bakı",
         district="Suraxanı r., Bakıxanov", address="Suraxanı rayonu, Bakıxanov qəsəbəsi",
         price_from=76000, deadline="2026", rating=4.4, accent="teal",
         description="Bakıxanov Residence — sərfəli qiymətlərlə, tam infrastrukturlu, ailələr üçün əlverişli yaşayış kompleksi.",
         amenities="Uşaq meydançası, Yeraltı parkinq, 24/7 təhlükəsizlik, Yaşıl ərazi",
         contact_name="Bakıxanov Satış Ofisi", contact_phone="0125550115"),
]

RESIDENCE_UNITS = {
    "sea-breeze": [
        dict(rooms=1, area_m2=52, price=139000, status="satılır"),
        dict(rooms=2, area_m2=78, price=189000, status="satılır"),
        dict(rooms=3, area_m2=112, price=249000, status="satılır"),
        dict(rooms=4, area_m2=145, price=319000, status="satılıb"),
    ],
    "port-baku-residence": [
        dict(rooms=2, area_m2=95, price=310000, status="satılır"),
        dict(rooms=3, area_m2=140, price=420000, status="satılır"),
        dict(rooms=4, area_m2=190, price=590000, status="satılır"),
    ],
    "yasamal-hills": [
        dict(rooms=1, area_m2=48, price=98000, status="satılır"),
        dict(rooms=2, area_m2=71, price=132000, status="satılır"),
        dict(rooms=3, area_m2=99, price=178000, status="satılıb"),
    ],
}

ABROAD_LISTINGS = [
    dict(user=0, category="xaricdə evlər", title="Dubai Marina-da 1 yataq otaqlı mənzil, dəniz mənzərəli",
         description="Tam mebelli, hovuz və idman zalı olan kompleksdə, metroya yaxın müasir mənzil.",
         price=185000, country="AE", city="Dubai", district="Dubai Marina", address="",
         rooms=1, area_m2=68, floor=12, floors_total=35, building_type="yeni tikili",
         repair_status="təmirli", deal_type="satılır"),
    dict(user=1, category="xaricdə evlər", title="İstanbul, Beşiktaşda 3 otaqlı mənzil",
         description="Boğaz mənzərəli, yeni tikili binada, mərkəzi yerləşən geniş mənzil.",
         price=245000, country="TR", city="İstanbul", district="Beşiktaş", address="",
         rooms=3, area_m2=125, floor=6, floors_total=14, building_type="yeni tikili",
         repair_status="təmirli", deal_type="satılır"),
]


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    with open(os.path.join(os.path.dirname(__file__), "schema.sql"), encoding="utf-8") as f:
        conn.executescript(f.read())

    cur = conn.cursor()

    for name in CITIES:
        cur.execute("INSERT OR IGNORE INTO cities(name) VALUES (?)", (name,))

    user_ids = []
    for idx, (full_name, phone, email, pw) in enumerate(USERS):
        cur.execute(
            """INSERT INTO users(full_name, phone, email, password_hash, is_verified, is_admin, is_phone_verified)
               VALUES (?,?,?,?,?,?,1)""",
            (full_name, phone, email, generate_password_hash(pw),
             1 if idx in (0, 1) else 0, 1 if idx == ADMIN_USER_INDEX else 0),
        )
        user_ids.append(cur.lastrowid)

    company_ids = {}
    for c in COMPANIES:
        cur.execute(
            """INSERT INTO construction_companies(slug, name, logo_path, cover_path, about, website, phone, city, founded_year)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (c["slug"], c["name"], f"/static/img/logos/{c['slug']}.svg", None,
             c["about"], c["website"], c["phone"], c["city"], c["founded_year"]),
        )
        company_ids[c["slug"]] = cur.lastrowid

    residence_ids = {}
    for i, item in enumerate(RESIDENCES, start=1):
        cover = f"/static/img/property_{((i - 1) % 6) + 1}.svg"
        company_id = company_ids.get(item.get("company_slug"))
        company_name = next((c["name"] for c in COMPANIES if c["slug"] == item.get("company_slug")), None)
        logo = f"/static/img/logos/{item['company_slug']}.svg" if item.get("company_slug") else None
        cur.execute(
            """INSERT INTO residences(slug, name, developer, company_id, city, district, address, price_from,
                                       deadline, rating, description, amenities, contact_name, contact_phone,
                                       image_path, logo_path, accent)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (item["slug"], item["name"], company_name, company_id, item["city"], item["district"], item["address"],
             item["price_from"], item["deadline"], item.get("rating", 4.7), item["description"], item["amenities"],
             item["contact_name"], item["contact_phone"], cover, logo, item["accent"]),
        )
        rid = cur.lastrowid
        residence_ids[item["slug"]] = rid
        gallery = [cover] + [f"/static/img/property_{((i - 1 + k) % 6) + 1}.svg" for k in (1, 2, 3)]
        for idx, img_path in enumerate(gallery):
            cur.execute(
                "INSERT INTO residence_images(residence_id, image_path, is_main, sort_order) VALUES (?,?,?,?)",
                (rid, img_path, 1 if idx == 0 else 0, idx),
            )
        units = RESIDENCE_UNITS.get(item["slug"])
        if units is None:
            base = item["price_from"]
            rnd = random.Random(item["slug"])
            units = []
            for rooms, mult, area in ((1, 0.62, 50), (2, 0.85, 76), (3, 1.15, 108), (4, 1.5, 145)):
                count = rnd.randint(2, 4)
                for _ in range(count):
                    status = "satılıb" if rnd.random() < 0.2 else "satılır"
                    units.append(dict(
                        rooms=rooms, area_m2=area + rnd.randint(-5, 8),
                        price=round(base * mult * (1 + rnd.uniform(-0.04, 0.06)), -2),
                        status=status,
                    ))
        for unit in units:
            cur.execute(
                "INSERT INTO residence_units(residence_id, rooms, area_m2, price, status) VALUES (?,?,?,?,?)",
                (rid, unit["rooms"], unit["area_m2"], unit["price"], unit["status"]),
            )

    for item in PROPERTY_LISTINGS:
        lat, lng = get_coords(item["city"], item["district"])
        rid = residence_ids.get(item.get("residence_slug"))
        cur.execute(
            """INSERT INTO listings(user_id, type, category, title, description, price, currency,
                                     city, district, address, is_negotiable, latitude, longitude, residence_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_ids[item["user"]], "emlak", item["category"], item["title"], item["description"],
             item["price"], "AZN", item["city"], item["district"], item["address"], 1, lat, lng, rid),
        )
        lid = cur.lastrowid
        cur.execute(
            """INSERT INTO property_details(listing_id, rooms, area_m2, floor, floors_total,
                                             building_type, repair_status, deal_type)
               VALUES (?,?,?,?,?,?,?,?)""",
            (lid, item["rooms"], item["area_m2"], item["floor"], item["floors_total"],
             item["building_type"], item["repair_status"], item["deal_type"]),
        )
        cur.execute(
            "INSERT INTO listing_images(listing_id, image_path, is_main) VALUES (?,?,1)",
            (lid, f"/static/img/property_{(lid % 6) + 1}.svg"),
        )

    for i, item in enumerate(VEHICLE_LISTINGS):
        lat, lng = get_coords(item["city"], item["district"])
        cur.execute(
            """INSERT INTO listings(user_id, type, category, title, description, price, currency,
                                     city, district, address, is_negotiable, latitude, longitude)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_ids[item["user"]], "neqliyyat", item["category"], item["title"], item["description"],
             item["price"], "AZN", item["city"], item["district"], item["address"], 1, lat, lng),
        )
        lid = cur.lastrowid
        has_credit = 1 if i % 3 != 0 else 0
        has_barter = 1 if i % 2 == 0 else 0
        has_vin = 1 if i % 4 != 1 else 0
        cur.execute(
            """INSERT INTO vehicle_details(listing_id, make, model, year, mileage_km, engine_volume,
                                            fuel_type, transmission, color, body_type, condition_status,
                                            has_credit, has_barter, has_vin, deal_type)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (lid, item["make"], item["model"], item["year"], item["mileage_km"], item["engine_volume"],
             item["fuel_type"], item["transmission"], item["color"], item["body_type"],
             item["condition_status"], has_credit, has_barter, has_vin, item.get("deal_type", "satılır")),
        )
        cur.execute(
            "INSERT INTO listing_images(listing_id, image_path, is_main) VALUES (?,?,1)",
            (lid, f"/static/img/vehicle_{(lid % 6) + 1}.svg"),
        )

    for item in ABROAD_LISTINGS:
        cur.execute(
            """INSERT INTO listings(user_id, type, category, title, description, price, currency,
                                     city, district, address, is_negotiable, country)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_ids[item["user"]], "emlak", item["category"], item["title"], item["description"],
             item["price"], "AZN", item["city"], item["district"], item["address"], 1, item["country"]),
        )
        lid = cur.lastrowid
        cur.execute(
            """INSERT INTO property_details(listing_id, rooms, area_m2, floor, floors_total,
                                             building_type, repair_status, deal_type)
               VALUES (?,?,?,?,?,?,?,?)""",
            (lid, item["rooms"], item["area_m2"], item["floor"], item["floors_total"],
             item["building_type"], item["repair_status"], item["deal_type"]),
        )
        cur.execute(
            "INSERT INTO listing_images(listing_id, image_path, is_main) VALUES (?,?,1)",
            (lid, f"/static/img/property_{(lid % 6) + 1}.svg"),
        )

    REVIEWS = [
        (0, 5, "Mənzili bir həftəyə satdım — elan yerləşdirmək 5 dəqiqə çəkdi, satıcılar birbaşa mənə yazırdı, heç bir vasitəçiyə ehtiyac olmadı."),
        (1, 5, "Avtomobil axtarışında filtrlər çox rahatdır — marka, il, qiymət üzrə dəqiq nəticə tapdım. VIP elan sayəsində sürətlə satdım."),
        (2, 5, "Xaricdə mənzil axtaran müştərilərimə bu saytı tövsiyə edirəm — Dubai və Türkiyə üzrə elanlar bir yerdə, çox rahatdır."),
    ]
    for user_idx, rating, body in REVIEWS:
        cur.execute(
            "INSERT INTO reviews(user_id, rating, body) VALUES (?,?,?)",
            (user_ids[user_idx], rating, body),
        )

    SELLER_REVIEWS = [
        (0, 1, 5, "Elvin ilə əlaqə çox rahat oldu, elanda yazılan qiymətdən fərqli deyildi."),
        (0, 2, 4, "Cavab vermə sürəti yaxşıdır, mənzil də təsvirə uyğun idi."),
        (1, 0, 5, "Aysel çox köməkçi oldu, avtomobilin bütün sənədləri hazır idi."),
    ]
    for seller_idx, reviewer_idx, rating, body in SELLER_REVIEWS:
        cur.execute(
            "INSERT INTO seller_reviews(seller_id, reviewer_id, rating, body) VALUES (?,?,?,?)",
            (user_ids[seller_idx], user_ids[reviewer_idx], rating, body),
        )

    TRENDING = ["BMW G30", "Sea Breeze", "Mercedes E-Class", "White City", "Dubai Marina",
                "Villa Mərdəkan", "2 otaqlı mənzil", "Toyota Camry"]
    for term in TRENDING:
        cur.execute("INSERT INTO search_queries(query) VALUES (?)", (term,))

    conn.commit()
    conn.close()
    print("Veritabani yaradildi:", DB_PATH)


if __name__ == "__main__":
    main()
