from fastapi import APIRouter, HTTPException, Depends
from app.router.schemas.UserSchema import UserCreate, UserRead
from app.repositories.UserRepository import UserRepository
from app.services.UnitOfWork import UserUnitOfWork
from app.services.UserService import UserService

from app.exceptions.UserException import UserHasAlreadyExistedError

router = APIRouter(prefix='/users', tags=['user'])

def get_user_service() -> UserService:
    return UserService()

@router.post('/create', operation_id='create_user')
async def create_user(
    request_body: UserCreate,
    user_service: UserService = Depends(get_user_service)
) -> UserRead:
        user = await user_service.add_user_or_fail(request_body)
        return user



@router.post('/profile/create', operation_id='create_user_profile')
async def create_user_profile(request_body):
    return request_body

@router.post('/update', operation_id='update_password')
async def update_password(request_body):
    return request_body

@router.post('/create-session', operation_id='create_user_session')
async def create_user_session(request_body):
    return request_body