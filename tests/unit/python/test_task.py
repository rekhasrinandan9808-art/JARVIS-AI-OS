from python.moa.task import Task


def test_task_creation():

    task = Task("Open Chrome")

    assert task.goal == "Open Chrome"

    assert task.status.value == "created"

    assert task.assigned_agent is None