from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from .. import schemas, crud, database
from fastapi.security import OAuth2PasswordBearer
from app.utils.sending_email import send_confirmation_email
import os
from datetime import timedelta


BASE_URL = os.getenv("BASE_URL")


# Initialize the APIRouter instance for user-related endpoints
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


@router.post("/register")
async def register_user(user: schemas.UserRegister,
                        db: Session = Depends(database.get_db)):
    """
    Endpoint to register a new user.
    Checks if the username or email already exists before creating a new user.
    If the user exists, it raises an HTTP 400 error.
    If the user is successfully created,
    it returns a success message with the user's ID.
    """
    # Check if the user with the same username or email already exists
    existing_user = crud.get_user_by_username_or_email(
        db, user.username, user.email)

    # If user already exists, raise a 400 error with a message
    if existing_user:
        raise HTTPException(
            status_code=400, detail="Username or email already registered")

    # create a new user
    new_user = crud.create_user(db, user)

    # create a token what will be valid for 1 hour
    confirmation_token = crud.create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(hours=1)
    )

    # create a confirmation link that will appear in the email
    confirmation_link = f"{BASE_URL}/users/confirm?token={confirmation_token}"

    await send_confirmation_email(user.email, confirmation_link)

    print(f"User {new_user.username} registered successfully.")
    print(f"User id: {new_user.id}")

    return schemas.UserResponse.from_orm(new_user)


@router.post("/login")
async def login_user(user: schemas.UserLogin,
                     db: Session = Depends(database.get_db)):
    """
    Endpoint for user login. Verifies username and password.
    If data is correct and user is confirmed, returns message and JWT token.
    If data is incorrect or user is not confirmed, returns HTTP error.
    """
    # Authenticate the user based on username and password
    authenticated_user = crud.authenticate_user(
        db, user.username, user.password)

    # If authentication fails, return HTTP 401 error
    if not authenticated_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password")

    # Check if the user has confirmed their email
    if not authenticated_user.is_confirmed:
        raise HTTPException(
            status_code=403,
            detail="Please confirm your email before logging in"
        )
    # Retrieve current token version from the database
    current_token_version = authenticated_user.token_version

    # Generate JWT access token for the logged-in user
    access_token = crud.create_access_token(
        data={"sub": user.username,
              "version": current_token_version})

    # Generate refresh token for the user
    refresh_token = crud.create_refresh_token(authenticated_user)

    # Return success message and tokens
    return {
        "message": f"{user.username} - you are logged in",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.get("/confirm")
async def confirm_registration(token: str,
                               db: Session = Depends(database.get_db)):
    """
    Endpoint to confirm user registration.
    Validates the token and sets the user's is_confirmed status to True.
    """
    user_data = crud.verify_token(token)
    if not user_data:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = crud.get_user_by_username_or_email(db, username=user_data["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Set is_confirmed to True to activate the user's account
    user.is_confirmed = True
    db.commit()

    return {
        "message": (
            "Email confirmed. "
            "Please log in to complete the registration process."
        )
    }


@router.post("/refresh")
async def refresh_token(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db)
):
    """
    Endpoint to refresh access and refresh tokens.
    Requires a valid refresh token.
    """
    # Verify the refresh token and get the user
    user = crud.verify_refresh_token(token, db)
    if not user:
        raise HTTPException(
            status_code=401, detail="Invalid or expired refresh token")

    # Generate new tokens
    access_token = crud.create_access_token(
        data={"sub": user.username,
              "version": user.token_version})
    refresh_token = crud.create_refresh_token(user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.get("/music")
async def get_music_table(db: Session = Depends(database.get_db),
                          token: str = Depends(oauth2_scheme)):
    # Verify user via token
    user = crud.get_logged_in_user(db, token)
    user_authenticated = bool(user)
    is_admin = user.role == "admin" if user else False

    music_entries = crud.get_tunes_table_content(
        db, user_authenticated, is_admin)

    if not music_entries:
        raise HTTPException(status_code=404, detail="No music records found")

    if is_admin:
        result = [
            {"id": record.id,
             "title": record.title,
             "composer": record.composer,
             "rhythm": record.rhythm,
             "link": record.link,
             "description": record.description,
             "demo": record.demo,
             "progress": record.progress}
            for record in music_entries
        ]

    else:

        result = [
            {"title": record.title,
             "composer": record.composer,
             "rhythm": record.rhythm,
             "link": record.link,
             "description": record.description}
            for record in music_entries
        ]

    return {"music_entries": result}


@router.get("/me")
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db)
):
    user = crud.get_logged_in_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {"username": user.username, "email": user.email}


@router.post("/proposals")
async def add_proposal(
    proposal: schemas.ProposalCreate,
    db: Session = Depends(database.get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Endpoint to add a new record to proposals table
    Available for users logged in
    """
    user = crud.get_logged_in_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # add a new record
    new_proposal = crud.create_proposal(db, proposal, user.id)

    return {
        "message": (
            f"{user.username} has added "
            f"a new proposal: {new_proposal.title}"
        )
    }


@router.post("/logout")
async def logout_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db)
):
    user = crud.get_logged_in_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # user logout
    crud.logout_user(db, user)

    return {"message": f"{user.username} successfully logged out"}


@router.get("/proposals")
async def get_proposals(db: Session = Depends(database.get_db),
                        token: str = Depends(oauth2_scheme)):
    # verify admin user via token
    user = crud.get_logged_in_user(db, token)
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=403, detail="Admin privileges required")

    proposal_entries = crud.get_proposal_content(db)
    if not proposal_entries:
        raise HTTPException(status_code=404, detail="No proposal found")
    result = [
        {"username": record.username,
         "email": record.email,
         "title": record.title,
         "composer": record.composer,
         "info": record.info}
        for record in proposal_entries
    ]
    return {"proposal_entries": result}


@router.post("/tunes")
async def add_tune(
    tune: schemas.TuneCreate,
    db: Session = Depends(database.get_db),
    token: str = Depends(oauth2_scheme)
):
    """Endpoint for an admin that enables adding a new tune"""
    user = crud.get_logged_in_user(db, token)
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=403, detail="Admin privileges required")

    new_tune = crud.create_tune(db, tune)

    return {"message": "Tune added successfully", "tune_id": new_tune.id}


@router.put("/tunes/{tune_id}")
async def update_tune(
    tune_id: int,
    tune: schemas.TuneUpdate,
    db: Session = Depends(database.get_db),
    token: str = Depends(oauth2_scheme)
):
    """Endpoint for an admin, that enables to edit the tune based on its id"""
    user = crud.get_logged_in_user(db, token)
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=403, detail="Admin privileges required")

    updated_tune = crud.update_tune(db, tune_id, tune)
    if not updated_tune:
        raise HTTPException(status_code=404, detail="Tune not found")

    return {"message": "Tune updated successfully", "tune_id": updated_tune.id}
