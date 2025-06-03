from pydantic import (
    BaseModel as PydanticBaseModel, 
    ConfigDict,
    Field,
    EmailStr
    )

from prisma.enums import UserEnum

class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

class UserCreate(BaseModel):
    uid: str = Field(description='帳號', examples=['user'])
    pwd: str = Field(examples=['P@ssword123'])
    name: str = Field(description='姓名', examples=['username'])
    age: int = Field(description='年齡', examples=[18])
    email: EmailStr = Field(description='電子郵件', examples=['username123@gmail.com'])
    description: str = Field(description='自我介紹', examples=[''])
    role: UserEnum = Field(examples=[UserEnum.NORMAL])

class UserRegistrationInput(BaseModel):
    uid: str = Field(description='帳號', examples=['user'])
    email: EmailStr = Field(description='電子郵件', examples=['username123@gmail.com'])
    password: str = Field(examples=['P@ssword123'])

class UserProfileInput(BaseModel):
    name: str
    age: int
    description: str
    user_id: str

class UserProfileRead(BaseModel):
    name: str
    age: int
    description: str

class UserRead(BaseModel):
    uid: str
    role: UserEnum
    profile: UserProfileRead