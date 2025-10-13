# backend/models/user_model.py
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker

ROOT = Path(__file__).resolve().parents[2]      # 프로젝트 루트
DB_PATH = ROOT / "data" / "adgen.db"
DB_URL  = f"sqlite:///{DB_PATH}"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True)
    provider      = Column(String, default="local")       # local/… (소셜 대비)
    provider_id   = Column(String, nullable=True)

    # ✅ 아이디 기반
    username      = Column(String, nullable=False, index=True)
    name          = Column(String, nullable=True)
    email         = Column(String, nullable=True, index=True)  # 선택

    password_hash = Column(String, nullable=True)         # local만 사용

    created_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, onupdate=func.now(), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="uq_provider_pid"),
        UniqueConstraint("provider", "username",   name="uq_provider_username"),
    )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
