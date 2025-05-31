from ..repositories.UserRepository import UserRepository
from ..repositories.BaseRepository import db

class UserUnitOfWork:
    def __init__(self):
        self.tx_manager = db.tx()
        self.tx = None
        self.users: UserRepository = None
    
    async def __aenter__(self):
        self.tx = await self.tx_manager.__aenter__()
        self.users = UserRepository(self.tx)
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.tx_manager.__aexit__(exc_type, exc_val, exc_tb)
