from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base
from datetime import datetime

# Create the base class for SQLAlchemy models
Base = declarative_base()

# User model class to map to the 'users' table in the database


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    is_confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    token_version = Column(Integer, default=0)
    refresh_token_version = Column(Integer, default=0)
    role = Column(String, default="user")

    reset_token = Column(String, nullable=True, unique=True)
    reset_token_expiry = Column(DateTime, nullable=True)

    proposals = relationship("Proposals", back_populates="user")


class Tunes(Base):
    __tablename__ = "tunes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    composer = Column(String)
    rhythm = Column(String)
    difficulty = Column(Integer)
    progress = Column(Integer)
    link = Column(String)
    description = Column(String)
    demo = Column(Boolean, default=False)


class Proposals(Base):
    __tablename__ = "proposals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    composer = Column(String)
    info = Column(String)

    user = relationship("User", back_populates="proposals")
