from __future__ import annotations
import uuid
from datetime import datetime, date
from enum import Enum, auto
from typing import Optional, Set, List, Dict, Union, Iterator

class Priority(Enum):
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4

    @classmethod
    def from_value(cls, value: int) -> Priority:
        for p in cls:
            if p.value == value:
                return p
        raise ValueError(f"Priority must be between 1 and 4, got {value}")

class Label:
    def __init__(self, name: str):
        if not name.strip():
            raise ValueError("Label name cannot be empty")
        self.name: str = name.strip()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Label):
            return NotImplemented
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __repr__(self) -> str:
        return f"Label({self.name!r})"

class Task:
    def __init__(self, title: str, description: str = "", due_date: Optional[date] = None,
                 priority: Priority = Priority.P4, labels: Optional[Set[Label]] = None,
                 parent: Optional[Task] = None, project: Optional[Project] = None):
        if not title.strip():
            raise ValueError("Task title cannot be empty")
        self._id: str = str(uuid.uuid4())
        self._title: str = title.strip()
        self._description: str = description
        self._due_date: Optional[date] = None
        self.set_due_date(due_date)  # validate
        self._priority: Priority = priority
        self._labels: Set[Label] = labels or set()
        self._is_completed: bool = False
        self._completed_at: Optional[datetime] = None
        self._parent: Optional[Task] = parent
        self._project: Optional[Project] = project
        self._children: List[Task] = []  # subtasks
        self._created_at: datetime = datetime.now()
        self._updated_at: datetime = datetime.now()

    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, new_title: str):
        if not new_title.strip():
            raise ValueError("Task title cannot be empty")
        self._title = new_title.strip()
        self._updated_at = datetime.now()

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, desc: str):
        self._description = desc
        self._updated_at = datetime.now()

    @property
    def due_date(self) -> Optional[date]:
        return self._due_date

    def set_due_date(self, due_date: Optional[date]) -> None:
        if due_date is not None and due_date < date.today() and not self._is_completed:
            raise ValueError("Cannot set due date in the past for an active task")
        self._due_date = due_date
        self._updated_at = datetime.now()

    @property
    def priority(self) -> Priority:
        return self._priority

    @priority.setter
    def priority(self, value: Union[int, Priority]):
        if isinstance(value, int):
            value = Priority.from_value(value)
        self._priority = value
        self._updated_at = datetime.now()

    @property
    def labels(self) -> Set[Label]:
        return self._labels.copy()

    def add_label(self, label: Label) -> None:
        self._labels.add(label)
        self._updated_at = datetime.now()

    def remove_label(self, label: Label) -> None:
        self._labels.discard(label)
        self._updated_at = datetime.now()

    @property
    def is_completed(self) -> bool:
        return self._is_completed

    def complete(self) -> None:
        if self._is_completed:
            return
        self._is_completed = True
        self._completed_at = datetime.now()
        self._updated_at = datetime.now()

    def uncomplete(self) -> None:
        if not self._is_completed:
            return
        self._is_completed = False
        self._completed_at = None
        self._updated_at = datetime.now()

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    @property
    def parent(self) -> Optional[Task]:
        return self._parent

    @parent.setter
    def parent(self, new_parent: Optional[Task]) -> None:
        if self._parent:
            self._parent._children.remove(self)
        if new_parent:
            new_parent._children.append(self)
        self._parent = new_parent
        self._updated_at = datetime.now()

    @property
    def children(self) -> List[Task]:
        return self._children.copy()

    def add_subtask(self, task: Task) -> None:
        if task is self:
            raise ValueError("A task cannot be a subtask of itself")
        task.parent = self
        self._updated_at = datetime.now()

    def remove_subtask(self, task: Task) -> None:
        if task.parent is self:
            task.parent = None
        self._updated_at = datetime.now()

    @property
    def project(self) -> Optional[Project]:
        return self._project

    @project.setter
    def project(self, new_project: Optional[Project]) -> None:
        self._project = new_project
        self._updated_at = datetime.now()

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def __repr__(self) -> str:
        status = "✓" if self._is_completed else " "
        return f"Task({status} {self._title!r}, id={self._id[:8]})"

