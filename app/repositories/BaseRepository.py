from prisma import Prisma

DEFAULT_ORDER_BY = {'created_at': 'desc'}
MAX_RECORDS_LIMIT = 10

db = Prisma(log_queries=False, auto_register=True)

class BaseRepository():
    def __init__(self):
        self.prisma = db
        self._options : dict = {
            "take": MAX_RECORDS_LIMIT,
            "order": DEFAULT_ORDER_BY
        }