from datetime import datetime
from typing import List, Dict, Optional, Set
import uuid

class Task:
    def __init__(self, title: str, description: str = "", due_date: Optional[datetime] = None, priority: int = 4):
        if not title.strip():
            raise ValueError("Task title cannot be empty")
        if not (1 <= priority <= 4):
            raise ValueError("Priority must be between 1 (highest) and 4 (lowest)")
            
        self.id: str = str(uuid.uuid4())
        self.title: str = title.strip()
        self.description: str = description
        self.created_at: datetime = datetime.now()
        self.due_date: Optional[datetime] = due_date
        self.priority: int = priority
        self.is_completed: bool = False
        self.tags: Set[str] = set()

    def complete(self) -> None:
        self.is_completed = True

    def uncomplete(self) -> None:
        self.is_completed = False

    def add_tag(self, tag: str) -> None:
        if tag.strip():
            self.tags.add(tag.strip().lower())

    def remove_tag(self, tag: str) -> None:
        self.tags.discard(tag.strip().lower())

    def update(self, 
               title: Optional[str] = None, 
               description: Optional[str] = None, 
               due_date: Optional[datetime] = None, 
               priority: Optional[int] = None) -> None:
        if title is not None:
            if not title.strip():
                raise ValueError("Task title cannot be empty")
            self.title = title.strip()
            
        if description is not None:
            self.description = description
            
        if due_date is not None:
            self.due_date = due_date
            
        if priority is not None:
            if not (1 <= priority <= 4):
                raise ValueError("Priority must be between 1 and 4")
            self.priority = priority


class Project:
    def __init__(self, name: str):
        if not name.strip():
            raise ValueError("Project name cannot be empty")
            
        self.id: str = str(uuid.uuid4())
        self.name: str = name.strip()
        self.tasks: Dict[str, Task] = {}

    def add_task(self, task: Task) -> None:
        self.tasks[task.id] = task

    def remove_task(self, task_id: str) -> None:
        if task_id in self.tasks:
            del self.tasks[task_id]
        else:
            raise KeyError(f"Task with id {task_id} not found in project '{self.name}'")

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        return list(self.tasks.values())

    def get_pending_tasks(self) -> List[Task]:
        return [task for task in self.tasks.values() if not task.is_completed]

    def get_completed_tasks(self) -> List[Task]:
        return [task for task in self.tasks.values() if task.is_completed]


class Planty:
    def __init__(self):
        self.inbox: Project = Project(name="Inbox")
        self.projects: Dict[str, Project] = {self.inbox.id: self.inbox}

    def create_project(self, name: str) -> Project:
        project = Project(name=name)
        self.projects[project.id] = project
        return project

    def delete_project(self, project_id: str) -> None:
        if project_id == self.inbox.id:
            raise ValueError("Cannot delete the default Inbox project")
        if project_id in self.projects:
            del self.projects[project_id]
        else:
            raise KeyError(f"Project with id {project_id} not found")

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.projects.get(project_id)

    def capture_task(self, title: str, description: str = "", due_date: Optional[datetime] = None, priority: int = 4) -> Task:
        task = Task(title=title, description=description, due_date=due_date, priority=priority)
        self.inbox.add_task(task)
        return task

    def move_task(self, task_id: str, from_project_id: str, to_project_id: str) -> None:
        if from_project_id not in self.projects:
            raise KeyError(f"Source project {from_project_id} not found")
        if to_project_id not in self.projects:
            raise KeyError(f"Destination project {to_project_id} not found")
            
        from_project = self.projects[from_project_id]
        to_project = self.projects[to_project_id]
        
        task = from_project.get_task(task_id)
        if not task:
            raise KeyError(f"Task {task_id} not found in source project")
            
        from_project.remove_task(task_id)
        to_project.add_task(task)

    def get_tasks_by_context(self, tag: str) -> List[Task]:
        matched_tasks = []
        search_tag = tag.strip().lower()
        for project in self.projects.values():
            for task in project.get_pending_tasks():
                if search_tag in task.tags:
                    matched_tasks.append(task)
        return matched_tasks

    def get_next_actions(self) -> List[Task]:
        all_pending = []
        for project in self.projects.values():
            all_pending.extend(project.get_pending_tasks())
        
        all_pending.sort(key=lambda t: (t.priority, t.due_date or datetime.max, t.created_at))
        return all_pending