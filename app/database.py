from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
import os
from dotenv import load_dotenv


load_dotenv()

# Retrieve database connection details from environment variables
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST", "db")  # Default host
DB_PORT = os.getenv("DB_PORT", "5432")       # Default PostgreSQL port

# Construct the database URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create the SQLAlchemy engine for the database
engine = create_engine(DATABASE_URL)

# Create a sessionmaker factory for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all database tables based on the models
Base.metadata.create_all(bind=engine)

# Dependency to manage database sessions in FastAPI
def get_db():
    """
    Dependency to handle database sessions.
    """
    db = SessionLocal()
    try:
        yield db  # Yield the session to the route handler
    finally:
        db.close()
