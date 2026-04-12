from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field, model_validator


CabinClass = Literal["economy", "business"]
OrderStatus = Literal["booked", "cancelled"]


class TicketInventoryCreate(BaseModel):
	flight_id: int = Field(gt=0)
	flight_date: date
	business_price: float = Field(ge=0)
	business_remain: int = Field(ge=0)
	economy_price: float = Field(ge=0)
	economy_remain: int = Field(ge=0)


class TicketInventoryUpdate(TicketInventoryCreate):
	pass


class TicketInventoryRead(TicketInventoryCreate):
	ticket_id: int = Field(gt=0)


class TicketGenerateRequest(BaseModel):
	start_date: date
	end_date: date

	@model_validator(mode="after")
	def validate_range(self):
		if self.end_date < self.start_date:
			raise ValueError("end_date must be >= start_date")
		return self


class TicketGenerateResult(BaseModel):
	added: int = Field(ge=0)


class TicketSearchItem(BaseModel):
	ticket_id: int
	flight_number: str
	airline_code: str
	airline_name: str
	source_city: str
	source_iata: str
	departure_time_local: time
	destination_city: str
	destination_iata: str
	arrival_time_local: time
	arrival_day_offset: int
	flight_date: date
	business_price: float
	business_remain: int
	economy_price: float
	economy_remain: int


class OrderCreateRequest(BaseModel):
	passenger_id: int = Field(gt=0)
	ticket_id: int = Field(gt=0)
	cabin_class: CabinClass


class OrderCreateResult(BaseModel):
	order_id: int
	passenger_id: int
	ticket_id: int
	cabin_class: CabinClass
	unit_price: float = Field(ge=0)
	status: OrderStatus
	booked_at: datetime


class OrderRead(BaseModel):
	order_id: int
	status: OrderStatus
	cabin_class: CabinClass
	unit_price: float
	booked_at: datetime
	flight_date: date
	flight_number: str
	source_city: str
	destination_city: str


class OrderCancelResult(BaseModel):
	order_id: int
	status: OrderStatus


class APIError(BaseModel):
	detail: str
