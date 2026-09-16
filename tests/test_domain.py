from ai_scientist.domain import Status, Task


def test_task_serializes_enum() -> None:
    task = Task(id="TASK-1", title="Test", status=Status.IN_PROGRESS)
    assert task.to_dict()["status"] == "in_progress"
    assert task.kind == "task"

