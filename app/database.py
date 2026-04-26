import uuid
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
from app.config import config
from app.logger import get_logger

logger = get_logger()

SQLALCHEMY_DATABASE_URL = "sqlite:///./photo_album.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    photos = relationship("Photo", back_populates="user", cascade="all, delete-orphan")
    owned_albums = relationship("Album", back_populates="owner", cascade="all, delete-orphan")
    album_memberships = relationship(
        "AlbumMember", 
        foreign_keys="AlbumMember.user_id",
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    invited_memberships = relationship(
        "AlbumMember",
        foreign_keys="AlbumMember.invited_by",
        back_populates="inviter"
    )

    def generate_new_token(self):
        self.token = uuid.uuid4().hex
        return self.token


class Album(Base):
    __tablename__ = "albums"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    is_public = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="owned_albums")
    photos = relationship("Photo", back_populates="album", cascade="all, delete-orphan")
    members = relationship("AlbumMember", back_populates="album", cascade="all, delete-orphan")

    def is_owner(self, user_id: int) -> bool:
        return self.owner_id == user_id

    def can_edit(self, user_id: int) -> bool:
        if self.is_owner(user_id):
            return True
        for member in self.members:
            if member.user_id == user_id and member.role in ["owner", "editor"]:
                return True
        return False

    def can_view(self, user_id: int = None) -> bool:
        if self.is_public:
            return True
        if user_id is None:
            return False
        if self.is_owner(user_id):
            return True
        for member in self.members:
            if member.user_id == user_id:
                return True
        return False


class AlbumMember(Base):
    __tablename__ = "album_members"

    id = Column(Integer, primary_key=True, index=True)
    album_id = Column(Integer, ForeignKey("albums.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(50), default="viewer")
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    album = relationship("Album", back_populates="members")
    user = relationship(
        "User", 
        foreign_keys=[user_id],
        back_populates="album_memberships"
    )
    inviter = relationship(
        "User",
        foreign_keys=[invited_by],
        back_populates="invited_memberships"
    )


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), index=True)
    thumbnail_filename = Column(String(255))
    tags = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    description = Column(Text, default="")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    album_id = Column(Integer, ForeignKey("albums.id"), nullable=True, index=True)

    user = relationship("User", back_populates="photos")
    album = relationship("Album", back_populates="photos")

    def get_tags_list(self):
        if self.tags:
            return [tag.strip() for tag in self.tags.split(",") if tag.strip()]
        return []


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        initial_user = db.query(User).filter(User.token == config.INITIAL_TOKEN).first()
        if not initial_user:
            initial_user = User(token=config.INITIAL_TOKEN, username="admin")
            db.add(initial_user)
            db.commit()
            db.refresh(initial_user)
            logger.info(f"Created initial user with token: {config.INITIAL_TOKEN}")
        
        _create_default_albums_for_existing_users(db)
    finally:
        db.close()


def _create_default_albums_for_existing_users(db):
    from sqlalchemy import exists
    
    users = db.query(User).all()
    for user in users:
        has_default_album = db.query(exists().where(
            Album.owner_id == user.id,
            Album.name == "默认相册"
        )).scalar()
        
        if not has_default_album:
            default_album = Album(
                name="默认相册",
                description="系统自动创建的默认相册",
                owner_id=user.id,
                is_public=False
            )
            db.add(default_album)
            db.commit()
            db.refresh(default_album)
            logger.info(f"Created default album for user {user.id}")
            
            _migrate_photos_to_default_album(db, user.id, default_album.id)


def _migrate_photos_to_default_album(db, user_id: int, album_id: int):
    photos_without_album = db.query(Photo).filter(
        Photo.user_id == user_id,
        Photo.album_id.is_(None)
    ).all()
    
    for photo in photos_without_album:
        photo.album_id = album_id
    
    if photos_without_album:
        db.commit()
        logger.info(f"Migrated {len(photos_without_album)} photos to default album for user {user_id}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
