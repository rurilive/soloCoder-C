import uuid
from typing import Dict
from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from captcha_generator import CaptchaGenerator, CaptchaType

app = FastAPI(title="打码平台", description="随机生成各种类型验证码的打码练习平台")
templates = Jinja2Templates(directory="templates")
captcha_gen = CaptchaGenerator(width=220, height=80)

captcha_store: Dict[str, str] = {}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/captcha")
async def get_captcha(type: str = "mixed", length: int = 4):
    captcha_id = str(uuid.uuid4())
    
    try:
        captcha_type = CaptchaType(type.lower())
    except ValueError:
        captcha_type = CaptchaType.MIXED
    
    image_bytes, answer = captcha_gen.generate_captcha(captcha_type, length)
    captcha_store[captcha_id] = answer.upper()
    
    return JSONResponse({
        "captcha_id": captcha_id,
        "captcha_type": captcha_type.value,
        "image": image_bytes.hex()
    })


@app.post("/api/verify")
async def verify_captcha(captcha_id: str = Form(...), user_input: str = Form(...)):
    correct_answer = captcha_store.get(captcha_id)
    
    if correct_answer is None:
        return JSONResponse({
            "success": False,
            "message": "验证码已过期或不存在，请刷新重试"
        })
    
    if user_input.upper() == correct_answer:
        del captcha_store[captcha_id]
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
