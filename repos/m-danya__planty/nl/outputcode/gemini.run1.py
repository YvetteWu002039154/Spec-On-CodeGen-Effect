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
    def __init__(
        self, 
        title: str, 
        description: str = "", 
        priority: Priority = Priority.P4, 
        due_date: Optional[datetime] = None, 
        tags: Optional[List[str]] = None
    ):
        self.id: str = str(uuid.uuid4())
        self.title: str = title
        self.description: str = description
        self.priority: Priority = priority
        self.due_date: Optional[datetime] = due_date
        self.tags: List[str] = tags if tags is not None else []
        self.is_completed: bool = False
        self.created_at: datetime = datetime.now()
        self.completed_at: Optional[datetime] = None

    def complete(self) -> None:
        self.is_completed = True
        self.completed_at = datetime.now()

    def uncomplete(self) -> None:
        self.is_completed = False
        self.completed_at = None

class Project:
    def __init__(self, name: str):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.tasks: List[Task] = []

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> Optional[Task]:
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                return self.tasks.pop(i)
        return None

    def get_task(self, task_id: str) -> Optional[Task]:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_all_tasks(self) -> List[Task]:
        return self.tasks

    def get_pending_tasks(self) -> List[Task]:
        return [task for task in self.tasks if not task.is_completed]

class Planty:
    def __init__(self):
        self.inbox: Project = Project("Inbox")
        self.projects: Dict[str, Project] = {}

    def create_project(self, name: str) -> Project:
        project = Project(name)
        self.projects[project.id] = project
        return project

    def delete_project(self, project_id: str) -> None:
        if project_id in self.projects:
            del self.projects[project_id]

    def add_task(
        self, 
        title: str, 
        description: str = "", 
        priority: Priority = Priority.P4, 
        due_date: Optional[datetime] = None, 
        tags: Optional[List[str]] = None, 
        project_id: Optional[str] = None
    ) -> Task:
        task = Task(title, description, priority, due_date, tags)
        if project_id and project_id in self.projects:
            self.projects[project_id].add_task(task)
        else:
            self.inbox.add_task(task)
        return task

    def complete_task(self, task_id: str) -> bool:
        task = self.inbox.get_task(task_id)
        if task:
            task.complete()
            return True
            
        for project in self.projects.values():
            task = project.get_task(task_id)
            if task:
                task.complete()
                return True
                
        return False

    def move_task(self, task_id: str, target_project_id: Optional[str]) -> bool:
        task = self.inbox.remove_task(task_id)
        if not task:
            for project in self.projects.values():
                task = project.remove_task(task_id)
                if task:
                    break
        
        if not task:
            return False

        if target_project_id and target_project_id in self.projects:
            self.projects[target_project_id].add_task(task)
        else:
            self.inbox.add_task(task)
            
        return True

    def get_next_actions(self) -> List[Task]:
        actions = self.inbox.get_pending_tasks()
        for project in self.projects.values():
            actions.extend(project.get_pending_tasks())
            
        actions.sort(key=lambda t: (t.priority.value, t.created_at))
        return actions

    def get_tasks_by_tag(self, tag: str) -> List[Task]:
        matched_tasks = []
        all_projects = [self.inbox] + list(self.projects.values())
        
        for project in all_projects:
            for task in project.get_pending_tasks():
                if tag in task.tags:
                    matched_tasks.append(task)
                    
        matched_tasks.sort(key=lambda t: (t.priority.value, t.created_at))
        return matched_tasks