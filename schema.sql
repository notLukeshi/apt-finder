-- Websites being scraped
CREATE TABLE websites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    base_url TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Target locations (work, school, etc.)
CREATE TABLE targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    arrival_time TEXT,  -- e.g., "09:00"
    arrival_day TEXT,   -- e.g., "Monday"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, address)
);

-- Apartment listings
CREATE TABLE apartments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT,  -- ID from the source website (if available)
    name TEXT NOT NULL,
    price REAL NOT NULL,
    website_id INTEGER NOT NULL,
    url TEXT,  -- Link to apartment detail page
    image_url TEXT,  -- Preview image URL
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (website_id) REFERENCES websites(id),
    UNIQUE(external_id, website_id)  -- Prevent duplicates from same source
);

-- Apartment addresses (separate table for flexibility)
CREATE TABLE addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment_id INTEGER NOT NULL UNIQUE,
    address_text TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    geocoded_at TIMESTAMP,
    FOREIGN KEY (apartment_id) REFERENCES apartments(id) ON DELETE CASCADE
);

-- Distance calculations
CREATE TABLE distances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    distance_km REAL,
    time_minutes INTEGER NOT NULL,  -- The minimum time across all modes
    time_transit_walk_minutes INTEGER,   -- WALK + TRANSIT time (walk to station, take train)
    time_transit_bike_minutes INTEGER,   -- BICYCLE + TRANSIT time (bike to station, take train)
    time_bike_minutes INTEGER,           -- BICYCLE only time (direct cycling)
    selected_mode TEXT,  -- Which was fastest: 'transit_walk', 'transit_bike', or 'bike'
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (apartment_id) REFERENCES apartments(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES targets(id) ON DELETE CASCADE,
    UNIQUE(apartment_id, target_id)  -- One distance record per apartment-target pair
);

-- Indexes for performance
CREATE INDEX idx_apartments_price ON apartments(price);
CREATE INDEX idx_apartments_website ON apartments(website_id);
CREATE INDEX idx_distances_apartment ON distances(apartment_id);
CREATE INDEX idx_distances_target ON distances(target_id);
CREATE INDEX idx_distances_time ON distances(time_minutes);