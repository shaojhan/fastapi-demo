from fastapi import APIRouter, HTTPException, Depends
from app.router.schemas.UserSchema import UserSchema, UserRead

from app.services.UserService import UserService

from app.exceptions.UserException import UserHasAlreadyExistedError

router = APIRouter(prefix='/users', tags=['user'])

def get_user_service() -> UserService:
    return UserService()

# def get_user_query_service() -> UserQueryService:
#     return UserQueryService()

@router.post('/create', operation_id='create_user')
async def create_user(
    request_body: UserSchema,
    user_service: UserService = Depends(get_user_service)
):
    user = user_service.add_user_profile(request_body)
    return user

@router.post('/update', operation_id='update_password')
async def update_password(request_body):
    return request_body

@router.post('/login', operation_id='login_user')
async def login_user(request_body):
    return request_body


@router.post('/profile/create', operation_id='create_user_profile')
async def create_user_profile(request_body):
    return request_body

@router.post('/profile/update', operation_id='update_user_profile')
def update_user_profile(request_body):
     return request_body

@router.post('/create-session', operation_id='create_user_session')
async def create_user_session(request_body):
    return request_body