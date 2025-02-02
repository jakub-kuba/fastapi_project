from fastapi import FastAPI, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from .routes import users
from pydantic import ValidationError
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.crud import remove_unconfirmed_users
from datetime import datetime

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

# Initialize the scheduler
scheduler = BackgroundScheduler()

# Function to remove unconfirmed users with a database session


def scheduled_remove_unconfirmed_users():
    print(f"Scheduler running at {datetime.utcnow()}")
    db = SessionLocal()
    try:
        remove_unconfirmed_users(db)
    finally:
        db.close()


# Add the job to the scheduler
scheduler.add_job(scheduled_remove_unconfirmed_users, 'interval', minutes=30)
scheduler.start()


@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
