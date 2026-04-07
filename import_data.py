#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR = REPO_ROOT / "Archive"

REGION_ALIAS = {
    "Hong Kong SAR of China": "Hong Kong",
    "DRAGON": "Hong Kong",
    "United States": "United States of America",
    "UK": "United Kingdom",
}


def normalize_region(name: str) -> str:
    name = (name or "").strip()
    return REGION_ALIAS.get(name, name)


def clean_code(code: str) -> str:
    code = (code or "").strip().upper()
    return code


def parse_date(value: str) -> dt.date:
    return dt.datetime.strptime(value.strip(), "%Y/%m/%d").date()


def parse_time_with_offset(value: str):
    value = value.strip()
    m = re.fullmatch(r"(\d{1,2}:\d{2})(\(\+1\))?", value)
    if not m:
        raise ValueError(f"Unsupported time format: {value}")
    t = dt.datetime.strptime(m.group(1), "%H:%M").time()
    offset = 1 if m.group(2) else 0
    return t, offset


def load_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def build_region_codes(region_rows, airport_rows, airline_rows, ticket_rows):
    from_region_csv = {}
    used_codes = set()

    for row in region_rows:
        name = normalize_region(row["name"])
        code = clean_code(row["code"])
        if code:
            from_region_csv[name] = code
            used_codes.add(code)

    region_names = set(from_region_csv.keys())
    for row in airport_rows:
        region_names.add(normalize_region(row["region"]))
    for row in airline_rows:
        region_names.add(normalize_region(row["region"]))
    for row in ticket_rows:
        region_names.add(normalize_region(row["source_region"]))
        region_names.add(normalize_region(row["destination_region"]))

    region_names.discard("")
    code_map = dict(from_region_csv)

    for name in sorted(region_names):
        if name in code_map:
            continue
        letters = "".join(ch for ch in name.upper() if ch.isalpha())
        base = (letters[:2] if len(letters) >= 2 else (letters + "X")[:2]) or "XX"
        code = base
        i = 1
        while code in used_codes:
            code = f"{base[0]}{i % 10}"
            i += 1
        code_map[name] = code
        used_codes.add(code)

    return code_map


def ensure_schema(conn, schema_path: Path):
    with schema_path.open("r", encoding="utf-8") as f, conn.cursor() as cur:
        cur.execute(f.read())
    conn.commit()


def upsert_region(conn, region_code_map):
    rows = [(code, name) for name, code in region_code_map.items()]
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO region(region_code, region_name)
            VALUES %s
            ON CONFLICT (region_code)
            DO UPDATE SET region_name = EXCLUDED.region_name
            """,
            rows,
        )
    conn.commit()


def upsert_cities(conn, airport_rows, ticket_rows, region_code_map):
    city_keys = set()

    for row in airport_rows:
        region_name = normalize_region(row["region"])
        city = row["city"].strip()
        if city and region_name:
            city_keys.add((city, region_code_map[region_name]))

    for row in ticket_rows:
        s_city = row["source_city"].strip()
        d_city = row["destination_city"].strip()
        s_region = normalize_region(row["source_region"])
        d_region = normalize_region(row["destination_region"])
        if s_city and s_region:
            city_keys.add((s_city, region_code_map[s_region]))
        if d_city and d_region:
            city_keys.add((d_city, region_code_map[d_region]))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO city(city_name, region_code)
            VALUES %s
            ON CONFLICT (city_name, region_code) DO NOTHING
            """,
            sorted(city_keys),
        )
    conn.commit()


