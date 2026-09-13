from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, Set

class Priority(Enum):
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4

class Project:
    def __init__(self, name: str, color: str = "#808080", order: int = 0, is_inbox: bool = False):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.color: str = color
        self.order: int = order
        self.is_inbox: bool = is_inbox
        self.is_archived: bool = False
        self.created_at: datetime = datetime.now()

    def __repr__(self) -> str:
        return f"Project(id={self.id!r}, name={self.name!r}, archived={self.is_archived})"

class Label:
    def __init__(self, name: str, color: str = "#808080"):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.color: str = color

    def __repr__(self) -> str:
        return f"Label(id={self.id!r}, name={self.name!r})"

class Comment:
    def __init__(self, task_id: str, content: str, author: str = "user"):
        self.id: str = str(uuid.uuid4())
        self.task_id: str = task_id
        self.content: str = content
        self.author: str = author
        self.created_at: datetime = datetime.now()

    def __repr__(self) -> str:
        return f"Comment(id={self.id!r}, task_id={self.task_id!r}, author={self.author!r})"

class Task:
    def __init__(
        self,
        title: str,
        project_id: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        priority: Optional[Priority] = None,
        due_date: Optional[datetime] = None,
        description: str = ""
    ):
        self.id: str = str(uuid.uuid4())
        self.title: str = title
        self.description: str = description
        self.priority: Optional[Priority] = priority
        self.due_date: Optional[datetime] = due_date
        self.is_completed: bool = False
        self.completed_at: Optional[datetime] = None
        self.project_id: Optional[str] = project_id
        self.parent_task_id: Optional[str] = parent_task_id
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.labels: Set[str] = set()
        self.comments: List[Comment] = []
        self.subtasks: List[Task] = []  # maintained by manager

    def complete(self) -> None:
        if not self.is_completed:
            self.is_completed = True
            self.completed_at = datetime.now()
            self.updated_at = datetime.now()
            # If this task is a parent, complete all subtasks recursively
            for subtask in self.subtasks:
                subtask.complete()

    def uncomplete(self) -> None:
        if self.is_completed:
            self.is_completed = False
            self.completed_at = None
            self.updated_at = datetime.now()
            # Keep subtasks as they are; GTD often uncompletes only the parent.

    def add_label(self, label_id: str) -> None:
        self.labels.add(label_id)

    def remove_label(self, label_id: str) -> None:
        self.labels.discard(label_id)

    def add_comment(self, content: str, author: str = "user") -> Comment:
        comment = Comment(self.id, content, author)
        self.comments.append(comment)
        self.updated_at = datetime.now()
        return comment

    def update(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[Priority] = None,
        due_date: Optional[datetime] = None,
        project_id: Optional[str] = None,
    ) -> None:
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if priority is not None:
            self.priority = priority
        if due_date is not None:
            self.due_date = due_date
        if project_id is not None:
            self.project_id = project_id
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return f"Task(id={self.id!r}, title={self.title!r}, completed={self.is_completed})"

