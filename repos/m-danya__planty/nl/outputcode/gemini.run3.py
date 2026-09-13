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
    def __init__(self, title: str, description: str = "", priority: Priority = Priority.P4, due_date: Optional[datetime] = None):
        if not title.strip():
            raise ValueError("Task title cannot be empty.")
        self._id: str = str(uuid.uuid4())
        self._title: str = title
        self._description: str = description
        self._priority: Priority = priority
        self._due_date: Optional[datetime] = due_date
        self._labels: List[str] = []
        self._is_completed: bool = False
        self._created_at: datetime = datetime.now()

    @property
    def id(self) -> str:
        return self._id

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
    def due_date(self) -> Optional[datetime]:
        return self._due_date

    @due_date.setter
    def due_date(self, value: Optional[datetime]) -> None:
        self._due_date = value

    @property
    def labels(self) -> List[str]:
        return self._labels

    def add_label(self, label: str) -> None:
        if label not in self._labels:
            self._labels.append(label)

    def remove_label(self, label: str) -> None:
        if label in self._labels:
            self._labels.remove(label)

    @property
    def is_completed(self) -> bool:
        return self._is_completed

    def complete(self) -> None:
        self._is_completed = True

    def uncomplete(self) -> None:
        self._is_completed = False

    @property
    def created_at(self) -> datetime:
        return self._created_at


class Project:
    def __init__(self, name: str):
        if not name.strip():
            raise ValueError("Project name cannot be empty.")
        self._id: str = str(uuid.uuid4())
        self._name: str = name
        self._tasks: List[Task] = []

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if not value.strip():
            raise ValueError("Project name cannot be empty.")
        self._name = value

    def add_task(self, task: Task) -> None:
        if task not in self._tasks:
            self._tasks.append(task)

    def remove_task(self, task: Task) -> None:
        if task in self._tasks:
            self._tasks.remove(task)

    def get_tasks(self, include_completed: bool = False) -> List[Task]:
        if include_completed:
            return self._tasks.copy()
        return [task for task in self._tasks if not task.is_completed]


class Planty:
    def __init__(self):
        self._inbox: Project = Project("Inbox")
        self._projects: Dict[str, Project] = {self._inbox.id: self._inbox}

    @property
    def inbox(self) -> Project:
        return self._inbox

    def create_project(self, name: str) -> Project:
        project = Project(name)
        self._projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)

    def delete_project(self, project_id: str) -> None:
        if project_id == self._inbox.id:
            raise ValueError("Cannot delete the Inbox project.")
        if project_id in self._projects:
            del self._projects[project_id]

    def get_all_projects(self) -> List[Project]:
        return list(self._projects.values())

    def add_task(self, title: str, description: str = "", priority: Priority = Priority.P4, 
                 due_date: Optional[datetime] = None, project_id: Optional[str] = None) -> Task:
        task = Task(title=title, description=description, priority=priority, due_date=due_date)
        
        if project_id and project_id in self._projects:
            self._projects[project_id].add_task(task)
        else:
            self._inbox.add_task(task)
            
        return task

    def get_next_actions(self) -> List[Task]:
        all_pending_tasks = []
        for project in self._projects.values():
            all_pending_tasks.extend(project.get_tasks(include_completed=False))
        
        all_pending_tasks.sort(key=lambda t: (
            t.priority.value, 
            t.due_date if t.due_date else datetime.max
        ))
        
        return all_pending_tasks

    def get_tasks_by_label(self, label: str) -> List[Task]:
        tasks_with_label = []
        for project in self._projects.values():
            for task in project.get_tasks(include_completed=False):
                if label in task.labels:
                    tasks_with_label.append(task)
        return tasks_with_label