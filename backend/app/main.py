from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.core.deps import get_db
from app.core.exceptions import register_exception_handlers
from app.core.event_handlers import register_event_handlers

app = FastAPI(title="Suvai API")
register_exception_handlers(app)
register_event_handlers()
app.include_router(api_router)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}