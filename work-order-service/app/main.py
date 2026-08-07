from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.db import engine, init_db
from app.routers import health_router, router
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with Session(engine) as session:
        seed(session)
    yield


app = FastAPI(title="Work Order Service", version="1.0.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(router)
