# db.py
from sqlalchemy import (
    create_engine, Column, Integer, DateTime, String, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.types import JSON
from datetime import datetime

Base = declarative_base()

class Response(Base):
    __tablename__ = "responses"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    timestamp   = Column(DateTime, default=datetime.utcnow, nullable=False)
    bm_yes_no   = Column(String(10), nullable=False)
    bm_nominee  = Column(String(100), nullable=False)
    bm_notes    = Column(Text, nullable=True)
    impacts     = Column(JSON, nullable=False)

# Configura l’engine: per SQLite, file locale
engine = create_engine("sqlite:///data.db", echo=False, future=True)

# Se passi a PostgreSQL, usa:
# engine = create_engine(st.secrets["DATABASE_URL"], echo=False, future=True)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def init_db():
    Base.metadata.create_all(bind=engine)
