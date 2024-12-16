import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

# SQLite database URL
DATABASE_URL = "sqlite:///./test_data/users.db"

# Ensure the directory for the database exists
os.makedirs("test_data", exist_ok=True)

# Create the SQLAlchemy engine for the database
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create a sessionmaker factory for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all database tables based on the models
Base.metadata.create_all(bind=engine)

# Dependency to manage database sessions in FastAPI


def get_db():
    """
    Dependency to handle database sessions.
    """
    db = SessionLocal()  # Create a new database session
    try:
        yield db  # Yield the session to the route handler
    finally:
        db.close()  # Ensure the session is closed after the request is finished
