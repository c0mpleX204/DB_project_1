#!/usr/bin/env python3
import argparse
import datetime as dt
from decimal import Decimal

import psycopg2


def get_conn(args):
    return psycopg2.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        dbname=args.database,
    )


def parse_date(text: str) -> dt.date:
    return dt.datetime.strptime(text, "%Y-%m-%d").date()


def parse_time(text: str) -> dt.time:
    return dt.datetime.strptime(text, "%H:%M").time()


def generate_tickets(conn, start_date: dt.date, end_date: dt.date):
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH latest_ticket AS (
                SELECT DISTINCT ON (ti.flight_id)
                    ti.flight_id,
                    ti.business_price,
                    ti.economy_price
                FROM ticket_inventory ti
                ORDER BY ti.flight_id, ti.flight_date DESC
            )
            SELECT f.flight_id, f.business_capacity, f.economy_capacity,
                   lt.business_price, lt.economy_price
            FROM flight f
            LEFT JOIN latest_ticket lt ON lt.flight_id = f.flight_id
            """
        )
        flights = cur.fetchall()

        added = 0
        day_count = (end_date - start_date).days + 1
        for flight_id, biz_cap, eco_cap, biz_price, eco_price in flights:
            if biz_price is None:
                biz_price = Decimal("1000")
            if eco_price is None:
                eco_price = Decimal("300")

            for i in range(day_count):
                d = start_date + dt.timedelta(days=i)
                weekday_factor = Decimal("1.00") + Decimal((d.weekday() % 3) * 5) / Decimal("100")
                b = (Decimal(biz_price) * weekday_factor).quantize(Decimal("0.01"))
                e = (Decimal(eco_price) * weekday_factor).quantize(Decimal("0.01"))
                cur.execute(
                    """
                    INSERT INTO ticket_inventory(
                        flight_id, flight_date, business_price, business_remain, economy_price, economy_remain
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (flight_id, flight_date) DO NOTHING
                    """,
                    (flight_id, d, b, biz_cap, e, eco_cap),
                )
                added += cur.rowcount

    conn.commit()
    print(f"Finish Generate {added} rows tickets info.")


def search_tickets(conn, departure_city, arrival_city, date_, airline=None, departure_time=None, arrival_time=None):
    query = """
        SELECT
            ti.ticket_id,
            f.flight_number,
            al.airline_code,
            al.airline_name,
            src_city.city_name AS source_city,
            src_air.iata_code AS source_iata,
            f.departure_time_local,
            dst_city.city_name AS destination_city,
            dst_air.iata_code AS destination_iata,
            f.arrival_time_local,
            f.arrival_day_offset,
            ti.flight_date,
            ti.business_price,
            ti.business_remain,
            ti.economy_price,
            ti.economy_remain
        FROM ticket_inventory ti
        JOIN flight f ON f.flight_id = ti.flight_id
        JOIN airline al ON al.airline_id = f.airline_id
        JOIN airport src_air ON src_air.airport_id = f.source_airport_id
        JOIN city src_city ON src_city.city_id = src_air.city_id
        JOIN airport dst_air ON dst_air.airport_id = f.destination_airport_id
        JOIN city dst_city ON dst_city.city_id = dst_air.city_id
        WHERE src_city.city_name = %s
          AND dst_city.city_name = %s
          AND ti.flight_date = %s
    """
    params = [departure_city, arrival_city, date_]

    if airline:
        query += " AND (al.airline_code = %s OR al.airline_name = %s)"
        params.extend([airline, airline])
    if departure_time:
        query += " AND f.departure_time_local >= %s"
        params.append(departure_time)
    if arrival_time:
        query += " AND f.arrival_time_local <= %s AND f.arrival_day_offset = 0"
        params.append(arrival_time)

    query += " ORDER BY ti.economy_price ASC, ti.ticket_id ASC"

    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    if not rows:
        print("No ticket found.")
        return

    for r in rows:
        print(
            f"ticket_id={r[0]} flight={r[1]} airline={r[2]}({r[3]}) "
            f"{r[4]}({r[5]})->{r[7]}({r[8]}) dep={r[6]} arr={r[9]}(+{r[10]}) "
            f"date={r[11]} eco={r[14]}/{r[15]} biz={r[12]}/{r[13]}"
        )


def book_ticket(conn, passenger_id: int, ticket_id: int, cabin_class: str):
    if cabin_class not in {"economy", "business"}:
        raise ValueError("cabin_class must be economy or business")

    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM passenger WHERE passenger_id = %s", (passenger_id,))
            if not cur.fetchone():
                raise ValueError(f"passenger_id {passenger_id} not found")

            if cabin_class == "economy":
                cur.execute(
                    """
                    UPDATE ticket_inventory
                    SET economy_remain = economy_remain - 1
                    WHERE ticket_id = %s AND economy_remain > 0
                    RETURNING economy_price
                    """,
                    (ticket_id,),
                )
            else:
                cur.execute(
                    """
                    UPDATE ticket_inventory
                    SET business_remain = business_remain - 1
                    WHERE ticket_id = %s AND business_remain > 0
                    RETURNING business_price
                    """,
                    (ticket_id,),
                )

            row = cur.fetchone()
            if not row:
                raise ValueError("ticket not found or no seat available")
            price = row[0]

            cur.execute(
                """
                INSERT INTO ticket_order(passenger_id, ticket_id, cabin_class, unit_price)
                VALUES (%s, %s, %s, %s)
                RETURNING order_id, booked_at
                """,
                (passenger_id, ticket_id, cabin_class, price),
            )
            order_id, booked_at = cur.fetchone()

    print(f"Booked successfully. order_id={order_id}, booked_at={booked_at}")


def list_orders(conn, passenger_id: int):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                o.order_id,
                o.status,
                o.cabin_class,
                o.unit_price,
                o.booked_at,
                ti.flight_date,
                f.flight_number,
                src_city.city_name,
                dst_city.city_name
            FROM ticket_order o
            JOIN ticket_inventory ti ON ti.ticket_id = o.ticket_id
            JOIN flight f ON f.flight_id = ti.flight_id
            JOIN airport src_air ON src_air.airport_id = f.source_airport_id
            JOIN city src_city ON src_city.city_id = src_air.city_id
            JOIN airport dst_air ON dst_air.airport_id = f.destination_airport_id
            JOIN city dst_city ON dst_city.city_id = dst_air.city_id
            WHERE o.passenger_id = %s
            ORDER BY o.order_id DESC
            """,
            (passenger_id,),
        )
        rows = cur.fetchall()

    if not rows:
        print("No orders found.")
        return

    for r in rows:
        print(
            f"order_id={r[0]} status={r[1]} class={r[2]} price={r[3]} booked_at={r[4]} "
            f"flight={r[6]} {r[7]}->{r[8]} date={r[5]}"
        )


