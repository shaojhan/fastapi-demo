from fastapi import APIRouter, HTTPException, Depends
from app.router.schemas.UserSchema import UserCreate, UserRead

from app.services.UserService import UserService, UserQueryService

from app.exceptions.UserException import UserHasAlreadyExistedError

router = APIRouter(prefix='/users', tags=['user'])

def get_user_service() -> UserService:
    return UserService()

# def get_user_query_service() -> UserQueryService:
#     return UserQueryService()

@router.post('/create', operation_id='create_user')
async def create_user(
    request_body: UserCreate,
    user_service: UserService = Depends(get_user_service)
) -> UserRead:
        user = await user_service.add_user_profile(request_body)
        return user

@router.post('/update', operation_id='update_password')
async def update_password(request_body):
    return request_body

# @router.get('/get_all', operation_id='get_all_users')
# async def get_all_users(
#     user_query_service: UserQueryService = Depends(get_user_query_service)
# ):
#     return await user_query_service.get_all_user()

# @router.get('/get_all/view', operation_id='get_all_user_view')
# async def get_all_user_view(
#     user_query_service: UserQueryService = Depends(get_user_query_service)
# ):
#     return await user_query_service.get_user_view()

# @router.get('/get_by_uid/{uid}', operation_id='get_user_by_uid')
# async def get_user_by_uid(
#     uid: str,
#     user_query_service: UserQueryService = Depends(get_user_query_service)
# ):
#     return await user_query_service.get_user_by_uid(uid)

@router.post('/profile/create', operation_id='create_user_profile')
async def create_user_profile(request_body):
    return request_body

@router.post('/profile/update', operation_id='update_user_profile')
def update_user_profile(request_body):
     return request_body

@router.post('/create-session', operation_id='create_user_session')
async def create_user_session(request_body):
    return request_body