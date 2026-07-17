import hashlib
import os
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./url_shortener.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class URLMapping(Base):
    __tablename__ = "url_mappings"

    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(16), unique=True, index=True, nullable=False)
    original_url = Column(String, nullable=False)


Base.metadata.create_all(bind=engine)

app = FastAPI()


class ShortenRequest(BaseModel):
    long_url: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Please provide a valid http/https URL.")
    return url


@app.post("/shorten")
def shorten_url(payload: ShortenRequest, db=Depends(get_db)):
    validated_url = validate_url(payload.long_url)

    existing_mapping = db.query(URLMapping).filter(URLMapping.original_url == validated_url).first()
    if existing_mapping:
        return {"short_code": existing_mapping.short_code}

    short_code = hashlib.sha1(validated_url.encode("utf-8").lower()).hexdigest()[:8]
    mapping = URLMapping(short_code=short_code, original_url=validated_url)
    db.add(mapping)
    db.commit()
    db.refresh(mapping)

    return {"short_code": mapping.short_code}


@app.get("/{short_code}")
def redirect_to_url(short_code: str, db=Depends(get_db)):
    mapping = db.query(URLMapping).filter(URLMapping.short_code == short_code).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Short code not found")

    return RedirectResponse(url=mapping.original_url, status_code=301)
