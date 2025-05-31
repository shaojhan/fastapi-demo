from loguru import logger

from ..repositories.BaseRepository import BaseRepository
from ..router.schemas.UserModel import UserCreate
from ..exceptions.UserException import UserHasAlreadyExistedError, UserException

class UserRepository(BaseRepository):
    def __init__(self, tx):
        super().__init__()
        self.user = self.prisma.user
        self.profile = self.prisma.profile
        self.tx = tx
    
    async def getAllUsers(self):
        return await self.user.find_many()
    
    async def addOneUser(self, request_body: UserCreate):
        logger.debug('Creating user...')
        userData = request_body.model_dump()
        profileFields = ["name", "age", "description"]
        profileData = {}
        for field in profileFields:
            profileData[field] = userData.pop(field, None)
        userData['profile'] = {'create':profileData}
        try:
            newUser = await self.tx.user.create(data=userData, include={'profile':True})
            return newUser
        except Exception as e:
            raise UserException(f"{e}")
    
    async def updateUser(self, userId, newPassword):
        return await self.user.update(
            data={'pwd': newPassword},
            where={'id':userId}
            )