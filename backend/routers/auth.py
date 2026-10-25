
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Response,
    status,
)

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession
from pwdlib import PasswordHash

from backend.database import get_db
from backend.models import User, Session as AuthSession
from backend.schemas import UserRegister, UserLogin


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

password_hash = PasswordHash.recommended()

# A login session lasts 24 hours.
SESSION_DURATION = timedelta(hours=24)
SESSION_COOKIE_NAME = "wattwise_session"

# Use False for local HTTP development.
# Set this to True when deployed over HTTPS.
COOKIE_SECURE = False


def hash_session_token(token: str) -> str:
    """Return a SHA-256 digest of a session token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()



def get_authenticated_user(
    wattwise_session: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
    db: DBSession = Depends(get_db),
):
    # A missing cookie means the user is not logged in.
    if not wattwise_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in to access this resource.",
        )

    # Hash the received token before looking it up.
    token_digest = hash_session_token(wattwise_session)

    session_record = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == token_digest
        )
    )

    # Reject unknown or expired sessions.
    if (
        session_record is None
        or session_record.expires_at <= datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is invalid or expired. Please log in again.",
        )

    user = db.get(User, session_record.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The account associated with this session no longer exists.",
        )

    return user



@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister,
    db: DBSession = Depends(get_db),
):
    email = str(user_data.email).strip().lower()
    name = user_data.name.strip()

    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name cannot be empty.",
        )

    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    new_user = User(
        name=name,
        email=email,
        password_hash=password_hash.hash(user_data.password),
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
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
def login(
    user_data: UserLogin,
    response: Response,
    db: DBSession = Depends(get_db),
):
    email = str(user_data.email).strip().lower()

    # Find the account using the submitted email.
    user = db.scalar(
        select(User).where(User.email == email)
    )

    # Use the same error for an unknown email or wrong password.
    if user is None or not password_hash.verify(
        user_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate a high-entropy random session token.
    raw_token = secrets.token_urlsafe(32)

    # Store only its hash in the database.
    token_digest = hash_session_token(raw_token)

    expires_at = datetime.now(timezone.utc) + SESSION_DURATION

    new_session = AuthSession(
        user_id=user.id,
        token_hash=token_digest,
        expires_at=expires_at,
    )

    try:
        db.add(new_session)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login could not be completed. Please try again.",
        )

    # Give the browser the original token in an HTTP-only cookie.
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )

    return {
        "message": "Login successful!",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
        "session_expires_at": expires_at.isoformat(),
    }


@router.get("/me")
def get_current_user(
    user: User = Depends(get_authenticated_user),
):
    return {
        "message": "Authenticated user retrieved successfully!",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
    }


@router.post("/logout")
def logout(
    response: Response,
    wattwise_session: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
    db: DBSession = Depends(get_db),
):
    if wattwise_session:
        token_digest = hash_session_token(wattwise_session)

        session_record = db.scalar(
            select(AuthSession).where(
                AuthSession.token_hash == token_digest
            )
        )

        if session_record is not None:
            db.delete(session_record)
            db.commit()

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )

    return {"message": "Logout successful!"}