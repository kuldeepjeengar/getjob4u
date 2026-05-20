import hashlib
import hmac
import os
import secrets
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, LargeBinary, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime


def _load_dotenv(path: Path) -> None:
    """Tiny .env loader (stdlib-only). Skips comments, blank lines, and
    keys that are already set in the real environment so OS-level vars win.
    """
    if not path.is_file():
        return
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        pass


_load_dotenv(Path(__file__).parent / ".env")


_HASH_ITER = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _HASH_ITER)
    return f"pbkdf2_sha256${_HASH_ITER}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, dk_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), dk_hex)
    except (ValueError, TypeError):
        return False

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
    grade = Column(String(40), nullable=True)
    word_count = Column(Integer, nullable=True)
    scan_type = Column(String(20), default="role")  # 'role' or 'jd'
    jd_text = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=True)
    file_content = Column(LargeBinary, nullable=True)
    uploader_name = Column(String(120), nullable=True)
    uploader_email = Column(String(160), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GeneratedEmail(Base):
    __tablename__ = "generated_emails"
    id = Column(Integer, primary_key=True, index=True)
    email_type = Column(String(50))
    recipient_role = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(60), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


def _ensure_columns():
    """Lightweight in-place migration for SQLite ATSScan additions."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    if "ats_scans" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("ats_scans")}
    statements = []
    if "grade" not in existing:
        statements.append("ALTER TABLE ats_scans ADD COLUMN grade VARCHAR(40)")
    if "word_count" not in existing:
        statements.append("ALTER TABLE ats_scans ADD COLUMN word_count INTEGER")
    if "scan_type" not in existing:
        statements.append("ALTER TABLE ats_scans ADD COLUMN scan_type VARCHAR(20) DEFAULT 'role'")
    if "jd_text" not in existing:
        statements.append("ALTER TABLE ats_scans ADD COLUMN jd_text TEXT")
    if "file_size" not in existing:
        statements.append("ALTER TABLE ats_scans ADD COLUMN file_size INTEGER")
    if "file_content" not in existing:
        statements.append("ALTER TABLE ats_scans ADD COLUMN file_content BLOB")
    if "uploader_name" not in existing:
        statements.append("ALTER TABLE ats_scans ADD COLUMN uploader_name VARCHAR(120)")
    if "uploader_email" not in existing:
        statements.append("ALTER TABLE ats_scans ADD COLUMN uploader_email VARCHAR(160)")
    if not statements:
        return
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def _ensure_default_admin():
    """Upsert the primary admin account from environment variables.

    Credentials come from .env (or the OS environment) — never hard-coded.
    Runs on every startup so the configured account always exists with the
    current password, surviving DB wipes / migrations.
    """
    target_user = os.environ.get("GETJOB4U_ADMIN_USER")
    target_pass = os.environ.get("GETJOB4U_ADMIN_PASS")
    if not target_user or not target_pass:
        # No creds configured — skip silently. The /admin/login route will
        # simply reject all attempts until the env vars are provided.
        return
    db = SessionLocal()
    try:
        existing = db.query(AdminUser).filter(AdminUser.username == target_user).first()
        if existing is None:
            db.add(AdminUser(
                username=target_user,
                password_hash=hash_password(target_pass),
                is_active=True,
            ))
        else:
            existing.password_hash = hash_password(target_pass)
            existing.is_active = True
        db.commit()
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    _ensure_default_admin()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
