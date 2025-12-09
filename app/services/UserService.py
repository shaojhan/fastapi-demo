from .unitofwork.UserUnitOfWork import UserUnitOfWork
from ..router.schemas.UserSchema import UserCreate, UserProfileInput, UserRegistrationInput
from ..exceptions.UserException import UserHasAlreadyExistedError

from passlib.context import CryptContext
import uuid

class UserService:
    def _split_user_profile(self, user_model: UserCreate):
        user_registration_keys_set = set(UserRegistrationInput.model_fields.keys())
        profile_keys_set = set(UserProfileInput.model_fields.keys())
        user_registration_dict = user_model.model_dump(exclude=profile_keys_set)
        profile_dict = user_model.model_dump(exclude=user_registration_keys_set)

        user_registration_model = UserRegistrationInput(**user_registration_dict)
        profile_model = UserProfileInput(**profile_dict)
        
        return user_registration_model, profile_model

    def add_user_profile(self, user_model: UserCreate):
        return self._split_user_profile(user_model)
        with UserUnitOfWork() as uow:
            user = uow.repo.add()
            return user



# class UserQueryService:
#     def __init__(self):
#         self.userquery_repo = UserQueryRepository()
    
#     async def get_all_user(self):
#         users = await self.userquery_repo.getAllUsers()
#         return users
    
#     async def get_user_by_uid(self, uid: str):
#         user = await self.userquery_repo.getUserByUid(uid)
#         return user
    
#     async def get_user_view(self):
#         users = await self.userquery_repo.getAllUserView()
#         return users
