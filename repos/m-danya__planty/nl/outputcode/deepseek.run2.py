import uuid
import datetime
from enum import IntEnum
from typing import Optional, List, Set, Dict
from dataclasses import dataclass, field

class Priority(IntEnum):
    P1 = 4
    P2 = 3
    P3 = 2
    P4 = 1

    @staticmethod
    def from_int(value: int) -> 'Priority':
        if value < 1 or value > 4:
            raise ValueError("Priority must be between 1 and 4")
        return Priority(value)

@dataclass
class HistoryEntry:
    id: str
    task_id: str
    action: str
    details: str
    timestamp: datetime.datetime

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "action": self.action,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    due_date: Optional[datetime.datetime] = None
    priority: Priority = Priority.P4
    is_completed: bool = False
    completed_at: Optional[datetime.datetime] = None
    parent_id: Optional[str] = None
    project_id: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = field(default_factory=datetime.datetime.now)

    def update_title(self, new_title: str):
        if not isinstance(new_title, str) or not new_title.strip():
            raise ValueError("Task title cannot be empty")
        if len(new_title) > 500:
            raise ValueError("Task title cannot exceed 500 characters")
        self.title = new_title.strip()
        self.updated_at = datetime.datetime.now()

    def update_description(self, new_description: str):
        self.description = new_description
        self.updated_at = datetime.datetime.now()

    def update_due_date(self, new_due_date: Optional[datetime.datetime]):
        if new_due_date is not None:
            if not isinstance(new_due_date, datetime.datetime):
                raise ValueError("Due date must be a datetime object")
            if new_due_date <= datetime.datetime.now():
                raise ValueError("Due date must be in the future")
        self.due_date = new_due_date
        self.updated_at = datetime.datetime.now()

    def update_priority(self, new_priority: Priority):
        if not isinstance(new_priority, Priority):
            raise ValueError("Priority must be a Priority enum")
        self.priority = new_priority
        self.updated_at = datetime.datetime.now()

    def add_tag(self, tag: str):
        if not isinstance(tag, str) or not tag.strip():
            raise ValueError("Tag cannot be empty")
        self.tags.add(tag.strip())
        self.updated_at = datetime.datetime.now()

    def remove_tag(self, tag: str):
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.datetime.now()

    def mark_completed(self):
        if self.is_completed:
            return
        self.is_completed = True
        self.completed_at = datetime.datetime.now()
        self.updated_at = datetime.datetime.now()

    def mark_uncompleted(self):
        if not self.is_completed:
            return
        self.is_completed = False
        self.completed_at = None
        self.updated_at = datetime.datetime.now()

    def set_parent(self, parent_id: Optional[str]):
        self.parent_id = parent_id
        self.updated_at = datetime.datetime.now()

    def set_project(self, project_id: Optional[str]):
        self.project_id = project_id
        self.updated_at = datetime.datetime.now()

    def is_subtask(self) -> bool:
        return self.parent_id is not None

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "priority": self.priority.name,
            "is_completed": self.is_completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "parent_id": self.parent_id,
            "project_id": self.project_id,
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

@dataclass
class Project:
    id: str
    name: str
    color: str = "#808080"
    is_archived: bool = False
    task_ids: List[str] = field(default_factory=list)

    def add_task_id(self, task_id: str):
        if task_id not in self.task_ids:
            self.task_ids.append(task_id)

    def remove_task_id(self, task_id: str):
        if task_id in self.task_ids:
            self.task_ids.remove(task_id)

    def archive(self):
        self.is_archived = True

    def unarchive(self):
        self.is_archived = False

    def rename(self, new_name: str):
        if not isinstance(new_name, str) or not new_name.strip():
            raise ValueError("Project name cannot be empty")
        if len(new_name) > 120:
            raise ValueError("Project name cannot exceed 120 characters")
        self.name = new_name.strip()

    def set_color(self, new_color: str):
        # Accept simple hex color validation
        if not isinstance(new_color, str) or not new_color.startswith('#') or len(new_color) != 7:
            raise ValueError("Color must be a hex code like '#RRGGBB'")
        self.color = new_color

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "is_archived": self.is_archived,
            "task_ids": self.task_ids
        }

