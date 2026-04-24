from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./photo_album.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), index=True)
    thumbnail_filename = Column(String(255))
    tags = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    description = Column(Text, default="")

    def get_tags_list(self):
        if self.tags:
            return [tag.strip() for tag in self.tags.split(",") if tag.strip()]
        return []


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
