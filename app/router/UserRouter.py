from fastapi import APIRouter
from app.router.schemas.UserModel import UserCreate, UserRead
from app.repositories.UserRepository import UserRepository
from app.services.UnitOfWork import UserUnitOfWork

router = APIRouter(prefix='/users', tags=['user'])
# userRepo = UserRepository()

@router.post('/create', operation_id='create_user')
async def create_user(request_body: UserCreate) -> UserRead:
    async with UserUnitOfWork() as uuow:
        user = await uuow.users.addOneUser(request_body)
        return user
    # return await userRepo.addOneUser(request_body)


@router.post('/profile/create', operation_id='create_user_profile')
async def create_user_profile(request_body):
    return request_body

@router.post('/update', operation_id='update_password')
async def update_password(request_body):
    return request_body