def fetch_city_map(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT city_id, city_name, region_code FROM city")
        return {(name, region): cid for cid, name, region in cur.fetchall()}


def upsert_airports(conn, airport_rows, ticket_rows, city_map, region_code_map):
    rows = []
    for r in airport_rows:
        region_name = normalize_region(r["region"])
        city_id = city_map[(r["city"].strip(), region_code_map[region_name])]
        rows.append(
            (
                int(r["id"]),
                r["name"].strip(),
                r["iata_code"].strip().upper(),
                city_id,
                float(r["latitude"]),
                float(r["longitude"]),
                int(r["altitude"]),
                int(r["timezone_offset"]),
                r["timezone_dst"].strip(),
                r["timezone_region"].strip(),
            )
        )

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO airport(
                source_airport_id, airport_name, iata_code, city_id,
                latitude, longitude, altitude, timezone_offset, timezone_dst, timezone_region
            ) VALUES %s
            ON CONFLICT (iata_code)
            DO UPDATE SET
                airport_name = EXCLUDED.airport_name,
                city_id = EXCLUDED.city_id,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                altitude = EXCLUDED.altitude,
                timezone_offset = EXCLUDED.timezone_offset,
                timezone_dst = EXCLUDED.timezone_dst,
                timezone_region = EXCLUDED.timezone_region
            """,
            rows,
        )

    known_iata = {row[2] for row in rows}
    missing_rows = []
    missing_iata = set()
    for r in ticket_rows:
        for city_key, region_key, iata_key in (
            ("source_city", "source_region", "source_code"),
            ("destination_city", "destination_region", "destination_code"),
        ):
            iata = r[iata_key].strip().upper()
            if not iata or iata in missing_iata:
                continue
            region_name = normalize_region(r[region_key])
            city = r[city_key].strip()
            if not city or not region_name:
                continue
            if iata in known_iata:
                continue
            city_id = city_map.get((city, region_code_map[region_name]))
            if not city_id:
                continue
            missing_iata.add(iata)
            missing_rows.append(
                (
                    None,
                    f"{city} {iata} Airport",
                    iata,
                    city_id,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                )
            )

    if missing_rows:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO airport(
                    source_airport_id, airport_name, iata_code, city_id,
                    latitude, longitude, altitude, timezone_offset, timezone_dst, timezone_region
                ) VALUES %s
                ON CONFLICT (iata_code) DO NOTHING
                """,
                missing_rows,
            )
    conn.commit()


def fetch_airport_iata_map(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT airport_id, iata_code FROM airport")
        return {iata: aid for aid, iata in cur.fetchall()}


def upsert_airlines(conn, airline_rows, region_code_map):
    rows = []
    for r in airline_rows:
        region_name = normalize_region(r["region"])
        rows.append(
            (
                int(r["id"]),
                r["code"].strip().upper(),
                r["name"].strip(),
                region_code_map[region_name],
            )
        )

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO airline(source_airline_id, airline_code, airline_name, region_code)
            VALUES %s
            ON CONFLICT (airline_code)
            DO UPDATE SET
                airline_name = EXCLUDED.airline_name,
                region_code = EXCLUDED.region_code
            """,
            rows,
        )
    conn.commit()


def fetch_airline_name_id_map(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT airline_id, airline_name FROM airline")
        return {name: aid for aid, name in cur.fetchall()}


def upsert_passengers(conn, passenger_rows):
    rows = [
        (
            int(r["id"]),
            r["name"].strip(),
            int(r["age"]),
            r["gender"].strip(),
            r["mobile_number"].strip(),
        )
        for r in passenger_rows
    ]

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO passenger(source_passenger_id, passenger_name, age, gender, mobile_number)
            VALUES %s
            ON CONFLICT (source_passenger_id)
            DO UPDATE SET
                passenger_name = EXCLUDED.passenger_name,
                age = EXCLUDED.age,
                gender = EXCLUDED.gender,
                mobile_number = EXCLUDED.mobile_number
            """,
            rows,
        )
    conn.commit()


