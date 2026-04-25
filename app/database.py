import uuid
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./photo_album.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

INITIAL_TOKEN = "aaaa"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    photos = relationship("Photo", back_populates="user", cascade="all, delete-orphan")

    def generate_new_token(self):
        self.token = uuid.uuid4().hex
        return self.token


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), index=True)
    thumbnail_filename = Column(String(255))
    tags = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    description = Column(Text, default="")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    user = relationship("User", back_populates="photos")

    def get_tags_list(self):
        if self.tags:
            return [tag.strip() for tag in self.tags.split(",") if tag.strip()]
        return []


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        initial_user = db.query(User).filter(User.token == INITIAL_TOKEN).first()
        if not initial_user:
            initial_user = User(token=INITIAL_TOKEN, username="admin")
            db.add(initial_user)
            db.commit()
            print(f"Created initial user with token: {INITIAL_TOKEN}")
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
