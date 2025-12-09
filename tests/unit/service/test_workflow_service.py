from SpiffWorkflow.task import Task
from SpiffWorkflow.workflow import Workflow
from SpiffWorkflow.specs.WorkflowSpec import WorkflowSpec
from SpiffWorkflow.specs.ExclusiveChoice import ExclusiveChoice
from SpiffWorkflow.specs.Cancel import Cancel
from SpiffWorkflow.specs.Simple import Simple
from SpiffWorkflow.operators import Equal, Attrib

import pytest

def send_email(msg, *args, **kwargs):
    print(f'Email Sended: {msg}')

class RegistorWorkflow(WorkflowSpec):
    def __init__(self, name=None, filename=None, addstart=True):
        super().__init__(name, filename, addstart)

        # After sending the email, waiting the user's confirmation
        send_email = Simple(wf_spec=self, name='send_email')
        self.start.connect(send_email)
        send_email.completed_event.connect(callback=send_email)

        # User should confirm manually
        user_click_email_link = ExclusiveChoice(wf_spec=self, name='user_confirmation', manual=True)
        user_click_email_link.connect(send_email)

        # Let the default of user confirmation be cancelled 
        cancel = Cancel(wf_spec=self, name='workflow_aborted')
        user_click_email_link.connect(cancel)

        # Otherwise, we will ask the user to make confirmation
        cond = Equal(Attrib(name='user_confirmation'), True)
        user_click_email_link.connect_if(condition=cond, task_spec=user_click_email_link)



def test_create_a_workflow():
    pass