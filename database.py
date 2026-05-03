from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./file_diff.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class FileComparison(Base):
    __tablename__ = "file_comparisons"

    id = Column(Integer, primary_key=True, index=True)
    file1_name = Column(String(255), nullable=False)
    file2_name = Column(String(255), nullable=False)
    file1_content = Column(Text, nullable=False)
    file2_content = Column(Text, nullable=False)
    diff_result = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
