from .UnitOfWork import UserUnitOfWork
from ..router.schemas.UserSchema import UserCreate
from ..exceptions.UserException import UserHasAlreadyExistedError

from passlib.context import CryptContext

from ..repositories.UserRepository import UserQueryRepository


class UserService:
    async def add_user_or_fail(self, request_body: UserCreate):
        async with UserUnitOfWork() as uow:
            user = await uow.users.addOneUser(request_body)
            return user

class UserQueryService:
    def __init__(self):
        self.userquery_repo = UserQueryRepository()
    
    async def get_all_user(self):
        users = await self.userquery_repo.getAllUsers()
        return users
    
    async def get_user_by_uid(self, uid: str):
        user = await self.userquery_repo.getUserByUid(uid)
        return user
