from fastapi import APIRouter
from app.api.v1 import orders, tickets

router = APIRouter()
router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
router.include_router(orders.router, prefix="/orders", tags=["orders"])