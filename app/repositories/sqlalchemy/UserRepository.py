from .BaseRepository import BaseRepository
from database.models.user import (
    User,
    Profile
)

class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__()
    
    def add(self, user_dict: dict, profile_dict: dict):
        user = User(**user_dict)
        profile = Profile(**profile_dict)
        user.profile = profile

        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user

        


    def update(self):
        pass

    def delete(self):
        pass

class UserQueryRepository(BaseException):
    pass