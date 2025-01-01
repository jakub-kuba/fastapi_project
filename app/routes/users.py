from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from .. import schemas, crud, database
from fastapi.security import OAuth2PasswordBearer


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

    # Return a success message with the user ID
    return {"message": "User registered successfully", "user_id": new_user.id}


@router.post("/login")
async def login_user(user: schemas.UserLogin,
                     db: Session = Depends(database.get_db)):
    """
    Endpoint for user login.
    Verifies username and password.
    If data is correct, returns message and JWT token.
    If data is incorrect, returns HTTP error 401.
    """
    # User verification based on username and password
    authenticated_user = crud.authenticate_user(
        db, user.username, user.password)

    # If verification failed, we return HTTP error 401
    if not authenticated_user:
        raise HTTPException(
            status_code=401, detail="Invalid username or password"
        )

    # get current token version from teh database
    current_token_version = authenticated_user.token_version

    # Generate JWT token for a logged user
    access_token = crud.create_access_token(
        data={"sub": user.username,
              "version": current_token_version})

    # generate refresh token
    refresh_token = crud.create_refresh_token(authenticated_user)

    # Return message
    return {
        "message": f"{user.username} - you are logged in",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
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
    # verify user via token
    user = crud.get_logged_in_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    music_entries = crud.get_music_table_content(db)
    if not music_entries:
        raise HTTPException(status_code=404, detail="No music records found")
    result = [
        {"title": record.title,
         "composer": record.composer,
         "rhythm": record.rhythm}
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
