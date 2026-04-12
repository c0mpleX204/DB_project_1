from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.db import get_db
from app.models.schemas import (
	OrderCancelResult,
	OrderCreateRequest,
	OrderCreateResult,
	OrderRead,
)
from app.services.order_service import (
	OrderConflictError,
	OrderNotFoundError,
	OrderService,
	OrderValidationError,
)

router = APIRouter()


def get_order_service(db=Depends(get_db)) -> OrderService:
	return OrderService(db)


@router.post("/book", response_model=OrderCreateResult, summary="下单购票")
def book_order(
	payload: OrderCreateRequest,
	service: OrderService = Depends(get_order_service),
):
	try:
		return service.book_order(payload)
	except OrderValidationError as exc:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{passenger_id}", response_model=list[OrderRead], summary="查询乘客订单")
def list_orders(
	passenger_id: int,
	limit: int = Query(default=200, ge=1, le=1000),
	offset: int = Query(default=0, ge=0),
	service: OrderService = Depends(get_order_service),
):
	return service.list_orders(passenger_id=passenger_id, limit=limit, offset=offset)


@router.post(
	"/{passenger_id}/{order_id}/cancel",
	response_model=OrderCancelResult,
	summary="取消订单并回补库存",
)
def cancel_order(
	passenger_id: int,
	order_id: int,
	service: OrderService = Depends(get_order_service),
):
	try:
		return service.cancel_order(passenger_id=passenger_id, order_id=order_id)
	except OrderNotFoundError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
	except OrderConflictError as exc:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
