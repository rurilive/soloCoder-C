from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db, User, INITIAL_TOKEN

security = HTTPBearer(auto_error=False)


def get_token_from_request(request: Request) -> Optional[str]:
    token = request.cookies.get("token")
    if token:
        return token
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        return authorization.replace("Bearer ", "")
    return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = get_token_from_request(request)
    if not token:
        return None
    user = db.query(User).filter(User.token == token).first()
    return user


async def get_current_user_required(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="未授权，请先登录")
    return user


def validate_token(db: Session, token: str) -> Optional[User]:
    if not token:
        return None
    user = db.query(User).filter(User.token == token).first()
    return user
