import prisma
from prisma import errors
import pytest

from app.repositories.BaseRepository import db

# prisma.register(db)

@pytest.mark.asyncio
async def test_catches_not_connected() -> None:
    """Trying to make a query before connection"""
    client = db
    with pytest.raises(errors.ClientNotConnectedError) as exc:
        await client.user.delete_many()
    assert 'connect()' in str(exc)