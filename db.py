# db.py
import os
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

DB_PATH    = os.environ.get("SQLITE_FILENAME", "responses.db")
SQLITE_URL = f"sqlite:///{os.path.join(os.getcwd(), DB_PATH)}"

engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Response(Base):
    __tablename__ = "responses"
    id         = Column(Integer, primary_key=True, index=True)
    timestamp  = Column(DateTime, default=datetime.utcnow)
    bm_yes_no  = Column(String, nullable=True)
    bm_nominee = Column(String, nullable=True)
    impacts    = Column(JSON,   nullable=True)   # <— JSON nativo

def init_db():
    Base.metadata.create_all(bind=engine)
