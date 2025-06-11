from loguru import logger

from ..repositories.BaseRepository import BaseRepository
from ..router.schemas.UserSchema import UserCreate
from ..exceptions.UserException import UserHasAlreadyExistedError
from ..infrastructure.cache import redis_cache

from prisma.errors import UniqueViolationError
from prisma.actions import UserActions, ProfileActions


from typing import Protocol

class UserTxClient(Protocol):
    user: UserActions
    profile: ProfileActions

class UserRepository(BaseRepository):
    def __init__(self, tx: UserTxClient):
        super().__init__()
        self.prisma = tx
        self.user = self.prisma.user
        self.profile = self.prisma.profile

    async def addOneUser(self, request_body: UserCreate):
        logger.debug('Creating user...')
        userData = request_body.model_dump()
        profileFields = ["name", "age", "description"]
        profileData = {}
        for field in profileFields:
            profileData[field] = userData.pop(field, None)
        userData['profile'] = {'create':profileData}
        try:
            newUser = await self.user.create(data=userData, include={'profile':True})
            return newUser
        except UniqueViolationError:
            raise UserHasAlreadyExistedError("User has already existed!")
    
    async def updateUser(self, userId, newPassword):
        return await self.user.update(
            data={'pwd': newPassword},
            where={'id':userId}
            )
        
class UserQueryRepository(BaseRepository):
    def __init__(self):
        super().__init__()
        self.user = self.prisma.user
    
    
    async def getUserById(self, uuid):
        return await self.user.find_unique(where={'id': uuid}, include={'profile': True})
    
    @redis_cache(prefix="get_all_users", ttl=60)
    async def getAllUsers(self):
        return await self.user.find_many()

