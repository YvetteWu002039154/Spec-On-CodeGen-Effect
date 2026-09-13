from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PlantyError(Exception):
    pass


class NotFoundError(PlantyError):
    pass


class ValidationError(PlantyError):
    pass


class PermissionError(PlantyError):
    pass


class TaskStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Priority(int, Enum):
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4


@dataclass(frozen=True)
class Event:
    timestamp: datetime
    actor_id: str
    type: str
    data: Dict[str, object]


class History:
    def __init__(self) -> None:
        self._events: List[Event] = []

    def add(self, actor_id: str, event_type: str, data: Optional[Dict[str, object]] = None) -> None:
        self._events.append(Event(timestamp=_utcnow(), actor_id=actor_id, type=event_type, data=data or {}))

    def list(self) -> Tuple[Event, ...]:
        return tuple(self._events)


class User:
    def __init__(self, user_id: str, name: str) -> None:
        if not user_id or not user_id.strip():
            raise ValidationError("user_id is required")
        if not name or not name.strip():
            raise ValidationError("name is required")
        self._id = user_id.strip()
        self._name = name.strip()
        self._created_at = _utcnow()

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def created_at(self) -> datetime:
        return self._created_at


class Label:
    def __init__(self, label_id: str, name: str, color: Optional[str] = None) -> None:
        if not label_id or not label_id.strip():
            raise ValidationError("label_id is required")
        if not name or not name.strip():
            raise ValidationError("name is required")
        self._id = label_id.strip()
        self._name = name.strip()
        self._color = color.strip() if isinstance(color, str) and color.strip() else None
        self._created_at = _utcnow()

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def color(self) -> Optional[str]:
        return self._color

    @property
    def created_at(self) -> datetime:
        return self._created_at


class Project:
    def __init__(self, project_id: str, owner_id: str, name: str) -> None:
        if not project_id or not project_id.strip():
            raise ValidationError("project_id is required")
        if not owner_id or not owner_id.strip():
            raise ValidationError("owner_id is required")
        if not name or not name.strip():
            raise ValidationError("name is required")
        self._id = project_id.strip()
        self._owner_id = owner_id.strip()
        self._name = name.strip()
        self._status: ProjectStatus = ProjectStatus.ACTIVE
        self._created_at = _utcnow()
        self._archived_at: Optional[datetime] = None

    @property
    def id(self) -> str:
        return self._id

    @property
    def owner_id(self) -> str:
        return self._owner_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> ProjectStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def archived_at(self) -> Optional[datetime]:
        return self._archived_at

    def rename(self, new_name: str) -> None:
        if not new_name or not new_name.strip():
            raise ValidationError("new_name is required")
        self._name = new_name.strip()

    def archive(self) -> None:
        if self._status == ProjectStatus.ARCHIVED:
            return
        self._status = ProjectStatus.ARCHIVED
        self._archived_at = _utcnow()

    def unarchive(self) -> None:
        if self._status == ProjectStatus.ACTIVE:
            return
        self._status = ProjectStatus.ACTIVE
        self._archived_at = None


class Task:
    def __init__(
        self,
        task_id: str,
        owner_id: str,
        title: str,
        *,
        description: str = "",
        project_id: Optional[str] = None,
        priority: Priority = Priority.P4,
        due_at: Optional[datetime] = None,
    ) -> None:
        if not task_id or not task_id.strip():
            raise ValidationError("task_id is required")
        if not owner_id or not owner_id.strip():
            raise ValidationError("owner_id is required")
        if not title or not title.strip():
            raise ValidationError("title is required")
        if due_at is not None and due_at.tzinfo is None:
            raise ValidationError("due_at must be timezone-aware")
        self._id = task_id.strip()
        self._owner_id = owner_id.strip()
        self._title = title.strip()
        self._description = description or ""
        self._project_id = project_id.strip() if isinstance(project_id, str) and project_id.strip() else None
        self._priority = Priority(int(priority))
        self._due_at = due_at
        self._status: TaskStatus = TaskStatus.ACTIVE
        self._created_at = _utcnow()
        self._completed_at: Optional[datetime] = None
        self._archived_at: Optional[datetime] = None
        self._labels: Set[str] = set()

    @property
    def id(self) -> str:
        return self._id

    @property
    def owner_id(self) -> str:
        return self._owner_id

    @property
    def title(self) -> str:
        return self._title

    @property
    def description(self) -> str:
        return self._description

    @property
    def project_id(self) -> Optional[str]:
        return self._project_id

    @property
    def priority(self) -> Priority:
        return self._priority

    @property
    def due_at(self) -> Optional[datetime]:
        return self._due_at

    @property
    def status(self) -> TaskStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    @property
    def archived_at(self) -> Optional[datetime]:
        return self._archived_at

    @property
    def labels(self) -> Tuple[str, ...]:
        return tuple(sorted(self._labels))

    def set_title(self, title: str) -> None:
        if not title or not title.strip():
            raise ValidationError("title is required")
        self._title = title.strip()

    def set_description(self, description: str) -> None:
        self._description = description or ""

    def set_project(self, project_id: Optional[str]) -> None:
        self._project_id = project_id.strip() if isinstance(project_id, str) and project_id.strip() else None

    def set_priority(self, priority: Priority) -> None:
        self._priority = Priority(int(priority))

    def set_due_at(self, due_at: Optional[datetime]) -> None:
        if due_at is not None and due_at.tzinfo is None:
            raise ValidationError("due_at must be timezone-aware")
        self._due_at = due_at

    def add_label(self, label_id: str) -> None:
        if not label_id or not label_id.strip():
            raise ValidationError("label_id is required")
        self._labels.add(label_id.strip())

    def remove_label(self, label_id: str) -> None:
        if not label_id or not label_id.strip():
            raise ValidationError("label_id is required")
        self._labels.discard(label_id.strip())

    def complete(self) -> None:
        if self._status == TaskStatus.ARCHIVED:
            raise ValidationError("cannot complete an archived task")
        if self._status == TaskStatus.COMPLETED:
            return
        self._status = TaskStatus.COMPLETED
        self._completed_at = _utcnow()

    def reopen(self) -> None:
        if self._status == TaskStatus.ARCHIVED:
            raise ValidationError("cannot reopen an archived task")
        if self._status == TaskStatus.ACTIVE:
            return
        self._status = TaskStatus.ACTIVE
        self._completed_at = None

    def archive(self) -> None:
        if self._status == TaskStatus.ARCHIVED:
            return
        self._status = TaskStatus.ARCHIVED
        self._archived_at = _utcnow()

    def unarchive(self) -> None:
        if self._status != TaskStatus.ARCHIVED:
            return
        self._status = TaskStatus.ACTIVE
        self._archived_at = None
        self._completed_at = None


