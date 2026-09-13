import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

class Label:
    def __init__(self, name: str):
        self.id: uuid.UUID = uuid.uuid4()
        self.name: str = name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Label):
            return NotImplemented
        return self.id == other.id

class Task:
    def __init__(self, title: str, description: str = "", priority: Priority = Priority.LOW, due_date: Optional[datetime] = None):
        self.id: uuid.UUID = uuid.uuid4()
        self.title: str = title
        self.description: str = description
        self.priority: Priority = priority
        self.due_date: Optional[datetime] = due_date
        self.is_completed: bool = False
        self.labels: List[Label] = []
        self.created_at: datetime = datetime.now()

    def complete(self) -> None:
        self.is_completed = True

    def uncomplete(self) -> None:
        self.is_completed = False

    def add_label(self, label: Label) -> None:
        if label not in self.labels:
            self.labels.append(label)

    def remove_label(self, label: Label) -> None:
        if label in self.labels:
            self.labels.remove(label)

    def update_details(self, title: Optional[str] = None, description: Optional[str] = None, priority: Optional[Priority] = None, due_date: Optional[datetime] = None) -> None:
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if priority is not None:
            self.priority = priority
        if due_date is not None:
            self.due_date = due_date

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Task):
            return NotImplemented
        return self.id == other.id

class Project:
    def __init__(self, name: str):
        self.id: uuid.UUID = uuid.uuid4()
        self.name: str = name
        self.tasks: List[Task] = []

    def add_task(self, task: Task) -> None:
        if task not in self.tasks:
            self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        if task in self.tasks:
            self.tasks.remove(task)

    def get_pending_tasks(self) -> List[Task]:
        return [task for task in self.tasks if not task.is_completed]

    def get_completed_tasks(self) -> List[Task]:
        return [task for task in self.tasks if task.is_completed]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Project):
            return NotImplemented
        return self.id == other.id

class PlantyApp:
    def __init__(self):
        self.inbox: Project = Project("Inbox")
        self.projects: List[Project] = [self.inbox]
        self.labels: List[Label] = []

    def add_project(self, name: str) -> Project:
        project = Project(name)
        self.projects.append(project)
        return project

    def remove_project(self, project: Project) -> None:
        if project in self.projects and project != self.inbox:
            self.projects.remove(project)

    def get_project_by_id(self, project_id: uuid.UUID) -> Optional[Project]:
        for project in self.projects:
            if project.id == project_id:
                return project
        return None

    def add_label(self, name: str) -> Label:
        label = Label(name)
        self.labels.append(label)
        return label

    def remove_label(self, label: Label) -> None:
        if label in self.labels:
            self.labels.remove(label)
            for task in self.get_all_tasks():
                task.remove_label(label)

    def get_all_tasks(self) -> List[Task]:
        all_tasks: List[Task] = []
        for project in self.projects:
            all_tasks.extend(project.tasks)
        return all_tasks

    def get_tasks_by_label(self, label: Label) -> List[Task]:
        return [task for task in self.get_all_tasks() if label in task.labels]

    def get_tasks_due_before(self, date: datetime) -> List[Task]:
        return [
            task for task in self.get_all_tasks() 
            if task.due_date and task.due_date < date and not task.is_completed
        ]

    def move_task(self, task: Task, from_project: Project, to_project: Project) -> None:
        if task in from_project.tasks:
            from_project.remove_task(task)
            to_project.add_task(task)