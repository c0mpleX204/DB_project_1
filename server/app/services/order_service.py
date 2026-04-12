from app.models.schemas import (
	OrderCancelResult,
	OrderCreateRequest,
	OrderCreateResult,
	OrderRead,
)
from app.repository.order_repo import OrderRepository


class OrderNotFoundError(Exception):
	pass


class OrderValidationError(Exception):
	pass


class OrderConflictError(Exception):
	pass


class OrderService:
	def __init__(self, conn):
		self.repo = OrderRepository(conn)

	def book_order(self, payload: OrderCreateRequest):
		if not self.repo.passenger_exists(payload.passenger_id):
			raise OrderValidationError(f"passenger_id {payload.passenger_id} not found")

		price = self.repo.decrement_seat_and_get_price(
			ticket_id=payload.ticket_id,
			cabin_class=payload.cabin_class,
		)
		if price is None:
			raise OrderValidationError("ticket not found or no seat available")

		row = self.repo.create_order(
			passenger_id=payload.passenger_id,
			ticket_id=payload.ticket_id,
			cabin_class=payload.cabin_class,
			unit_price=price,
		)
		return OrderCreateResult.model_validate(row)

	def list_orders(self, passenger_id: int, limit: int, offset: int):
		rows = self.repo.list_orders(passenger_id=passenger_id, limit=limit, offset=offset)
		return [OrderRead.model_validate(r) for r in rows]

	def cancel_order(self, passenger_id: int, order_id: int):
		row = self.repo.get_order_for_update(passenger_id=passenger_id, order_id=order_id)
		if not row:
			raise OrderNotFoundError("order not found")

		if row["status"] == "cancelled":
			raise OrderConflictError("order already cancelled")

		self.repo.mark_cancelled(order_id)
		self.repo.increment_seat(ticket_id=row["ticket_id"], cabin_class=row["cabin_class"])

		return OrderCancelResult(order_id=order_id, status="cancelled")
