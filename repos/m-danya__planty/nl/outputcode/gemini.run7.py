import uuid
from datetime import datetime
from typing import List, Dict, Optional, Set

class Task:
    def __init__(self, title: str, description: str = "", due_date: Optional[datetime] = None, priority: int = 4):
        self.id: str = str(uuid.uuid4())
        self.title: str = title
        self.description: str = description
        self.due_date: Optional[datetime] = due_date
        self.priority: int = priority
        self.is_completed: bool = False
        self.tags: Set[str] = set()

    def complete(self) -> None:
        self.is_completed = True

    def uncomplete(self) -> None:
        self.is_completed = False

    def add_tag(self, tag: str) -> None:
        self.tags.add(tag)

    def remove_tag(self, tag: str) -> None:
        if tag in self.tags:
            self.tags.remove(tag)

    def update_title(self, new_title: str) -> None:
        if not new_title.strip():
            raise ValueError("Task title cannot be empty.")
        self.title = new_title

    def update_description(self, new_description: str) -> None:
        self.description = new_description

    def set_priority(self, priority: int) -> None:
        if not 1 <= priority <= 4:
            raise ValueError("Priority must be between 1 (highest) and 4 (lowest).")
        self.priority = priority


class Project:
    def __init__(self, name: str):
        if not name.strip():
            raise ValueError("Project name cannot be empty.")
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.tasks: Dict[str, Task] = {}

    def add_task(self, task: Task) -> None:
        self.tasks[task.id] = task

    def remove_task(self, task_id: str) -> None:
        if task_id in self.tasks:
            del self.tasks[task_id]
        else:
            raise KeyError(f"Task with id {task_id} not found in project {self.name}.")

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
            raise ValueError("Cannot delete the Inbox project.")
        if project_id in self.projects:
            del self.projects[project_id]
        else:
            raise KeyError(f"Project with id {project_id} not found.")

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.projects.get(project_id)

    def get_all_projects(self) -> List[Project]:
        return list(self.projects.values())

    def add_task(self, title: str, description: str = "", project_id: Optional[str] = None, 
                 due_date: Optional[datetime] = None, priority: int = 4) -> Task:
        task = Task(title=title, description=description, due_date=due_date, priority=priority)
        
        if project_id and project_id in self.projects:
            self.projects[project_id].add_task(task)
        else:
            self.inbox.add_task(task)
            
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        for project in self.projects.values():
            task = project.get_task(task_id)
            if task:
                return task
        return None

    def complete_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if task:
            task.complete()
            return True
        return False

    def move_task(self, task_id: str, source_project_id: str, target_project_id: str) -> None:
        source_project = self.get_project(source_project_id)
        target_project = self.get_project(target_project_id)

        if not source_project or not target_project:
            raise ValueError("Invalid source or target project ID.")

        task = source_project.get_task(task_id)
        if not task:
            raise ValueError("Task not found in the source project.")

        source_project.remove_task(task_id)
        target_project.add_task(task)

    def get_tasks_by_context(self, tag: str) -> List[Task]:
        tagged_tasks = []
        for project in self.projects.values():
            for task in project.get_all_tasks():
                if tag in task.tags:
                    tagged_tasks.append(task)
        return tagged_tasks

    def get_next_actions(self) -> List[Task]:
        next_actions = []
        for project in self.projects.values():
            pending = project.get_pending_tasks()
            if pending:
                pending.sort(key=lambda t: (t.priority, t.due_date or datetime.max))
                next_actions.append(pending[0])
        return next_actions