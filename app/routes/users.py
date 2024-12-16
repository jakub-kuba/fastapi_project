from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from .. import schemas, crud, database

# Initialize the APIRouter instance for user-related endpoints
router = APIRouter()

# Endpoint to register a new user


@router.post("/register")
async def register_user(user: schemas.UserRegister, db: Session = Depends(database.get_db)):
    # Check if the user with the same username or email already exists in the database
    existing_user = crud.get_user_by_username_or_email(
        db, user.username, user.email)
    if existing_user:
        raise HTTPException(
            status_code=400, detail="Username or email already registered")
    new_user = crud.create_user(db, user)
    return {"message": "User registered successfully", "user_id": new_user.id}
