from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from . import models, schemas

# Function to get a user by either username or email


def get_user_by_username_or_email(db: Session, username: str, email: str):
    return db.query(models.User).filter(
        (models.User.username == username) | (models.User.email == email)
    ).first()


# Function to create a new user, hash the password, and store it in the database
def create_user(db: Session, user: schemas.UserRegister):
    hashed_password = bcrypt.hash(user.password)
    new_user = models.User(username=user.username,
                           email=user.email, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
