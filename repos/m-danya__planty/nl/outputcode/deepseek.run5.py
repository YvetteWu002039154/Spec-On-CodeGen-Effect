from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime, date
from enum import Enum, auto
from typing import Optional, List, Dict, Any, Union
import json
import os
import sys

# ---------- Enums ----------

class Priority(Enum):
    P1 = 1  # Highest
    P2 = 2
    P3 = 3
    P4 = 4  # Lowest

class Status(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DELETED = "deleted"

# ---------- Base Entity ----------

class Entity(ABC):
    def __init__(self, entity_id: str) -> None:
        self._id = entity_id

    @property
    def id(self) -> str:
        return self._id

    @abstractmethod
    def to_dict(self) -> dict:
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> Entity:
        pass

# ---------- Label (context in GTD) ----------

class Label(Entity):
    def __init__(self, label_id: str, name: str) -> None:
        super().__init__(label_id)
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self._name}

    @classmethod
    def from_dict(cls, data: dict) -> Label:
        return cls(data["id"], data["name"])

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Label):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"Label({self._name})"

# ---------- Comment ----------

class Comment(Entity):
    def __init__(self, comment_id: str, content: str, author_id: str, timestamp: datetime) -> None:
        super().__init__(comment_id)
        self._content = content
        self._author_id = author_id
        self._timestamp = timestamp

    @property
    def content(self) -> str:
        return self._content

    @property
    def author_id(self) -> str:
        return self._author_id

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self._content,
            "author_id": self._author_id,
            "timestamp": self._timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> Comment:
        return cls(
            data["id"],
            data["content"],
            data["author_id"],
            datetime.fromisoformat(data["timestamp"])
        )

# ---------- Task ----------

