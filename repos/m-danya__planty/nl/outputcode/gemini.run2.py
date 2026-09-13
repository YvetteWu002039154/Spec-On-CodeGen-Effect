from typing import List, Optional
from datetime import datetime
import uuid

class Task:
    def __init__(self, title: str, description: str = ""):
        self.id: str = str(uuid.uuid4())
        self.title: str = title
        self.description: str = description
        self.is_completed: bool = False
        self.created_at: datetime = datetime.now()
        self.due_date: Optional[datetime] = None
        self.labels: List[str] = []
        self.priority: int = 4

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

    def set_due_date(self, due_date: datetime) -> None:
        self.due_date = due_date

    def set_priority(self, priority: int) -> None:
        if 1 <= priority <= 4:
            self.priority = priority
        else:
            raise ValueError("Priority must be between 1 and 4")


class Project:
    def __init__(self, name: str):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.tasks: List[Task] = []

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        self.tasks = [t for t in self.tasks if t.id != task_id]

    def get_task(self, task_id: str) -> Optional[Task]:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_tasks(self, include_completed: bool = False) -> List[Task]:
        if include_completed:
            return self.tasks
        return [t for t in self.tasks if not t.is_completed]


class Planty:
    def __init__(self):
        self.inbox: Project = Project("Inbox")
        self.projects: List[Project] = []

    def add_project(self, name: str) -> Project:
        if self.get_project(name):
            raise ValueError(f"Project with name '{name}' already exists.")
        project = Project(name)
        self.projects.append(project)
        return project

    def get_project(self, name: str) -> Optional[Project]:
        if name.lower() == "inbox":
            return self.inbox
        for project in self.projects:
            if project.name.lower() == name.lower():
                return project
        return None

    def capture_task(self, title: str, description: str = "") -> Task:
        task = Task(title, description)
        self.inbox.add_task(task)
        return task

    def move_task(self, task_id: str, source_project_name: str, target_project_name: str) -> None:
        source = self.get_project(source_project_name)
        target = self.get_project(target_project_name)
        
        if not source or not target:
            raise ValueError("Source or target project not found")

        task_to_move = source.get_task(task_id)
        
        if task_to_move:
            source.remove_task(task_id)
            target.add_task(task_to_move)
        else:
            raise ValueError("Task not found in source project")

    def get_next_actions(self) -> List[Task]:
        next_actions = []
        next_actions.extend(self.inbox.get_tasks())
        for project in self.projects:
            next_actions.extend(project.get_tasks())
        
        next_actions.sort(key=lambda t: (t.priority, t.created_at))
        return next_actions

    def get_tasks_by_label(self, label: str) -> List[Task]:
        tasks_with_label = []
        all_tasks = self.get_next_actions()
        for task in all_tasks:
            if label in task.labels:
                tasks_with_label.append(task)
        return tasks_with_label