class PlantyApp:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.projects: Dict[str, Project] = {}
        self.history: List[HistoryEntry] = []
        self._next_ids = {'task': 0, 'project': 0, 'history': 0}

    def _generate_id(self, prefix: str) -> str:
        self._next_ids[prefix] += 1
        return f"{prefix}_{self._next_ids[prefix]}"

    def _log_history(self, task_id: str, action: str, details: str = ""):
        entry = HistoryEntry(
            id=self._generate_id("history"),
            task_id=task_id,
            action=action,
            details=details,
            timestamp=datetime.datetime.now()
        )
        self.history.append(entry)

    def create_project(self, name: str, color: str = "#808080") -> Project:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Project name cannot be empty")
        project = Project(
            id=self._generate_id("project"),
            name=name.strip(),
            color=color,
            is_archived=False,
            task_ids=[]
        )
        self.projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.projects.get(project_id)

    def archive_project(self, project_id: str):
        project = self.projects.get(project_id)
        if not project:
            raise ValueError("Project not found")
        project.archive()

    def unarchive_project(self, project_id: str):
        project = self.projects.get(project_id)
        if not project:
            raise ValueError("Project not found")
        project.unarchive()

    def create_task(self, title: str, **kwargs) -> Task:
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Task title cannot be empty")
        if len(title) > 500:
            raise ValueError("Task title cannot exceed 500 characters")

        task_data = {
            "id": self._generate_id("task"),
            "title": title.strip(),
            "description": kwargs.get("description", ""),
            "due_date": kwargs.get("due_date"),
            "priority": kwargs.get("priority", Priority.P4),
            "parent_id": kwargs.get("parent_id"),
            "project_id": kwargs.get("project_id"),
            "tags": set(kwargs.get("tags", []))
        }
        task = Task(**task_data)

        # Validate due date
        if task.due_date is not None:
            if not isinstance(task.due_date, datetime.datetime):
                raise ValueError("Due date must be a datetime object")
            if task.due_date <= datetime.datetime.now():
                raise ValueError("Due date must be in the future")

        # Validate priority
        if not isinstance(task.priority, Priority):
            try:
                task.priority = Priority.from_int(task.priority)
            except (ValueError, TypeError):
                raise ValueError("Priority must be between 1 and 4")

        # Parent task check
        if task.parent_id and task.parent_id not in self.tasks:
            raise ValueError("Parent task does not exist")

        # Project check
        if task.project_id and task.project_id not in self.projects:
            raise ValueError("Project does not exist")

        self.tasks[task.id] = task

        # Add to project if applicable
        if task.project_id:
            self.projects[task.project_id].add_task_id(task.id)

        self._log_history(task.id, "created", f"Task '{task.title}' created")

        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def update_task(self, task_id: str, **kwargs) -> Task:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError("Task not found")

        # Track changes for history
        changes = []

        if "title" in kwargs:
            old_title = task.title
            task.update_title(kwargs["title"])
            changes.append(f"title from '{old_title}' to '{task.title}'")

        if "description" in kwargs:
            task.update_description(kwargs["description"])
            changes.append("description updated")

        if "due_date" in kwargs:
            old_due = task.due_date
            task.update_due_date(kwargs["due_date"])
            changes.append(f"due_date from {old_due} to {task.due_date}")

        if "priority" in kwargs:
            old_priority = task.priority
            task.update_priority(kwargs["priority"])
            changes.append(f"priority from {old_priority.name} to {task.priority.name}")

        if "tags_add" in kwargs:
            tags = kwargs["tags_add"]
            if isinstance(tags, list):
                for tag in tags:
                    task.add_tag(tag)
                changes.append(f"added tags: {tags}")

        if "tags_remove" in kwargs:
            tags = kwargs["tags_remove"]
            if isinstance(tags, list):
                for tag in tags:
                    task.remove_tag(tag)
                changes.append(f"removed tags: {tags}")

        if changes:
            self._log_history(task.id, "updated", "; ".join(changes))

        return task

    def complete_task(self, task_id: str) -> Task:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError("Task not found")
        task.mark_completed()
        self._log_history(task.id, "completed", f"Task '{task.title}' completed")
        return task

    def reopen_task(self, task_id: str) -> Task:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError("Task not found")
        task.mark_uncompleted()
        self._log_history(task.id, "reopened", f"Task '{task.title}' reopened")
        return task

    def move_task_to_project(self, task_id: str, new_project_id: Optional[str]) -> Task:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError("Task not found")
        if new_project_id and new_project_id not in self.projects:
            raise ValueError("Project does not exist")

        old_project_id = task.project_id

        # Remove from old project
        if old_project_id and old_project_id in self.projects:
            self.projects[old_project_id].remove_task_id(task.id)

        # Set new project
        task.set_project(new_project_id)

        # Add to new project
        if new_project_id:
            self.projects[new_project_id].add_task_id(task.id)

        # Propagate to subtasks recursively
        children = self._get_child_tasks(task_id)
        for child_id in children:
            child = self.tasks[child_id]
            old_child_project = child.project_id
            if old_child_project and old_child_project in self.projects:
                self.projects[old_child_project].remove_task_id(child.id)
            child.set_project(new_project_id)
            if new_project_id:
                self.projects[new_project_id].add_task_id(child.id)

        self._log_history(task.id, "moved", f"Moved from project '{old_project_id}' to '{new_project_id}'")
        return task

    def _get_child_tasks(self, parent_id: str) -> List[str]:
        """Get all direct and indirect subtask ids."""
        children = []
        for task in self.tasks.values():
            if task.parent_id == parent_id:
                children.append(task.id)
                children.extend(self._get_child_tasks(task.id))
        return children

    def add_subtask(self, parent_task_id: str, subtask_title: str, **kwargs) -> Task:
        parent = self.tasks.get(parent_task_id)
        if not parent:
            raise ValueError("Parent task not found")
        kwargs["parent_id"] = parent_task_id
        # Subtask inherits project from parent unless specified
        if "project_id" not in kwargs:
            kwargs["project_id"] = parent.project_id
        subtask = self.create_task(subtask_title, **kwargs)
        self._log_history(parent_task_id, "subtask_added", f"Subtasks '{subtask.title}' added")
        return subtask

    def delete_task(self, task_id: str):
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError("Task not found")

        # Recursively delete subtasks
        children = self._get_child_tasks(task_id)
        for child_id in children:
            self._delete_single_task(child_id)

        self._delete_single_task(task_id)

    def _delete_single_task(self, task_id: str):
        task = self.tasks.pop(task_id, None)
        if task:
            # Remove from project
            if task.project_id and task.project_id in self.projects:
                self.projects[task.project_id].remove_task_id(task_id)
            self._log_history(task_id, "deleted", f"Task '{task.title}' deleted")

    def get_tasks_by_project(self, project_id: str) -> List[Task]:
        project = self.projects.get(project_id)
        if not project:
            return []
        return [self.tasks[tid] for tid in project.task_ids if tid in self.tasks]

    def get_inbox_tasks(self) -> List[Task]:
        return [t for t in self.tasks.values() if t.project_id is None and not t.is_subtask()]

    def get_all_tasks(self) -> List[Task]:
        return list(self.tasks.values())

    def get_tasks_by_context(self, tag: str) -> List[Task]:
        return [t for t in self.tasks.values() if tag in t.tags]

    def get_task_history(self, task_id: str) -> List[HistoryEntry]:
        return [entry for entry in self.history if entry.task_id == task_id]