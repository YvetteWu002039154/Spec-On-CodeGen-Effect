import uuid
from enum import Enum
from datetime import datetime
from typing import List, Optional, Set, Dict

class Priority(Enum):
    P4 = 1
    P3 = 2
    P2 = 3
    P1 = 4

class Status(Enum):
    TODO = "TODO"
    DONE = "DONE"

class BaseEntity:
    def __init__(self) -> None:
        self._id: uuid.UUID = uuid.uuid4()
        self._created_at: datetime = datetime.now()

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def created_at(self) -> datetime:
        return self._created_at

class Task(BaseEntity):
    def __init__(self, title: str, description: str = "", priority: Priority = Priority.P4, due_date: Optional[datetime] = None) -> None:
        super().__init__()
        if not title.strip():
            raise ValueError("Task title cannot be empty.")
        self._title: str = title
        self._description: str = description
        self._priority: Priority = priority
        self._status: Status = Status.TODO
        self._tags: Set[str] = set()
        self._due_date: Optional[datetime] = due_date
        self._completed_at: Optional[datetime] = None

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        if not value.strip():
            raise ValueError("Task title cannot be empty.")
        self._title = value

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = value

    @property
    def priority(self) -> Priority:
        return self._priority

    @priority.setter
    def priority(self, value: Priority) -> None:
        self._priority = value

    @property
    def status(self) -> Status:
        return self._status

    @property
    def tags(self) -> Set[str]:
        return self._tags

    @property
    def due_date(self) -> Optional[datetime]:
        return self._due_date

    @due_date.setter
    def due_date(self, value: Optional[datetime]) -> None:
        self._due_date = value

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    def complete(self) -> None:
        if self._status != Status.DONE:
            self._status = Status.DONE
            self._completed_at = datetime.now()

    def add_tag(self, tag: str) -> None:
        if tag.strip():
            self._tags.add(tag.strip().lower())

    def remove_tag(self, tag: str) -> None:
        self._tags.discard(tag.strip().lower())

class Project(BaseEntity):
    def __init__(self, name: str) -> None:
        super().__init__()
        if not name.strip():
            raise ValueError("Project name cannot be empty.")
        self._name: str = name
        self._tasks: Dict[uuid.UUID, Task] = {}

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if not value.strip():
            raise ValueError("Project name cannot be empty.")
        self._name = value

    def add_task(self, task: Task) -> None:
        self._tasks[task.id] = task

    def remove_task(self, task_id: uuid.UUID) -> None:
        if task_id in self._tasks:
            del self._tasks[task_id]

    def get_task(self, task_id: uuid.UUID) -> Optional[Task]:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        return list(self._tasks.values())

    def get_pending_tasks(self) -> List[Task]:
        return [t for t in self._tasks.values() if t.status == Status.TODO]

class PlantyApp:
    def __init__(self) -> None:
        self._inbox: Project = Project("Inbox")
        self._projects: Dict[uuid.UUID, Project] = {self._inbox.id: self._inbox}

    @property
    def inbox(self) -> Project:
        return self._inbox

    def create_project(self, name: str) -> Project:
        project = Project(name)
        self._projects[project.id] = project
        return project

    def get_project(self, project_id: uuid.UUID) -> Optional[Project]:
        return self._projects.get(project_id)

    def get_all_projects(self) -> List[Project]:
        return list(self._projects.values())

    def capture(self, title: str, description: str = "", priority: Priority = Priority.P4, due_date: Optional[datetime] = None) -> Task:
        task = Task(title=title, description=description, priority=priority, due_date=due_date)
        self._inbox.add_task(task)
        return task

    def organize(self, task_id: uuid.UUID, target_project_id: uuid.UUID) -> None:
        task = None
        source_project_id = None

        for pid, project in self._projects.items():
            found_task = project.get_task(task_id)
            if found_task:
                task = found_task
                source_project_id = pid
                break

        if not task:
            raise ValueError("Task not found.")
        
        if target_project_id not in self._projects:
            raise ValueError("Target project not found.")

        if source_project_id != target_project_id:
            self._projects[source_project_id].remove_task(task_id)
            self._projects[target_project_id].add_task(task)

    def get_next_actions(self) -> List[Task]:
        all_pending: List[Task] = []
        for project in self._projects.values():
            all_pending.extend(project.get_pending_tasks())

        all_pending.sort(key=lambda t: (
            -t.priority.value,
            t.due_date if t.due_date else datetime.max
        ))
        return all_pending