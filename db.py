# db.py

import os
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

#  Assicuriamoci che il DB stia nella working dir, non in assets/
DB_FILENAME = os.environ.get("SQLITE_FILENAME", "responses.db")
DB_PATH     = os.path.join(os.getcwd(), DB_FILENAME)
SQLITE_URL  = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Response(Base):
    __tablename__ = "responses"
    id         = Column(Integer, primary_key=True, index=True)
    timestamp  = Column(DateTime, default=datetime.utcnow)
    bm_yes_no  = Column(String, nullable=False)
    bm_nominee = Column(String, nullable=False)
    bm_notes   = Column(String, nullable=True)
    impacts    = Column(JSON,   nullable=True)  # o Text, se preferisci serializzare

def init_db():
    # crea il file e le tabelle se non esistono
    Base.metadata.create_all(bind=engine)
