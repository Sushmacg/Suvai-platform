from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.core.deps import get_db
from app.core.exceptions import register_exception_handlers

app = FastAPI(title="Suvai API")
register_exception_handlers(app)
app.include_router(api_router)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}