def upsert_flights_and_tickets(conn, ticket_rows, airport_map, airline_name_map):
    per_flight = {}
    capacity = defaultdict(lambda: {"biz": 0, "eco": 0})

    for r in ticket_rows:
        number = r["number"].strip()
        dep_time, _ = parse_time_with_offset(r["departure_time"])
        arr_time, arr_offset = parse_time_with_offset(r["arrival_time"])

        airline_id = airline_name_map.get(r["airline_name"].strip())
        if not airline_id:
            continue

        flight_key = (
            number,
            airline_id,
            airport_map[r["source_code"].strip().upper()],
            airport_map[r["destination_code"].strip().upper()],
            dep_time,
            arr_time,
            arr_offset,
        )

        per_flight[number] = flight_key
        capacity[number]["biz"] = max(capacity[number]["biz"], int(r["business_remain"]))
        capacity[number]["eco"] = max(capacity[number]["eco"], int(r["economy_remain"]))

    flight_rows = [
        (
            fk[0],
            fk[1],
            fk[2],
            fk[3],
            fk[4],
            fk[5],
            fk[6],
            max(capacity[fk[0]]["biz"], 1),
            max(capacity[fk[0]]["eco"], 1),
        )
        for fk in per_flight.values()
    ]

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO flight(
                flight_number, airline_id, source_airport_id, destination_airport_id,
                departure_time_local, arrival_time_local, arrival_day_offset,
                business_capacity, economy_capacity
            ) VALUES %s
            ON CONFLICT (flight_number)
            DO UPDATE SET
                airline_id = EXCLUDED.airline_id,
                source_airport_id = EXCLUDED.source_airport_id,
                destination_airport_id = EXCLUDED.destination_airport_id,
                departure_time_local = EXCLUDED.departure_time_local,
                arrival_time_local = EXCLUDED.arrival_time_local,
                arrival_day_offset = EXCLUDED.arrival_day_offset,
                business_capacity = EXCLUDED.business_capacity,
                economy_capacity = EXCLUDED.economy_capacity
            """,
            flight_rows,
        )
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("SELECT flight_id, flight_number FROM flight")
        flight_id_map = {num: fid for fid, num in cur.fetchall()}

    ticket_values = []
    for r in ticket_rows:
        number = r["number"].strip()
        if number not in flight_id_map:
            continue
        ticket_values.append(
            (
                flight_id_map[number],
                parse_date(r["date"]),
                Decimal(r["business_price"]),
                int(r["business_remain"]),
                Decimal(r["economy_price"]),
                int(r["economy_remain"]),
            )
        )

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO ticket_inventory(
                flight_id, flight_date, business_price, business_remain, economy_price, economy_remain
            ) VALUES %s
            ON CONFLICT (flight_id, flight_date)
            DO UPDATE SET
                business_price = EXCLUDED.business_price,
                business_remain = EXCLUDED.business_remain,
                economy_price = EXCLUDED.economy_price,
                economy_remain = EXCLUDED.economy_remain
            """,
            ticket_values,
        )
    conn.commit()


def validate_counts(conn):
    checks = {
        "region": "SELECT COUNT(*) FROM region",
        "city": "SELECT COUNT(*) FROM city",
        "airport": "SELECT COUNT(*) FROM airport",
        "airline": "SELECT COUNT(*) FROM airline",
        "passenger": "SELECT COUNT(*) FROM passenger",
        "flight": "SELECT COUNT(*) FROM flight",
        "ticket_inventory": "SELECT COUNT(*) FROM ticket_inventory",
    }

    out = {}
    with conn.cursor() as cur:
        for key, q in checks.items():
            cur.execute(q)
            out[key] = cur.fetchone()[0]
    return out


def main():
    parser = argparse.ArgumentParser(description="Import CS307 project CSV data into PostgreSQL")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="postgres")
    parser.add_argument("--database", default="db_project_1")
    parser.add_argument("--schema", default=str(REPO_ROOT / "schema.sql"))
    args = parser.parse_args()

    conn = psycopg2.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        dbname=args.database,
    )

    try:
        ensure_schema(conn, Path(args.schema))

        region_rows = load_csv(DATA_DIR / "region.csv")
        airport_rows = load_csv(DATA_DIR / "airport.csv")
        airline_rows = load_csv(DATA_DIR / "airline.csv")
        passenger_rows = load_csv(DATA_DIR / "passenger.csv")
        ticket_rows = load_csv(DATA_DIR / "tickets.csv")

        region_code_map = build_region_codes(region_rows, airport_rows, airline_rows, ticket_rows)

        upsert_region(conn, region_code_map)
        upsert_cities(conn, airport_rows, ticket_rows, region_code_map)
        city_map = fetch_city_map(conn)

        upsert_airports(conn, airport_rows, ticket_rows, city_map, region_code_map)
        airport_map = fetch_airport_iata_map(conn)

        upsert_airlines(conn, airline_rows, region_code_map)
        airline_name_map = fetch_airline_name_id_map(conn)

        upsert_passengers(conn, passenger_rows)
        upsert_flights_and_tickets(conn, ticket_rows, airport_map, airline_name_map)

        counts = validate_counts(conn)
        print("Import completed. Row counts:")
        for k, v in counts.items():
            print(f"  {k}: {v}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
