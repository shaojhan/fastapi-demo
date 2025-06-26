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
                'pwd':'MyPassword',
                'email': 'admin@example.com',
                'role': UserEnum.ADMIN,
                'profile': {
                    'create':{
                        'name':'ADMIN_USER',
                        'age': 9999999,
                        'description': 'THE HIGHEST AUTHORITY'
                    }
                }
                
            }
        )
        return admin_user
    except UniqueViolationError as e:
        logger.warning(e)
    except Exception as e:
        logger.error(f'發生未知錯誤：{e}')

async def create_user_profile_view(db: Prisma):
    await db.execute_raw('''
        create  or replace view user_stats as
        select u.id, u.created_at, u.uid, u.email, u."role", p."name" ,p.age, p.description
        from users u
        left join profiles p on u.id = p.user_id;
    ''')

async def main() -> None:
    await db.connect()
    await create_admin_user(db)
    await create_user_profile_view(db)
    await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())