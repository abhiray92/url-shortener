import hashlib
import os
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
else:
    db_path = os.getenv("DB_PATH", "/app/url_shortener.db")
    engine = create_engine(f"sqlite:///{db_path}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class URLMapping(Base):
    __tablename__ = "url_mappings"

    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(16), unique=True, index=True, nullable=False)
    original_url = Column(String, nullable=False)


Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener")


class ShortenRequest(BaseModel):
    long_url: str


class ShortenResponse(BaseModel):
    short_code: str


class URLResponse(BaseModel):
    original_url: str


def generate_short_code(long_url: str) -> str:
    return hashlib.sha256(long_url.encode("utf-8")).hexdigest()[:8]


def validate_url(long_url: str) -> str:
    parsed = urlparse(long_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid http/https URL.",
        )
    return long_url


@app.post("/shorten", response_model=ShortenResponse)
def shorten_url(payload: ShortenRequest):
    long_url = validate_url(payload.long_url)

    db = SessionLocal()
    try:
        existing = db.query(URLMapping).filter(URLMapping.original_url == long_url).first()
        if existing:
            return ShortenResponse(short_code=existing.short_code)

        short_code = generate_short_code(long_url)
        while db.query(URLMapping).filter(URLMapping.short_code == short_code).first():
            short_code = generate_short_code(long_url + "-")

        mapping = URLMapping(short_code=short_code, original_url=long_url)
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        return ShortenResponse(short_code=mapping.short_code)
    finally:
        db.close()


@app.get("/{short_code}")
def get_original_url(short_code: str):
    db = SessionLocal()
    try:
        mapping = db.query(URLMapping).filter(URLMapping.short_code == short_code).first()
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Short code not found.",
            )
        return RedirectResponse(url=mapping.original_url, status_code=status.HTTP_301_MOVED_PERMANENTLY)
    finally:
        db.close()