class TaskManager:
    def __init__(self):
        self.projects: dict[str, Project] = {}
        self.tasks: dict[str, Task] = {}
        self.labels: dict[str, Label] = {}
        self.comments: dict[str, Comment] = {}

        # Create default inbox project
        self.create_project(name="Inbox", is_inbox=True, color="#FFD700")

    def create_project(self, name: str, color: str = "#808080", order: Optional[int] = None, is_inbox: bool = False) -> Project:
        if order is None:
            order = len(self.projects)
        project = Project(name, color, order, is_inbox)
        self.projects[project.id] = project
        return project

    def archive_project(self, project_id: str) -> None:
        if project_id not in self.projects:
            raise ValueError("Project not found")
        project = self.projects[project_id]
        project.is_archived = True

    def unarchive_project(self, project_id: str) -> None:
        if project_id not in self.projects:
            raise ValueError("Project not found")
        project = self.projects[project_id]
        project.is_archived = False

    def delete_project(self, project_id: str) -> None:
        if project_id not in self.projects:
            raise ValueError("Project not found")
        # Optionally reassign or delete tasks? Here we detach tasks from project.
        for task in self.tasks.values():
            if task.project_id == project_id:
                task.project_id = None
        del self.projects[project_id]

    def create_task(
        self,
        title: str,
        project_id: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        priority: Optional[Priority] = None,
        due_date: Optional[datetime] = None,
        description: str = ""
    ) -> Task:
        if project_id is not None and project_id not in self.projects:
            raise ValueError("Project not found")
        if parent_task_id is not None and parent_task_id not in self.tasks:
            raise ValueError("Parent task not found")
        if due_date is not None and due_date < datetime.now():
            raise ValueError("Due date cannot be in the past")

        task = Task(title, project_id, parent_task_id, priority, due_date, description)
        self.tasks[task.id] = task

        # Add as subtask to parent
        if parent_task_id:
            parent = self.tasks[parent_task_id]
            parent.subtasks.append(task)

        return task

    def complete_task(self, task_id: str) -> None:
        if task_id not in self.tasks:
            raise ValueError("Task not found")
        task = self.tasks[task_id]
        task.complete()

    def uncomplete_task(self, task_id: str) -> None:
        if task_id not in self.tasks:
            raise ValueError("Task not found")
        task = self.tasks[task_id]
        task.uncomplete()

    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[Priority] = None,
        due_date: Optional[datetime] = None,
        project_id: Optional[str] = None,
    ) -> None:
        if task_id not in self.tasks:
            raise ValueError("Task not found")
        if project_id is not None and project_id not in self.projects:
            raise ValueError("Project not found")
        if due_date is not None and due_date < datetime.now():
            raise ValueError("Due date cannot be in the past")

        task = self.tasks[task_id]
        task.update(title, description, priority, due_date, project_id)

    def delete_task(self, task_id: str) -> None:
        if task_id not in self.tasks:
            raise ValueError("Task not found")
        task = self.tasks[task_id]
        # Remove from parent's subtasks
        if task.parent_task_id and task.parent_task_id in self.tasks:
            parent = self.tasks[task.parent_task_id]
            parent.subtasks = [t for t in parent.subtasks if t.id != task_id]
        # Recursively delete subtasks (or just detach?) We'll cascade delete subtasks.
        for subtask in list(task.subtasks):
            self.delete_task(subtask.id)
        # Remove from comments reference (comments are stored in task, but global comment dict also)
        for comment in task.comments:
            if comment.id in self.comments:
                del self.comments[comment.id]
        del self.tasks[task_id]

    def create_label(self, name: str, color: str = "#808080") -> Label:
        label = Label(name, color)
        self.labels[label.id] = label
        return label

    def delete_label(self, label_id: str) -> None:
        if label_id not in self.labels:
            raise ValueError("Label not found")
        # Remove from all tasks
        for task in self.tasks.values():
            task.remove_label(label_id)
        del self.labels[label_id]

    def add_label_to_task(self, task_id: str, label_id: str) -> None:
        if task_id not in self.tasks:
            raise ValueError("Task not found")
        if label_id not in self.labels:
            raise ValueError("Label not found")
        self.tasks[task_id].add_label(label_id)

    def remove_label_from_task(self, task_id: str, label_id: str) -> None:
        if task_id not in self.tasks:
            raise ValueError("Task not found")
        if label_id not in self.labels:
            raise ValueError("Label not found")
        self.tasks[task_id].remove_label(label_id)

    def add_comment_to_task(self, task_id: str, content: str, author: str = "user") -> Comment:
        if task_id not in self.tasks:
            raise ValueError("Task not found")
        task = self.tasks[task_id]
        comment = task.add_comment(content, author)
        self.comments[comment.id] = comment
        return comment

    def get_inbox_tasks(self) -> List[Task]:
        # Tasks in inbox project or no project
        inbox_projects = [p.id for p in self.projects.values() if p.is_inbox and not p.is_archived]
        tasks = []
        for task in self.tasks.values():
            if not task.is_completed and (task.project_id is None or task.project_id in inbox_projects):
                tasks.append(task)
        # Sort by created_at or priority
        tasks.sort(key=lambda t: (t.priority.value if t.priority else 5, t.created_at))
        return tasks

    def get_project_tasks(self, project_id: str) -> List[Task]:
        if project_id not in self.projects:
            raise ValueError("Project not found")
        tasks = [t for t in self.tasks.values() if t.project_id == project_id and not t.is_completed]
        tasks.sort(key=lambda t: (t.priority.value if t.priority else 5, t.created_at))
        return tasks

    def get_next_actions(self) -> List[Task]:
        """GTD next actions: tasks without parent, not completed, not in archived projects, with a project or inbox."""
        actions = []
        for t in self.tasks.values():
            if t.is_completed:
                continue
            if t.parent_task_id is not None:
                continue
            # Exclude tasks in archived projects
            if t.project_id and t.project_id in self.projects and self.projects[t.project_id].is_archived:
                continue
            actions.append(t)
        # Sort by priority then due date
        actions.sort(key=lambda t: (
            t.priority.value if t.priority else 5,
            t.due_date if t.due_date else datetime.max,
            t.created_at
        ))
        return actions

    def get_all_tasks(self) -> List[Task]:
        return list(self.tasks.values())

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)