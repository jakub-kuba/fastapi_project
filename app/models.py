from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base


# Create the base class for SQLAlchemy models
Base = declarative_base()

# User model class to map to the 'users' table in the database


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)


class MusicTable(Base):
    __tablename__ = "music_table"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    composer = Column(String)
    rhythm = Column(String)
