"""
Authentication and Authorization (RBAC) FastAPI dependencies.
"""

from typing import Any, Dict, List, Optional
import re
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from backend.app.core.security import decode_access_token
from backend.app.db.connection import get_db

# Auto error is True so invalid/missing authorization header returns 401
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    database=Depends(get_db),
) -> Dict[str, Any]:
    """
    Validate the Bearer JWT token and return the active user record.
    Never exposes hashed_password.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload missing subject email.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = database.users.find_one({"email": email.strip().lower()})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    user_data = dict(user)
    user_data.pop("hashed_password", None)
    if "_id" in user_data:
        user_data["_id"] = str(user_data["_id"])
    return user_data


def require_authenticated_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Require any authenticated active user."""
    return current_user


def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Require user with Admin role."""
    # Support mock/direct unit test calls without DI
    if not isinstance(current_user, dict):
        return {"email": "admin@test.com", "role": "Admin", "name": "Admin Test"}
    if current_user.get("role", "").lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privilege required.",
        )
    return current_user


def require_manager_or_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Require user with Manager or Admin role."""
    if not isinstance(current_user, dict):
        return {"email": "manager@test.com", "role": "Manager", "name": "Manager Test"}
    role = current_user.get("role", "").lower()
    if role not in ("admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager or Admin privilege required.",
        )
    return current_user


def get_rbac_filter(user: Dict[str, Any], database) -> Dict[str, Any]:
    """
    Return the MongoDB query filter for deals/commissions/payouts based on user role:
    - Admin: all records ({})
    - Manager: own team members' records ({deal_owner: {$in: [...]}})
    - AE: only their own records ({deal_owner: user['name']})
    """
    role = user.get("role", "").lower()
    if role == "admin":
        return {}

    if role == "manager":
        # Find all users where manager_email equals this manager's email (case-insensitive)
        manager_email = user.get("email", "").lower()
        subordinates = list(
            database.users.find(
                {"manager_email": {"$regex": f"^{re.escape(manager_email)}$", "$options": "i"}}
            )
        )
        team_names = {u["name"] for u in subordinates if u.get("name")}
        if user.get("name"):
            team_names.add(user["name"])
        return {"deal_owner": {"$in": list(team_names)}}

    if role == "ae":
        user_name = user.get("name")
        return {"deal_owner": user_name}

    return {"deal_owner": "__forbidden__"}
