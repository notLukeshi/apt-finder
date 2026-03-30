-- Websites being scraped
CREATE TABLE IF NOT EXISTS websites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    base_url TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Target locations (work, school, etc.)
CREATE TABLE IF NOT EXISTS targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    arrival_time TEXT,
    arrival_day TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, address)
);

-- Apartment listings
CREATE TABLE IF NOT EXISTS apartments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    website_id INTEGER NOT NULL,
    url TEXT,
    image_url TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (website_id) REFERENCES websites(id),
    UNIQUE(external_id, website_id)
);

-- Apartment addresses
CREATE TABLE IF NOT EXISTS addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment_id INTEGER NOT NULL UNIQUE,
    address_text TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    geocoded_at TIMESTAMP,
    FOREIGN KEY (apartment_id) REFERENCES apartments(id) ON DELETE CASCADE
);

-- Distance calculations
CREATE TABLE IF NOT EXISTS distances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    distance_km REAL,
    time_minutes INTEGER NOT NULL,
    time_transit_walk_minutes INTEGER,
    time_transit_bike_minutes INTEGER,
    time_bike_minutes INTEGER,
    selected_mode TEXT,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (apartment_id) REFERENCES apartments(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES targets(id) ON DELETE CASCADE,
    UNIQUE(apartment_id, target_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_apartments_price ON apartments(price);
CREATE INDEX IF NOT EXISTS idx_apartments_website ON apartments(website_id);
CREATE INDEX IF NOT EXISTS idx_distances_apartment ON distances(apartment_id);
CREATE INDEX IF NOT EXISTS idx_distances_target ON distances(target_id);
CREATE INDEX IF NOT EXISTS idx_distances_time ON distances(time_minutes);
