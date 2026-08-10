# database/session.py
import os
from sqlmodel import SQLModel, Session, create_engine
from dotenv import load_dotenv

load_dotenv()

# Fallback to SQLite if DATABASE_URL is not set in .env
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./product.db")

# check_same_thread required only for SQLite
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=True, connect_args=connect_args)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session