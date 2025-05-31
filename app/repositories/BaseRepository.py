from prisma import Prisma
from urllib.parse import urlparse
from loguru import logger

from socket import socket, AF_INET, SOCK_STREAM, SHUT_RDWR
from app.config import get_settings
from app.exceptions.BaseException import DatabaseException

DEFAULT_ORDER_BY = {'created_at': 'desc'}
MAX_RECORDS_LIMIT = 10

settings = get_settings()
db = Prisma(log_queries=False, auto_register=True)

class BaseRepository():
    def __init__(self):
        self.prisma = db
        self._options : dict = {
            "take": MAX_RECORDS_LIMIT,
            "order": DEFAULT_ORDER_BY
        }
    
    def test_db_conn():
        db_url = urlparse(url=settings.DATABASE_URL)
        db_hostname = db_url.hostname
        db_port = db_url.port
        try:
            s = socket(AF_INET, SOCK_STREAM)
            s.connect((db_hostname, db_port))
            s.shutdown(SHUT_RDWR)
            s.close()
        except OSError as e:
            logger.error(e)
            raise DatabaseException