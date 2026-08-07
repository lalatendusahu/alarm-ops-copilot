from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.db import engine, init_db
from app.logging_utils import get_logger
from app.routers import alarms, analytics, assets, calculations, health, recommendations
from app.seed import seed

logger = get_logger("alarm_simulator")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with Session(engine) as session:
        inserted = seed(session)
        if inserted:
            logger.info("seeded database with %d alarms", inserted)
    yield


app = FastAPI(title="Alarm Management API Simulator", version="1.0.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(assets.router)
app.include_router(alarms.router)
app.include_router(recommendations.router)
app.include_router(calculations.router)
app.include_router(analytics.router)
