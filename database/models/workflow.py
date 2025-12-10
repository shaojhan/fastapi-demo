from sqlalchemy.orm import (
    relationship,
    Mapped,
    mapped_column,
    
)

from sqlalchemy import (
    Column,
    ForeignKey,
    Enum as SqlEnum,
    UUID,
    DateTime,
    Integer,
    String,
    Boolean,
    JSON,
    DECIMAL
)

from sqlalchemy import func

from uuid import UUID
from datetime import datetime
from typing import Any

from app.database import Base
from sqlalchemy import Uuid


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)
    
    workflow_spec_name: Mapped[str] = mapped_column(String(64), nullable=False)
    workflow_spec_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    workflow_instance_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)



# class WorkflowTask(Base):
#     __tablename__ = "workflow_tasks"