class PlantyApp:
    def __init__(self) -> None:
        self._users: Dict[str, User] = {}
        self._projects: Dict[str, Project] = {}
        self._tasks: Dict[str, Task] = {}
        self._labels: Dict[str, Label] = {}
        self._history = History()

    @property
    def history(self) -> History:
        return self._history

    def create_user(self, actor_id: str, user_id: str, name: str) -> User:
        if user_id in self._users:
            raise ValidationError("user_id already exists")
        user = User(user_id=user_id, name=name)
        self._users[user.id] = user
        self._history.add(actor_id=actor_id, event_type="user.created", data={"user_id": user.id, "name": user.name})
        return user

    def get_user(self, user_id: str) -> User:
        try:
            return self._users[user_id]
        except KeyError as e:
            raise NotFoundError("user not found") from e

    def create_label(self, actor_id: str, label_id: str, name: str, color: Optional[str] = None) -> Label:
        if label_id in self._labels:
            raise ValidationError("label_id already exists")
        label = Label(label_id=label_id, name=name, color=color)
        self._labels[label.id] = label
        self._history.add(
            actor_id=actor_id,
            event_type="label.created",
            data={"label_id": label.id, "name": label.name, "color": label.color},
        )
        return label

    def get_label(self, label_id: str) -> Label:
        try:
            return self._labels[label_id]
        except KeyError as e:
            raise NotFoundError("label not found") from e

    def create_project(self, actor_id: str, project_id: str, owner_id: str, name: str) -> Project:
        if project_id in self._projects:
            raise ValidationError("project_id already exists")
        if owner_id not in self._users:
            raise NotFoundError("owner user not found")
        project = Project(project_id=project_id, owner_id=owner_id, name=name)
        self._projects[project.id] = project
        self._history.add(
            actor_id=actor_id,
            event_type="project.created",
            data={"project_id": project.id, "owner_id": project.owner_id, "name": project.name},
        )
        return project

    def get_project(self, project_id: str) -> Project:
        try:
            return self._projects[project_id]
        except KeyError as e:
            raise NotFoundError("project not found") from e

    def rename_project(self, actor_id: str, project_id: str, new_name: str) -> None:
        project = self.get_project(project_id)
        self._require_owner(actor_id, project.owner_id)
        old = project.name
        project.rename(new_name)
        self._history.add(
            actor_id=actor_id,
            event_type="project.renamed",
            data={"project_id": project.id, "old_name": old, "new_name": project.name},
        )

    def archive_project(self, actor_id: str, project_id: str) -> None:
        project = self.get_project(project_id)
        self._require_owner(actor_id, project.owner_id)
        project.archive()
        self._history.add(actor_id=actor_id, event_type="project.archived", data={"project_id": project.id})

    def unarchive_project(self, actor_id: str, project_id: str) -> None:
        project = self.get_project(project_id)
        self._require_owner(actor_id, project.owner_id)
        project.unarchive()
        self._history.add(actor_id=actor_id, event_type="project.unarchived", data={"project_id": project.id})

    def create_task(
        self,
        actor_id: str,
        task_id: str,
        owner_id: str,
        title: str,
        *,
        description: str = "",
        project_id: Optional[str] = None,
        priority: Priority = Priority.P4,
        due_at: Optional[datetime] = None,
    ) -> Task:
        if task_id in self._tasks:
            raise ValidationError("task_id already exists")
        if owner_id not in self._users:
            raise NotFoundError("owner user not found")
        if project_id is not None:
            project = self.get_project(project_id)
            if project.owner_id != owner_id:
                raise PermissionError("task owner must match project owner")
            if project.status == ProjectStatus.ARCHIVED:
                raise ValidationError("cannot add task to archived project")
        task = Task(
            task_id=task_id,
            owner_id=owner_id,
            title=title,
            description=description,
            project_id=project_id,
            priority=priority,
            due_at=due_at,
        )
        self._tasks[task.id] = task
        self._history.add(
            actor_id=actor_id,
            event_type="task.created",
            data={
                "task_id": task.id,
                "owner_id": task.owner_id,
                "title": task.title,
                "project_id": task.project_id,
                "priority": int(task.priority),
                "due_at": task.due_at.isoformat() if task.due_at else None,
            },
        )
        return task

    def get_task(self, task_id: str) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError as e:
            raise NotFoundError("task not found") from e

    def update_task_title(self, actor_id: str, task_id: str, title: str) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        old = task.title
        task.set_title(title)
        self._history.add(
            actor_id=actor_id,
            event_type="task.title_updated",
            data={"task_id": task.id, "old_title": old, "new_title": task.title},
        )

    def update_task_description(self, actor_id: str, task_id: str, description: str) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        task.set_description(description)
        self._history.add(actor_id=actor_id, event_type="task.description_updated", data={"task_id": task.id})

    def move_task_to_project(self, actor_id: str, task_id: str, project_id: Optional[str]) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        if project_id is not None:
            project = self.get_project(project_id)
            if project.owner_id != task.owner_id:
                raise PermissionError("task owner must match project owner")
            if project.status == ProjectStatus.ARCHIVED:
                raise ValidationError("cannot move task to archived project")
        old = task.project_id
        task.set_project(project_id)
        self._history.add(
            actor_id=actor_id,
            event_type="task.moved",
            data={"task_id": task.id, "old_project_id": old, "new_project_id": task.project_id},
        )

    def set_task_priority(self, actor_id: str, task_id: str, priority: Priority) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        old = int(task.priority)
        task.set_priority(priority)
        self._history.add(
            actor_id=actor_id,
            event_type="task.priority_updated",
            data={"task_id": task.id, "old_priority": old, "new_priority": int(task.priority)},
        )

    def set_task_due_at(self, actor_id: str, task_id: str, due_at: Optional[datetime]) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        old = task.due_at.isoformat() if task.due_at else None
        task.set_due_at(due_at)
        new = task.due_at.isoformat() if task.due_at else None
        self._history.add(
            actor_id=actor_id,
            event_type="task.due_updated",
            data={"task_id": task.id, "old_due_at": old, "new_due_at": new},
        )

    def add_label_to_task(self, actor_id: str, task_id: str, label_id: str) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        _ = self.get_label(label_id)
        task.add_label(label_id)
        self._history.add(
            actor_id=actor_id,
            event_type="task.label_added",
            data={"task_id": task.id, "label_id": label_id},
        )

    def remove_label_from_task(self, actor_id: str, task_id: str, label_id: str) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        task.remove_label(label_id)
        self._history.add(
            actor_id=actor_id,
            event_type="task.label_removed",
            data={"task_id": task.id, "label_id": label_id},
        )

    def complete_task(self, actor_id: str, task_id: str) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        task.complete()
        self._history.add(actor_id=actor_id, event_type="task.completed", data={"task_id": task.id})

    def reopen_task(self, actor_id: str, task_id: str) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        task.reopen()
        self._history.add(actor_id=actor_id, event_type="task.reopened", data={"task_id": task.id})

    def archive_task(self, actor_id: str, task_id: str) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        task.archive()
        self._history.add(actor_id=actor_id, event_type="task.archived", data={"task_id": task.id})

    def unarchive_task(self, actor_id: str, task_id: str) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        task.unarchive()
        self._history.add(actor_id=actor_id, event_type="task.unarchived", data={"task_id": task.id})

    def list_tasks(
        self,
        *,
        owner_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        label_id: Optional[str] = None,
    ) -> Tuple[Task, ...]:
        tasks = list(self._tasks.values())
        if owner_id is not None:
            tasks = [t for t in tasks if t.owner_id == owner_id]
        if project_id is not None:
            tasks = [t for t in tasks if t.project_id == project_id]
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if label_id is not None:
            tasks = [t for t in tasks if label_id in set(t.labels)]
        tasks.sort(key=lambda t: (t.status.value, int(t.priority), t.created_at))
        return tuple(tasks)

    def list_projects(self, *, owner_id: Optional[str] = None, status: Optional[ProjectStatus] = None) -> Tuple[Project, ...]:
        projects = list(self._projects.values())
        if owner_id is not None:
            projects = [p for p in projects if p.owner_id == owner_id]
        if status is not None:
            projects = [p for p in projects if p.status == status]
        projects.sort(key=lambda p: (p.status.value, p.created_at))
        return tuple(projects)

    def _require_owner(self, actor_id: str, owner_id: str) -> None:
        if actor_id != owner_id:
            raise PermissionError("actor is not the owner")