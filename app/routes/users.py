from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .. import schemas, crud, database
from app.utils.sending_email import (
    send_confirmation_email,
    send_reset_password_email,
)
import os
from datetime import timedelta
from app.crud import generate_reset_token
from pydantic.error_wrappers import ValidationError
from pydantic import EmailStr
import json
import httpx


BASE_URL = os.getenv("BASE_URL")


# Initialize the APIRouter instance for user-related endpoints
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Statis files and templates settings
router.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@router.post("/register")  # to be deleted?
async def register_user(
    user: schemas.UserRegister, db: Session = Depends(database.get_db)
):
    """
    Endpoint to register a new user.
    Checks if the username or email already exists before creating a new user.
    If the user exists, it raises an HTTP 400 error.
    If the user is successfully created,
    it returns a success message with the user's ID.
    """
    # Check if the user with the same username or email already exists
    existing_user = crud.get_user_by_username_or_email(
        db, user.username, user.email
    )

    # If user already exists, raise a 400 error with a message
    if existing_user:
        raise HTTPException(
            status_code=400, detail="Username or email already registered"
        )

    # create a new user
    new_user = crud.create_user(db, user)

    # create a token what will be valid for 1 hour
    confirmation_token = crud.create_access_token(
        data={"sub": user.username}, expires_delta=timedelta(hours=1)
    )

    # create a confirmation link that will appear in the email
    confirmation_link = f"{BASE_URL}/users/confirm?token={confirmation_token}"

    await send_confirmation_email(user.email, confirmation_link)

    print(f"User {new_user.username} registered successfully.")
    print(f"User id: {new_user.id}")

    return schemas.UserResponse.from_orm(new_user)


@router.post("/registered", response_class=HTMLResponse)
async def register_user_from_form(
    request: Request,
    username: str = Form(...),
    email: EmailStr = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
    db: Session = Depends(database.get_db),
):
    """
    Processes user registration from form data.
    Validates input fields and checks password confirmation. Creates a new user
    in the database and sends a confirmation email with a unique token. Renders
    an appropriate HTML template based on success or errors.
    """
    errors = []

    if not (username and email and password and password2):
        error_message = "All fields must be filled in."
        errors.append(error_message)
        return templates.TemplateResponse(
            "index.html", {"request": request, "errors": errors}
        )

    if password != password2:
        error_message = "Passwords do not match"
        errors.append(error_message)
        return templates.TemplateResponse(
            "index.html", {"request": request, "errors": errors}
        )

    try:
        # Creating a temporary object to verify validators from schemas.py
        user_data = schemas.UserRegister(
            username=username, email=email, password=password
        )
        crud.create_user(db, user_data)

        confirmation_token = crud.create_access_token(
            data={"sub": username}, expires_delta=timedelta(hours=1)
        )
        confirmation_link = (
            f"{BASE_URL}/users/confirm?token={confirmation_token}"
        )

        await send_confirmation_email(email, confirmation_link)

        return templates.TemplateResponse(
            "confirmation.html", {"request": request, "email": email}
        )

    except ValidationError as e:
        errors_list = json.loads(e.json())
        for item in errors_list:
            errors.append(item.get("msg"))
        print(errors)
        return templates.TemplateResponse(
            "index.html", {"request": request, "errors": errors}
        )

    except IntegrityError:
        # Handle unique constraint violation error
        db.rollback()
        errors.append("Email/Username already registered.")
        return templates.TemplateResponse(
            "index.html", {"request": request, "errors": errors}
        )