def cancel_order(conn, passenger_id: int, order_id: int):
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT o.status, o.cabin_class, o.ticket_id
                FROM ticket_order o
                WHERE o.order_id = %s AND o.passenger_id = %s
                FOR UPDATE
                """,
                (order_id, passenger_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("order not found")
            status, cabin_class, ticket_id = row
            if status == "cancelled":
                raise ValueError("order already cancelled")

            cur.execute(
                "UPDATE ticket_order SET status = 'cancelled' WHERE order_id = %s",
                (order_id,),
            )
            if cabin_class == "economy":
                cur.execute(
                    "UPDATE ticket_inventory SET economy_remain = economy_remain + 1 WHERE ticket_id = %s",
                    (ticket_id,),
                )
            else:
                cur.execute(
                    "UPDATE ticket_inventory SET business_remain = business_remain + 1 WHERE ticket_id = %s",
                    (ticket_id,),
                )

    print(f"Cancelled order {order_id}.")


def list_cities_by_region(conn, region_code: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT c.city_name
            FROM city c
            WHERE UPPER(c.region_code) = UPPER(%s)
            ORDER BY c.city_name
            """,
            (region_code,),
        )
        rows = cur.fetchall()
    for (name,) in rows:
        print(name)


def list_airports_by_city(conn, city_name: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.airport_name, a.iata_code
            FROM airport a
            JOIN city c ON c.city_id = a.city_id
            WHERE c.city_name = %s
            ORDER BY a.airport_name
            """,
            (city_name,),
        )
        rows = cur.fetchall()
    for airport, iata in rows:
        print(f"{airport} ({iata})")


def list_airlines_by_region(conn, region_code: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT airline_code, airline_name
            FROM airline
            WHERE UPPER(region_code) = UPPER(%s)
            ORDER BY airline_code
            """,
            (region_code,),
        )
        rows = cur.fetchall()
    for code, name in rows:
        print(f"{code} - {name}")


