from fastapi import FastAPI, Request, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from .routes import users
from pydantic import ValidationError
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal, get_db
from sqlalchemy.orm import Session
from app.crud import (
    remove_unconfirmed_users,
    get_tunes_table_content,
    get_demotune_by_id,
)
from datetime import datetime


# TEMPORARY
print("system timestamp:", datetime.utcnow().timestamp())
print("utcnow:", datetime.utcnow())

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# Initialize FastAPI app
app = FastAPI()

# Include the user-related routes with a specific prefix and tags
app.include_router(users.router, prefix="/users", tags=["users"])

# Statis files and templates settings
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Global validation error handling


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/")
async def serve_homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/demo")
async def get_demo(request: Request, db: Session = Depends(get_db)):
    # demo is available for everyone
    user_authenticated = False
    is_admin = False

    music_entries = get_tunes_table_content(db, user_authenticated, is_admin)

    # if not music_entries:
    #     raise HTTPException(status_code=404, detail="No music records found")

    return templates.TemplateResponse(
        "demo.html", {"request": request, "demo_tunes": music_entries}
    )


@app.get(
    "/demodetails/{tune_id}", name="demodetails", response_class=HTMLResponse
)
async def tune_details(
    request: Request, tune_id: int, db: Session = Depends(get_db)
):
    tune = get_demotune_by_id(db, tune_id)
    if tune is None:
        raise HTTPException(status_code=404, detail="Tune not found")
    return templates.TemplateResponse(
        "demodetails.html", {"request": request, "tune": tune}
    )


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
# scheduler.add_job(scheduled_remove_unconfirmed_users, "interval", minutes=30)
scheduler.add_job(
    scheduled_remove_unconfirmed_users, "interval", minutes=2
)  # TEMP
scheduler.start()


@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