@router.post("/login")
async def login_user(
    user: schemas.UserLogin, db: Session = Depends(database.get_db)
):
    """
    Endpoint for user login. Verifies username and password.
    If data is correct and user is confirmed, returns message and JWT token.
    If data is incorrect or user is not confirmed, returns HTTP error.
    """
    # Authenticate the user based on username and password
    authenticated_user = crud.authenticate_user(
        db, user.username, user.password
    )

    # If authentication fails, return HTTP 401 error
    if not authenticated_user:
        raise HTTPException(
            status_code=401, detail="Invalid username or password"
        )

    # Check if the user has confirmed their email
    if not authenticated_user.is_confirmed:
        raise HTTPException(
            status_code=403,
            detail="Please confirm your email before logging in",
        )
    # Retrieve current token version from the database
    current_token_version = authenticated_user.token_version

    # Generate JWT access token for the logged-in user
    access_token = crud.create_access_token(
        data={"sub": user.username, "version": current_token_version}
    )

    # Generate refresh token for the user
    refresh_token = crud.create_refresh_token(authenticated_user)

    # Return success message and tokens
    return {
        "message": f"{user.username} - you are logged in",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/logged", response_class=HTMLResponse)
async def login_user_from_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(database.get_db),
):
    errors_login = []

    # Authenticate user
    authenticated_user = crud.authenticate_user(
        db, username=username, password=password
    )

    if not authenticated_user:
        errors_login.append("Incorrect email or password")
        return templates.TemplateResponse(
            "index.html", {"request": request, "errors_login": errors_login}
        )

    # Check if user confirmed email
    if not authenticated_user.is_confirmed:
        errors_login.append("Please confirm your email before logging in")
        return templates.TemplateResponse(
            "index.html", {"request": request, "errors_login": errors_login}
        )

    # Get current token version
    current_token_version = authenticated_user.token_version

    # Generate JWT tokens
    access_token = crud.create_access_token(
        data={"sub": username, "version": current_token_version}
    )

    print("DEBUG - token generated in /logged:")
    print(access_token)

    refresh_token = crud.create_refresh_token(authenticated_user)

    expires_in = crud.get_token_expiration(access_token)

    print("expires_in:", expires_in)

    # Get content for tunes table (assuming admin=False by default)
    is_admin = False
    music_entries = crud.get_tunes_table_content(
        db, authenticated_user, is_admin
    )

    # Prepare response with template
    response = templates.TemplateResponse(
        "tunes.html",
        {
            "request": request,
            "username": username,
            "ready_tunes": music_entries,
            "expires_in": expires_in,
        },
    )

    # Set tokens in HTTP-only cookies
    response.set_cookie(
        key="access_token", value=access_token, httponly=True, samesite="lax"
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True, samesite="lax"
    )

    # # Optional: set session info (if using SessionMiddleware)
    # request.session["user"] = username

    return response


@router.get("/logged", response_class=HTMLResponse)
async def refresh_via_cookie(
    request: Request, db: Session = Depends(database.get_db)
):
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=401, detail="No refresh token provided"
        )

    user = crud.verify_refresh_token(refresh_token, db)
    if not user:
        raise HTTPException(
            status_code=401, detail="Invalid or expired refresh token"
        )

    access_token = crud.create_access_token(
        data={"sub": user.username, "version": user.token_version}
    )
    new_refresh_token = crud.create_refresh_token(user)

    expires_in = crud.get_token_expiration(access_token)

    music_entries = crud.get_tunes_table_content(
        db, user_authenticated=True, is_admin=False
    )

    response = templates.TemplateResponse(
        "tunes.html",
        {
            "request": request,
            "username": user.username,
            "ready_tunes": music_entries,
            "expires_in": expires_in,
        },
    )

    response.set_cookie(
        "access_token", access_token, httponly=True, samesite="lax"
    )
    response.set_cookie(
        "refresh_token", new_refresh_token, httponly=True, samesite="lax"
    )

    return response


@router.get("/details/{tune_id}", name="details", response_class=HTMLResponse)
async def tune_details(
    request: Request,
    tune_id: int,
    db: Session = Depends(database.get_db),
):
    # Get access token from cookie
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Verify the token and get the logged-in user
    user = crud.get_logged_in_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Fetch the tune details from the database
    tune = crud.get_tune_by_id(db, tune_id)
    if tune is None:
        raise HTTPException(status_code=404, detail="Tune not found")

    # Check if the tune is a demo tune or if the user has permission to view it
    if not tune.demo and not user.is_admin:
        raise HTTPException(
            status_code=403, detail="You are not authorized to view this tune"
        )

    # Generate access token (can be refreshed here if needed)
    access_token = crud.create_access_token(
        data={"sub": user.username, "version": user.token_version}
    )

    expires_in = crud.get_token_expiration(access_token)

    # Prepare response with template
    response = templates.TemplateResponse(
        "details.html",
        {
            "request": request,
            "tune": tune,
            "username": user.username,
            "expires_in": expires_in,
        },
    )

    # Set the new access token in HTTP-only cookies
    response.set_cookie(
        key="access_token", value=access_token, httponly=True, samesite="lax"
    )

    return response


@router.get("/confirm")
async def confirm_registration(
    request: Request, token: str, db: Session = Depends(database.get_db)
):
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

    return templates.TemplateResponse("confirmed.html", {"request": request})