def list_flights_between_iata(conn, source_code: str, destination_code: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                f.flight_number,
                src_city.city_name,
                src_region.region_name,
                dst_city.city_name,
                dst_region.region_name
            FROM flight f
            JOIN airport src_air ON src_air.airport_id = f.source_airport_id
            JOIN city src_city ON src_city.city_id = src_air.city_id
            JOIN region src_region ON src_region.region_code = src_city.region_code
            JOIN airport dst_air ON dst_air.airport_id = f.destination_airport_id
            JOIN city dst_city ON dst_city.city_id = dst_air.city_id
            JOIN region dst_region ON dst_region.region_code = dst_city.region_code
            WHERE src_air.iata_code = %s AND dst_air.iata_code = %s
            ORDER BY f.flight_number
            """,
            (source_code.upper(), destination_code.upper()),
        )
        rows = cur.fetchall()

    for r in rows:
        print(f"{r[0]} | {r[1]} ({r[2]}) -> {r[3]} ({r[4]})")


def list_tickets_by_date_city(conn, date_, departure_city: str, arrival_city: str):
    search_tickets(
        conn,
        departure_city=departure_city,
        arrival_city=arrival_city,
        date_=date_,
        airline=None,
        departure_time=None,
        arrival_time=None,
    )


def list_tickets_by_time_window(
    conn,
    date_,
    departure_city: str,
    arrival_city: str,
    departure_time_after,
    arrival_time_before,
):
    search_tickets(
        conn,
        departure_city=departure_city,
        arrival_city=arrival_city,
        date_=date_,
        airline=None,
        departure_time=departure_time_after,
        arrival_time=arrival_time_before,
    )


def main():
    parser = argparse.ArgumentParser(description="CS307 DB Project CLI")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="postgres")
    parser.add_argument("--database", default="db_project_1")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("generate", help="Generate ticket inventory for date range")
    p.add_argument("--start-date", required=True)
    p.add_argument("--end-date", required=True)

    p = sub.add_parser("search", help="Search tickets")
    p.add_argument("--departure-city", required=True)
    p.add_argument("--arrival-city", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--airline")
    p.add_argument("--departure-time")
    p.add_argument("--arrival-time")

    p = sub.add_parser("book", help="Book one ticket")
    p.add_argument("--passenger-id", type=int, required=True)
    p.add_argument("--ticket-id", type=int, required=True)
    p.add_argument("--cabin-class", choices=["economy", "business"], required=True)

    p = sub.add_parser("orders", help="List passenger orders")
    p.add_argument("--passenger-id", type=int, required=True)

    p = sub.add_parser("cancel", help="Cancel one order")
    p.add_argument("--passenger-id", type=int, required=True)
    p.add_argument("--order-id", type=int, required=True)

    p = sub.add_parser("cities-by-region", help="Task 3.2 query #1")
    p.add_argument("--region-code", required=True)

    p = sub.add_parser("airports-by-city", help="Task 3.2 query #2")
    p.add_argument("--city", required=True)

    p = sub.add_parser("airlines-by-region", help="Task 3.2 query #3")
    p.add_argument("--region-code", required=True)

    p = sub.add_parser("flights-by-iata", help="Task 3.2 query #4")
    p.add_argument("--source", required=True)
    p.add_argument("--destination", required=True)

    p = sub.add_parser("tickets-by-date-city", help="Task 3.2 query #5")
    p.add_argument("--date", required=True)
    p.add_argument("--departure-city", required=True)
    p.add_argument("--arrival-city", required=True)

    p = sub.add_parser("tickets-by-time-window", help="Task 3.2 query #6")
    p.add_argument("--date", required=True)
    p.add_argument("--departure-city", required=True)
    p.add_argument("--arrival-city", required=True)
    p.add_argument("--departure-time-after", required=True)
    p.add_argument("--arrival-time-before", required=True)

    args = parser.parse_args()

    conn = get_conn(args)
    try:
        if args.cmd == "generate":
            generate_tickets(conn, parse_date(args.start_date), parse_date(args.end_date))
        elif args.cmd == "search":
            search_tickets(
                conn,
                args.departure_city,
                args.arrival_city,
                parse_date(args.date),
                args.airline,
                parse_time(args.departure_time) if args.departure_time else None,
                parse_time(args.arrival_time) if args.arrival_time else None,
            )
        elif args.cmd == "book":
            book_ticket(conn, args.passenger_id, args.ticket_id, args.cabin_class)
        elif args.cmd == "orders":
            list_orders(conn, args.passenger_id)
        elif args.cmd == "cancel":
            cancel_order(conn, args.passenger_id, args.order_id)
        elif args.cmd == "cities-by-region":
            list_cities_by_region(conn, args.region_code.upper())
        elif args.cmd == "airports-by-city":
            list_airports_by_city(conn, args.city)
        elif args.cmd == "airlines-by-region":
            list_airlines_by_region(conn, args.region_code.upper())
        elif args.cmd == "flights-by-iata":
            list_flights_between_iata(conn, args.source, args.destination)
        elif args.cmd == "tickets-by-date-city":
            list_tickets_by_date_city(
                conn,
                parse_date(args.date),
                args.departure_city,
                args.arrival_city,
            )
        elif args.cmd == "tickets-by-time-window":
            list_tickets_by_time_window(
                conn,
                parse_date(args.date),
                args.departure_city,
                args.arrival_city,
                parse_time(args.departure_time_after),
                parse_time(args.arrival_time_before),
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
