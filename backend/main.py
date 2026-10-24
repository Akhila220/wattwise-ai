
from backend.routers.auth import router as auth_router
from fastapi import FastAPI

# Create the FastAPI application
app = FastAPI(
    title="WattWise AI",
    description="Household electricity consumption forecasting API",
    version="0.1.0",
)
app.include_router(auth_router)

@app.get("/")
def home():
    return {
        "message": "Welcome to WattWise AI!",
        "status": "Backend is running",
        "project": "Household Electricity Consumption Forecasting System",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
