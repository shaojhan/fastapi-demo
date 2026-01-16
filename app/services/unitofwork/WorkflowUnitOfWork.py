from sqlalchemy.orm import sessionmaker
from app.db import engine
from app.repositories.sqlalchemy.WorkflowRepository import WorkflowRepository


from SpiffWorkflow.serializer.json import JSONSerializer

class WorkflowUnitOfWork:
    def __init__(self):
        self.session_factory = sessionmaker(
            engine,
            expire_on_commit=True
        )
        self.serializer = JSONSerializer()

    def __enter__(self):
        self.session = self.session_factory()
        self.repo = WorkflowRepository(self.session)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type: self.session.rollback()
            else: self.session.commit()
        except:
            self.session.close()
    