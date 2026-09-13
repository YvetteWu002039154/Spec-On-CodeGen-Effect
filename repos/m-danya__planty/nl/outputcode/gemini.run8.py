import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict

class Priority(Enum):
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4

class Task:
    def __init__(self, title: str, description: str = "", due_date: Optional[datetime] = None, priority: Priority = Priority.P4):
        self.id: str = str(uuid.uuid4())
        self.title: str = title
        self.description: str = description
        self.due_date: Optional[datetime] = due_date
        self.priority: Priority = priority
        self.is_completed: bool = False
        self.labels: List[str] = []

    def complete(self) -> None:
        self.is_completed = True

    def uncomplete(self) -> None:
        self.is_completed = False

    def add_label(self, label: str) -> None:
        if label not in self.labels:
            self.labels.append(label)

    def remove_label(self, label: str) -> None:
        if label in self.labels:
            self.labels.remove(label)

class Project:
    def __init__(self, name: str):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.tasks: Dict[str, Task] = {}

    def add_task(self, task: Task) -> None:
        self.tasks[task.id] = task

    def remove_task(self, task_id: str) -> None:
        if task_id in self.tasks:
            del self.tasks[task_id]

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        return list(self.tasks.values())

    def get_pending_tasks(self) -> List[Task]:
        return [task for task in self.tasks.values() if not task.is_completed]

class Planty:
    def __init__(self):
        self.inbox: Project = Project(name="Inbox")
        self.projects: Dict[str, Project] = {self.inbox.id: self.inbox}

    def create_project(self, name: str) -> Project:
        project = Project(name=name)
        self.projects[project.id] = project
        return project

    def delete_project(self, project_id: str) -> None:
        if project_id in self.projects and project_id != self.inbox.id:
            del self.projects[project_id]

    def add_task(self, title: str, description: str = "", project_id: Optional[str] = None) -> Task:
        task = Task(title=title, description=description)
        target_project = self.projects.get(project_id, self.inbox) if project_id else self.inbox
        target_project.add_task(task)
        return task

    def move_task(self, task_id: str, from_project_id: str, to_project_id: str) -> None:
        if from_project_id in self.projects and to_project_id in self.projects:
            from_proj = self.projects[from_project_id]
            to_proj = self.projects[to_project_id]
            task = from_proj.get_task(task_id)
            if task:
                from_proj.remove_task(task_id)
                to_proj.add_task(task)

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.projects.get(project_id)