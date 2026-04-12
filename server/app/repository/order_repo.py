from app.repository.base import BaseRepository


class OrderRepository(BaseRepository):
	def passenger_exists(self, passenger_id: int) -> bool:
		row = self.fetch_one(
			"SELECT 1 FROM passenger WHERE passenger_id = %s",
			(passenger_id,),
		)
		return row is not None

	def decrement_seat_and_get_price(self, ticket_id: int, cabin_class: str):
		if cabin_class == "economy":
			row = self.fetch_one(
				"""
				UPDATE ticket_inventory
				SET economy_remain = economy_remain - 1
				WHERE ticket_id = %s AND economy_remain > 0
				RETURNING economy_price
				""",
				(ticket_id,),
			)
		else:
			row = self.fetch_one(
				"""
				UPDATE ticket_inventory
				SET business_remain = business_remain - 1
				WHERE ticket_id = %s AND business_remain > 0
				RETURNING business_price
				""",
				(ticket_id,),
			)
		return float(row[0]) if row else None

	def create_order(self, passenger_id: int, ticket_id: int, cabin_class: str, unit_price: float):
		row = self.fetch_one(
			"""
			INSERT INTO ticket_order(passenger_id, ticket_id, cabin_class, unit_price)
			VALUES (%s, %s, %s, %s)
			RETURNING order_id, passenger_id, ticket_id, cabin_class, unit_price, status, booked_at
			""",
			(passenger_id, ticket_id, cabin_class, unit_price),
		)
		return {
			"order_id": row[0],
			"passenger_id": row[1],
			"ticket_id": row[2],
			"cabin_class": row[3],
			"unit_price": float(row[4]),
			"status": row[5],
			"booked_at": row[6],
		}

	def list_orders(self, passenger_id: int, limit: int, offset: int):
		rows = self.fetch_all(
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
			LIMIT %s OFFSET %s
			""",
			(passenger_id, limit, offset),
		)
		return [
			{
				"order_id": r[0],
				"status": r[1],
				"cabin_class": r[2],
				"unit_price": float(r[3]),
				"booked_at": r[4],
				"flight_date": r[5],
				"flight_number": r[6],
				"source_city": r[7],
				"destination_city": r[8],
			}
			for r in rows
		]

	def get_order_for_update(self, passenger_id: int, order_id: int):
		row = self.fetch_one(
			"""
			SELECT o.status, o.cabin_class, o.ticket_id
			FROM ticket_order o
			WHERE o.order_id = %s AND o.passenger_id = %s
			FOR UPDATE
			""",
			(order_id, passenger_id),
		)
		if not row:
			return None
		return {
			"status": row[0],
			"cabin_class": row[1],
			"ticket_id": row[2],
		}

	def mark_cancelled(self, order_id: int):
		self.execute(
			"UPDATE ticket_order SET status = 'cancelled' WHERE order_id = %s",
			(order_id,),
		)

	def increment_seat(self, ticket_id: int, cabin_class: str):
		if cabin_class == "economy":
			self.execute(
				"UPDATE ticket_inventory SET economy_remain = economy_remain + 1 WHERE ticket_id = %s",
				(ticket_id,),
			)
		else:
			self.execute(
				"UPDATE ticket_inventory SET business_remain = business_remain + 1 WHERE ticket_id = %s",
				(ticket_id,),
			)
