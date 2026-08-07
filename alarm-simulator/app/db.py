import os
from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine

DB_PATH = os.getenv("ALARM_DB_PATH", "./data/alarm_simulator.db")
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
