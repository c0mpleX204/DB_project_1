from psycopg2 import errors

from app.models.schemas import (
	TicketGenerateRequest,
	TicketGenerateResult,
	TicketInventoryCreate,
	TicketInventoryRead,
	TicketInventoryUpdate,
	TicketSearchItem,
)
from app.repository.ticket_repo import TicketRepository


class TicketNotFoundError(Exception):
	pass


class TicketConflictError(Exception):
	pass


class TicketValidationError(Exception):
	pass


class TicketService:
	def __init__(self, conn):
		self.repo = TicketRepository(conn)

	def list_city_suggestions(self, keyword: str, limit: int = 12):
		k = keyword.strip()
		if not k:
			return []
		return self.repo.list_city_suggestions(k, limit)

	def list_inventory(self, limit: int, offset: int):
		rows = self.repo.list_inventory(limit=limit, offset=offset)
		return [TicketInventoryRead.model_validate(r) for r in rows]

	def get_inventory(self, ticket_id: int):
		row = self.repo.get_inventory(ticket_id)
		if not row:
			raise TicketNotFoundError("Ticket inventory not found")
		return TicketInventoryRead.model_validate(row)

	def create_inventory(self, payload: TicketInventoryCreate):
		try:
			row = self.repo.create_inventory(payload)
			return TicketInventoryRead.model_validate(row)
		except errors.ForeignKeyViolation:
			raise TicketValidationError("flight_id does not exist")
		except errors.UniqueViolation:
			raise TicketConflictError("(flight_id, flight_date) already exists")

	def update_inventory(self, ticket_id: int, payload: TicketInventoryUpdate):
		try:
			row = self.repo.update_inventory(ticket_id, payload)
			if not row:
				raise TicketNotFoundError("Ticket inventory not found")
			return TicketInventoryRead.model_validate(row)
		except errors.ForeignKeyViolation:
			raise TicketValidationError("flight_id does not exist")
		except errors.UniqueViolation:
			raise TicketConflictError("(flight_id, flight_date) already exists")

	def delete_inventory(self, ticket_id: int):
		ok = self.repo.delete_inventory(ticket_id)
		if not ok:
			raise TicketNotFoundError("Ticket inventory not found")

	def search_tickets(
		self,
		departure_city: str,
		arrival_city: str,
		date_,
		airline=None,
		source_iata=None,
		destination_iata=None,
		departure_time=None,
		arrival_time=None,
		limit: int = 200,
		offset: int = 0,
	):
		rows = self.repo.search_tickets(
			departure_city=departure_city,
			arrival_city=arrival_city,
			date_=date_,
			airline=airline,
			source_iata=source_iata,
			destination_iata=destination_iata,
			departure_time=departure_time,
			arrival_time=arrival_time,
			limit=limit,
			offset=offset,
		)
		return [TicketSearchItem.model_validate(r) for r in rows]

	def generate_inventory(self, payload: TicketGenerateRequest):
		added = self.repo.generate_inventory(payload.start_date, payload.end_date)
		return TicketGenerateResult(added=added)
