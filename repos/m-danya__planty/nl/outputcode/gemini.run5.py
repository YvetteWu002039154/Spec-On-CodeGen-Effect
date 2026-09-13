import uuid
from enum import Enum
from datetime import datetime
from typing import List, Optional, Set, Dict

class Priority(Enum):
    URGENT = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

class Status(Enum):
    INBOX = "INBOX"
    NEXT_ACTION = "NEXT_ACTION"
    WAITING = "WAITING"
    SOMEDAY = "SOMEDAY"
    COMPLETED = "COMPLETED"

class Task:
    def __init__(self, title: str, description: str = "", priority: Priority = Priority.LOW, due_date: Optional[datetime] = None):
        if not title.strip():
            raise ValueError("Task title cannot be empty.")
        self._id: str = str(uuid.uuid4())
        self._title: str = title
        self._description: str = description
        self._priority: Priority = priority
        self._status: Status = Status.INBOX
        self._due_date: Optional[datetime] = due_date
        self._tags: Set[str] = set()
        self._created_at: datetime = datetime.now()
        self._completed_at: Optional[datetime] = None

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
    def status(self) -> Status:
        return self._status

    @property
    def due_date(self) -> Optional[datetime]:
        return self._due_date

    @due_date.setter
    def due_date(self, value: Optional[datetime]) -> None:
        self._due_date = value

    @property
    def tags(self) -> Set[str]:
        return self._tags

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    def add_tag(self, tag: str) -> None:
        if tag and tag.strip():
            self._tags.add(tag.strip().lower())

    def remove_tag(self, tag: str) -> None:
        self._tags.discard(tag.strip().lower())

    def update_status(self, new_status: Status) -> None:
        self._status = new_status
        if new_status == Status.COMPLETED:
            self._completed_at = datetime.now()
        else:
            self._completed_at = None

    def complete(self) -> None:
        self.update_status(Status.COMPLETED)


class Project:
    def __init__(self, name: str, description: str = ""):
        if not name.strip():
            raise ValueError("Project name cannot be empty.")
        self._id: str = str(uuid.uuid4())
        self._name: str = name
        self._description: str = description
        self._tasks: Dict[str, Task] = {}

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

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = value

    def add_task(self, task: Task) -> None:
        self._tasks[task.id] = task

    def remove_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.pop(task_id, None)

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        return list(self._tasks.values())

    def get_active_tasks(self) -> List[Task]:
        return [task for task in self._tasks.values() if task.status != Status.COMPLETED]


class PlantyApp:
    def __init__(self):
        self._inbox: Project = Project(name="Inbox", description="GTD Inbox for capturing ideas and tasks")
        self._projects: Dict[str, Project] = {self._inbox.id: self._inbox}

    @property
    def inbox(self) -> Project:
        return self._inbox

    def create_project(self, name: str, description: str = "") -> Project:
        project = Project(name=name, description=description)
        self._projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)

    def get_all_projects(self) -> List[Project]:
        return list(self._projects.values())

    def delete_project(self, project_id: str) -> None:
        if project_id == self._inbox.id:
            raise ValueError("Cannot delete the Inbox project.")
        if project_id in self._projects:
            del self._projects[project_id]

    def capture_task(self, title: str, description: str = "", priority: Priority = Priority.LOW, due_date: Optional[datetime] = None) -> Task:
        task = Task(title=title, description=description, priority=priority, due_date=due_date)
        self._inbox.add_task(task)
        return task

    def move_task(self, task_id: str, from_project_id: str, to_project_id: str) -> bool:
        from_project = self.get_project(from_project_id)
        to_project = self.get_project(to_project_id)

        if not from_project or not to_project:
            raise ValueError("Invalid project ID(s) provided.")

        task = from_project.remove_task(task_id)
        if task:
            to_project.add_task(task)
            return True
        return False

    def process_inbox_task(self, task_id: str, new_status: Status, target_project_id: Optional[str] = None) -> bool:
        task = self._inbox.get_task(task_id)
        if not task:
            return False
        
        task.update_status(new_status)
        
        if target_project_id and target_project_id != self._inbox.id:
            return self.move_task(task_id, self._inbox.id, target_project_id)
        return True

    def get_tasks_by_status(self, status: Status) -> List[Task]:
        tasks = []
        for project in self._projects.values():
            for task in project.get_all_tasks():
                if task.status == status:
                    tasks.append(task)
        return tasks

    def get_next_actions(self) -> List[Task]:
        return self.get_tasks_by_status(Status.NEXT_ACTION)

    def get_waiting_for(self) -> List[Task]:
        return self.get_tasks_by_status(Status.WAITING)

    def get_someday_maybe(self) -> List[Task]:
        return self.get_tasks_by_status(Status.SOMEDAY)

    def get_completed_tasks(self) -> List[Task]:
        return self.get_tasks_by_status(Status.COMPLETED)