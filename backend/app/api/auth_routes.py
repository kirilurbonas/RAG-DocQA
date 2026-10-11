"""Authentication endpoints for user registration and login."""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from datetime import timedelta

from app.db.database import get_db
from app.services.user_service import UserService
from app.services.password_service import PasswordService
from app.security.auth import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    email: str


class UserResponse(BaseModel):
    """User information response."""
    id: str
    email: str
    username: str
    is_active: bool
    is_admin: bool
    created_at: str
    last_login: str = None


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    try:
        user_service = UserService(db)
        user = user_service.create_user(
            email=request.email,
            username=request.username,
            password=request.password
        )

        # Create JWT token
        access_token = create_access_token(
            data={
                "sub": user['id'],
                "email": user['email'],
                "username": user['username']
            },
            expires_delta=timedelta(hours=24)
        )

        return TokenResponse(
            access_token=access_token,
            user_id=user['id'],
            username=user['username'],
            email=user['email']
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login user with email and password."""
    user_service = UserService(db)
    user = user_service.authenticate_user(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Create JWT token
    access_token = create_access_token(
        data={
            "sub": user['id'],
            "email": user['email'],
            "username": user['username']
        },
        expires_delta=timedelta(hours=24)
    )

    return TokenResponse(
        access_token=access_token,
        user_id=user['id'],
        username=user['username'],
        email=user['email']
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(
        id=current_user['id'],
        email=current_user['email'],
        username=current_user['username'],
        is_active=current_user.get('is_active', True),
        is_admin=current_user.get('is_admin', False),
        created_at=current_user.get('created_at', ''),
        last_login=current_user.get('last_login')
    )


@router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Change user password."""
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters"
        )

    user_service = UserService(db)
    success = user_service.update_password(
        current_user['id'],
        old_password,
        new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid current password"
        )

    return {"message": "Password changed successfully"}
