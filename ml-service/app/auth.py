# ml-service/app/auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/auth", tags=["authentication"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str

# Временная база данных пользователей
users_db = {
    "doctor1": {"password": "password123", "user_id": 1, "username": "doctor1"},
    "admin": {"password": "admin123", "user_id": 2, "username": "admin"},
    "test": {"password": "123", "user_id": 3, "username": "test"},
}

@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    user = users_db.get(login_data.username)
    
    if not user or user["password"] != login_data.password:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    # В реальном приложении здесь должна быть генерация JWT токена
    return LoginResponse(
        access_token=f"temp_token_{login_data.username}",
        user_id=user["user_id"],
        username=user["username"]
    )

@router.get("/me")
async def get_current_user():
    # В реальном приложении здесь проверка токена из заголовка
    # Пока заглушка - возвращаем тестовые данные
    return {
        "user_id": 1,
        "username": "doctor1", 
        "full_name": "Иванов А.С.",
        "role": "doctor",
        "department": "Акушерство и гинекология"
    }

@router.get("/me")
async def get_current_user():
    # Заглушка - в реальном приложении здесь проверка токена
    return {"user_id": 1, "username": "doctor1", "role": "doctor"}

# app/auth.py - ДОБАВИТЬ:
@router.post("/logout")
async def logout():
    # В реальном приложении здесь инвалидация токена
    return {"message": "Успешный выход из системы"}