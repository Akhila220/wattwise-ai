import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Base class for all database table models.
class Base(DeclarativeBase):
    pass


# Find the root folder of the project.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from the root .env file.
load_dotenv(BASE_DIR / ".env")

# Read the database URL from the environment.
DATABASE_URL = os.getenv("DATABASE_URL")

# Stop if the database URL is missing.
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. Please check the project-root .env file."
    )

# Create the SQLAlchemy engine for PostgreSQL.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

# Test the connection to PostgreSQL.
def test_db_connection():
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database()")
        )
        return result.scalar_one()

# Create a reusable database session factory.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


# Provide a database session to API endpoints.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()