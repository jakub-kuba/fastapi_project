from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from .routes import users


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# Initialize FastAPI app
app = FastAPI()

# Include the user-related routes with a specific prefix and tags
app.include_router(users.router, prefix="/users", tags=["users"])


# Root endpoint for testing the application
@app.get("/")
async def root():
    return {"message": "This is my project"}
