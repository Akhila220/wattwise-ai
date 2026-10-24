
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from pwdlib import PasswordHash

from backend.database import get_db
from backend.models import User
from backend.schemas import UserRegister


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

password_hash = PasswordHash.recommended()


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister,
    db: DBSession = Depends(get_db),
):
    # Check whether this email is already registered.
    existing_user = db.scalar(
        select(User).where(User.email == str(user_data.email).lower())
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    # Hash the password before storing it.
    hashed_password = password_hash.hash(user_data.password)

    # Create the new user record.
    new_user = User(
        name=user_data.name.strip(),
        email=str(user_data.email).lower(),
        password_hash=hashed_password,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration could not be completed. Please try again.",
        )

    return {
        "message": "Registration successful!",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
        },
    }


@router.post("/login")
def login():
    return {"message": "Login endpoint is ready"}


@router.get("/me")
def get_current_user():
    return {"message": "Current-user endpoint is ready"}


@router.post("/logout")
def logout():
    return {"message": "Logout endpoint is ready"}