class Project:
    def __init__(self, name: str, is_inbox: bool = False):
        if not name.strip():
            raise ValueError("Project name cannot be empty")
        self._id: str = str(uuid.uuid4())
        self._name: str = name.strip()
        self._is_inbox: bool = is_inbox
        self._tasks: List[Task] = []

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, new_name: str):
        if not new_name.strip():
            raise ValueError("Project name cannot be empty")
        self._name = new_name.strip()

    @property
    def is_inbox(self) -> bool:
        return self._is_inbox

    def add_task(self, task: Task) -> None:
        if task.project is not None and task.project is not self:
            task.project._tasks.remove(task)
        task.project = self
        if task not in self._tasks:
            self._tasks.append(task)
        # Move sub-tasks recursively? No, individual subtasks keep their parent relationship.
        # They are not automatically added to project as separate entries.
        # Only the root task (and potentially children via parent) is in the project list.

    def remove_task(self, task: Task) -> None:
        if task in self._tasks:
            self._tasks.remove(task)
            task.project = None

    def get_all_tasks(self) -> Iterator[Task]:
        # returns all tasks directly in this project (with subtasks reachable via children)
        return iter(self._tasks)

    def __repr__(self) -> str:
        return f"Project({self._name!r}, {len(self._tasks)} tasks)"

class TaskManager:
    def __init__(self):
        self._projects: Dict[str, Project] = {}
        self._inbox: Project = Project("Inbox", is_inbox=True)
        self._projects[self._inbox.id] = self._inbox
        self._task_index: Dict[str, Task] = {}

    @property
    def inbox(self) -> Project:
        return self._inbox

    def create_project(self, name: str) -> Project:
        if name.lower() == "inbox":
            raise ValueError("Cannot create a project named 'Inbox'")
        project = Project(name)
        self._projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)

    def delete_project(self, project_id: str) -> None:
        if project_id == self._inbox.id:
            raise ValueError("Cannot delete the Inbox project")
        project = self._projects.pop(project_id, None)
        if project:
            for task in list(project.get_all_tasks()):
                task.project = None  # orphan tasks

    def add_inbox_task(self, title: str, **kwargs) -> Task:
        task = Task(title, **kwargs)
        self._inbox.add_task(task)
        self._task_index[task.id] = task
        return task

    def add_task_to_project(self, project_id: str, title: str, **kwargs) -> Optional[Task]:
        project = self._projects.get(project_id)
        if not project:
            raise ValueError(f"Project with id {project_id} not found")
        task = Task(title, **kwargs)
        project.add_task(task)
        self._task_index[task.id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._task_index.get(task_id)

    def move_task_to_project(self, task_id: str, project_id: str) -> bool:
        task = self._task_index.get(task_id)
        if not task:
            return False
        project = self._projects.get(project_id)
        if not project:
            return False
        project.add_task(task)
        return True

    def complete_task(self, task_id: str) -> bool:
        task = self._task_index.get(task_id)
        if not task:
            return False
        task.complete()
        return True

    def uncomplete_task(self, task_id: str) -> bool:
        task = self._task_index.get(task_id)
        if not task:
            return False
        task.uncomplete()
        return True

    def delete_task(self, task_id: str) -> bool:
        task = self._task_index.get(task_id)
        if not task:
            return False
        # Remove from project / parent
        if task.project:
            task.project.remove_task(task)
        if task.parent:
            task.parent.remove_subtask(task)
        # Remove children recursively? For simplicity, orphan all children.
        for child in task.children:
            child.parent = None
        del self._task_index[task_id]
        return True

    def search_tasks_by_label(self, label: Label) -> List[Task]:
        return [task for task in self._task_index.values() if label in task.labels]

    def get_all_projects(self) -> List[Project]:
        return list(self._projects.values())

    def __repr__(self) -> str:
        return f"TaskManager({len(self._projects)} projects, {len(self._task_index)} tasks)"

if __name__ == "__main__":
    # Example usage
    tm = TaskManager()
    inbox_task = tm.add_inbox_task("Buy groceries", priority=Priority.P2, due_date=date.today())
    print(inbox_task)

    project = tm.create_project("Work")
    task = tm.add_task_to_project(project.id, "Finish report", priority=Priority.P1, due_date=date(2025, 12, 31))
    task.add_label(Label("urgent"))
    task.add_subtask(Task("Draft introduction"))
    print(project, task)

    tm.complete_task(task.id)
    print(task, task.is_completed)

    # Invalid due date in past for active task
    try:
        task.set_due_date(date(2020, 1, 1))
    except ValueError as e:
        print("Error:", e)