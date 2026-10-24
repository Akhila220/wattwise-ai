
from fastapi import APIRouter

# Create a router for authentication endpoints
router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)
