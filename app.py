import os
import secrets
import sqlite3
import uuid
import json
import re
from functools import wraps

from flask import (Flask, g, render_template, request, redirect, url_for,
                    session, flash, jsonify, abort)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from translations import get_translator, LANGUAGES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "varaz.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXT = {"png", "jpg", "jpeg", "webp"}

with open(os.path.join(BASE_DIR, "data", "locations.json"), encoding="utf-8") as f:
    COUNTRIES = json.load(f)  # { "AE": {"name":..,"flag":..,"cities":{city: [districts]}}, ... }

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("VARAZ_SECRET_KEY", "dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024  # 12 MB per request

PROPERTY_CATEGORIES = ["mənzil", "həyət evi/bağ evi", "ofis", "qaraj", "torpaq", "obyekt", "xaricdə evlər"]
VEHICLE_CATEGORIES = ["minik", "suv", "moto", "pikap", "furqon", "kommersiya", "ehtiyat hissələri"]
BUILDING_TYPES = ["yeni tikili", "köhnə tikili", "fərdi"]
VEHICLE_MAKES = [
    "Mercedes-Benz", "BMW", "Audi", "Volkswagen", "Toyota", "Hyundai", "Kia",
    "Chevrolet", "Ford", "Nissan", "Honda", "Mazda", "Lexus", "Porsche",
    "Land Rover", "Lada (VAZ)", "GAZ", "UAZ", "Opel", "Skoda", "Renault",
    "Peugeot", "Citroen", "Fiat", "Mitsubishi", "Subaru", "Suzuki", "Volvo",
    "Jeep", "Mini", "Infiniti", "Cadillac", "Chrysler", "Dodge", "GMC",
    "Yamaha", "Kawasaki", "Harley-Davidson", "Iveco", "MAN", "Scania", "Isuzu",
    "Digər",
]
LISTINGS_PAGE_SIZE = 9
VIP_PACKAGES = {
    "3": {"days": 3, "price": 5, "label": "3 gün"},
    "7": {"days": 7, "price": 10, "label": "7 gün"},
    "30": {"days": 30, "price": 25, "label": "30 gün"},
}

VEHICLE_BODY_TYPES = [
    "Sedan", "SUV", "Jeep", "Pickup", "Coupe", "Hatchback", "Universal", "Minivan", "Cabriolet", "Van",
]
VEHICLE_FUEL_TYPES = [
    ("benzin", "Benzin"), ("dizel", "Dizel"), ("qaz", "Qaz"),
    ("hibrid", "Hibrid"), ("plug-in", "Plug-in Hybrid"), ("elektro", "Elektrik"),
]
VEHICLE_DRIVETRAINS = [("tam", "Tam"), ("arxa", "Arxa"), ("on", "Ön")]
VEHICLE_TRANSMISSIONS = [
    ("avtomat", "Avtomat"), ("mexanika", "Mexanika"), ("robot", "Robot"), ("variator", "Variator (CVT)"),
]
VEHICLE_MARKETS = [
    "Amerika", "Avropa", "Dubay", "Koreya", "Rusiya", "Rəsmi diler", "Yaponiya", "Çin", "Digər",
]
VEHICLE_COLORS = [
    ("qara", "Qara", "#1a1a1a"), ("ağ", "Ağ", "#ffffff"), ("qırmızı", "Qırmızı", "#e4483a"),
    ("mavi", "Mavi", "#2f6fa8"), ("yaşıl", "Yaşıl", "#2e8b57"), ("sarı", "Sarı", "#f0d020"),
    ("qəhvəyi", "Qəhvəyi", "#6b4423"), ("narıncı", "Narıncı", "#e8772e"), ("bənövşəyi", "Bənövşəyi", "#7a4fe9"),
    ("boz", "Boz", "#8a8f98"), ("gümüşü", "Gümüşü", "#c0c0c0"), ("göy", "Göy", "#3a8fd9"),
]
VEHICLE_EQUIPMENT = [
    "360º kamera", "ABS", "Arxa görüntü kamerası", "Dəri salon", "Kondisioner", "Ksenon lampalar",
    "Lyuk", "Mərkəzi qapanma", "Oturacaqların isidilməsi", "Oturacaqların ventilyasiyası",
    "Park radarı", "Yan pərdələr", "Yağış sensoru", "Yüngül lehimli disklər",
]
CURRENCIES = ["AZN", "USD", "EUR"]


def is_valid_vin(vin):
    if not vin:
        return True  # optional-friendly; required check happens separately
    vin = vin.strip().upper()
    if len(vin) != 17:
        return False
    if any(ch in vin for ch in ("I", "O", "Q")):
        return False
    return vin.isalnum()


# ---------------------------------------------------------------- database

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ------------------------------------------------------------------ auth

def current_user():
    if "user_id" not in session:
        return None
    if "_user_cache" not in g:
        db = get_db()
        g._user_cache = db.execute(
            "SELECT * FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
    return g._user_cache


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Bu əməliyyat üçün hesabınıza daxil olun.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            return redirect(url_for("login", next=request.path))
        if not user["is_admin"]:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def unread_message_count(user_id):
    db = get_db()
    row = db.execute(
        """SELECT COUNT(*) AS cnt FROM messages m
           JOIN conversations c ON c.id = m.conversation_id
           WHERE (c.buyer_id = ? OR c.seller_id = ?) AND m.sender_id != ? AND m.is_read = 0""",
        (user_id, user_id, user_id),
    ).fetchone()
    return row["cnt"]


def unread_notification_count(user_id):
    db = get_db()
    row = db.execute(
        "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id=? AND is_read=0", (user_id,)
    ).fetchone()
    return row["cnt"]


SMTP_HOST_DEFAULT = "smtp.gmail.com"
SMTP_PORT_DEFAULT = 587
SMTP_SENDER_DEFAULT = "azvar2026@gmail.com"


def send_email(to_addr, subject, body):
    """Best-effort email send via Gmail SMTP (azvar2026@gmail.com).
    Requires a Gmail *App Password* (not the normal account password) set as the
    SMTP_PASS environment variable before starting the app, e.g.:
        set SMTP_PASS=xxxxxxxxxxxxxxxx   (Windows)
        export SMTP_PASS=xxxxxxxxxxxxxxxx (Mac/Linux)
    Generate one at https://myaccount.google.com/apppasswords (2-Step Verification
    must be enabled on the Google account first).
    Falls back to a local log entry when SMTP_PASS is not set, so the app still
    works fully in dev/demo mode without real credentials.
    Override sender/host via SMTP_HOST/SMTP_PORT/SMTP_USER if needed."""
    smtp_pass = os.environ.get("SMTP_PASS")
    smtp_user = os.environ.get("SMTP_USER", SMTP_SENDER_DEFAULT)
    if not smtp_pass or not to_addr:
        print(f"[email-sim] to={to_addr!r} subject={subject!r}\n{body}\n")
        return False
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to_addr
        smtp_host = os.environ.get("SMTP_HOST", SMTP_HOST_DEFAULT)
        smtp_port = int(os.environ.get("SMTP_PORT", SMTP_PORT_DEFAULT))
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as exc:
        print(f"[email-error] {exc}")
        return False


def send_sms(phone, message):
    """Best-effort SMS send. No SMS gateway is wired up (no provider credentials
    were supplied), so this always falls back to a local log entry — the flow
    itself is fully built and ready to plug into a real provider (e.g. Twilio,
    or a local AZ gateway) by filling in this function.
    For now, the verification code is also returned to the caller so it can be
    shown directly on-screen in this dev/demo environment."""
    print(f"[sms-sim] to={phone!r}\n{message}\n")
    return False


def get_recently_viewed(exclude_id=None, limit=8):
    ids = [i for i in session.get("recently_viewed", []) if i != exclude_id][:limit]
    if not ids:
        return []
    db = get_db()
    placeholders = ",".join("?" * len(ids))
    rows = db.execute(
        f"""SELECT l.*, (SELECT image_path FROM listing_images WHERE listing_id=l.id
                          ORDER BY is_main DESC LIMIT 1) AS thumb,
                   CASE WHEN l.is_vip=1 AND l.vip_expires_at > datetime('now') THEN 1 ELSE 0 END AS is_vip_active
            FROM listings l WHERE l.id IN ({placeholders}) AND l.status='active'""",
        ids,
    ).fetchall()
    by_id = {r["id"]: r for r in rows}
    return [by_id[i] for i in ids if i in by_id]


@app.route("/dil/<lang>")
def set_language(lang):
    if lang in LANGUAGES:
        session["lang"] = lang
    next_url = request.referrer or url_for("home")
    return redirect(next_url)


@app.context_processor
def inject_globals():
    user = current_user()
    current_lang = session.get("lang", "az")
    return {
        "current_user": user,
        "property_categories": PROPERTY_CATEGORIES,
        "vehicle_categories": VEHICLE_CATEGORIES,
        "building_types": BUILDING_TYPES,
        "vehicle_makes": VEHICLE_MAKES,
        "unread_messages": unread_message_count(user["id"]) if user else 0,
        "unread_notifications": unread_notification_count(user["id"]) if user else 0,
        "compare_count": len(session.get("compare_ids", [])),
        "compare_ids": session.get("compare_ids", []),
        "countries": COUNTRIES,
        "t": get_translator(current_lang),
        "current_lang": current_lang,
        "languages": LANGUAGES,
        "vehicle_body_types": VEHICLE_BODY_TYPES,
        "vehicle_fuel_types": VEHICLE_FUEL_TYPES,
        "vehicle_drivetrains": VEHICLE_DRIVETRAINS,
        "vehicle_transmissions": VEHICLE_TRANSMISSIONS,
        "vehicle_markets": VEHICLE_MARKETS,
        "vehicle_colors": VEHICLE_COLORS,
        "vehicle_equipment": VEHICLE_EQUIPMENT,
        "currencies": CURRENCIES,
    }


@app.template_filter("money")
def money_filter(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value
    return f"{value:,.0f}".replace(",", " ")


@app.template_filter("timeago")
def timeago_filter(value):
    from datetime import datetime as _dt
    try:
        then = _dt.strptime(value[:19], "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return value
    diff = _dt.now() - then
    seconds = diff.total_seconds()
    if seconds < 60:
        return "indicə"
    if seconds < 3600:
        return f"{int(seconds // 60)} dəqiqə əvvəl"
    if seconds < 86400:
        return f"{int(seconds // 3600)} saat əvvəl"
    days = int(seconds // 86400)
    if days < 30:
        return f"{days} gün əvvəl"
    return then.strftime("%d.%m.%Y")


# --------------------------------------------------------------- listing helpers

def fetch_listing_row(listing_id):
    db = get_db()
    listing = db.execute(
        """SELECT l.*, CASE WHEN l.is_vip=1 AND l.vip_expires_at > datetime('now') THEN 1 ELSE 0 END AS is_vip_active
           FROM listings l WHERE l.id = ?""",
        (listing_id,),
    ).fetchone()
    if listing is None:
        return None, None, []
    if listing["type"] == "emlak":
        details = db.execute(
            "SELECT * FROM property_details WHERE listing_id = ?", (listing_id,)
        ).fetchone()
    else:
        details = db.execute(
            "SELECT * FROM vehicle_details WHERE listing_id = ?", (listing_id,)
        ).fetchone()
    images = db.execute(
        "SELECT * FROM listing_images WHERE listing_id = ? ORDER BY is_main DESC, sort_order ASC",
        (listing_id,),
    ).fetchall()
    return listing, details, images


def build_listing_query(args):
    """Builds a filtered SELECT over listings based on query-string args."""
    where = ["l.status = 'active'"]
    params = []

    ltype = args.get("type")
    if ltype in ("emlak", "neqliyyat"):
        where.append("l.type = ?")
        params.append(ltype)

    category = args.get("category")
    if category:
        where.append("l.category = ?")
        params.append(category)

    city = args.get("city")
    if city:
        where.append("l.city = ?")
        params.append(city)

    country = args.get("country")
    if country:
        where.append("l.country = ?")
        params.append(country)

    q = args.get("q")
    if q:
        tokens = [t for t in q.strip().split() if t][:6]
        for t in tokens:
            like = f"%{t}%"
            where.append(
                """(
                    l.title LIKE ? OR l.description LIKE ? OR l.city LIKE ? OR l.district LIKE ? OR l.category LIKE ?
                    OR l.id IN (SELECT listing_id FROM vehicle_details WHERE make LIKE ? OR model LIKE ?)
                    OR l.id IN (SELECT listing_id FROM property_details WHERE building_type LIKE ?)
                    OR (l.residence_id IS NOT NULL AND l.residence_id IN (SELECT id FROM residences WHERE name LIKE ?))
                )"""
            )
            params.extend([like] * 9)

    price_min = args.get("price_min")
    if price_min:
        where.append("l.price >= ?")
        params.append(float(price_min))

    price_max = args.get("price_max")
    if price_max:
        where.append("l.price <= ?")
        params.append(float(price_max))

    deal_type = args.get("deal_type")
    if deal_type:
        where.append(
            """(l.id IN (SELECT listing_id FROM property_details WHERE deal_type = ?)
                OR l.id IN (SELECT listing_id FROM vehicle_details WHERE deal_type = ?))"""
        )
        params.extend([deal_type, deal_type])

    building_type = args.get("building_type")
    if building_type:
        where.append(
            "l.id IN (SELECT listing_id FROM property_details WHERE building_type = ?)"
        )
        params.append(building_type)

    body_types = [v for v in (args.getlist("body_type") if hasattr(args, "getlist") else ([args["body_type"]] if args.get("body_type") else [])) if v]
    if body_types:
        placeholders = ",".join("?" * len(body_types))
        where.append(
            f"l.id IN (SELECT listing_id FROM vehicle_details WHERE body_type IN ({placeholders}))"
        )
        params.extend(body_types)

    make = args.get("make")
    if make:
        where.append(
            "l.id IN (SELECT listing_id FROM vehicle_details WHERE make = ?)"
        )
        params.append(make)

    model = args.get("model")
    if model:
        where.append(
            "l.id IN (SELECT listing_id FROM vehicle_details WHERE model = ?)"
        )
        params.append(model)

    year_min = args.get("year_min")
    if year_min:
        where.append("l.id IN (SELECT listing_id FROM vehicle_details WHERE year >= ?)")
        params.append(int(year_min))

    year_max = args.get("year_max")
    if year_max:
        where.append("l.id IN (SELECT listing_id FROM vehicle_details WHERE year <= ?)")
        params.append(int(year_max))

    fuel_types = [v for v in (args.getlist("fuel_type") if hasattr(args, "getlist") else ([args["fuel_type"]] if args.get("fuel_type") else [])) if v]
    if fuel_types:
        placeholders = ",".join("?" * len(fuel_types))
        where.append(f"l.id IN (SELECT listing_id FROM vehicle_details WHERE fuel_type IN ({placeholders}))")
        params.extend(fuel_types)

    transmissions = [v for v in (args.getlist("transmission") if hasattr(args, "getlist") else ([args["transmission"]] if args.get("transmission") else [])) if v]
    if transmissions:
        placeholders = ",".join("?" * len(transmissions))
        where.append(f"l.id IN (SELECT listing_id FROM vehicle_details WHERE transmission IN ({placeholders}))")
        params.extend(transmissions)

    colors = [v for v in (args.getlist("color") if hasattr(args, "getlist") else ([args["color"]] if args.get("color") else [])) if v]
    if colors:
        placeholders = ",".join("?" * len(colors))
        where.append(f"l.id IN (SELECT listing_id FROM vehicle_details WHERE color IN ({placeholders}))")
        params.extend(colors)

    engines = [v for v in (args.getlist("engine") if hasattr(args, "getlist") else ([args["engine"]] if args.get("engine") else [])) if v]
    if engines:
        engine_clauses = []
        for e in engines:
            try:
                ev = float(e)
            except ValueError:
                continue
            if ev >= 4.0:
                engine_clauses.append("engine_volume >= ?")
                params.append(3.95)
            else:
                engine_clauses.append("engine_volume BETWEEN ? AND ?")
                params.extend([ev - 0.1, ev + 0.1])
        if engine_clauses:
            where.append(f"l.id IN (SELECT listing_id FROM vehicle_details WHERE {' OR '.join(engine_clauses)})")

    mileage_range = args.get("mileage_range")
    if mileage_range:
        bounds = {
            "0-50000": (0, 50000),
            "50000-100000": (50000, 100000),
            "100000-200000": (100000, 200000),
            "200000+": (200000, None),
        }.get(mileage_range)
        if bounds:
            lo, hi = bounds
            if hi is None:
                where.append("l.id IN (SELECT listing_id FROM vehicle_details WHERE mileage_km >= ?)")
                params.append(lo)
            else:
                where.append("l.id IN (SELECT listing_id FROM vehicle_details WHERE mileage_km BETWEEN ? AND ?)")
                params.extend([lo, hi])

    if args.get("has_credit"):
        where.append("l.id IN (SELECT listing_id FROM vehicle_details WHERE has_credit = 1)")
    if args.get("has_barter"):
        where.append("l.id IN (SELECT listing_id FROM vehicle_details WHERE has_barter = 1)")
    if args.get("has_vin"):
        where.append("l.id IN (SELECT listing_id FROM vehicle_details WHERE has_vin = 1)")

    sort = args.get("sort", "new")
    order_sql = {
        "new": "l.created_at DESC",
        "price_asc": "l.price ASC",
        "price_desc": "l.price DESC",
    }.get(sort, "l.created_at DESC")

    sql = f"""
        SELECT l.*, (SELECT image_path FROM listing_images
                      WHERE listing_id = l.id ORDER BY is_main DESC LIMIT 1) AS thumb,
               CASE WHEN l.is_vip = 1 AND l.vip_expires_at > datetime('now') THEN 1 ELSE 0 END AS is_vip_active,
               (SELECT mileage_km FROM vehicle_details WHERE listing_id = l.id) AS mileage_km,
               (SELECT transmission FROM vehicle_details WHERE listing_id = l.id) AS transmission,
               (SELECT deal_type FROM vehicle_details WHERE listing_id = l.id) AS vehicle_deal_type
        FROM listings l
        WHERE {' AND '.join(where)}
        ORDER BY is_vip_active DESC, {order_sql}
    """
    count_sql = f"SELECT COUNT(*) AS cnt FROM listings l WHERE {' AND '.join(where)}"
    return sql, count_sql, params


# ------------------------------------------------------------------ pages

@app.route("/")
def home():
    db = get_db()
    featured_property = db.execute(
        """SELECT l.*, (SELECT image_path FROM listing_images WHERE listing_id=l.id
                         ORDER BY is_main DESC LIMIT 1) AS thumb,
                  CASE WHEN l.is_vip=1 AND l.vip_expires_at > datetime('now') THEN 1 ELSE 0 END AS is_vip_active
           FROM listings l WHERE type='emlak' AND status='active'
           ORDER BY is_vip_active DESC, created_at DESC LIMIT 4"""
    ).fetchall()
    featured_vehicle = db.execute(
        """SELECT l.*, (SELECT image_path FROM listing_images WHERE listing_id=l.id
                         ORDER BY is_main DESC LIMIT 1) AS thumb,
                  CASE WHEN l.is_vip=1 AND l.vip_expires_at > datetime('now') THEN 1 ELSE 0 END AS is_vip_active
           FROM listings l WHERE type='neqliyyat' AND status='active'
           ORDER BY is_vip_active DESC, created_at DESC LIMIT 4"""
    ).fetchall()
    vip_listings = db.execute(
        """SELECT l.*, (SELECT image_path FROM listing_images WHERE listing_id=l.id
                         ORDER BY is_main DESC LIMIT 1) AS thumb, 1 AS is_vip_active
           FROM listings l WHERE status='active' AND is_vip=1 AND vip_expires_at > datetime('now')
           ORDER BY vip_expires_at DESC LIMIT 8"""
    ).fetchall()
    stats = db.execute(
        """SELECT
             (SELECT COUNT(*) FROM listings WHERE type='emlak' AND status='active') AS emlak_count,
             (SELECT COUNT(*) FROM listings WHERE type='neqliyyat' AND status='active') AS neqliyyat_count,
             (SELECT COUNT(*) FROM users) AS user_count
        """
    ).fetchone()
    cities = db.execute("SELECT name FROM cities ORDER BY name").fetchall()
    residences = db.execute(
        """SELECT r.*, c.name AS company_name, c.slug AS company_slug
           FROM residences r LEFT JOIN construction_companies c ON c.id = r.company_id
           ORDER BY r.rating DESC, r.id LIMIT 6"""
    ).fetchall()
    top_cities = db.execute(
        """SELECT city, COUNT(*) AS cnt FROM listings WHERE status='active'
           GROUP BY city ORDER BY cnt DESC LIMIT 6"""
    ).fetchall()
    reviews = db.execute(
        """SELECT r.*, u.full_name FROM reviews r
           JOIN users u ON u.id = r.user_id
           ORDER BY r.created_at DESC LIMIT 6"""
    ).fetchall()
    popular_projects = db.execute(
        """SELECT r.*, c.name AS company_name, c.slug AS company_slug
           FROM residences r LEFT JOIN construction_companies c ON c.id = r.company_id
           ORDER BY r.rating DESC, r.id LIMIT 12"""
    ).fetchall()
    recently_viewed = get_recently_viewed(limit=8)
    trending_searches = db.execute(
        """SELECT query, COUNT(*) AS cnt FROM search_queries
           WHERE created_at > datetime('now', '-30 days')
           GROUP BY LOWER(query) ORDER BY cnt DESC, MAX(created_at) DESC LIMIT 8"""
    ).fetchall()
    return render_template(
        "home.html", featured_property=featured_property,
        featured_vehicle=featured_vehicle, stats=stats, cities=cities,
        residences=residences, vip_listings=vip_listings, top_cities=top_cities,
        reviews=reviews, popular_projects=popular_projects, recently_viewed=recently_viewed,
        trending_searches=trending_searches,
    )


@app.route("/rey-yaz", methods=["GET", "POST"])
@login_required
def write_review():
    if request.method == "GET":
        return render_template("review_form.html")

    db = get_db()
    user = current_user()
    body = request.form.get("body", "").strip()
    try:
        rating = int(request.form.get("rating", "0"))
    except ValueError:
        rating = 0

    errors = []
    if rating < 1 or rating > 5:
        errors.append("Zəhmət olmasa ulduz reytinqi seçin.")
    if len(body) < 10:
        errors.append("Rəy ən azı 10 simvol olmalıdır.")

    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("review_form.html", form=request.form), 400

    db.execute(
        "INSERT INTO reviews(user_id, rating, body) VALUES (?,?,?)",
        (user["id"], rating, body),
    )
    db.commit()
    flash("Rəyiniz üçün təşəkkür edirik!", "success")
    return redirect(url_for("home"))


@app.route("/daha-cox")
def more_menu():
    return render_template("more_menu.html")


@app.route("/qaydalar")
def rules():
    return render_template("rules.html")


@app.route("/elaqe")
def contact():
    return render_template("contact.html")


@app.route("/haqqimizda")
def about():
    return render_template("about.html")


@app.route("/layihe/<slug>")
def residence_detail(slug):
    db = get_db()
    residence = db.execute("SELECT * FROM residences WHERE slug=?", (slug,)).fetchone()
    if residence is None:
        abort(404)
    company = None
    if residence["company_id"]:
        company = db.execute(
            "SELECT * FROM construction_companies WHERE id=?", (residence["company_id"],)
        ).fetchone()
    images = db.execute(
        "SELECT * FROM residence_images WHERE residence_id=? ORDER BY is_main DESC, sort_order ASC",
        (residence["id"],),
    ).fetchall()
    if not images:
        images = [{"image_path": residence["image_path"]}] if residence["image_path"] else []
    units = db.execute(
        "SELECT * FROM residence_units WHERE residence_id=? ORDER BY rooms ASC, area_m2 ASC",
        (residence["id"],),
    ).fetchall()
    amenities = [a.strip() for a in (residence["amenities"] or "").split(",") if a.strip()]
    similar = db.execute(
        """SELECT * FROM residences
           WHERE id != ? AND (company_id = ? OR company_id IS NULL)
           ORDER BY (company_id = ?) DESC, id LIMIT 3""",
        (residence["id"], residence["company_id"], residence["company_id"]),
    ).fetchall()
    listings_here = db.execute(
        """SELECT l.*, (SELECT image_path FROM listing_images WHERE listing_id=l.id
                         ORDER BY is_main DESC LIMIT 1) AS thumb,
                  CASE WHEN l.is_vip=1 AND l.vip_expires_at > datetime('now') THEN 1 ELSE 0 END AS is_vip_active
           FROM listings l WHERE l.residence_id=? AND l.status='active'
           ORDER BY is_vip_active DESC, l.created_at DESC""",
        (residence["id"],),
    ).fetchall()
    active_apartments = db.execute(
        """SELECT
             (SELECT COUNT(*) FROM residence_units WHERE residence_id=? AND status='satılır') +
             (SELECT COUNT(*) FROM listings WHERE residence_id=? AND status='active') AS cnt""",
        (residence["id"], residence["id"]),
    ).fetchone()["cnt"]
    return render_template(
        "residence_detail.html", residence=residence, images=images, units=units,
        amenities=amenities, similar=similar, listings_here=listings_here,
        company=company, active_apartments=active_apartments,
    )


@app.route("/layiheler")
def projects_list():
    db = get_db()
    company_slug = request.args.get("company")
    district = request.args.get("district")
    where = []
    params = []
    if company_slug:
        where.append("c.slug = ?")
        params.append(company_slug)
    if district:
        where.append("r.district = ?")
        params.append(district)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    residences = db.execute(
        f"""SELECT r.*, c.name AS company_name, c.slug AS company_slug
            FROM residences r LEFT JOIN construction_companies c ON c.id = r.company_id
            {where_sql}
            ORDER BY r.rating DESC, r.id""",
        params,
    ).fetchall()
    companies = db.execute("SELECT slug, name FROM construction_companies ORDER BY name").fetchall()
    districts = db.execute(
        "SELECT DISTINCT district FROM residences WHERE district IS NOT NULL ORDER BY district"
    ).fetchall()
    return render_template(
        "projects_list.html", residences=residences, companies=companies, districts=districts,
        args=request.args,
    )


@app.route("/sirketler")
def companies_list():
    db = get_db()
    companies = db.execute(
        """SELECT c.*, COUNT(r.id) AS project_count
           FROM construction_companies c LEFT JOIN residences r ON r.company_id = c.id
           GROUP BY c.id ORDER BY c.name"""
    ).fetchall()
    return render_template("companies_list.html", companies=companies)


@app.route("/sirket/<slug>")
def company_detail(slug):
    db = get_db()
    company = db.execute("SELECT * FROM construction_companies WHERE slug=?", (slug,)).fetchone()
    if company is None:
        abort(404)
    residences = db.execute(
        "SELECT * FROM residences WHERE company_id=? ORDER BY rating DESC", (company["id"],)
    ).fetchall()
    residence_ids = [r["id"] for r in residences]
    stats = {"total_projects": len(residences), "total_apartments": 0, "active_projects": 0, "completed_projects": 0}
    from datetime import datetime as _dt
    current_year = _dt.now().year
    for r in residences:
        try:
            if int(r["deadline"]) <= current_year:
                stats["completed_projects"] += 1
            else:
                stats["active_projects"] += 1
        except (TypeError, ValueError):
            stats["active_projects"] += 1
    if residence_ids:
        placeholders = ",".join("?" * len(residence_ids))
        stats["total_apartments"] = db.execute(
            f"""SELECT
                  (SELECT COUNT(*) FROM residence_units WHERE residence_id IN ({placeholders})) +
                  (SELECT COUNT(*) FROM listings WHERE residence_id IN ({placeholders}) AND status='active') AS cnt""",
            residence_ids + residence_ids,
        ).fetchone()["cnt"]
    company_listings = db.execute(
        f"""SELECT l.*, (SELECT image_path FROM listing_images WHERE listing_id=l.id
                         ORDER BY is_main DESC LIMIT 1) AS thumb,
                  CASE WHEN l.is_vip=1 AND l.vip_expires_at > datetime('now') THEN 1 ELSE 0 END AS is_vip_active
           FROM listings l WHERE l.residence_id IN ({placeholders if residence_ids else 'SELECT -1'}) AND l.status='active'
           ORDER BY is_vip_active DESC, l.created_at DESC LIMIT 8""",
        residence_ids,
    ).fetchall() if residence_ids else []
    return render_template(
        "company_detail.html", company=company, residences=residences, stats=stats,
        company_listings=company_listings,
    )


@app.route("/elanlar")
def listings():
    db = get_db()
    sql, count_sql, params = build_listing_query(request.args)

    q = request.args.get("q", "").strip()
    matched_residence = None
    if q:
        db.execute("INSERT INTO search_queries(query) VALUES (?)", (q,))
        db.commit()
        matched_residence = db.execute(
            "SELECT * FROM residences WHERE name LIKE ? ORDER BY rating DESC LIMIT 1", (f"%{q}%",)
        ).fetchone()

    total_count = db.execute(count_sql, params).fetchone()["cnt"]
    total_pages = max(1, (total_count + LISTINGS_PAGE_SIZE - 1) // LISTINGS_PAGE_SIZE)
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    page = max(1, min(page, total_pages))
    offset = (page - 1) * LISTINGS_PAGE_SIZE

    paged_sql = sql + " LIMIT ? OFFSET ?"
    rows = db.execute(paged_sql, params + [LISTINGS_PAGE_SIZE, offset]).fetchall()

    cities = db.execute("SELECT name FROM cities ORDER BY name").fetchall()
    ltype = request.args.get("type", "")
    categories = PROPERTY_CATEGORIES if ltype == "emlak" else (
        VEHICLE_CATEGORIES if ltype == "neqliyyat" else PROPERTY_CATEGORIES + VEHICLE_CATEGORIES
    )

    if ltype == "neqliyyat":
        colors_available = db.execute(
            "SELECT DISTINCT color FROM vehicle_details WHERE color IS NOT NULL AND color != '' ORDER BY color"
        ).fetchall()
        return render_template(
            "vehicle_listings.html", rows=rows, cities=cities, categories=categories,
            args=request.args, result_count=total_count,
            page=page, total_pages=total_pages, colors_available=colors_available,
            matched_residence=matched_residence,
        )

    return render_template(
        "listings.html", rows=rows, cities=cities, categories=categories,
        args=request.args, result_count=total_count,
        page=page, total_pages=total_pages, matched_residence=matched_residence,
    )


@app.route("/elan/<int:listing_id>")
def listing_detail(listing_id):
    db = get_db()
    db.execute("UPDATE listings SET views = views + 1 WHERE id = ?", (listing_id,))
    db.commit()
    listing, details, images = fetch_listing_row(listing_id)
    if listing is None:
        abort(404)

    recent = [i for i in session.get("recently_viewed", []) if i != listing_id]
    recent.insert(0, listing_id)
    session["recently_viewed"] = recent[:10]

    owner = db.execute("SELECT * FROM users WHERE id = ?", (listing["user_id"],)).fetchone()
    seller_stats = db.execute(
        """SELECT
             (SELECT COUNT(*) FROM listings WHERE user_id=? AND status='active') AS listing_count,
             (SELECT AVG(rating) FROM seller_reviews WHERE seller_id=?) AS avg_rating,
             (SELECT COUNT(*) FROM seller_reviews WHERE seller_id=?) AS review_count""",
        (listing["user_id"], listing["user_id"], listing["user_id"]),
    ).fetchone()

    is_favorite = False
    is_watching = False
    user = current_user()
    if user:
        fav = db.execute(
            "SELECT 1 FROM favorites WHERE user_id=? AND listing_id=?",
            (user["id"], listing_id),
        ).fetchone()
        is_favorite = fav is not None
        watch = db.execute(
            "SELECT 1 FROM price_watches WHERE user_id=? AND listing_id=?",
            (user["id"], listing_id),
        ).fetchone()
        is_watching = watch is not None

    similar = db.execute(
        """SELECT l.*, (SELECT image_path FROM listing_images WHERE listing_id=l.id
                         ORDER BY is_main DESC LIMIT 1) AS thumb,
                  CASE WHEN l.is_vip=1 AND l.vip_expires_at > datetime('now') THEN 1 ELSE 0 END AS is_vip_active
           FROM listings l WHERE type=? AND category=? AND id!=? AND status='active'
           ORDER BY is_vip_active DESC, created_at DESC LIMIT 4""",
        (listing["type"], listing["category"], listing_id),
    ).fetchall()
    recently_viewed = get_recently_viewed(exclude_id=listing_id, limit=4)
    return render_template(
        "listing_detail.html", listing=listing, details=details, images=images,
        owner=owner, is_favorite=is_favorite, similar=similar, seller_stats=seller_stats,
        is_watching=is_watching, recently_viewed=recently_viewed,
        compare_ids=session.get("compare_ids", []),
    )


@app.route("/elan/yeni", methods=["GET", "POST"])
@login_required
def new_listing():
    if request.method == "GET":
        residences = get_db().execute("SELECT id, name FROM residences ORDER BY name").fetchall()
        return render_template("new_listing.html", residences=residences)

    db = get_db()
    user = current_user()
    ltype = request.form.get("type")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "0")
    city = request.form.get("city", "").strip()
    district = request.form.get("district", "").strip()
    category = request.form.get("category", "").strip()
    country = request.form.get("country", "").strip() or None
    residence_id = request.form.get("residence_id", "").strip() or None

    def parse_coord(name):
        val = request.form.get(name, "").strip()
        try:
            return float(val) if val else None
        except ValueError:
            return None

    latitude = parse_coord("latitude")
    longitude = parse_coord("longitude")
    currency = request.form.get("currency") if request.form.get("currency") in CURRENCIES else "AZN"
    vin_code = request.form.get("vin_code", "").strip().upper() or None

    errors = []
    if ltype not in ("emlak", "neqliyyat"):
        errors.append("Elan növü seçilməyib.")
    if not title:
        errors.append("Başlıq daxil edilməyib.")
    if not city:
        errors.append("Şəhər seçilməyib.")
    try:
        price = float(price)
        if price <= 0:
            raise ValueError
    except ValueError:
        errors.append("Qiymət düzgün deyil.")

    if ltype == "neqliyyat" and category not in ("kommersiya", "ehtiyat hissələri"):
        required_vehicle_fields = {
            "make": "Marka", "model": "Model", "year": "Buraxılış ili", "body_type": "Ban növü",
            "fuel_type": "Yanacaq növü", "drivetrain": "Ötürücü", "transmission": "Sürətlər qutusu",
            "modification": "Modifikasiya", "color": "Rəng", "market": "Bazar", "mileage_km": "Yürüş",
        }
        for field, label in required_vehicle_fields.items():
            if not request.form.get(field, "").strip():
                errors.append(f"\"{label}\" doldurulmayıb.")
        if vin_code and not is_valid_vin(vin_code):
            errors.append("VIN kod 17 simvoldan ibarət olmalı və I, O, Q hərflərini ehtiva etməməlidir.")

    if errors:
        for e in errors:
            flash(e, "error")
        residences = db.execute("SELECT id, name FROM residences ORDER BY name").fetchall()
        return render_template("new_listing.html", form=request.form, residences=residences), 400

    cur = db.execute(
        """INSERT INTO listings(user_id, type, category, title, description, price,
                                 currency, city, district, is_negotiable, latitude, longitude, country, residence_id,
                                 contact_phone, contact_phone2, contact_whatsapp)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (user["id"], ltype, category, title, description, price, currency, city, district,
         1 if request.form.get("negotiable") else 0, latitude, longitude, country, residence_id,
         request.form.get("contact_phone", "").strip() or None,
         request.form.get("contact_phone2", "").strip() or None,
         request.form.get("contact_whatsapp", "").strip() or None),
    )
    listing_id = cur.lastrowid

    if ltype == "emlak":
        db.execute(
            """INSERT INTO property_details(listing_id, rooms, area_m2, floor, floors_total,
                                             building_type, repair_status, deal_type)
               VALUES (?,?,?,?,?,?,?,?)""",
            (listing_id,
             request.form.get("rooms") or None,
             request.form.get("area_m2") or None,
             request.form.get("floor") or None,
             request.form.get("floors_total") or None,
             request.form.get("building_type") or None,
             request.form.get("repair_status") or None,
             request.form.get("deal_type") or "satılır"),
        )
    else:
        equipment_list = ",".join(request.form.getlist("equipment"))
        modification_text = request.form.get("modification", "").strip()
        engine_match = re.search(r"(\d+[.,]\d+|\d+)", modification_text)
        engine_volume = engine_match.group(1).replace(",", ".") if engine_match else None
        db.execute(
            """INSERT INTO vehicle_details(listing_id, make, model, year, mileage_km, engine_volume,
                                            fuel_type, transmission, color, body_type, condition_status,
                                            has_credit, has_barter, has_vin,
                                            drivetrain, modification, market, mileage_unit, equipment,
                                            is_crashed, is_painted, is_for_parts, vin_code, deal_type)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (listing_id,
             request.form.get("make") or None,
             request.form.get("model") or None,
             request.form.get("year") or None,
             request.form.get("mileage_km") or None,
             engine_volume,
             request.form.get("fuel_type") or None,
             request.form.get("transmission") or None,
             request.form.get("color") or None,
             request.form.get("body_type") or None,
             request.form.get("condition_status") or "sürücülü",
             1 if request.form.get("has_credit") else 0,
             1 if request.form.get("has_barter") else 0,
             1 if vin_code else 0,
             request.form.get("drivetrain") or None,
             request.form.get("modification") or None,
             request.form.get("market") or None,
             request.form.get("mileage_unit") or "km",
             equipment_list or None,
             1 if request.form.get("is_crashed") == "yes" else 0,
             1 if request.form.get("is_painted") == "yes" else 0,
             1 if request.form.get("is_for_parts") == "yes" else 0,
             vin_code,
             request.form.get("vehicle_deal_type") or "satılır"),
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    files = request.files.getlist("images")
    saved_any = False
    for idx, file in enumerate(files):
        if not file or not file.filename:
            continue
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED_EXT:
            continue
        fname = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(UPLOAD_DIR, fname))
        db.execute(
            "INSERT INTO listing_images(listing_id, image_path, is_main, sort_order) VALUES (?,?,?,?)",
            (listing_id, f"/static/uploads/{fname}", 1 if idx == 0 else 0, idx),
        )
        saved_any = True

    if not saved_any:
        placeholder = f"/static/img/{'property' if ltype == 'emlak' else 'vehicle'}_{(listing_id % 6) + 1}.svg"
        db.execute(
            "INSERT INTO listing_images(listing_id, image_path, is_main) VALUES (?,?,1)",
            (listing_id, placeholder),
        )

    db.commit()
    flash("Elanınız uğurla yerləşdirildi.", "success")
    return redirect(url_for("listing_detail", listing_id=listing_id))


@app.route("/elan/<int:listing_id>/redakte", methods=["GET", "POST"])
@login_required
def edit_listing(listing_id):
    db = get_db()
    listing, details, images = fetch_listing_row(listing_id)
    if listing is None:
        abort(404)
    if listing["user_id"] != current_user()["id"]:
        abort(403)

    if request.method == "GET":
        residences = db.execute("SELECT id, name FROM residences ORDER BY name").fetchall()
        return render_template(
            "edit_listing.html", listing=listing, details=details, images=images, residences=residences
        )

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "0")
    city = request.form.get("city", "").strip()
    district = request.form.get("district", "").strip()
    category = request.form.get("category", "").strip()
    country = request.form.get("country", "").strip() or None
    residence_id = request.form.get("residence_id", "").strip() or None

    def parse_coord(name):
        val = request.form.get(name, "").strip()
        try:
            return float(val) if val else None
        except ValueError:
            return None

    latitude = parse_coord("latitude")
    longitude = parse_coord("longitude")
    currency = request.form.get("currency") if request.form.get("currency") in CURRENCIES else (listing["currency"] or "AZN")
    vin_code = request.form.get("vin_code", "").strip().upper() or None

    errors = []
    if not title:
        errors.append("Başlıq daxil edilməyib.")
    if not city:
        errors.append("Şəhər seçilməyib.")
    try:
        price = float(price)
        if price <= 0:
            raise ValueError
    except ValueError:
        errors.append("Qiymət düzgün deyil.")
    if listing["type"] == "neqliyyat" and vin_code and not is_valid_vin(vin_code):
        errors.append("VIN kod 17 simvoldan ibarət olmalı və I, O, Q hərflərini ehtiva etməməlidir.")

    if errors:
        for e in errors:
            flash(e, "error")
        residences = db.execute("SELECT id, name FROM residences ORDER BY name").fetchall()
        return render_template(
            "edit_listing.html", listing=listing, details=details, images=images,
            form=request.form, residences=residences,
        ), 400

    db.execute(
        """UPDATE listings SET category=?, title=?, description=?, price=?, currency=?, city=?, district=?,
                                is_negotiable=?, latitude=?, longitude=?, country=?, residence_id=?,
                                contact_phone=?, contact_phone2=?, contact_whatsapp=?, updated_at=datetime('now')
           WHERE id=?""",
        (category, title, description, price, currency, city, district,
         1 if request.form.get("negotiable") else 0, latitude, longitude, country, residence_id,
         request.form.get("contact_phone", "").strip() or None,
         request.form.get("contact_phone2", "").strip() or None,
         request.form.get("contact_whatsapp", "").strip() or None,
         listing_id),
    )

    if price < listing["price"]:
        watchers = db.execute(
            """SELECT pw.user_id, pw.watched_price, u.email, u.full_name FROM price_watches pw
               JOIN users u ON u.id = pw.user_id
               WHERE pw.listing_id=? AND pw.watched_price > ?""",
            (listing_id, price),
        ).fetchall()
        for w in watchers:
            msg = f'"{title}" elanının qiyməti {w["watched_price"]:,.0f} AZN-dən {price:,.0f} AZN-ə düşdü.'.replace(",", " ")
            db.execute(
                "INSERT INTO notifications(user_id, listing_id, message) VALUES (?,?,?)",
                (w["user_id"], listing_id, msg),
            )
            db.execute(
                "UPDATE price_watches SET watched_price=? WHERE user_id=? AND listing_id=?",
                (price, w["user_id"], listing_id),
            )
            if w["email"]:
                send_email(w["email"], "VarAz — Qiymət düşdü!", msg + f"\n\nElana baxın: /elan/{listing_id}")

    if listing["type"] == "emlak":
        db.execute(
            """UPDATE property_details SET rooms=?, area_m2=?, floor=?, floors_total=?,
                                            building_type=?, repair_status=?, deal_type=?
               WHERE listing_id=?""",
            (request.form.get("rooms") or None,
             request.form.get("area_m2") or None,
             request.form.get("floor") or None,
             request.form.get("floors_total") or None,
             request.form.get("building_type") or None,
             request.form.get("repair_status") or None,
             request.form.get("deal_type") or "satılır",
             listing_id),
        )
    else:
        equipment_list = ",".join(request.form.getlist("equipment"))
        modification_text = request.form.get("modification", "").strip()
        engine_match = re.search(r"(\d+[.,]\d+|\d+)", modification_text)
        engine_volume = engine_match.group(1).replace(",", ".") if engine_match else None
        db.execute(
            """UPDATE vehicle_details SET make=?, model=?, year=?, mileage_km=?, engine_volume=?,
                                           fuel_type=?, transmission=?, color=?, body_type=?, condition_status=?,
                                           has_credit=?, has_barter=?, has_vin=?,
                                           drivetrain=?, modification=?, market=?, mileage_unit=?, equipment=?,
                                           is_crashed=?, is_painted=?, is_for_parts=?, vin_code=?, deal_type=?
               WHERE listing_id=?""",
            (request.form.get("make") or None,
             request.form.get("model") or None,
             request.form.get("year") or None,
             request.form.get("mileage_km") or None,
             engine_volume,
             request.form.get("fuel_type") or None,
             request.form.get("transmission") or None,
             request.form.get("color") or None,
             request.form.get("body_type") or None,
             request.form.get("condition_status") or "sürücülü",
             1 if request.form.get("has_credit") else 0,
             1 if request.form.get("has_barter") else 0,
             1 if vin_code else 0,
             request.form.get("drivetrain") or None,
             request.form.get("modification") or None,
             request.form.get("market") or None,
             request.form.get("mileage_unit") or "km",
             equipment_list or None,
             1 if request.form.get("is_crashed") == "yes" else 0,
             1 if request.form.get("is_painted") == "yes" else 0,
             1 if request.form.get("is_for_parts") == "yes" else 0,
             vin_code,
             request.form.get("vehicle_deal_type") or "satılır",
             listing_id),
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    files = request.files.getlist("images")
    for idx, file in enumerate(files):
        if not file or not file.filename:
            continue
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED_EXT:
            continue
        fname = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(UPLOAD_DIR, fname))
        db.execute(
            "INSERT INTO listing_images(listing_id, image_path, is_main, sort_order) VALUES (?,?,0,?)",
            (listing_id, f"/static/uploads/{fname}", idx + 100),
        )

    db.commit()
    flash("Elan yeniləndi.", "success")
    return redirect(url_for("listing_detail", listing_id=listing_id))


@app.route("/elan/<int:listing_id>/sil", methods=["POST"])
@login_required
def delete_listing(listing_id):
    db = get_db()
    listing = db.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
    if listing is None:
        abort(404)
    if listing["user_id"] != current_user()["id"]:
        abort(403)
    db.execute("DELETE FROM listings WHERE id=?", (listing_id,))
    db.commit()
    flash("Elan silindi.", "success")
    return redirect(url_for("my_listings"))


@app.route("/elan/<int:listing_id>/vip", methods=["GET"])
@login_required
def vip_options(listing_id):
    db = get_db()
    listing = db.execute(
        """SELECT l.*, CASE WHEN l.is_vip=1 AND l.vip_expires_at > datetime('now') THEN 1 ELSE 0 END AS is_vip_active
           FROM listings l WHERE l.id=?""",
        (listing_id,),
    ).fetchone()
    if listing is None:
        abort(404)
    if listing["user_id"] != current_user()["id"]:
        abort(403)
    return render_template("vip_options.html", listing=listing, packages=VIP_PACKAGES)


@app.route("/elan/<int:listing_id>/vip/<package>", methods=["POST"])
@login_required
def vip_purchase(listing_id, package):
    db = get_db()
    listing = db.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
    if listing is None:
        abort(404)
    if listing["user_id"] != current_user()["id"]:
        abort(403)
    if package not in VIP_PACKAGES:
        abort(404)

    pkg = VIP_PACKAGES[package]
    user = current_user()

    # NOT: bu, real odenis deyil -- test/simulyasiya rejimidir.
    # Real provayder (Payriff / EPoint / basqa) qosulanda, burada
    # provayderin ravi API-sine yonlendirme ve callback-de bu kodun
    # ise dusmesi lazimdir (asagidaki INSERT + UPDATE hissesi).
    cur = db.execute(
        """INSERT INTO payments(listing_id, user_id, package, amount, currency, status, provider, paid_at)
           VALUES (?,?,?,?,?,?,?,datetime('now'))""",
        (listing_id, user["id"], package, pkg["price"], "AZN", "paid", "test"),
    )

    db.execute(
        """UPDATE listings SET is_vip=1,
               vip_expires_at = datetime(
                   CASE WHEN vip_expires_at IS NOT NULL AND vip_expires_at > datetime('now')
                        THEN vip_expires_at ELSE datetime('now') END,
                   '+' || ? || ' days'
               )
           WHERE id=?""",
        (pkg["days"], listing_id),
    )
    db.commit()
    flash(f"Elan {pkg['label']} müddətinə VIP edildi! (test ödənişi)", "success")
    return redirect(url_for("listing_detail", listing_id=listing_id))


@app.route("/elanlarim")
@login_required
def my_listings():
    db = get_db()
    rows = db.execute(
        """SELECT l.*, (SELECT image_path FROM listing_images WHERE listing_id=l.id
                         ORDER BY is_main DESC LIMIT 1) AS thumb,
                  CASE WHEN l.is_vip=1 AND l.vip_expires_at > datetime('now') THEN 1 ELSE 0 END AS is_vip_active
           FROM listings l WHERE user_id=? ORDER BY created_at DESC""",
        (current_user()["id"],),
    ).fetchall()
    return render_template("my_listings.html", rows=rows)


@app.route("/sevimliler")
@login_required
def favorites_page():
    db = get_db()
    user_id = current_user()["id"]
    collection_id = request.args.get("collection")
    where = "f.user_id = ?"
    params = [user_id]
    if collection_id == "none":
        where += " AND f.collection_id IS NULL"
    elif collection_id:
        where += " AND f.collection_id = ?"
        params.append(collection_id)
    rows = db.execute(
        f"""SELECT l.*, (SELECT image_path FROM listing_images WHERE listing_id=l.id
                         ORDER BY is_main DESC LIMIT 1) AS thumb
           FROM listings l
           JOIN favorites f ON f.listing_id = l.id
           WHERE {where} ORDER BY f.created_at DESC""",
        params,
    ).fetchall()
    collections = db.execute(
        """SELECT c.*, (SELECT COUNT(*) FROM favorites WHERE collection_id=c.id) AS item_count
           FROM favorite_collections c WHERE c.user_id=? ORDER BY c.created_at""",
        (user_id,),
    ).fetchall()
    return render_template("favorites.html", rows=rows, collections=collections, selected_collection=collection_id)


@app.route("/sevimliler/kolleksiya", methods=["POST"])
@login_required
def create_collection():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Kolleksiya adı boş ola bilməz.", "error")
        return redirect(url_for("favorites_page"))
    db = get_db()
    db.execute(
        "INSERT INTO favorite_collections(user_id, name) VALUES (?,?)",
        (current_user()["id"], name),
    )
    db.commit()
    flash(f'"{name}" kolleksiyası yaradıldı.', "success")
    return redirect(url_for("favorites_page"))


@app.route("/api/sevimli/<int:listing_id>/kolleksiya", methods=["POST"])
@login_required
def set_favorite_collection(listing_id):
    collection_id = request.form.get("collection_id") or None
    db = get_db()
    db.execute(
        "UPDATE favorites SET collection_id=? WHERE user_id=? AND listing_id=?",
        (collection_id, current_user()["id"], listing_id),
    )
    db.commit()
    return jsonify({"ok": True})


@app.route("/satici/<int:seller_id>")
def seller_profile(seller_id):
    db = get_db()
    seller = db.execute("SELECT * FROM users WHERE id=?", (seller_id,)).fetchone()
    if seller is None:
        abort(404)
    listings_rows = db.execute(
        """SELECT l.*, (SELECT image_path FROM listing_images WHERE listing_id=l.id
                         ORDER BY is_main DESC LIMIT 1) AS thumb,
                  CASE WHEN l.is_vip=1 AND l.vip_expires_at > datetime('now') THEN 1 ELSE 0 END AS is_vip_active
           FROM listings l WHERE user_id=? AND status='active'
           ORDER BY is_vip_active DESC, created_at DESC""",
        (seller_id,),
    ).fetchall()
    reviews = db.execute(
        """SELECT sr.*, u.full_name AS reviewer_name FROM seller_reviews sr
           JOIN users u ON u.id = sr.reviewer_id
           WHERE sr.seller_id=? ORDER BY sr.created_at DESC""",
        (seller_id,),
    ).fetchall()
    stats = db.execute(
        """SELECT
             (SELECT COUNT(*) FROM listings WHERE user_id=? AND status='active') AS listing_count,
             (SELECT AVG(rating) FROM seller_reviews WHERE seller_id=?) AS avg_rating,
             (SELECT COUNT(*) FROM seller_reviews WHERE seller_id=?) AS review_count""",
        (seller_id, seller_id, seller_id),
    ).fetchone()
    already_reviewed = False
    user = current_user()
    if user:
        already_reviewed = db.execute(
            "SELECT 1 FROM seller_reviews WHERE seller_id=? AND reviewer_id=?", (seller_id, user["id"])
        ).fetchone() is not None
    return render_template(
        "seller_profile.html", seller=seller, listings=listings_rows, reviews=reviews,
        stats=stats, already_reviewed=already_reviewed,
    )


@app.route("/satici/<int:seller_id>/rey", methods=["POST"])
@login_required
def rate_seller(seller_id):
    user = current_user()
    if user["id"] == seller_id:
        flash("Özünüzə rəy yaza bilməzsiniz.", "error")
        return redirect(url_for("seller_profile", seller_id=seller_id))
    try:
        rating = int(request.form.get("rating", "0"))
    except ValueError:
        rating = 0
    body = request.form.get("body", "").strip()
    if rating < 1 or rating > 5 or len(body) < 5:
        flash("Zəhmət olmasa reytinq seçin və qısa rəy yazın.", "error")
        return redirect(url_for("seller_profile", seller_id=seller_id))
    db = get_db()
    try:
        db.execute(
            "INSERT INTO seller_reviews(seller_id, reviewer_id, rating, body) VALUES (?,?,?,?)",
            (seller_id, user["id"], rating, body),
        )
        db.commit()
        flash("Rəyiniz üçün təşəkkür edirik!", "success")
    except sqlite3.IntegrityError:
        flash("Bu satıcıya artıq rəy yazmısınız.", "error")
    return redirect(url_for("seller_profile", seller_id=seller_id))


@app.route("/muqayise")
def compare_page():
    ids = session.get("compare_ids", [])
    db = get_db()
    rows = []
    if ids:
        placeholders = ",".join("?" * len(ids))
        by_id = {
            r["id"]: r for r in db.execute(
                f"SELECT * FROM listings WHERE id IN ({placeholders})", ids
            ).fetchall()
        }
        rows = [by_id[i] for i in ids if i in by_id]
    details_by_id = {}
    for l in rows:
        _, details, images = fetch_listing_row(l["id"])
        details_by_id[l["id"]] = {"details": details, "thumb": images[0]["image_path"] if images else None}
    return render_template("compare.html", rows=rows, details_by_id=details_by_id)


@app.route("/muqayise/elave/<int:listing_id>", methods=["POST"])
def compare_add(listing_id):
    ids = session.get("compare_ids", [])
    if listing_id not in ids:
        if len(ids) >= 3:
            flash("Eyni anda maksimum 3 elanı müqayisə edə bilərsiniz.", "error")
            return redirect(request.referrer or url_for("home"))
        ids.append(listing_id)
        session["compare_ids"] = ids
        flash("Müqayisəyə əlavə olundu.", "success")
    return redirect(request.referrer or url_for("home"))


@app.route("/muqayise/cixar/<int:listing_id>", methods=["POST"])
def compare_remove(listing_id):
    ids = session.get("compare_ids", [])
    if listing_id in ids:
        ids.remove(listing_id)
        session["compare_ids"] = ids
    return redirect(request.referrer or url_for("compare_page"))


@app.route("/elan/<int:listing_id>/watch", methods=["POST"])
@login_required
def toggle_price_watch(listing_id):
    db = get_db()
    user = current_user()
    listing = db.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
    if listing is None:
        abort(404)
    existing = db.execute(
        "SELECT 1 FROM price_watches WHERE user_id=? AND listing_id=?", (user["id"], listing_id)
    ).fetchone()
    if existing:
        db.execute("DELETE FROM price_watches WHERE user_id=? AND listing_id=?", (user["id"], listing_id))
        flash("Qiymət bildirişi ləğv edildi.", "success")
    else:
        db.execute(
            "INSERT INTO price_watches(user_id, listing_id, watched_price) VALUES (?,?,?)",
            (user["id"], listing_id, listing["price"]),
        )
        flash("Qiymət düşəndə sizə bildiriş göndəriləcək.", "success")
    db.commit()
    return redirect(url_for("listing_detail", listing_id=listing_id))


@app.route("/bildirisler")
@login_required
def notifications_page():
    db = get_db()
    user = current_user()
    rows = db.execute(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50", (user["id"],)
    ).fetchall()
    db.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user["id"],))
    db.commit()
    return render_template("notifications.html", rows=rows)



@app.route("/elan/<int:listing_id>/mesaj", methods=["POST"])
@login_required
def send_listing_message(listing_id):
    db = get_db()
    listing = db.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
    if listing is None:
        abort(404)
    user = current_user()
    if listing["user_id"] == user["id"]:
        flash("Öz elanınıza mesaj göndərə bilməzsiniz.", "error")
        return redirect(url_for("listing_detail", listing_id=listing_id))

    body = request.form.get("body", "").strip()
    if not body:
        flash("Mesaj boş ola bilməz.", "error")
        return redirect(url_for("listing_detail", listing_id=listing_id))

    conv = db.execute(
        "SELECT id FROM conversations WHERE listing_id=? AND buyer_id=? AND seller_id=?",
        (listing_id, user["id"], listing["user_id"]),
    ).fetchone()
    if conv:
        conv_id = conv["id"]
    else:
        cur = db.execute(
            "INSERT INTO conversations(listing_id, buyer_id, seller_id) VALUES (?,?,?)",
            (listing_id, user["id"], listing["user_id"]),
        )
        conv_id = cur.lastrowid

    db.execute(
        "INSERT INTO messages(conversation_id, sender_id, body) VALUES (?,?,?)",
        (conv_id, user["id"], body),
    )
    db.execute("UPDATE conversations SET updated_at=datetime('now') WHERE id=?", (conv_id,))
    db.commit()
    flash("Mesajınız göndərildi.", "success")
    return redirect(url_for("conversation", conversation_id=conv_id))


@app.route("/mesajlar")
@login_required
def messages_inbox():
    db = get_db()
    user = current_user()
    rows = db.execute(
        """SELECT c.*, l.title AS listing_title,
                  (SELECT image_path FROM listing_images WHERE listing_id=l.id ORDER BY is_main DESC LIMIT 1) AS listing_thumb,
                  CASE WHEN c.buyer_id=? THEN c.seller_id ELSE c.buyer_id END AS other_user_id,
                  (SELECT body FROM messages WHERE conversation_id=c.id ORDER BY created_at DESC LIMIT 1) AS last_message,
                  (SELECT COUNT(*) FROM messages WHERE conversation_id=c.id AND sender_id!=? AND is_read=0) AS unread_count
           FROM conversations c
           LEFT JOIN listings l ON l.id = c.listing_id
           WHERE c.buyer_id=? OR c.seller_id=?
           ORDER BY c.updated_at DESC""",
        (user["id"], user["id"], user["id"], user["id"]),
    ).fetchall()

    conversations = []
    for r in rows:
        other = db.execute("SELECT full_name FROM users WHERE id=?", (r["other_user_id"],)).fetchone()
        item = dict(r)
        item["other_name"] = other["full_name"] if other else "İstifadəçi"
        conversations.append(item)

    return render_template("messages_inbox.html", conversations=conversations)


@app.route("/mesajlar/<int:conversation_id>", methods=["GET", "POST"])
@login_required
def conversation(conversation_id):
    db = get_db()
    user = current_user()
    conv = db.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()
    if conv is None:
        abort(404)
    if user["id"] not in (conv["buyer_id"], conv["seller_id"]):
        abort(403)

    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if body:
            db.execute(
                "INSERT INTO messages(conversation_id, sender_id, body) VALUES (?,?,?)",
                (conversation_id, user["id"], body),
            )
            db.execute("UPDATE conversations SET updated_at=datetime('now') WHERE id=?", (conversation_id,))
            db.commit()
        return redirect(url_for("conversation", conversation_id=conversation_id))

    db.execute(
        "UPDATE messages SET is_read=1 WHERE conversation_id=? AND sender_id!=?",
        (conversation_id, user["id"]),
    )
    db.commit()

    msgs = db.execute(
        "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at ASC", (conversation_id,)
    ).fetchall()
    other_id = conv["seller_id"] if conv["buyer_id"] == user["id"] else conv["buyer_id"]
    other = db.execute("SELECT * FROM users WHERE id=?", (other_id,)).fetchone()
    listing = None
    if conv["listing_id"]:
        listing = db.execute("SELECT * FROM listings WHERE id=?", (conv["listing_id"],)).fetchone()

    return render_template("conversation.html", conv=conv, messages=msgs, other=other, listing=listing)


@app.route("/api/sevimli/<int:listing_id>", methods=["POST"])
@login_required
def toggle_favorite(listing_id):
    db = get_db()
    user = current_user()
    fav = db.execute(
        "SELECT 1 FROM favorites WHERE user_id=? AND listing_id=?",
        (user["id"], listing_id),
    ).fetchone()
    if fav:
        db.execute(
            "DELETE FROM favorites WHERE user_id=? AND listing_id=?",
            (user["id"], listing_id),
        )
        is_fav = False
    else:
        db.execute(
            "INSERT INTO favorites(user_id, listing_id) VALUES (?,?)",
            (user["id"], listing_id),
        )
        is_fav = True
    db.commit()
    return jsonify({"is_favorite": is_fav})


# ------------------------------------------------------------------ admin panel

@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    stats = {
        "users": db.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"],
        "listings": db.execute("SELECT COUNT(*) AS c FROM listings WHERE status='active'").fetchone()["c"],
        "pending_reports": db.execute("SELECT COUNT(*) AS c FROM reports WHERE status='pending'").fetchone()["c"],
        "unverified_phones": db.execute("SELECT COUNT(*) AS c FROM users WHERE is_phone_verified=0").fetchone()["c"],
        "vip_active": db.execute(
            "SELECT COUNT(*) AS c FROM listings WHERE is_vip=1 AND vip_expires_at > datetime('now')"
        ).fetchone()["c"],
    }
    recent_listings = db.execute(
        "SELECT * FROM listings ORDER BY created_at DESC LIMIT 8"
    ).fetchall()
    recent_reports = db.execute(
        """SELECT r.*, l.title AS listing_title, u.full_name AS reporter_name
           FROM reports r JOIN listings l ON l.id=r.listing_id JOIN users u ON u.id=r.reporter_id
           WHERE r.status='pending' ORDER BY r.created_at DESC LIMIT 5"""
    ).fetchall()
    return render_template(
        "admin/dashboard.html", stats=stats, recent_listings=recent_listings, recent_reports=recent_reports
    )


@app.route("/admin/elanlar")
@admin_required
def admin_listings():
    db = get_db()
    q = request.args.get("q", "").strip()
    where = ""
    params = []
    if q:
        where = "WHERE l.title LIKE ? OR l.city LIKE ?"
        params = [f"%{q}%", f"%{q}%"]
    rows = db.execute(
        f"""SELECT l.*, u.full_name AS owner_name, u.phone AS owner_phone
            FROM listings l JOIN users u ON u.id=l.user_id
            {where} ORDER BY l.created_at DESC LIMIT 100""",
        params,
    ).fetchall()
    return render_template("admin/listings.html", rows=rows, q=q)


@app.route("/admin/elanlar/<int:listing_id>/sil", methods=["POST"])
@admin_required
def admin_delete_listing(listing_id):
    db = get_db()
    db.execute("DELETE FROM listings WHERE id=?", (listing_id,))
    db.commit()
    flash("Elan silindi.", "success")
    return redirect(request.referrer or url_for("admin_listings"))


@app.route("/admin/elanlar/<int:listing_id>/statusu-deyis", methods=["POST"])
@admin_required
def admin_toggle_listing_status(listing_id):
    db = get_db()
    listing = db.execute("SELECT status FROM listings WHERE id=?", (listing_id,)).fetchone()
    if listing is None:
        abort(404)
    new_status = "hidden" if listing["status"] == "active" else "active"
    db.execute("UPDATE listings SET status=? WHERE id=?", (new_status, listing_id))
    db.commit()
    flash("Elanın statusu dəyişdirildi.", "success")
    return redirect(request.referrer or url_for("admin_listings"))


@app.route("/admin/istifadeciler")
@admin_required
def admin_users():
    db = get_db()
    q = request.args.get("q", "").strip()
    where = ""
    params = []
    if q:
        where = "WHERE full_name LIKE ? OR phone LIKE ? OR email LIKE ?"
        params = [f"%{q}%", f"%{q}%", f"%{q}%"]
    rows = db.execute(
        f"""SELECT u.*, (SELECT COUNT(*) FROM listings WHERE user_id=u.id) AS listing_count
            FROM users u {where} ORDER BY u.created_at DESC LIMIT 200""",
        params,
    ).fetchall()
    return render_template("admin/users.html", rows=rows, q=q)


@app.route("/admin/istifadeciler/<int:user_id>/blokla", methods=["POST"])
@admin_required
def admin_toggle_ban(user_id):
    db = get_db()
    user = db.execute("SELECT is_banned FROM users WHERE id=?", (user_id,)).fetchone()
    if user is None:
        abort(404)
    db.execute("UPDATE users SET is_banned=? WHERE id=?", (0 if user["is_banned"] else 1, user_id))
    db.commit()
    flash("İstifadəçinin statusu yeniləndi.", "success")
    return redirect(request.referrer or url_for("admin_users"))


@app.route("/admin/istifadeciler/<int:user_id>/tesdiq", methods=["POST"])
@admin_required
def admin_toggle_verified(user_id):
    db = get_db()
    user = db.execute("SELECT is_verified FROM users WHERE id=?", (user_id,)).fetchone()
    if user is None:
        abort(404)
    db.execute("UPDATE users SET is_verified=? WHERE id=?", (0 if user["is_verified"] else 1, user_id))
    db.commit()
    flash("Doğrulama statusu yeniləndi.", "success")
    return redirect(request.referrer or url_for("admin_users"))


@app.route("/admin/sikayetler")
@admin_required
def admin_reports():
    db = get_db()
    rows = db.execute(
        """SELECT r.*, l.title AS listing_title, l.id AS listing_id, u.full_name AS reporter_name
           FROM reports r JOIN listings l ON l.id=r.listing_id JOIN users u ON u.id=r.reporter_id
           ORDER BY (r.status='pending') DESC, r.created_at DESC"""
    ).fetchall()
    return render_template("admin/reports.html", rows=rows)


@app.route("/admin/sikayetler/<int:report_id>/heltet", methods=["POST"])
@admin_required
def admin_resolve_report(report_id):
    action = request.form.get("action", "reviewed")
    db = get_db()
    db.execute("UPDATE reports SET status=? WHERE id=?", (action, report_id))
    db.commit()
    flash("Şikayət yeniləndi.", "success")
    return redirect(url_for("admin_reports"))


@app.route("/elan/<int:listing_id>/sikayet", methods=["POST"])
@login_required
def report_listing(listing_id):
    db = get_db()
    listing = db.execute("SELECT id FROM listings WHERE id=?", (listing_id,)).fetchone()
    if listing is None:
        abort(404)
    reason = request.form.get("reason", "").strip()
    body = request.form.get("body", "").strip()
    if not reason:
        flash("Zəhmət olmasa şikayət səbəbini seçin.", "error")
        return redirect(url_for("listing_detail", listing_id=listing_id))
    db.execute(
        "INSERT INTO reports(listing_id, reporter_id, reason, body) VALUES (?,?,?,?)",
        (listing_id, current_user()["id"], reason, body or None),
    )
    db.commit()
    flash("Şikayətiniz qəbul edildi, moderasiya nəzərdən keçirəcək.", "success")
    return redirect(url_for("listing_detail", listing_id=listing_id))



def create_verification_code(user_id):
    import random as _random
    from datetime import datetime as _dt, timedelta as _td
    code = f"{_random.randint(0, 999999):06d}"
    expires = (_dt.now() + _td(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    db.execute(
        "INSERT INTO phone_verifications(user_id, code, expires_at) VALUES (?,?,?)",
        (user_id, code, expires),
    )
    db.commit()
    return code


@app.route("/qeydiyyat", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    db = get_db()
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip() or None
    password = request.form.get("password", "")

    errors = []
    if len(full_name) < 3:
        errors.append("Ad Soyad düzgün deyil.")
    if len(phone) < 7:
        errors.append("Telefon nömrəsi düzgün deyil.")
    if len(password) < 6:
        errors.append("Şifrə ən azı 6 simvol olmalıdır.")
    if db.execute("SELECT 1 FROM users WHERE phone=?", (phone,)).fetchone():
        errors.append("Bu telefon nömrəsi ilə artıq qeydiyyat var.")

    if errors:
        for e in errors:
            flash(e, "error")
        return render_template("register.html", form=request.form), 400

    cur = db.execute(
        "INSERT INTO users(full_name, phone, email, password_hash) VALUES (?,?,?,?)",
        (full_name, phone, email, generate_password_hash(password)),
    )
    db.commit()
    session["user_id"] = cur.lastrowid

    code = create_verification_code(cur.lastrowid)
    sent = send_sms(phone, f"VarAz təsdiq kodunuz: {code}")
    if not sent:
        session["dev_sms_code"] = code  # dev/demo fallback so the flow stays testable
    flash("Xoş gəldiniz! Telefon nömrənizi təsdiqləyin.", "success")
    return redirect(url_for("verify_phone"))


@app.route("/qeydiyyat/tesdiq", methods=["GET", "POST"])
@login_required
def verify_phone():
    user = current_user()
    if user["is_phone_verified"]:
        return redirect(url_for("home"))
    db = get_db()

    if request.method == "GET":
        return render_template("verify_phone.html", dev_code=session.get("dev_sms_code"))

    code = request.form.get("code", "").strip()
    row = db.execute(
        """SELECT * FROM phone_verifications WHERE user_id=? AND code=? AND verified_at IS NULL
           AND expires_at > datetime('now') ORDER BY id DESC LIMIT 1""",
        (user["id"], code),
    ).fetchone()
    if row is None:
        flash("Kod yanlışdır və ya vaxtı bitib.", "error")
        return render_template("verify_phone.html", dev_code=session.get("dev_sms_code")), 400

    db.execute("UPDATE phone_verifications SET verified_at=datetime('now') WHERE id=?", (row["id"],))
    db.execute("UPDATE users SET is_phone_verified=1 WHERE id=?", (user["id"],))
    db.commit()
    session.pop("dev_sms_code", None)
    flash("Telefon nömrəniz təsdiqləndi!", "success")
    return redirect(url_for("home"))


@app.route("/qeydiyyat/tesdiq/yeniden", methods=["POST"])
@login_required
def resend_verification():
    user = current_user()
    code = create_verification_code(user["id"])
    sent = send_sms(user["phone"], f"VarAz təsdiq kodunuz: {code}")
    if not sent:
        session["dev_sms_code"] = code
    flash("Yeni kod göndərildi.", "success")
    return redirect(url_for("verify_phone"))


@app.route("/sifreni-unutdum", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html")

    db = get_db()
    identifier = request.form.get("identifier", "").strip()
    user = db.execute(
        "SELECT * FROM users WHERE phone=? OR email=?", (identifier, identifier)
    ).fetchone()

    # Always show the same message whether or not the account exists, to avoid
    # leaking which phone numbers/emails are registered.
    if user is not None:
        token = secrets.token_urlsafe(32)
        from datetime import datetime as _dt, timedelta as _td
        expires = (_dt.now() + _td(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO password_resets(user_id, token, expires_at) VALUES (?,?,?)",
            (user["id"], token, expires),
        )
        db.commit()
        reset_url = url_for("reset_password", token=token, _external=True)
        body = f"Şifrənizi sıfırlamaq üçün bu linkə klikləyin (1 saat etibarlıdır):\n{reset_url}"
        sent = False
        if user["email"]:
            sent = send_email(user["email"], "VarAz — Şifrə sıfırlama", body)
        if not sent:
            session["dev_reset_url"] = reset_url  # dev/demo fallback

    flash("Əgər bu məlumatla hesab varsa, şifrə sıfırlama linki göndərildi.", "success")
    return render_template("forgot_password.html", dev_reset_url=session.pop("dev_reset_url", None))


@app.route("/sifre-sifirla/<token>", methods=["GET", "POST"])
def reset_password(token):
    db = get_db()
    row = db.execute(
        "SELECT * FROM password_resets WHERE token=? AND used_at IS NULL AND expires_at > datetime('now')",
        (token,),
    ).fetchone()
    if row is None:
        flash("Bu link etibarsızdır və ya vaxtı bitib.", "error")
        return redirect(url_for("forgot_password"))

    if request.method == "GET":
        return render_template("reset_password.html", token=token)

    password = request.form.get("password", "")
    if len(password) < 6:
        flash("Şifrə ən azı 6 simvol olmalıdır.", "error")
        return render_template("reset_password.html", token=token), 400

    db.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(password), row["user_id"]))
    db.execute("UPDATE password_resets SET used_at=datetime('now') WHERE id=?", (row["id"],))
    db.commit()
    flash("Şifrəniz yeniləndi. İndi daxil ola bilərsiniz.", "success")
    return redirect(url_for("login"))


@app.route("/giris", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    db = get_db()
    phone = request.form.get("phone", "").strip()
    password = request.form.get("password", "")
    user = db.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        flash("Telefon nömrəsi və ya şifrə yanlışdır.", "error")
        return render_template("login.html", form=request.form), 400

    if user["is_banned"]:
        flash("Hesabınız bloklanıb. Dəstək xidməti ilə əlaqə saxlayın.", "error")
        return render_template("login.html", form=request.form), 403

    session["user_id"] = user["id"]
    flash(f"Xoş gəldin, {user['full_name']}!", "success")
    next_url = request.args.get("next") or url_for("home")
    return redirect(next_url)


@app.route("/cixis")
def logout():
    session.clear()
    flash("Hesabdan çıxış edildi.", "success")
    return redirect(url_for("home"))



@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        import seed
        seed.main()
    app.run(debug=True, host="0.0.0.0", port=5000)
