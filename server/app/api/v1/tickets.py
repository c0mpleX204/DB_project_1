from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.auth import require_admin
from app.core.db import get_db
from app.models.schemas import (
    TicketGenerateRequest,
    TicketGenerateResult,
    TicketInventoryCreate,
    TicketInventoryRead,
    TicketInventoryUpdate,
    TicketSearchItem,
)
from app.services.ticket_service import (
    TicketConflictError,
    TicketNotFoundError,
    TicketService,
    TicketValidationError,
)


router = APIRouter()


def get_ticket_service(db=Depends(get_db)) -> TicketService:
    return TicketService(db)


@router.get("/", response_model=list[TicketInventoryRead], summary="获取机票列表")
def get_tickets(
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: TicketService = Depends(get_ticket_service),
):
    return service.list_inventory(limit=limit, offset=offset)


@router.get("/cities", response_model=list[str], summary="城市输入联想")
def city_suggestions(
    keyword: str = Query(..., min_length=1),
    limit: int = Query(default=12, ge=1, le=50),
    service: TicketService = Depends(get_ticket_service),
):
    return service.list_city_suggestions(keyword=keyword, limit=limit)


@router.get("/search", response_model=list[TicketSearchItem], summary="组合条件搜索机票")
def search_tickets(
    departure_city: str = Query(...),
    arrival_city: str = Query(...),
    flight_date: date = Query(...),
    airline: str | None = Query(default=None),
    source_iata: str | None = Query(default=None),
    destination_iata: str | None = Query(default=None),
    departure_time: time | None = Query(default=None),
    arrival_time: time | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: TicketService = Depends(get_ticket_service),
):
    return service.search_tickets(
        departure_city=departure_city,
        arrival_city=arrival_city,
        date_=flight_date,
        airline=airline,
        source_iata=source_iata,
        destination_iata=destination_iata,
        departure_time=departure_time,
        arrival_time=arrival_time,
        limit=limit,
        offset=offset,
    )


@router.post("/generate", response_model=TicketGenerateResult, summary="按日期范围自动生成机票")
def generate_tickets(
    payload: TicketGenerateRequest,
    _admin_id: int = Depends(require_admin),
    service: TicketService = Depends(get_ticket_service),
):
    return service.generate_inventory(payload)


@router.get("/{ticket_id}", response_model=TicketInventoryRead, summary="获取单张机票")
def get_ticket(ticket_id: int, service: TicketService = Depends(get_ticket_service)):
    try:
        return service.get_inventory(ticket_id)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/", response_model=TicketInventoryRead, summary="创建机票")
def create_ticket(
    ticket: TicketInventoryCreate,
    service: TicketService = Depends(get_ticket_service),
):
    try:
        return service.create_inventory(ticket)
    except TicketValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except TicketConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.put("/{ticket_id}", response_model=TicketInventoryRead, summary="更新机票")
def update_ticket(
    ticket_id: int,
    ticket: TicketInventoryUpdate,
    service: TicketService = Depends(get_ticket_service),
):
    try:
        return service.update_inventory(ticket_id, ticket)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except TicketValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except TicketConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.delete("/{ticket_id}", summary="删除机票")
def delete_ticket(ticket_id: int, service: TicketService = Depends(get_ticket_service)):
    try:
        service.delete_inventory(ticket_id)
        return {"message": "Ticket inventory deleted"}
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
