from loguru import logger
import logging
import asyncio

from prisma import Prisma
from prisma.enums import UserEnum
from prisma.errors import UniqueViolationError


logger.add(
    sink='./logs/fastapi-{time:YYYY-MM-DD}.log',
    level=logging.DEBUG,
    rotation='10MB'
)

db = Prisma(log_queries=True, auto_register=True)

async def create_admin_user(db: Prisma) -> None:
    try:
        admin_user = await db.user.create(
            data={
                'uid':'ADMIN',
                'name':'ADMIN',
                'age':18,
                'pwd':'MyPassword',
                'email': 'admin@example.com',
                'role': UserEnum.ADMIN
            }
        )
        return admin_user
    except Exception as e:
        logger.warning(e)


async def create_user_profile_view():
    await db.execute_raw('''
        
    ''')

async def main() -> None:
    await db.connect()
    await create_admin_user(db)
    await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())