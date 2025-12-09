from enum import Enum
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from typing import Optional


from pydantic import (
    BaseModel as PydanticBaseModel,
    Field,
    ConfigDict
)


from SpiffWorkflow import Workflow
from SpiffWorkflow.specs.WorkflowSpec import WorkflowSpec
from SpiffWorkflow.task import Task, TaskState
from SpiffWorkflow.specs.base import TaskSpec
class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

class TaskStateEnum(str, Enum):
    """
    PREDICTED Tasks
    - MAYBE
    - LIKELY

    DEFINITE Tasks
    - FUTURE
    - WAITING
    - STARTED

    FINISHED Tasks
    - COMPLETED
    - ERROR
    - CANCELLED
    """
    MAYBE = 'MAYBE'
    LIKELY = 'LIKELY'
    FUTURE = 'FUTURE'
    WAITING = 'WAITING'
    READY = 'RAEDY'
    STARTED = 'STARTED'
    COMPLETED = 'COMPLETED'
    ERROR = 'ERROR'
    CANCELLED = 'CANCELLED'

    @classmethod
    def convert_to_task_state(cls, state):
        match state:
            case 'MAYBE': return TaskState.MAYBE
            case 'LIKELY': return TaskState.LIKELY
            case 'FUTURE': return TaskState.FUTURE
            case 'WAITING': return TaskState.WAITING
            case 'READY': return TaskState.READY
            case 'STARTED': return TaskState.STARTED
            case 'COMPLETED': return TaskState.COMPLETED
            case 'ERROR': return TaskState.ERROR
            case 'CANCELLED': return TaskState.CANCELLED
            case _: return TaskState.ANY_MASK

######### Workflow Spec ##########

class TaskSpecRead(BaseModel):
    """
        - id (UUID): a unique identifierfor this task
        - workflow (`Workflow`): the workflow associated with this task
        - parent (`Task`): the parent of this task
        - children (list(`Task`)): the children of this task
        - triggered (bool): True if the task is not part of output specification of the task spec
        - task_spec (`TaskSpec`): the spec associated with this task
        - thread_id (int): a thread id for this task
        - data (dict): a dictionary containing data for this task
        - internal_data (dict): a dictionary containing information relevant to the task state or execution
        - last_state_change (float): the timestamp when this task last changed state
        - thread_id (int): a thread identifier
    """
    data: dict
    name: str = Field(examples=['Start', 'workflow_aborted'])
    inputs: list[str] = Field(examples=[['Start']])
    manual: bool
    defines: dict
    outputs: list[str] = Field(examples=[['workflow_aborted']])
    lookahead: int
    pre_assign: list
    description: Optional[str] = Field(examples=[''])
    post_assign: list = Field(examples=[[]])

class WorkflowSpecRead(BaseModel):
    file: Optional[str]
    name: str
    task_specs: dict
    description: str


class WorkflowInstanceRead(BaseModel):
    """
        - spec : WorkflowSpec
        the spec that describes this workflow instance
        - data : dict
        the data associated with the workflow
        - locks : dict
        a dictionary holding locaks used by Mutex tasks
        - last_task : Task
        the last successfully completed task
        - success : bool
        whether the workflow was successful
        - tasks : dict(id, Task)
        a mapping of task ids to tasks
        - task_tree : Task
        the root task of this workflow's task tree
        - completed_event : Event
        an event holding callbacks to be run when the workflow completes
    """
    spec: WorkflowSpec
    data: dict
    last_task: Task
    success: bool
    tasks: dict[int, Task]
    task_tree: Task
    event: str

class WorkflowInstanceTaskRead(BaseModel):
    id: UUID
    data: dict
    state: TaskStateEnum
    parent: Optional[UUID]
    task_spec: str
    triggered: bool
    internal_data: dict
    last_state_change: Decimal
    children: list[str]

class WorkflowInstanceTaskTreeRead(BaseModel):
    id: dict[str, str] = Field(examples=[{'__uuid__': ''}])
    data: dict
    state: int
    parent: Optional[dict[str, str]] = Field(examples=[{'__uuid__': ''}])
    task_spec: str
    triggered: bool
    internal_data: dict
    last_state_change: Decimal
    children: list['WorkflowInstanceTaskTreeRead']



class WorkflowRead(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]

    workflow_spec_name: str
    workflow_spec_json: Optional[WorkflowSpec]