from pydantic import (
    BaseModel as PydanticBaseModel, 
    ConfigDict,
    Field,
    EmailStr
    )

from enum import Enum
from uuid import UUID
from app.domain.UserModel import UserRole

class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class UserSchema(BaseModel):
    uid: str = Field(..., description='帳號', examples=['user'])
    pwd: str = Field(examples=['P@ssword123'])
    email: EmailStr = Field(description='電子郵件', examples=['username123@gmail.com'])
    name: str = Field(description='姓名', examples=['username'])
    age: int = Field(description='年齡', examples=[18])
    description: str = Field(description='自我介紹', examples=[''])
    role: UserRole = Field(examples=[UserRole.NORMAL])

class UserRegistrationInput(BaseModel):
    id: UUID = Field(description='uuid', examples=[UUID('11d200ac-48d8-4675-bfc0-a3a61af3c499')])
    uid: str = Field(description='帳號', examples=['user'])
    pwd: str = Field(examples=['P@ssword123'])
    email: EmailStr = Field(description='電子郵件', examples=['username123@gmail.com'])
    role: UserRole = Field(examples=[UserRole.NORMAL])

class UserProfileInput(BaseModel):
    name: str = Field(description='姓名', examples=['username'])
    age: int = Field(description='年齡', examples=[18])
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