class Task(Entity):
    def __init__(
        self,
        task_id: str,
        title: str,
        description: str = "",
        priority: Priority = Priority.P4,
        due_date: Optional[date] = None,
        labels: Optional[List[Label]] = None,
        project_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        status: Status = Status.ACTIVE,
        order: int = 0,
        created_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ) -> None:
        super().__init__(task_id)
        if not title.strip():
            raise ValueError("Task title cannot be empty")
        self._title = title.strip()
        self._description = description
        self._priority = priority
        self._due_date = due_date
        self._labels = labels if labels else []
        self._project_id = project_id
        self._parent_id = parent_id  # subtask parent
        self._status = status
        self._order = order
        self._created_at = created_at if created_at else datetime.now()
        self._completed_at = completed_at
        self._subtasks: List[Task] = []  # runtime only, not stored directly in dict

    # Properties
    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        if not value.strip():
            raise ValueError("Task title cannot be empty")
        self._title = value.strip()

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
    def due_date(self) -> Optional[date]:
        return self._due_date

    @due_date.setter
    def due_date(self, value: Optional[date]) -> None:
        self._due_date = value

    @property
    def labels(self) -> List[Label]:
        return self._labels.copy()

    def add_label(self, label: Label) -> None:
        if label not in self._labels:
            self._labels.append(label)

    def remove_label(self, label: Label) -> None:
        if label in self._labels:
            self._labels.remove(label)

    @property
    def project_id(self) -> Optional[str]:
        return self._project_id

    @project_id.setter
    def project_id(self, value: Optional[str]) -> None:
        self._project_id = value

    @property
    def parent_id(self) -> Optional[str]:
        return self._parent_id

    @parent_id.setter
    def parent_id(self, value: Optional[str]) -> None:
        self._parent_id = value

    @property
    def status(self) -> Status:
        return self._status

    @property
    def order(self) -> int:
        return self._order

    @order.setter
    def order(self, value: int) -> None:
        self._order = value

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    # Business methods
    def complete(self) -> None:
        if self._status == Status.ACTIVE:
            self._status = Status.COMPLETED
            self._completed_at = datetime.now()
            # Recursively complete subtasks? GTD might allow subtasks independently.
            # Here we follow Todoist: completing parent completes subtasks.
            for sub in self._subtasks:
                sub.complete()

    def uncomplete(self) -> None:
        if self._status == Status.COMPLETED:
            self._status = Status.ACTIVE
            self._completed_at = None
            # Reopen subtasks? We'll leave them as they are; you can manage separately.

    def is_overdue(self) -> bool:
        if self._due_date and self._status == Status.ACTIVE:
            return date.today() > self._due_date
        return False

    def add_subtask(self, subtask: Task) -> None:
        if subtask.parent_id != self.id:
            raise ValueError("Subtask must have parent_id set to this task")
        if subtask not in self._subtasks:
            self._subtasks.append(subtask)

    def remove_subtask(self, subtask: Task) -> None:
        if subtask in self._subtasks:
            self._subtasks.remove(subtask)

    def get_subtasks(self) -> List[Task]:
        return self._subtasks.copy()

    # Serialization
    def to_dict(self, include_subtasks: bool = False) -> dict:
        data = {
            "id": self.id,
            "title": self._title,
            "description": self._description,
            "priority": self._priority.value,
            "due_date": self._due_date.isoformat() if self._due_date else None,
            "labels": [label.id for label in self._labels],
            "project_id": self._project_id,
            "parent_id": self._parent_id,
            "status": self._status.value,
            "order": self._order,
            "created_at": self._created_at.isoformat(),
            "completed_at": self._completed_at.isoformat() if self._completed_at else None,
        }
        if include_subtasks:
            data["subtasks"] = [sub.to_dict() for sub in self._subtasks]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        labels = []  # Labels must be resolved separately from a LabelManager
        due = date.fromisoformat(data["due_date"]) if data.get("due_date") else None
        completed = datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        return cls(
            task_id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            priority=Priority(data["priority"]),
            due_date=due,
            labels=labels,  # to be set later
            project_id=data.get("project_id"),
            parent_id=data.get("parent_id"),
            status=Status(data["status"]),
            order=data.get("order", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
            completed_at=completed
        )

    def __repr__(self) -> str:
        status_icon = "✓" if self._status == Status.COMPLETED else "○"
        return f"{status_icon} {self._title}"

# ---------- Project ----------

class Project(Entity):
    def __init__(
        self,
        project_id: str,
        name: str,
        color: str = "grey",
        is_inbox: bool = False,
        order: int = 0
    ) -> None:
        super().__init__(project_id)
        if not name.strip():
            raise ValueError("Project name cannot be empty")
        self._name = name.strip()
        self._color = color
        self._is_inbox = is_inbox
        self._order = order
        self._tasks: List[Task] = []  # runtime

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if not value.strip():
            raise ValueError("Project name cannot be empty")
        self._name = value.strip()

    @property
    def color(self) -> str:
        return self._color

    @color.setter
    def color(self, value: str) -> None:
        self._color = value

    @property
    def is_inbox(self) -> bool:
        return self._is_inbox

    @property
    def order(self) -> int:
        return self._order

    @order.setter
    def order(self, value: int) -> None:
        self._order = value

    def add_task(self, task: Task) -> None:
        if task not in self._tasks:
            self._tasks.append(task)
            task.project_id = self.id

    def remove_task(self, task: Task) -> None:
        if task in self._tasks:
            self._tasks.remove(task)
            task.project_id = None

    def get_tasks(self, include_completed: bool = False) -> List[Task]:
        filtered = [t for t in self._tasks if include_completed or t.status != Status.COMPLETED]
        return sorted(filtered, key=lambda t: (t.order, t.created_at))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self._name,
            "color": self._color,
            "is_inbox": self._is_inbox,
            "order": self._order,
            "tasks": [t.id for t in self._tasks]
        }

    @classmethod
    def from_dict(cls, data: dict) -> Project:
        return cls(
            project_id=data["id"],
            name=data["name"],
            color=data.get("color", "grey"),
            is_inbox=data.get("is_inbox", False),
            order=data.get("order", 0)
        )

    def __repr__(self) -> str:
        inbox_mark = " [Inbox]" if self._is_inbox else ""
        return f"Project({self._name}{inbox_mark})"

# ---------- User ----------

class User(Entity):
    def __init__(self, user_id: str, email: str, name: str = "") -> None:
        super().__init__(user_id)
        self._email = email
        self._name = name

    @property
    def email(self) -> str:
        return self._email

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    def to_dict(self) -> dict:
        return {"id": self.id, "email": self._email, "name": self._name}

    @classmethod
    def from_dict(cls, data: dict) -> User:
        return cls(data["id"], data["email"], data.get("name", ""))

# ---------- Label Manager ----------

class LabelManager:
    def __init__(self) -> None:
        self._labels: Dict[str, Label] = {}

    def create_label(self, label_id: str, name: str) -> Label:
        if label_id in self._labels:
            raise ValueError(f"Label with id {label_id} already exists")
        label = Label(label_id, name)
        self._labels[label_id] = label
        return label

    def get_label(self, label_id: str) -> Optional[Label]:
        return self._labels.get(label_id)

    def delete_label(self, label_id: str) -> None:
        if label_id in self._labels:
            del self._labels[label_id]

    def all_labels(self) -> List[Label]:
        return list(self._labels.values())

    def to_dict(self) -> dict:
        return {lid: label.to_dict() for lid, label in self._labels.items()}

    @classmethod
    def from_dict(cls, data: dict) -> LabelManager:
        lm = cls()
        for lid, ldata in data.items():
            lm._labels[lid] = Label.from_dict(ldata)
        return lm

