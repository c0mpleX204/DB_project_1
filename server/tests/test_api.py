from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import tickets


class _FakeTicketService:
	def search_tickets(
		self,
		departure_city,
		arrival_city,
		date_,
		airline=None,
		departure_time=None,
		arrival_time=None,
		limit=200,
		offset=0,
	):
		return [
			{
				"ticket_id": 1,
				"flight_number": "MU1001",
				"airline_code": "MU",
				"airline_name": "China Eastern",
				"source_city": departure_city,
				"source_iata": "SHA",
				"departure_time_local": "08:30:00",
				"destination_city": arrival_city,
				"destination_iata": "PEK",
				"arrival_time_local": "10:50:00",
				"arrival_day_offset": 0,
				"flight_date": str(date_),
				"business_price": 1280.0,
				"business_remain": 6,
				"economy_price": 580.0,
				"economy_remain": 28,
			}
		]


def test_search_tickets_returns_data():
	app = FastAPI()
	app.include_router(tickets.router, prefix="/api/v1/tickets")
	app.dependency_overrides[tickets.get_ticket_service] = lambda: _FakeTicketService()

	client = TestClient(app)
	resp = client.get(
		"/api/v1/tickets/search",
		params={
			"departure_city": "Shanghai",
			"arrival_city": "Beijing",
			"flight_date": "2026-04-11",
		},
	)

	assert resp.status_code == 200
	data = resp.json()
	assert isinstance(data, list)
	assert len(data) == 1
	assert data[0]["source_city"] == "Shanghai"
	assert data[0]["destination_city"] == "Beijing"
