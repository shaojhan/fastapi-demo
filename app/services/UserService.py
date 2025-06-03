from .UnitOfWork import UserUnitOfWork
from ..router.schemas.UserSchema import UserCreate
from ..exceptions.UserException import UserHasAlreadyExistedError

class UserService:
    async def add_user_or_fail(self, request_body: UserCreate):
        async with UserUnitOfWork() as uow:
            user = await uow.users.addOneUser(request_body)
            return user
