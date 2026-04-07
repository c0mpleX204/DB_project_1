BEGIN;

CREATE TABLE IF NOT EXISTS region (
    region_code VARCHAR(8) PRIMARY KEY,
    region_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS city (
    city_id BIGSERIAL PRIMARY KEY,
    city_name TEXT NOT NULL,
    region_code VARCHAR(8) NOT NULL REFERENCES region(region_code),
    UNIQUE(city_name, region_code)
);

CREATE TABLE IF NOT EXISTS airport (
    airport_id BIGSERIAL PRIMARY KEY,
    source_airport_id BIGINT UNIQUE,
    airport_name TEXT NOT NULL,
    iata_code CHAR(3) NOT NULL UNIQUE,
    city_id BIGINT NOT NULL REFERENCES city(city_id),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    altitude INTEGER,
    timezone_offset INTEGER,
    timezone_dst VARCHAR(8),
    timezone_region TEXT
);

CREATE TABLE IF NOT EXISTS airline (
    airline_id BIGSERIAL PRIMARY KEY,
    source_airline_id BIGINT UNIQUE,
    airline_code VARCHAR(8) NOT NULL UNIQUE,
    airline_name TEXT NOT NULL,
    region_code VARCHAR(8) NOT NULL REFERENCES region(region_code)
);

CREATE TABLE IF NOT EXISTS passenger (
    passenger_id BIGSERIAL PRIMARY KEY,
    source_passenger_id BIGINT UNIQUE,
    passenger_name TEXT NOT NULL,
    age INTEGER CHECK (age >= 0),
    gender VARCHAR(16),
    mobile_number VARCHAR(32) UNIQUE
);

CREATE TABLE IF NOT EXISTS flight (
    flight_id BIGSERIAL PRIMARY KEY,
    flight_number VARCHAR(16) NOT NULL UNIQUE,
    airline_id BIGINT NOT NULL REFERENCES airline(airline_id),
    source_airport_id BIGINT NOT NULL REFERENCES airport(airport_id),
    destination_airport_id BIGINT NOT NULL REFERENCES airport(airport_id),
    departure_time_local TIME NOT NULL,
    arrival_time_local TIME NOT NULL,
    arrival_day_offset SMALLINT NOT NULL DEFAULT 0,
    business_capacity INTEGER NOT NULL CHECK (business_capacity >= 0),
    economy_capacity INTEGER NOT NULL CHECK (economy_capacity >= 0),
    CHECK (source_airport_id <> destination_airport_id)
);

CREATE TABLE IF NOT EXISTS ticket_inventory (
    ticket_id BIGSERIAL PRIMARY KEY,
    flight_id BIGINT NOT NULL REFERENCES flight(flight_id),
    flight_date DATE NOT NULL,
    business_price NUMERIC(10,2) NOT NULL CHECK (business_price >= 0),
    business_remain INTEGER NOT NULL CHECK (business_remain >= 0),
    economy_price NUMERIC(10,2) NOT NULL CHECK (economy_price >= 0),
    economy_remain INTEGER NOT NULL CHECK (economy_remain >= 0),
    UNIQUE(flight_id, flight_date)
);

CREATE TABLE IF NOT EXISTS ticket_order (
    order_id BIGSERIAL PRIMARY KEY,
    passenger_id BIGINT NOT NULL REFERENCES passenger(passenger_id),
    ticket_id BIGINT NOT NULL REFERENCES ticket_inventory(ticket_id),
    cabin_class VARCHAR(16) NOT NULL CHECK (cabin_class IN ('economy', 'business')),
    unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
    booked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(16) NOT NULL DEFAULT 'booked' CHECK (status IN ('booked', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_airport_iata_code ON airport(iata_code);
CREATE INDEX IF NOT EXISTS idx_city_name ON city(city_name);
CREATE INDEX IF NOT EXISTS idx_airline_code ON airline(airline_code);
CREATE INDEX IF NOT EXISTS idx_ticket_flight_date ON ticket_inventory(flight_date);
CREATE INDEX IF NOT EXISTS idx_ticket_arrival_lookup ON flight(arrival_time_local, arrival_day_offset);
CREATE INDEX IF NOT EXISTS idx_order_passenger_status ON ticket_order(passenger_id, status);

COMMIT;
