-- VarAz veritabani sxemi

DROP TABLE IF EXISTS favorites;
DROP TABLE IF EXISTS listing_images;
DROP TABLE IF EXISTS vehicle_details;
DROP TABLE IF EXISTS property_details;
DROP TABLE IF EXISTS listings;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS cities;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    is_verified INTEGER NOT NULL DEFAULT 0,
    is_admin INTEGER NOT NULL DEFAULT 0,
    is_phone_verified INTEGER NOT NULL DEFAULT 0,
    is_banned INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE cities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    type TEXT NOT NULL CHECK(type IN ('emlak','neqliyyat')),
    category TEXT NOT NULL,          -- e.g. 'menzil','heyet evi','ofis','torpaq' | 'minik','suv','moto'
    title TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'AZN',
    city TEXT NOT NULL,
    district TEXT,
    address TEXT,
    country TEXT,                      -- 'AZ' (default/domestic) | 'AE' | 'TR' | ... for Xaricde evler
    residence_id INTEGER REFERENCES residences(id) ON DELETE SET NULL,  -- optional link to a yaşayış kompleksi
    is_negotiable INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',   -- active | sold | archived
    views INTEGER NOT NULL DEFAULT 0,
    latitude REAL,
    longitude REAL,
    is_vip INTEGER NOT NULL DEFAULT 0,
    vip_expires_at TEXT,
    contact_phone TEXT,
    contact_phone2 TEXT,
    contact_whatsapp TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE property_details (
    listing_id INTEGER PRIMARY KEY REFERENCES listings(id) ON DELETE CASCADE,
    rooms INTEGER,
    area_m2 REAL,
    floor INTEGER,
    floors_total INTEGER,
    building_type TEXT,      -- kohne tikili / yeni tikili
    repair_status TEXT,      -- temirli / temirsiz / ortaq
    deal_type TEXT NOT NULL DEFAULT 'satilir'  -- satilir / kiraye
);

CREATE TABLE vehicle_details (
    listing_id INTEGER PRIMARY KEY REFERENCES listings(id) ON DELETE CASCADE,
    make TEXT,
    model TEXT,
    year INTEGER,
    mileage_km INTEGER,
    engine_volume REAL,
    fuel_type TEXT,      -- benzin/dizel/qaz/hibrid/elektro
    transmission TEXT,   -- manual/avtomat
    color TEXT,
    body_type TEXT,      -- sedan/offroader/hetchbek...
    condition_status TEXT DEFAULT 'suruculu', -- suruculu / vurulmayib / qeza
    has_credit INTEGER NOT NULL DEFAULT 0,
    has_barter INTEGER NOT NULL DEFAULT 0,
    has_vin INTEGER NOT NULL DEFAULT 0,
    drivetrain TEXT,          -- tam / arxa / ön
    modification TEXT,        -- serbest metn: '2.0 Turbo', '3.5 V6'...
    market TEXT,              -- Amerika/Avropa/Dubay/Koreya/Rusiya/Resmi diler/Yaponiya/Cin/Diger
    mileage_unit TEXT NOT NULL DEFAULT 'km',  -- km / mil
    equipment TEXT,           -- vergul ile ayrilmis techizat siyahisi
    is_crashed INTEGER NOT NULL DEFAULT 0,    -- vuruğu var?
    is_painted INTEGER NOT NULL DEFAULT 0,    -- rənglənib?
    is_for_parts INTEGER NOT NULL DEFAULT 0,  -- qezali / ehtiyat hisse ucun?
    vin_code TEXT,
    deal_type TEXT NOT NULL DEFAULT 'satılır'  -- satılır | kirayə
);

CREATE TABLE listing_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    image_path TEXT NOT NULL,
    is_main INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE favorite_collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE favorites (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    collection_id INTEGER REFERENCES favorite_collections(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, listing_id)
);

CREATE TABLE construction_companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    logo_path TEXT,
    cover_path TEXT,
    about TEXT,
    website TEXT,
    phone TEXT,
    city TEXT,
    founded_year INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE residences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    developer TEXT,
    company_id INTEGER REFERENCES construction_companies(id) ON DELETE SET NULL,
    city TEXT NOT NULL,
    district TEXT,
    address TEXT,
    price_from REAL,
    deadline TEXT,          -- e.g. '2026', '2027'
    rating REAL DEFAULT 4.7,
    description TEXT,
    amenities TEXT,         -- comma-separated list
    contact_name TEXT,
    contact_phone TEXT,
    image_path TEXT,        -- main/cover image (used on cards)
    logo_path TEXT,         -- project logo (small badge)
    accent TEXT NOT NULL DEFAULT 'teal'   -- teal | brass | ink (card accent color)
);

CREATE TABLE residence_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    residence_id INTEGER NOT NULL REFERENCES residences(id) ON DELETE CASCADE,
    image_path TEXT NOT NULL,
    is_main INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE residence_units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    residence_id INTEGER NOT NULL REFERENCES residences(id) ON DELETE CASCADE,
    rooms INTEGER,
    area_m2 REAL,
    price REAL,
    status TEXT NOT NULL DEFAULT 'satılır'  -- satılır | satılıb
);

CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER REFERENCES listings(id) ON DELETE CASCADE,
    buyer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    seller_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(listing_id, buyer_id, seller_id)
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_read INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_conversations_buyer ON conversations(buyer_id);
CREATE INDEX idx_conversations_seller ON conversations(seller_id);

CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    package TEXT NOT NULL,                   -- '3','7','30' (gun sayi)
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'AZN',
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | paid | failed
    provider TEXT NOT NULL DEFAULT 'test',   -- test | million | payriff | epoint | ...
    gateway_ref TEXT,                        -- bankin sifariş/tranzaksiya ID-si (callback yoxlaması üçün)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    paid_at TEXT
);

CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE seller_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reviewer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(seller_id, reviewer_id)
);

CREATE TABLE price_watches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    watched_price REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, listing_id)
);

CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    listing_id INTEGER REFERENCES listings(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE search_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE phone_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    verified_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE password_resets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    reporter_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    body TEXT,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | reviewed | dismissed
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_listings_type ON listings(type);
CREATE INDEX idx_listings_city ON listings(city);
CREATE INDEX idx_listings_price ON listings(price);
CREATE INDEX idx_listings_status ON listings(status);
CREATE INDEX idx_price_watches_listing ON price_watches(listing_id);
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_reports_status ON reports(status);
