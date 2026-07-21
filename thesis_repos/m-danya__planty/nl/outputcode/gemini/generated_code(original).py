import uuid
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional

class Priority(Enum):
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4

class Label:
    def __init__(self, name: str, color: str = "#000000"):
        if not name.strip():
            raise ValueError("Label name cannot be empty.")
        self.id: uuid.UUID = uuid.uuid4()
        self.name: str = name.strip()
        self.color: str = color

class Task:
    def __init__(self, title: str, description: str = "", priority: Priority = Priority.P4, due_date: Optional[datetime] = None):
        if not title.strip():
            raise ValueError("Task title cannot be empty.")
        self.id: uuid.UUID = uuid.uuid4()
        self.title: str = title.strip()
        self.description: str = description.strip()
        self.priority: Priority = priority
        self.due_date: Optional[datetime] = due_date
        self.is_completed: bool = False
        self.created_at: datetime = datetime.now()
        self.labels: List[Label] = []

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

class Project:
    def __init__(self, name: str):
        if not name.strip():
            raise ValueError("Project name cannot be empty.")
        self.id: uuid.UUID = uuid.uuid4()
        self.name: str = name.strip()
        self.tasks: List[Task] = []
        self.created_at: datetime = datetime.now()

    def add_task(self, task: Task) -> None:
        if task not in self.tasks:
            self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        if task in self.tasks:
            self.tasks.remove(task)

    def get_tasks(self, include_completed: bool = False) -> List[Task]:
        if include_completed:
            return self.tasks
        return [t for t in self.tasks if not t.is_completed]

class HistoryLog:
    def __init__(self, action: str, entity_id: uuid.UUID, details: str):
        self.id: uuid.UUID = uuid.uuid4()
        self.timestamp: datetime = datetime.now()
        self.action: str = action
        self.entity_id: uuid.UUID = entity_id
        self.details: str = details

class PlantyApp:
    MAX_PROJECTS = 100
    MAX_LABELS = 500

    def __init__(self):
        self.inbox: Project = Project("Inbox")
        self.projects: Dict[uuid.UUID, Project] = {self.inbox.id: self.inbox}
        self.labels: Dict[uuid.UUID, Label] = {}
        self.history: List[HistoryLog] = []

    def _log(self, action: str, entity_id: uuid.UUID, details: str) -> None:
        self.history.append(HistoryLog(action, entity_id, details))

    def create_project(self, name: str) -> Project:
        if len(self.projects) >= self.MAX_PROJECTS:
            raise ValueError(f"Maximum number of projects ({self.MAX_PROJECTS}) reached.")
        project = Project(name)
        self.projects[project.id] = project
        self._log("CREATE_PROJECT", project.id, f"Created project '{project.name}'")
        return project

    def delete_project(self, project_id: uuid.UUID) -> None:
        if project_id == self.inbox.id:
            raise ValueError("Cannot delete the Inbox project.")
        project = self.projects.pop(project_id, None)
        if not project:
            raise ValueError("Project not found.")
        
        for task in project.tasks:
            self.inbox.add_task(task)
            self._log("MOVE_TASK", task.id, f"Moved task '{task.title}' to Inbox due to project deletion")
            
        self._log("DELETE_PROJECT", project_id, f"Deleted project '{project.name}'")

    def create_label(self, name: str, color: str = "#000000") -> Label:
        if len(self.labels) >= self.MAX_LABELS:
            raise ValueError(f"Maximum number of labels ({self.MAX_LABELS}) reached.")
        label = Label(name, color)
        self.labels[label.id] = label
        self._log("CREATE_LABEL", label.id, f"Created label '{label.name}'")
        return label

    def delete_label(self, label_id: uuid.UUID) -> None:
        label = self.labels.pop(label_id, None)
        if not label:
            raise ValueError("Label not found.")
        
        for project in self.projects.values():
            for task in project.tasks:
                task.remove_label(label)
                
        self._log("DELETE_LABEL", label_id, f"Deleted label '{label.name}'")

    def add_task(self, title: str, description: str = "", priority: Priority = Priority.P4, 
                 due_date: Optional[datetime] = None, project_id: Optional[uuid.UUID] = None) -> Task:
        task = Task(title, description, priority, due_date)
        target_project = self.projects.get(project_id, self.inbox) if project_id else self.inbox
        target_project.add_task(task)
        self._log("ADD_TASK", task.id, f"Added task '{task.title}' to project '{target_project.name}'")
        return task

    def complete_task(self, task_id: uuid.UUID) -> None:
        task = self._find_task(task_id)
        if not task:
            raise ValueError("Task not found.")
        task.complete()
        self._log("COMPLETE_TASK", task.id, f"Completed task '{task.title}'")

    def uncomplete_task(self, task_id: uuid.UUID) -> None:
        task = self._find_task(task_id)
        if not task:
            raise ValueError("Task not found.")
        task.uncomplete()
        self._log("UNCOMPLETE_TASK", task.id, f"Uncompleted task '{task.title}'")

    def assign_label_to_task(self, task_id: uuid.UUID, label_id: uuid.UUID) -> None:
        task = self._find_task(task_id)
        if not task:
            raise ValueError("Task not found.")
        label = self.labels.get(label_id)
        if not label:
            raise ValueError("Label not found.")
        task.add_label(label)
        self._log("ASSIGN_LABEL", task.id, f"Assigned label '{label.name}' to task '{task.title}'")

    def remove_label_from_task(self, task_id: uuid.UUID, label_id: uuid.UUID) -> None:
        task = self._find_task(task_id)
        if not task:
            raise ValueError("Task not found.")
        label = self.labels.get(label_id)
        if not label:
            raise ValueError("Label not found.")
        task.remove_label(label)
        self._log("REMOVE_LABEL", task.id, f"Removed label '{label.name}' from task '{task.title}'")

    def move_task(self, task_id: uuid.UUID, target_project_id: uuid.UUID) -> None:
        task = self._find_task(task_id)
        if not task:
            raise ValueError("Task not found.")
        
        target_project = self.projects.get(target_project_id)
        if not target_project:
            raise ValueError("Target project not found.")

        for project in self.projects.values():
            if task in project.tasks:
                project.remove_task(task)
                break
        
        target_project.add_task(task)
        self._log("MOVE_TASK", task.id, f"Moved task '{task.title}' to project '{target_project.name}'")

    def _find_task(self, task_id: uuid.UUID) -> Optional[Task]:
        for project in self.projects.values():
            for task in project.tasks:
                if task.id == task_id:
                    return task
        return None

    def get_next_actions(self) -> List[Task]:
        all_tasks = []
        for project in self.projects.values():
            all_tasks.extend(project.get_tasks(include_completed=False))
        
        all_tasks.sort(key=lambda t: (
            t.priority.value,
            t.due_date if t.due_date else datetime.max
        ))
        return all_tasks

    def get_tasks_by_label(self, label_id: uuid.UUID, include_completed: bool = False) -> List[Task]:
        label = self.labels.get(label_id)
        if not label:
            raise ValueError("Label not found.")
            
        filtered_tasks = []
        for project in self.projects.values():
            for task in project.get_tasks(include_completed):
                if label in task.labels:
                    filtered_tasks.append(task)
        return filtered_tasks

    def get_history(self) -> List[HistoryLog]:
        return sorted(self.history, key=lambda h: h.timestamp, reverse=True)