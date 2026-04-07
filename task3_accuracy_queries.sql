-- Task 3.2 #1: Given a region code, list all cities.
SELECT DISTINCT c.city_name
FROM city c
WHERE c.region_code = :region_code
ORDER BY c.city_name;

-- Task 3.2 #2: Given a city name, list all airports and its iata_code.
SELECT a.airport_name, a.iata_code
FROM airport a
JOIN city c ON c.city_id = a.city_id
WHERE c.city_name = :city_name
ORDER BY a.airport_name;

-- Task 3.2 #3: Given a region code, list all airlines (airline_code, airline_name).
SELECT al.airline_code, al.airline_name
FROM airline al
WHERE al.region_code = :region_code
ORDER BY al.airline_code;

-- Task 3.2 #4: Given departure iata_code and arrival iata_code, list all flights.
SELECT
    f.flight_number,
    src_city.city_name AS source_city,
    src_region.region_name AS source_region,
    dst_city.city_name AS destination_city,
    dst_region.region_name AS destination_region
FROM flight f
JOIN airport src_air ON src_air.airport_id = f.source_airport_id
JOIN city src_city ON src_city.city_id = src_air.city_id
JOIN region src_region ON src_region.region_code = src_city.region_code
JOIN airport dst_air ON dst_air.airport_id = f.destination_airport_id
JOIN city dst_city ON dst_city.city_id = dst_air.city_id
JOIN region dst_region ON dst_region.region_code = dst_city.region_code
WHERE src_air.iata_code = :source_iata_code
  AND dst_air.iata_code = :destination_iata_code
ORDER BY f.flight_number;

-- Task 3.2 #5: Given date + departure city + arrival city, list tickets
-- ordered by ascending economy price.
SELECT
    f.departure_time_local AS departure_time,
    f.arrival_time_local AS arrive_time,
    f.arrival_day_offset,
    src_air.airport_name AS departure_airport_name,
    dst_air.airport_name AS arrival_airport_name,
    ti.economy_price
FROM ticket_inventory ti
JOIN flight f ON f.flight_id = ti.flight_id
JOIN airport src_air ON src_air.airport_id = f.source_airport_id
JOIN city src_city ON src_city.city_id = src_air.city_id
JOIN airport dst_air ON dst_air.airport_id = f.destination_airport_id
JOIN city dst_city ON dst_city.city_id = dst_air.city_id
WHERE ti.flight_date = :flight_date
  AND src_city.city_name = :departure_city
  AND dst_city.city_name = :arrival_city
ORDER BY ti.economy_price ASC;

-- Task 3.2 #6: Continue #5 and add departure_time after xxx
-- and arrival_time before xxx (same-day arrival).
SELECT
    f.departure_time_local AS departure_time,
    f.arrival_time_local AS arrive_time,
    f.arrival_day_offset,
    src_air.airport_name AS departure_airport_name,
    dst_air.airport_name AS arrival_airport_name,
    ti.economy_price
FROM ticket_inventory ti
JOIN flight f ON f.flight_id = ti.flight_id
JOIN airport src_air ON src_air.airport_id = f.source_airport_id
JOIN city src_city ON src_city.city_id = src_air.city_id
JOIN airport dst_air ON dst_air.airport_id = f.destination_airport_id
JOIN city dst_city ON dst_city.city_id = dst_air.city_id
WHERE ti.flight_date = :flight_date
  AND src_city.city_name = :departure_city
  AND dst_city.city_name = :arrival_city
  AND f.departure_time_local >= :departure_time_after
  AND f.arrival_day_offset = 0
  AND f.arrival_time_local <= :arrival_time_before
ORDER BY ti.economy_price ASC;
