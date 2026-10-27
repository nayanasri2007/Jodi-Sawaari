import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jodi.db")

# Make sure Postgres addresses use the psycopg2 driver we installed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def ensure_columns():
    """Add new columns to tables that already exist (works on SQLite and PostgreSQL)."""
    inspector = inspect(engine)
    existing = {c["name"] for c in inspector.get_columns("ride_requests")}
    wanted = {
        "pickup_label": "VARCHAR DEFAULT ''",
        "drop_label": "VARCHAR DEFAULT ''",
        "created_at": "TIMESTAMP",
    }
    with engine.begin() as conn:
        for name, col_type in wanted.items():
            if name not in existing:
                conn.execute(text("ALTER TABLE ride_requests ADD COLUMN " + name + " " + col_type))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()