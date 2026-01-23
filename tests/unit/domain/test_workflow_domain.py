# from SpiffWorkflow.specs.WorkflowSpec import WorkflowSpec
# from SpiffWorkflow.specs.ExclusiveChoice import ExclusiveChoice
# from SpiffWorkflow.specs.Cancel import Cancel
# from SpiffWorkflow.specs.Simple import Simple
# from SpiffWorkflow.specs.base import TaskSpec
# from SpiffWorkflow.specs.StartTask import StartTask

# from SpiffWorkflow.operators import Equal, Attrib


# def my_nuclear_strike(msg, *args, **kwargs):
#     print("Launched: ", msg)

# # Define workflow spec
# class NuclearStrikeWorkflowSpec(WorkflowSpec):
#     def __init__(self):
#         super().__init__()
#         self.start = StartTask(wf_spec=self)

#         general_choice = ExclusiveChoice(wf_spec=self, name='general')
#         self.start.connect(task_spec=general_choice)

#         cancel = Cancel(wf_spec=self, name='workflow_aborted')
#         general_choice.connect(taskspec=cancel)

#         president_choice = ExclusiveChoice(wf_spec=self, name='president')
#         cond = Equal(Attrib(name='confirmation'), 'yes')

#         strike = Simple(wf_spec=self, name='nuclear_strike')
#         president_choice.connect_if(condition=cond, task_spec=strike)

#         strike.completed_event.connect(callback=my_nuclear_strike)
        
# from SpiffWorkflow.workflow import Workflow
# from SpiffWorkflow.task import Task, TaskStates

# workflow_instance = Workflow(workflow_spec=NuclearStrikeWorkflowSpec())
# workflow_instance.dump()

# workflow_instance.get_tasks(first_task='Start')
