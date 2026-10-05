"""
Authentication endpoints: login and profile retrieval.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from backend.app.api.deps import require_authenticated_user
from backend.app.core.security import create_access_token, verify_password
from backend.app.db.connection import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, database=Depends(get_db)):
    """
    Authenticate user using email and password.
    Returns signed JWT access token and user metadata.
    """
    email_clean = payload.email.strip().lower()
    user = database.users.find_one({"email": email_clean})

    if not user or not user.get("hashed_password"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.get("active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    token = create_access_token(
        data={
            "sub": user["email"],
            "role": user["role"],
            "name": user.get("name"),
        }
    )

    user_info = {
        "email": user["email"],
        "name": user.get("name"),
        "role": user["role"],
        "manager_email": user.get("manager_email"),
        "active": user.get("active", True),
    }

    return LoginResponse(access_token=token, token_type="bearer", user=user_info)


@router.get("/me")
def get_me(current_user: Dict[str, Any] = Depends(require_authenticated_user)):
    """Return the currently authenticated user's profile."""
    return current_user
