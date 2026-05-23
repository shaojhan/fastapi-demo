from SpiffWorkflow.serializer.json import JSONSerializer

from app.repositories.sqlalchemy.WorkflowRepository import WorkflowRepository
from app.services.unitofwork.base import BaseUnitOfWork


class WorkflowUnitOfWork(BaseUnitOfWork):
    """Unit of Work for workflow write operations.

    Uses ``expire_on_commit=True`` so persisted objects are refreshed after commit.
    """

    expire_on_commit = True

    def __init__(self):
        super().__init__()
        self.serializer = JSONSerializer()

    def _setup_repositories(self, session):
        self.repo = WorkflowRepository(session)
