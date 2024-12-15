from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.hash import bcrypt
import os


app = FastAPI()

# database configuration
os.makedirs("test_data", exist_ok=True)
DATABASE_URL = "sqlite:///./test_data/users.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# database model


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)


# table creation
Base.metadata.create_all(bind=engine)

# input data model


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

# database session dependency function


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
async def root():
    return {"message": "This is my project"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello, {name}!"}


@app.post("/register")
async def register_user(user: UserRegister, db: Session = Depends(get_db)):
    # check if user exists
    existing_user = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=400, detail="Username or email already registered")

    # password hashing
    hashed_password = bcrypt.hash(user.password)

    # new user creation
    new_user = User(username=user.username, email=user.email,
                    password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully", "user_id": new_user.id}
