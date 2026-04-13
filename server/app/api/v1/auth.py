from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.core.db import get_db

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login", summary="用户登录")
def login(payload: LoginRequest, db=Depends(get_db)):
    username = payload.username.strip()
    password = payload.password.strip()

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username and password are required",
        )

    with db.cursor() as cur:
        cur.execute(
            "SELECT pa.passenger_id FROM passenger_auth pa WHERE pa.mobile_number = %s AND pa.password = %s",
            (username, password)
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return {"passenger_id": row[0]}