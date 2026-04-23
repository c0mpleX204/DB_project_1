import datetime as dt

from app.repository.base import BaseRepository


class TicketRepository(BaseRepository):
	def list_city_suggestions(self, keyword: str, limit: int = 12):
		rows = self.fetch_all(
			"""
			SELECT DISTINCT city_name
			FROM city
			WHERE city_name ILIKE %s
			ORDER BY city_name
			LIMIT %s
			""",
			(f"{keyword}%", limit),
		)
		return [r[0] for r in rows]

	def list_inventory(self, limit: int, offset: int):
		rows = self.fetch_all(
			"""
			SELECT ticket_id, flight_id, flight_date,
				   business_price, business_remain,
				   economy_price, economy_remain
			FROM ticket_inventory
			ORDER BY ticket_id
			LIMIT %s OFFSET %s
			""",
			(limit, offset),
		)
		return [self._map_inventory_row(r) for r in rows]

	def get_inventory(self, ticket_id: int):
		row = self.fetch_one(
			"""
			SELECT ticket_id, flight_id, flight_date,
				   business_price, business_remain,
				   economy_price, economy_remain
			FROM ticket_inventory
			WHERE ticket_id = %s
			""",
			(ticket_id,),
		)
		return self._map_inventory_row(row) if row else None

	def create_inventory(self, payload):
		row = self.fetch_one(
			"""
			INSERT INTO ticket_inventory(
				flight_id, flight_date,
				business_price, business_remain,
				economy_price, economy_remain
			)
			VALUES (%s, %s, %s, %s, %s, %s)
			RETURNING ticket_id, flight_id, flight_date,
					  business_price, business_remain,
					  economy_price, economy_remain
			""",
			(
				payload.flight_id,
				payload.flight_date,
				payload.business_price,
				payload.business_remain,
				payload.economy_price,
				payload.economy_remain,
			),
		)
		return self._map_inventory_row(row)

	def update_inventory(self, ticket_id: int, payload):
		row = self.fetch_one(
			"""
			UPDATE ticket_inventory
			SET flight_id = %s,
				flight_date = %s,
				business_price = %s,
				business_remain = %s,
				economy_price = %s,
				economy_remain = %s
			WHERE ticket_id = %s
			RETURNING ticket_id, flight_id, flight_date,
					  business_price, business_remain,
					  economy_price, economy_remain
			""",
			(
				payload.flight_id,
				payload.flight_date,
				payload.business_price,
				payload.business_remain,
				payload.economy_price,
				payload.economy_remain,
				ticket_id,
			),
		)
		return self._map_inventory_row(row) if row else None

	def delete_inventory(self, ticket_id: int) -> bool:
		affected = self.execute(
			"DELETE FROM ticket_inventory WHERE ticket_id = %s",
			(ticket_id,),
		)
		return affected > 0

	def search_tickets(
		self,
		departure_city: str,
		arrival_city: str,
		date_,
		airline: str | None = None,
		source_iata: str | None = None,
		destination_iata: str | None = None,
		departure_time: dt.time | None = None,
		arrival_time: dt.time | None = None,
		limit: int = 200,
		offset: int = 0,
	):
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

		if source_iata:
			query += " AND src_air.iata_code = %s"
			params.append(source_iata.upper())

		if destination_iata:
			query += " AND dst_air.iata_code = %s"
			params.append(destination_iata.upper())

		if departure_time:
			query += " AND f.departure_time_local >= %s"
			params.append(departure_time)

		if arrival_time:
			query += " AND f.arrival_time_local <= %s AND f.arrival_day_offset = 0"
			params.append(arrival_time)

		query += " ORDER BY ti.economy_price ASC, ti.ticket_id ASC LIMIT %s OFFSET %s"
		params.extend([limit, offset])

		rows = self.fetch_all(query, tuple(params))
		return [self._map_search_row(r) for r in rows]

	def generate_inventory(self, start_date: dt.date, end_date: dt.date) -> int:
		row = self.fetch_one(
			"""
			WITH latest_ticket AS (
				SELECT DISTINCT ON (ti.flight_id)
					ti.flight_id,
					ti.business_price,
					ti.economy_price
				FROM ticket_inventory ti
				ORDER BY ti.flight_id, ti.flight_date DESC
			),
			date_series AS (
				SELECT generate_series(%s::date, %s::date, interval '1 day')::date AS flight_date
			),
			inserted AS (
				INSERT INTO ticket_inventory(
					flight_id,
					flight_date,
					business_price,
					business_remain,
					economy_price,
					economy_remain
				)
				SELECT
					f.flight_id,
					ds.flight_date,
					ROUND(
						(COALESCE(lt.business_price, 1000::numeric) * (
							1 + ((EXTRACT(DOW FROM ds.flight_date)::int %% 3) * 0.05)
						))::numeric,
						2
					),
					f.business_capacity,
					ROUND(
						(COALESCE(lt.economy_price, 300::numeric) * (
							1 + ((EXTRACT(DOW FROM ds.flight_date)::int %% 3) * 0.05)
						))::numeric,
						2
					),
					f.economy_capacity
				FROM flight f
				CROSS JOIN date_series ds
				LEFT JOIN latest_ticket lt ON lt.flight_id = f.flight_id
				ON CONFLICT (flight_id, flight_date) DO NOTHING
				RETURNING 1
			)
			SELECT COUNT(*) FROM inserted
			""",
			(start_date, end_date),
		)
		return int(row[0]) if row else 0

	@staticmethod
	def _map_inventory_row(row):
		return {
			"ticket_id": row[0],
			"flight_id": row[1],
			"flight_date": row[2],
			"business_price": float(row[3]),
			"business_remain": row[4],
			"economy_price": float(row[5]),
			"economy_remain": row[6],
		}

	@staticmethod
	def _map_search_row(row):
		return {
			"ticket_id": row[0],
			"flight_number": row[1],
			"airline_code": row[2],
			"airline_name": row[3],
			"source_city": row[4],
			"source_iata": row[5],
			"departure_time_local": row[6],
			"destination_city": row[7],
			"destination_iata": row[8],
			"arrival_time_local": row[9],
			"arrival_day_offset": row[10],
			"flight_date": row[11],
			"business_price": float(row[12]),
			"business_remain": row[13],
			"economy_price": float(row[14]),
			"economy_remain": row[15],
		}
