from .unitofwork.UserUnitOfWork import UserUnitOfWork
from ..router.schemas.UserSchema import UserSchema, UserProfileInput, UserRegistrationInput
from ..exceptions.UserException import UserHasAlreadyExistedError

from passlib.context import CryptContext
from uuid import uuid4

from app.utils.token_generator import generate_token_with_expiry

from app.repositories.sqlalchemy.UserRepository import UserQueryRepository


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    def generate_uuid(self):
        return uuid4()

    def _split_user_profile(self, user_model: UserSchema):
        registration_keys = set(UserRegistrationInput.model_fields.keys())
        profile_keys = set(UserProfileInput.model_fields.keys())
        
        user_data = user_model.model_dump()

        user_registration_dict = {k: v for k, v in user_data.items() if k in registration_keys}
        user_registration_dict['id'] = self.generate_uuid()
        profile_dict = {k: v for k, v in user_data.items() if k in profile_keys}
        
        user_registration_model = UserRegistrationInput(**user_registration_dict)
        profile_model = UserProfileInput(**profile_dict)
        
        return user_registration_model, profile_model

    def add_user_profile(self, user_model: UserSchema):
        user_registration_model, profile_model = self._split_user_profile(user_model)
        with UserUnitOfWork() as uow:
            user = uow.repo.add(user_registration_model.model_dump(), profile_model.model_dump())
            uow.commit()
            return user
    



class UserQueryService:
    def __init__(self):
        self.userquery_repo = UserQueryRepository()

        