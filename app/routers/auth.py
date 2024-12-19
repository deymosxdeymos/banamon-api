from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from app.utils.auth import AuthHandler
from typing import Dict

router = APIRouter()
auth = AuthHandler()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
async def register(request: RegisterRequest) -> JSONResponse:
    """Register endpoint - creates a new user"""
    try:
        user_data = await auth.register(request.email, request.password)
        return JSONResponse(
            content={
                "data": user_data
            }
        )
    except HTTPException as e:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Registration failed"
        )

@router.post("/login")
async def login(request: LoginRequest) -> JSONResponse:
    """Login endpoint - returns access & refresh tokens"""
    try:
        tokens = await auth.authenticate(request.email, request.password)
        return JSONResponse(
            content={
                "data": tokens
            }
        )
    except HTTPException as e:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Login failed"
        )

@router.post("/refresh")
async def refresh(request: RefreshRequest) -> JSONResponse:
    """Refresh endpoint - returns new access token"""
    try:
        tokens = await auth.refresh(request.refresh_token)
        return JSONResponse(
            content={
                "data": tokens
            }
        )
    except HTTPException as e:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Token refresh failed"
        )

@router.get("/me")
async def get_current_user(user_id: str = Depends(auth.get_current_user)) -> JSONResponse:
    """Protected endpoint example"""
    try:
        user = await auth.db.get_user(user_id)
        return JSONResponse(
            content={
                "data": {
                    "id": user["id"],
                    "email": user["email"]
                }
            }
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to get user data"
        )
