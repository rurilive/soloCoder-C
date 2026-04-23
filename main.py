import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import func, desc, Integer
from sqlalchemy.orm import Session

from captcha_generator import CaptchaGenerator, CaptchaType
from database import get_db, init_db, User, CaptchaRecord, SessionLocal, get_password_hash, verify_password

SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

app = FastAPI(title="打码平台", description="随机生成各种类型验证码的打码练习平台")
captcha_gen = CaptchaGenerator(width=220, height=80)

captcha_store: Dict[str, Dict] = {}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

init_db()


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None


class UserRegister(BaseModel):
    username: str
    password: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


@app.get("/")
async def index():
    html_path = os.path.join(BASE_DIR, "templates", "index.html")
    return FileResponse(html_path, media_type="text/html")


@app.get("/admin")
async def admin_page():
    html_path = os.path.join(BASE_DIR, "templates", "admin.html")
    return FileResponse(html_path, media_type="text/html")


@app.post("/api/register")
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    if len(user_data.username) < 3 or len(user_data.username) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名长度应为3-20个字符"
        )
    
    if len(user_data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码长度至少6个字符"
        )
    
    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        is_admin=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return JSONResponse({
        "success": True,
        "message": "注册成功",
        "user": new_user.to_dict()
    })


@app.post("/api/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = create_access_token(
        data={"user_id": user.id, "username": user.username}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/user/info")
async def get_user_info(current_user: User = Depends(get_current_user)):
    return JSONResponse({
        "success": True,
        "user": current_user.to_dict()
    })


@app.get("/api/captcha")
async def get_captcha(
    type: str = "mixed",
    length: int = 4,
    current_user: User = Depends(get_current_user)
):
    captcha_id = str(uuid.uuid4())
    
    try:
        captcha_type = CaptchaType(type.lower())
    except ValueError:
        captcha_type = CaptchaType.MIXED
    
    image_bytes, answer = captcha_gen.generate_captcha(captcha_type, length)
    captcha_store[captcha_id] = {
        "answer": answer.upper(),
        "user_id": current_user.id,
        "captcha_type": type.lower()
    }
    
    return JSONResponse({
        "captcha_id": captcha_id,
        "captcha_type": captcha_type.value,
        "image": image_bytes.hex()
    })


@app.post("/api/verify")
async def verify_captcha(
    captcha_id: str = Form(...),
    user_input: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    captcha_data = captcha_store.get(captcha_id)
    
    if captcha_data is None or captcha_data["user_id"] != current_user.id:
        return JSONResponse({
            "success": False,
            "message": "验证码已过期或不存在，请刷新重试"
        })
    
    correct_answer = captcha_data["answer"]
    is_correct = user_input.upper() == correct_answer
    
    record = CaptchaRecord(
        user_id=current_user.id,
        captcha_type=captcha_data["captcha_type"],
        user_input=user_input.upper(),
        correct_answer=correct_answer,
        is_correct=is_correct
    )
    db.add(record)
    db.commit()
    
    del captcha_store[captcha_id]
    
    if is_correct:
        return JSONResponse({
            "success": True,
            "message": "验证通过！恭喜你打码正确！"
        })
    else:
        return JSONResponse({
            "success": False,
            "message": f"验证失败！正确答案是: {correct_answer}",
            "correct_answer": correct_answer,
            "user_input": user_input
        })


@app.get("/api/user/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    total = db.query(func.count(CaptchaRecord.id)).filter(
        CaptchaRecord.user_id == current_user.id
    ).scalar()
    
    correct = db.query(func.count(CaptchaRecord.id)).filter(
        CaptchaRecord.user_id == current_user.id,
        CaptchaRecord.is_correct == True
    ).scalar()
    
    accuracy = round((correct / total * 100) if total > 0 else 0, 2)
    
    type_stats = db.query(
        CaptchaRecord.captcha_type,
        func.count(CaptchaRecord.id).label('total'),
        func.sum(func.cast(CaptchaRecord.is_correct, Integer)).label('correct')
    ).filter(
        CaptchaRecord.user_id == current_user.id
    ).group_by(CaptchaRecord.captcha_type).all()
    
    type_breakdown = []
    for stat in type_stats:
        type_breakdown.append({
            "type": stat.captcha_type,
            "total": stat.total,
            "correct": stat.correct or 0,
            "accuracy": round(((stat.correct or 0) / stat.total * 100), 2)
        })
    
    return JSONResponse({
        "success": True,
        "stats": {
            "total": total,
            "correct": correct,
            "accuracy": accuracy,
            "type_breakdown": type_breakdown
        }
    })


@app.get("/api/admin/users")
async def get_all_users(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    user_list = []
    
    for user in users:
        total = db.query(func.count(CaptchaRecord.id)).filter(
            CaptchaRecord.user_id == user.id
        ).scalar()
        correct = db.query(func.count(CaptchaRecord.id)).filter(
            CaptchaRecord.user_id == user.id,
            CaptchaRecord.is_correct == True
        ).scalar()
        
        user_dict = user.to_dict()
        user_dict.update({
            "total_captcha": total,
            "correct_captcha": correct,
            "accuracy": round((correct / total * 100) if total > 0 else 0, 2)
        })
        user_list.append(user_dict)
    
    return JSONResponse({
        "success": True,
        "users": user_list
    })


@app.get("/api/admin/stats")
async def get_admin_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    total_users = db.query(func.count(User.id)).scalar()
    total_captcha = db.query(func.count(CaptchaRecord.id)).scalar()
    correct_captcha = db.query(func.count(CaptchaRecord.id)).filter(
        CaptchaRecord.is_correct == True
    ).scalar()
    
    type_stats = db.query(
        CaptchaRecord.captcha_type,
        func.count(CaptchaRecord.id).label('total'),
        func.sum(func.cast(CaptchaRecord.is_correct, Integer)).label('correct')
    ).group_by(CaptchaRecord.captcha_type).all()
    
    type_breakdown = []
    for stat in type_stats:
        type_breakdown.append({
            "type": stat.captcha_type,
            "total": stat.total,
            "correct": stat.correct or 0,
            "accuracy": round(((stat.correct or 0) / stat.total * 100), 2)
        })
    
    recent_activity = db.query(CaptchaRecord, User).join(
        User, CaptchaRecord.user_id == User.id
    ).order_by(desc(CaptchaRecord.created_at)).limit(50).all()
    
    activity_list = []
    for record, user in recent_activity:
        activity_list.append({
            "id": record.id,
            "username": user.username,
            "captcha_type": record.captcha_type,
            "user_input": record.user_input,
            "correct_answer": record.correct_answer,
            "is_correct": record.is_correct,
            "created_at": record.created_at.isoformat() if record.created_at else None
        })
    
    return JSONResponse({
        "success": True,
        "stats": {
            "total_users": total_users,
            "total_captcha": total_captcha,
            "correct_captcha": correct_captcha,
            "overall_accuracy": round((correct_captcha / total_captcha * 100) if total_captcha > 0 else 0, 2),
            "type_breakdown": type_breakdown,
            "recent_activity": activity_list
        }
    })


@app.get("/api/types")
async def get_captcha_types():
    return JSONResponse({
        "types": [
            {"value": "digits", "name": "数字验证码", "description": "纯数字组成的验证码"},
            {"value": "letters", "name": "字母验证码", "description": "纯大写字母组成的验证码"},
            {"value": "mixed", "name": "混合验证码", "description": "数字和字母混合的验证码"},
            {"value": "math", "name": "数学运算", "description": "简单的加减乘运算题"}
        ]
    })