@router.post("/refresh")
async def refresh_token(
    token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)
):
    """
    Endpoint to refresh access and refresh tokens.
    Requires a valid refresh token.
    """
    # Verify the refresh token and get the user
    user = crud.verify_refresh_token(token, db)
    if not user:
        raise HTTPException(
            status_code=401, detail="Invalid or expired refresh token"
        )

    # Generate new tokens
    access_token = crud.create_access_token(
        data={"sub": user.username, "version": user.token_version}
    )
    refresh_token = crud.create_refresh_token(user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.get("/music")
async def get_music_table(
    db: Session = Depends(database.get_db), token: str = Depends(oauth2_scheme)
):
    # Verify user via token
    user = crud.get_logged_in_user(db, token)
    user_authenticated = bool(user)
    is_admin = user.role == "admin" if user else False

    music_entries = crud.get_tunes_table_content(
        db, user_authenticated, is_admin
    )

    if not music_entries:
        raise HTTPException(status_code=404, detail="No music records found")

    if is_admin:
        result = [
            {
                "id": record.id,
                "title": record.title,
                "composer": record.composer,
                "rhythm": record.rhythm,
                "link": record.link,
                "description": record.description,
                "demo": record.demo,
                "progress": record.progress,
            }
            for record in music_entries
        ]

    else:
        result = [
            {
                "title": record.title,
                "composer": record.composer,
                "rhythm": record.rhythm,
                "link": record.link,
                "description": record.description,
            }
            for record in music_entries
        ]

    return {"music_entries": result}


@router.get("/me")
async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)
):
    user = crud.get_logged_in_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {"username": user.username, "email": user.email}


@router.post("/proposals")
async def add_proposal(
    proposal: schemas.ProposalCreate,
    db: Session = Depends(database.get_db),
    token: str = Depends(oauth2_scheme),
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
    token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)
):
    user = crud.get_logged_in_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # user logout
    crud.logout_user(db, user)

    return {"message": f"{user.username} successfully logged out"}


@router.get("/logout", name="logout")
async def logout(request: Request):
    access_token = request.cookies.get("access_token")

    if access_token:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{BASE_URL}/logout",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
        except Exception as e:
            print("Logout request failed:", e)

    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response


@router.get("/proposals")
async def get_proposals(
    db: Session = Depends(database.get_db), token: str = Depends(oauth2_scheme)
):
    # verify admin user via token
    user = crud.get_logged_in_user(db, token)
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=403, detail="Admin privileges required"
        )

    proposal_entries = crud.get_proposal_content(db)
    if not proposal_entries:
        raise HTTPException(status_code=404, detail="No proposal found")
    result = [
        {
            "username": record.username,
            "email": record.email,
            "title": record.title,
            "composer": record.composer,
            "info": record.info,
        }
        for record in proposal_entries
    ]
    return {"proposal_entries": result}


@router.post("/tunes")
async def add_tune(
    tune: schemas.TuneCreate,
    db: Session = Depends(database.get_db),
    token: str = Depends(oauth2_scheme),
):
    """Endpoint for an admin that enables adding a new tune"""
    user = crud.get_logged_in_user(db, token)
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=403, detail="Admin privileges required"
        )

    new_tune = crud.create_tune(db, tune)

    return {"message": "Tune added successfully", "tune_id": new_tune.id}


@router.put("/tunes/{tune_id}")
async def update_tune(
    tune_id: int,
    tune: schemas.TuneUpdate,
    db: Session = Depends(database.get_db),
    token: str = Depends(oauth2_scheme),
):
    """Endpoint for an admin, that enables to edit the tune based on its id"""
    user = crud.get_logged_in_user(db, token)
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=403, detail="Admin privileges required"
        )

    updated_tune = crud.update_tune(db, tune_id, tune)
    if not updated_tune:
        raise HTTPException(status_code=404, detail="Tune not found")

    return {"message": "Tune updated successfully", "tune_id": updated_tune.id}


@router.post("/forgot-password/")
async def forgot_password(
    request: schemas.ForgotPasswordRequest,
    db: Session = Depends(database.get_db),
):
    """Handles password reset requests"""
    email = request.email

    reset_token = generate_reset_token(db, email)

    if not reset_token:
        raise HTTPException(status_code=404, detail="User not found")

    await send_reset_password_email(email, reset_token)

    return {
        "message": "Password reset email sent",
        "reset_token": reset_token,
    }


@router.get("/reset-password")
def reset_password_form(token: str, db: Session = Depends(database.get_db)):
    """Displays password reset form if token is valid"""
    user = crud.verify_reset_token(db, token)
    if not user:
        return {"error": "Invalid or expired token"}

    return {"message": "Show reset password form here", "token": token}


@router.post("/reset-password")
def reset_password(
    request: schemas.ResetPasswordRequest,
    db: Session = Depends(database.get_db),
):
    """Resets the user's password if the reset token is valid."""
    user = crud.verify_reset_token(db, request.token)

    if not user:
        return {"error": "Invalid or expired token"}

    # hash new password and save it to the database
    hashed_password = crud.hash_password(request.new_password)
    user.password = hashed_password

    # delete the used token
    user.reset_token = None
    user.reset_token_expiry = None

    db.commit()

    return {"message": "Password reset successfully"}