# ---------- History / Activity Log (GTD reflection) ----------

class ActivityType(Enum):
    CREATED = auto()
    UPDATED = auto()
    COMPLETED = auto()
    UNCOMPLETED = auto()
    DELETED = auto()
    MOVED = auto()

class HistoryEntry:
    def __init__(self, activity_type: ActivityType, task_id: str, timestamp: datetime, details: str = "") -> None:
        self.activity_type = activity_type
        self.task_id = task_id
        self.timestamp = timestamp
        self.details = details

    def to_dict(self) -> dict:
        return {
            "activity_type": self.activity_type.name,
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }

    @classmethod
    def from_dict(cls, data: dict) -> HistoryEntry:
        return cls(
            ActivityType[data["activity_type"]],
            data["task_id"],
            datetime.fromisoformat(data["timestamp"]),
            data.get("details", "")
        )

# ---------- Application State (Data Store) ----------

class PlantyApp:
    def __init__(self, user: User) -> None:
        self.user = user
        self.projects: Dict[str, Project] = {}
        self.tasks: Dict[str, Task] = {}
        self.labels = LabelManager()
        self.history: List[HistoryEntry] = []
        self._next_id_counter = 1

        # Ensure a default Inbox project exists
        self._create_inbox()

    def _generate_id(self, prefix: str = "item") -> str:
        """Simple sequential ID generator."""
        new_id = f"{prefix}_{self._next_id_counter}"
        self._next_id_counter += 1
        return new_id

    def _create_inbox(self) -> Project:
        inbox_id = "inbox"
        if inbox_id not in self.projects:
            inbox = Project(inbox_id, "Inbox", color="grey", is_inbox=True)
            self.projects[inbox_id] = inbox
        return self.projects[inbox_id]

    # Project operations
    def create_project(self, name: str, color: str = "grey") -> Project:
        if not name.strip():
            raise ValueError("Project name cannot be empty")
        project_id = self._generate_id("proj")
        project = Project(project_id, name, color)
        self.projects[project_id] = project
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.projects.get(project_id)

    def delete_project(self, project_id: str) -> None:
        project = self.projects.get(project_id)
        if not project:
            raise ValueError("Project not found")
        if project.is_inbox:
            raise ValueError("Cannot delete the Inbox project")
        # Move all tasks to Inbox
        inbox = self._create_inbox()
        for task in project._tasks:
            task.project_id = inbox.id
            inbox.add_task(task)
        del self.projects[project_id]

    # Task operations
    def create_task(
        self,
        title: str,
        description: str = "",
        priority: Priority = Priority.P4,
        due_date: Optional[date] = None,
        project_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        labels: Optional[List[Label]] = None
    ) -> Task:
        if not title.strip():
            raise ValueError("Task title cannot be empty")
        task_id = self._generate_id("task")
        task = Task(
            task_id=task_id,
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            project_id=project_id,
            parent_id=parent_id,
            labels=labels if labels else []
        )
        self.tasks[task_id] = task

        # If parent specified, add as subtask and ensure parent exists
        if parent_id:
            parent_task = self.tasks.get(parent_id)
            if not parent_task:
                raise ValueError(f"Parent task {parent_id} not found")
            parent_task.add_subtask(task)

        # Add to project if provided; otherwise use Inbox
        if project_id:
            project = self.projects.get(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")
            project.add_task(task)
        else:
            inbox = self._create_inbox()
            inbox.add_task(task)

        self._add_history(ActivityType.CREATED, task_id, f"Task '{title}' created")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def update_task(self, task_id: str, **kwargs) -> Task:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError("Task not found")
        # Apply allowed updates
        allowed = {"title", "description", "priority", "due_date", "order"}
        changes = []
        for key, value in kwargs.items():
            if key in allowed:
                current = getattr(task, key)
                if current != value:
                    changes.append(f"{key}: {current} -> {value}")
                if key == "title":
                    task.title = value
                elif key == "description":
                    task.description = value
                elif key == "priority":
                    task.priority = value
                elif key == "due_date":
                    task.due_date = value
                elif key == "order":
                    task.order = value
        if changes:
            self._add_history(ActivityType.UPDATED, task_id, "; ".join(changes))
        return task

    def complete_task(self, task_id: str) -> Task:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError("Task not found")
        task.complete()
        self._add_history(ActivityType.COMPLETED, task_id, f"Task '{task.title}' completed")
        return task

    def uncomplete_task(self, task_id: str) -> Task:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError("Task not found")
        task.uncomplete()
        self._add_history(ActivityType.UNCOMPLETED, task_id, f"Task '{task.title}' reopened")
        return task

    def delete_task(self, task_id: str) -> None:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError("Task not found")
        # Remove from project
        project = self.projects.get(task.project_id) if task.project_id else None
        if project:
            project.remove_task(task)
        # Remove from parent subtask list if exists
        if task.parent_id:
            parent = self.tasks.get(task.parent_id)
            if parent:
                parent.remove_subtask(task)
        # Remove subtasks? Usually subtasks are deleted along with parent
        # We'll delete all subtasks recursively
        for sub in task.get_subtasks():
            self.delete_task(sub.id)
        del self.tasks[task_id]
        self._add_history(ActivityType.DELETED, task_id, f"Task '{task.title}' deleted")

    def move_task_to_project(self, task_id: str, new_project_id: str) -> None:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError("Task not found")
        new_project = self.projects.get(new_project_id)
        if not new_project:
            raise ValueError("Project not found")
        old_project = self.projects.get(task.project_id) if task.project_id else None
        if old_project:
            old_project.remove_task(task)
        new_project.add_task(task)
        self._add_history(ActivityType.MOVED, task_id,
                          f"Moved to project '{new_project.name}'")

    # Label operations
    def create_label(self, name: str) -> Label:
        label_id = self._generate_id("label")
        return self.labels.create_label(label_id, name)

    def assign_label_to_task(self, task_id: str, label_id: str) -> None:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError("Task not found")
        label = self.labels.get_label(label_id)
        if not label:
            raise ValueError("Label not found")
        task.add_label(label)

    def remove_label_from_task(self, task_id: str, label_id: str) -> None:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError("Task not found")
        label = self.labels.get_label(label_id)
        if label:
            task.remove_label(label)

    # History
    def _add_history(self, activity_type: ActivityType, task_id: str, details: str) -> None:
        entry = HistoryEntry(activity_type, task_id, datetime.now(), details)
        self.history.append(entry)

    def get_task_history(self, task_id: str) -> List[HistoryEntry]:
        return [e for e in self.history if e.task_id == task_id]

    # Query helpers
    def get_all_tasks(self, include_completed: bool = False) -> List[Task]:
        tasks = list(self.tasks.values())
        if not include_completed:
            tasks = [t for t in tasks if t.status != Status.COMPLETED]
        return sorted(tasks, key=lambda t: (t.order, t.created_at))

    def get_inbox_tasks(self) -> List[Task]:
        inbox = self._create_inbox()
        return inbox.get_tasks()

    def get_tasks_by_label(self, label_name: str) -> List[Task]:
        label = None
        for l in self.labels.all_labels():
            if l.name == label_name:
                label = l
                break
        if not label:
            return []
        result = []
        for task in self.tasks.values():
            if label in task.labels and task.status != Status.COMPLETED:
                result.append(task)
        return result

    # Persistence (simple JSON)
    def to_dict(self) -> dict:
        return {
            "user": self.user.to_dict(),
            "projects": {pid: proj.to_dict() for pid, proj in self.projects.items()},
            "tasks": {tid: task.to_dict(include_subtasks=False) for tid, task in self.tasks.items()},
            "labels": self.labels.to_dict(),
            "history": [h.to_dict() for h in self.history],
            "next_id": self._next_id_counter
        }

    @classmethod
    def from_dict(cls, data: dict) -> PlantyApp:
        user = User.from_dict(data["user"])
        app = cls(user)
        # Restore next_id
        app._next_id_counter = data.get("next_id", 1)
        # Restore labels
        app.labels = LabelManager.from_dict(data.get("labels", {}))
        # Restore projects (empty tasks list)
        for pid, pdata in data["projects"].items():
            project = Project.from_dict(pdata)
            app.projects[pid] = project
        # Restore tasks and link them
        for tid, tdata in data["tasks"].items():
            task = Task.from_dict(tdata)
            # Assign labels
            label_ids = tdata.get("labels", [])
            for lid in label_ids:
                label = app.labels.get_label(lid)
                if label:
                    task.add_label(label)
            app.tasks[tid] = task
        # Link tasks to projects and subtasks
        for tid, task in app.tasks.items():
            # Project
            if task.project_id and task.project_id in app.projects:
                app.projects[task.project_id].add_task(task)
            # Parent
            if task.parent_id and task.parent_id in app.tasks:
                app.tasks[task.parent_id].add_subtask(task)
        # Restore history
        app.history = [HistoryEntry.from_dict(h) for h in data.get("history", [])]
        return app

    def save_to_file(self, filepath: str) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> PlantyApp:
        if not os.path.exists(filepath):
            # Return new app with default user
            return cls(User("default_user", "user@planty.app", "Default User"))
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)

