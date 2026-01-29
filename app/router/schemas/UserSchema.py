from pydantic import (
    BaseModel as PydanticBaseModel, 
    ConfigDict,
    Field,
    EmailStr,
    field_validator
    )

from datetime import date
from enum import Enum

from datetime import timezone

from uuid import UUID
from app.domain.UserModel import UserRole

from datetime import datetime
from typing import Optional

class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class UserSchema(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: Optional[datetime] = None

    uid: str = Field(..., description='帳號', examples=['user'])
    pwd: str = Field(examples=['P@ssword123'])
    email: EmailStr = Field(description='電子郵件', examples=['username123@gmail.com'])
    name: str = Field(description='姓名', examples=['username'])
    birthdate: date = Field(description='出生日期', examples=[date(1990, 1, 1)])
    description: str = Field(description='自我介紹', examples=[''])
    role: UserRole = Field(examples=[UserRole.NORMAL])

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'uid': 'user',
                    'pwd': 'P@ssword123',
                    'email': 'username123@gmail.com',
                    'name': 'username',
                    'birthdate': '1990-01-01',
                    'description': '',
                    'role': UserRole.NORMAL
                }
            ]
        }
    }

class UserRegistrationInput(BaseModel):
    id: UUID = Field(description='uuid', examples=[UUID('11d200ac-48d8-4675-bfc0-a3a61af3c499')])
    created_at: datetime
    uid: str = Field(description='帳號', examples=['user'])
    pwd: str = Field(examples=['P@ssword123'])
    email: EmailStr = Field(description='電子郵件', examples=['username123@gmail.com'])
    role: UserRole = Field(examples=[UserRole.NORMAL])
    email_verified: bool = Field(default=False)


class UserProfileInput(BaseModel):
    name: str = Field(description='姓名', examples=['username'])
    created_at: datetime
    birthdate: date = Field(description='出生日期', examples=[date(1990, 1, 1)])
    description: str = Field(description='自我介紹', examples=[''])

class UserProfileRead(BaseModel):
    name: str
    age: int
    description: str

class UserRead(BaseModel):
    id: UUID = Field(description='uuid', examples=[UUID('11d200ac-48d8-4675-bfc0-a3a61af3c499')])
    uid: str
    role: UserRole
    profile: UserProfileRead


class UpdateProfileRequest(BaseModel):
    """Request schema for updating user profile."""
    user_id: UUID = Field(..., description='使用者 UUID')
    name: str = Field(..., description='姓名', examples=['username'])
    birthdate: date = Field(..., description='出生日期', examples=[date(1990, 1, 1)])
    description: str = Field(..., description='自我介紹', examples=['Hello!'])


class UpdatePasswordRequest(BaseModel):
    """Request schema for updating user password."""
    user_id: UUID = Field(..., description='使用者 UUID')
    old_password: str = Field(..., description='舊密碼', examples=['OldP@ssword123'])
    new_password: str = Field(..., description='新密碼', examples=['NewP@ssword456'])


class LoginRequest(BaseModel):
    """Request schema for user login."""
    uid: str = Field(..., description='帳號', examples=['user'])
    password: str = Field(..., description='密碼', examples=['P@ssword123'])

    model_config = {
        'json_schema_extra': {
            'examples': [
                {
                    'uid': 'user',
                    'password': 'P@ssword123'
                }
            ]
        }
    }


class LoginUserInfo(BaseModel):
    """User information returned after login."""
    id: UUID = Field(description='uuid')
    uid: str = Field(description='帳號')
    email: str = Field(description='電子郵件')
    role: UserRole = Field(description='角色')


class LoginResponse(BaseModel):
    """Response schema for successful login."""
    access_token: str = Field(description='JWT access token')
    token_type: str = Field(default='bearer', description='Token type')
    expires_in: int = Field(description='Token expiration time in seconds')
    user: LoginUserInfo = Field(description='User information')


class CurrentUserProfileResponse(BaseModel):
    """Profile info for current user."""
    name: Optional[str] = Field(None, description='姓名')
    birthdate: Optional[date] = Field(None, description='出生日期')
    description: Optional[str] = Field(None, description='自我介紹')


class CurrentUserResponse(BaseModel):
    """Response schema for GET /users/me."""
    id: UUID = Field(description='uuid')
    uid: str = Field(description='帳號')
    email: str = Field(description='電子郵件')
    role: UserRole = Field(description='角色')
    profile: CurrentUserProfileResponse = Field(description='個人資料')


class ResendVerificationRequest(BaseModel):
    """Request schema for resending verification email."""
    email: EmailStr = Field(..., description='電子郵件', examples=['username123@gmail.com'])