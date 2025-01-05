from sqlalchemy.orm import Session
from sqlalchemy import or_
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from . import models, schemas

# secret key and algorithm to JWT
SECRET_KEY = "your_secret_key"  # to be changed in prod
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 0.5
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Initialize bcrypt context for hashing passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hashes the password before storing it in the database."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies if the plain password matches the hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_user_by_username_or_email(db: Session,
                                  username: str = None, email: str = None):
    """Fetches a user from the database by either username or email."""

    query = db.query(models.User).filter(or_(
        models.User.username == username,
        models.User.email == email
    ))

    return query.first()


def create_user(db: Session, user_data: schemas.UserRegister):
    """Creates a new user in the database."""
    hashed_password = hash_password(user_data.password)
    db_user = models.User(
        username=user_data.username,
        email=user_data.email,
        password=hashed_password
    )

    # Add the new user to the session
    db.add(db_user)
    # Commit the transaction to save the user in the database
    db.commit()
    # Refresh the instance to get the latest data (e.g., generated ID)
    db.refresh(db_user)

    return db_user


def authenticate_user(db: Session, username: str, password: str):
    """
    Authenticates a user by checking if
    the username and password are correct.
    """
    # Fetch user by username
    user = get_user_by_username_or_email(db, username=username)
    # Verify the provided password
    if user and verify_password(password, user.password):
        return user
    # If user doesn't exist or password is incorrect, return None
    return None


def create_access_token(data: dict,
                        expires_delta: timedelta = timedelta(
                            minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    """Generates JWT token for a user."""
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire, "version": data.get("version", 0)})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user: models.User):
    """Generates a refresh token for a user."""
    data = {
        "sub": user.username,
        "version": user.refresh_token_version,
        "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    """Verifies the JWT token and returns the decoded data."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_datetime = datetime.fromtimestamp(payload["exp"])
        return payload if exp_datetime >= datetime.utcnow() else None
    except JWTError:
        return None


def verify_refresh_token(token: str, db: Session):
    """Verifies a refresh token and ensures it is still valid."""
    payload = verify_token(token)
    if not payload:
        return None

    username = payload.get("sub")
    version = payload.get("version")

    if not username or version is None:
        return None

    user = get_user_by_username_or_email(db, username=username)
    if not user or user.refresh_token_version != version:
        return None

    return user


def get_logged_in_user(db: Session, token: str):
    """Verifies the token and fetches the logged-in user from the database."""
    # Verify the token
    token_data = verify_token(token)
    if not token_data:
        return None

    # Extract the username from the token
    username = token_data.get("sub")
    token_version = token_data.get("version")
    if not username or token_version is None:
        return None

    print("token_data:", token_data)
    print("username:", username)
    print("token_version:", token_version)

    # Fetch the user from the database
    user = get_user_by_username_or_email(db, username=username)

    print("user", user)
    print("user.token_version", user.token_version)

    if not user or user.token_version != token_version:
        return None

    return user


def logout_user(db: Session, user: models.User):
    """Increments the token version, effectively invalidating old tokens."""
    user.token_version += 1
    user.refresh_token_version += 1
    db.commit()


def get_tunes_table_content(db: Session):
    """Shows content of music table"""
    records = db.query(models.Tunes.title,
                       models.Tunes.composer,
                       models.Tunes.rhythm,
                       models.Tunes.link,
                       models.Tunes.description).all()
    return records


def create_proposal(db: Session,
                    proposal_data: schemas.ProposalCreate, user_id: int):
    """Creates a new record in the proposal table"""
    new_proposal = models.Proposals(
        user_id=user_id,
        title=proposal_data.title,
        composer=proposal_data.composer,
        info=proposal_data.info
    )
    db.add(new_proposal)
    db.commit()
    db.refresh(new_proposal)

    return new_proposal


def get_proposal_content(db: Session):
    """Shows content of proposals"""
    records = (
        db.query(
            models.Proposals.user_id,
            models.Proposals.title,
            models.Proposals.composer,
            models.Proposals.info,
            models.User.username,
            models.User.email
        )
        .join(models.User, models.Proposals.user_id == models.User.id)
        .all()
    )
    return records
