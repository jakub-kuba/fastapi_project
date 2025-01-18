from fastapi import FastAPI, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from .routes import users
from pydantic import ValidationError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# Initialize FastAPI app
app = FastAPI()

# Include the user-related routes with a specific prefix and tags
app.include_router(users.router, prefix="/users", tags=["users"])

# Global validation error handling


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )


# Root endpoint for testing the application
@app.get("/")
async def root():
    return {"message": "This is my project"}