# ---------- CLI (simple demonstration) ----------

def main():
    app = PlantyApp.load_from_file("planty_data.json")
    print("Planty Task Manager")
    print("-------------------")
    print(f"Logged in as: {app.user.name} ({app.user.email})")

    while True:
        print("\nOptions:")
        print("1. Show all tasks")
        print("2. Add task")
        print("3. Complete task")
        print("4. Show projects")
        print("5. Add project")
        print("6. Show labels")
        print("7. Create label")
        print("8. Assign label to task")
        print("9. Move task to project")
        print("10. Show task history")
        print("11. Delete task")
        print("12. Save and exit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            tasks = app.get_all_tasks(include_completed=False)
            if not tasks:
                print("No active tasks.")
            for t in tasks:
                proj = app.get_project(t.project_id) if t.project_id else None
                proj_name = proj.name if proj else "No Project"
                labels = ", ".join([l.name for l in t.labels]) or "none"
                due = f" due {t.due_date}" if t.due_date else ""
                print(f"[{t.id}] {t.title} ({t.priority.name}, {proj_name}, labels: {labels}){due}")

        elif choice == "2":
            title = input("Title: ").strip()
            desc = input("Description (optional): ").strip()
            priority_input = input("Priority (1-4, default 4): ").strip()
            priority = Priority.P4
            if priority_input in {"1", "2", "3", "4"}:
                priority = Priority(int(priority_input))
            due_str = input("Due date (YYYY-MM-DD, leave blank): ").strip()
            due = date.fromisoformat(due_str) if due_str else None
            proj_name = input("Project name (leave blank for Inbox): ").strip()
            project_id = None
            if proj_name:
                # find project by name
                for p in app.projects.values():
                    if p.name.lower() == proj_name.lower():
                        project_id = p.id
                        break
                if not project_id:
                    print("Project not found, using Inbox.")
            parent_id = input("Parent task ID (optional): ").strip() or None
            try:
                task = app.create_task(title, desc, priority, due, project_id, parent_id)
                print(f"Task '{task.title}' created with ID {task.id}")
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == "3":
            tid = input("Task ID to complete: ").strip()
            try:
                app.complete_task(tid)
                print("Task completed.")
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == "4":
            for p in app.projects.values():
                print(f"{p.name} (color: {p.color}, tasks: {len(p._tasks)})")

        elif choice == "5":
            name = input("Project name: ").strip()
            color = input("Color (default grey): ").strip() or "grey"
            try:
                proj = app.create_project(name, color)
                print(f"Project '{proj.name}' created.")
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == "6":
            labels = app.labels.all_labels()
            if not labels:
                print("No labels.")
            for l in labels:
                print(f"{l.name} (id: {l.id})")

        elif choice == "7":
            name = input("Label name: ").strip()
            label = app.create_label(name)
            print(f"Label '{label.name}' created with ID {label.id}")

        elif choice == "8":
            task_id = input("Task ID: ").strip()
            label_id = input("Label ID: ").strip()
            try:
                app.assign_label_to_task(task_id, label_id)
                print("Label assigned.")
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == "9":
            task_id = input("Task ID: ").strip()
            new_proj_name = input("New project name: ").strip()
            # find project
            new_id = None
            for p in app.projects.values():
                if p.name.lower() == new_proj_name.lower():
                    new_id = p.id
                    break
            if not new_id:
                print("Project not found.")
                continue
            try:
                app.move_task_to_project(task_id, new_id)
                print("Task moved.")
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == "10":
            tid = input("Task ID: ").strip()
            history = app.get_task_history(tid)
            if not history:
                print("No history.")
            for h in history:
                print(f"{h.timestamp} - {h.activity_type.name}: {h.details}")

        elif choice == "11":
            tid = input("Task ID to delete: ").strip()
            try:
                app.delete_task(tid)
                print("Task deleted.")
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == "12":
            app.save_to_file("planty_data.json")
            print("Data saved. Goodbye!")
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()