from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./getjob4u.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), nullable=False)
    rating = Column(Integer, nullable=False)
    category = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ATSScan(Base):
    __tablename__ = "ats_scans"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    target_role = Column(String(100))
    score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class GeneratedEmail(Base):
    __tablename__ = "generated_emails"
    id = Column(Integer, primary_key=True, index=True)
    email_type = Column(String(50))
    recipient_role = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
