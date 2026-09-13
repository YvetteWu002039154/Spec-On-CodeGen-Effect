from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


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


class Priority(int, Enum):
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require_non_empty(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    v = value.strip()
    if not v:
        raise ValidationError(f"{field} cannot be empty")
    return v


def _require_optional_str(value: Optional[str], field: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string or None")
    v = value.strip()
    return v if v else None


def _require_priority(value: Optional[int]) -> Priority:
    if value is None:
        return Priority.P4
    try:
        p = Priority(int(value))
    except Exception as e:
        raise ValidationError("priority must be an integer 1..4") from e
    return p


def _require_datetime(value: Optional[datetime], field: str) -> Optional[datetime]:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise ValidationError(f"{field} must be a datetime or None")
    if value.tzinfo is None:
        raise ValidationError(f"{field} must be timezone-aware")
    return value


@dataclass(frozen=True)
class Event:
    at: datetime
    type: str
    entity: str
    entity_id: int
    data: Dict[str, object]


class _IdGen:
    def __init__(self) -> None:
        self._next = 1

    def next(self) -> int:
        v = self._next
        self._next += 1
        return v


class User:
    def __init__(self, user_id: int, name: str) -> None:
        self._id = user_id
        self._name = _require_non_empty(name, "name")
        self._created_at = _now()

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def rename(self, new_name: str) -> None:
        self._name = _require_non_empty(new_name, "name")


class Project:
    def __init__(self, project_id: int, owner_id: int, name: str) -> None:
        self._id = project_id
        self._owner_id = owner_id
        self._name = _require_non_empty(name, "name")
        self._created_at = _now()
        self._archived = False

    @property
    def id(self) -> int:
        return self._id

    @property
    def owner_id(self) -> int:
        return self._owner_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def archived(self) -> bool:
        return self._archived

    def rename(self, name: str) -> None:
        self._name = _require_non_empty(name, "name")

    def archive(self) -> None:
        self._archived = True

    def unarchive(self) -> None:
        self._archived = False


class Task:
    def __init__(
        self,
        task_id: int,
        owner_id: int,
        title: str,
        project_id: Optional[int] = None,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        due_at: Optional[datetime] = None,
        labels: Optional[Set[str]] = None,
    ) -> None:
        self._id = task_id
        self._owner_id = owner_id
        self._title = _require_non_empty(title, "title")
        self._description = _require_optional_str(description, "description")
        self._project_id = project_id
        self._priority = _require_priority(priority)
        self._due_at = _require_datetime(due_at, "due_at")
        self._labels: Set[str] = set()
        if labels:
            self.set_labels(labels)
        self._status = TaskStatus.ACTIVE
        self._created_at = _now()
        self._updated_at = self._created_at
        self._completed_at: Optional[datetime] = None

    @property
    def id(self) -> int:
        return self._id

    @property
    def owner_id(self) -> int:
        return self._owner_id

    @property
    def title(self) -> str:
        return self._title

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def project_id(self) -> Optional[int]:
        return self._project_id

    @property
    def priority(self) -> Priority:
        return self._priority

    @property
    def due_at(self) -> Optional[datetime]:
        return self._due_at

    @property
    def labels(self) -> Set[str]:
        return set(self._labels)

    @property
    def status(self) -> TaskStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    def _touch(self) -> None:
        self._updated_at = _now()

    def rename(self, title: str) -> None:
        self._title = _require_non_empty(title, "title")
        self._touch()

    def set_description(self, description: Optional[str]) -> None:
        self._description = _require_optional_str(description, "description")
        self._touch()

    def set_project(self, project_id: Optional[int]) -> None:
        self._project_id = project_id
        self._touch()

    def set_priority(self, priority: Optional[int]) -> None:
        self._priority = _require_priority(priority)
        self._touch()

    def set_due_at(self, due_at: Optional[datetime]) -> None:
        self._due_at = _require_datetime(due_at, "due_at")
        self._touch()

    def set_labels(self, labels: Set[str]) -> None:
        if not isinstance(labels, set):
            raise ValidationError("labels must be a set of strings")
        cleaned: Set[str] = set()
        for l in labels:
            if not isinstance(l, str):
                raise ValidationError("label must be a string")
            s = l.strip()
            if not s:
                raise ValidationError("label cannot be empty")
            cleaned.add(s)
        self._labels = cleaned
        self._touch()

    def add_label(self, label: str) -> None:
        s = _require_non_empty(label, "label")
        self._labels.add(s)
        self._touch()

    def remove_label(self, label: str) -> None:
        s = _require_non_empty(label, "label")
        self._labels.discard(s)
        self._touch()

    def complete(self) -> None:
        if self._status == TaskStatus.ARCHIVED:
            raise ValidationError("cannot complete an archived task")
        self._status = TaskStatus.COMPLETED
        self._completed_at = _now()
        self._touch()

    def reopen(self) -> None:
        if self._status == TaskStatus.ARCHIVED:
            raise ValidationError("cannot reopen an archived task")
        self._status = TaskStatus.ACTIVE
        self._completed_at = None
        self._touch()

    def archive(self) -> None:
        self._status = TaskStatus.ARCHIVED
        self._touch()


class PlantyApp:
    def __init__(self) -> None:
        self._user_ids = _IdGen()
        self._project_ids = _IdGen()
        self._task_ids = _IdGen()

        self._users: Dict[int, User] = {}
        self._projects: Dict[int, Project] = {}
        self._tasks: Dict[int, Task] = {}

        self._events: List[Event] = []

    def _emit(self, type_: str, entity: str, entity_id: int, data: Optional[Dict[str, object]] = None) -> None:
        self._events.append(
            Event(
                at=_now(),
                type=_require_non_empty(type_, "type"),
                entity=_require_non_empty(entity, "entity"),
                entity_id=int(entity_id),
                data=dict(data or {}),
            )
        )

    def events(self) -> Tuple[Event, ...]:
        return tuple(self._events)

    def create_user(self, name: str) -> User:
        uid = self._user_ids.next()
        user = User(uid, name)
        self._users[uid] = user
        self._emit("user.created", "user", uid, {"name": user.name})
        return user

    def get_user(self, user_id: int) -> User:
        try:
            return self._users[int(user_id)]
        except Exception as e:
            raise NotFoundError("user not found") from e

    def rename_user(self, user_id: int, new_name: str) -> None:
        user = self.get_user(user_id)
        old = user.name
        user.rename(new_name)
        self._emit("user.renamed", "user", user.id, {"old_name": old, "new_name": user.name})

    def create_project(self, owner_id: int, name: str) -> Project:
        owner = self.get_user(owner_id)
        pid = self._project_ids.next()
        project = Project(pid, owner.id, name)
        self._projects[pid] = project
        self._emit("project.created", "project", pid, {"owner_id": owner.id, "name": project.name})
        return project

    def get_project(self, project_id: int) -> Project:
        try:
            return self._projects[int(project_id)]
        except Exception as e:
            raise NotFoundError("project not found") from e

    def _require_project_owner(self, owner_id: int, project: Project) -> None:
        if int(owner_id) != project.owner_id:
            raise PermissionError("not project owner")

    def rename_project(self, owner_id: int, project_id: int, name: str) -> None:
        project = self.get_project(project_id)
        self._require_project_owner(owner_id, project)
        old = project.name
        project.rename(name)
        self._emit("project.renamed", "project", project.id, {"old_name": old, "new_name": project.name})

    def archive_project(self, owner_id: int, project_id: int) -> None:
        project = self.get_project(project_id)
        self._require_project_owner(owner_id, project)
        if project.archived:
            return
        project.archive()
        self._emit("project.archived", "project", project.id, {"owner_id": project.owner_id})

    def unarchive_project(self, owner_id: int, project_id: int) -> None:
        project = self.get_project(project_id)
        self._require_project_owner(owner_id, project)
        if not project.archived:
            return
        project.unarchive()
        self._emit("project.unarchived", "project", project.id, {"owner_id": project.owner_id})

    def create_task(
        self,
        owner_id: int,
        title: str,
        project_id: Optional[int] = None,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        due_at: Optional[datetime] = None,
        labels: Optional[Set[str]] = None,
    ) -> Task:
        owner = self.get_user(owner_id)
        if project_id is not None:
            project = self.get_project(project_id)
            if project.owner_id != owner.id:
                raise PermissionError("cannot add task to another user's project")
            if project.archived:
                raise ValidationError("cannot add task to archived project")
        tid = self._task_ids.next()
        task = Task(
            task_id=tid,
            owner_id=owner.id,
            title=title,
            project_id=project_id,
            description=description,
            priority=priority,
            due_at=due_at,
            labels=labels,
        )
        self._tasks[tid] = task
        self._emit(
            "task.created",
            "task",
            tid,
            {
                "owner_id": owner.id,
                "title": task.title,
                "project_id": task.project_id,
                "priority": int(task.priority),
                "due_at": task.due_at.isoformat() if task.due_at else None,
            },
        )
        return task

    def get_task(self, task_id: int) -> Task:
        try:
            return self._tasks[int(task_id)]
        except Exception as e:
            raise NotFoundError("task not found") from e

    def _require_task_owner(self, owner_id: int, task: Task) -> None:
        if int(owner_id) != task.owner_id:
            raise PermissionError("not task owner")

    def update_task(
        self,
        owner_id: int,
        task_id: int,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        project_id: Optional[int] = None,
        priority: Optional[int] = None,
        due_at: Optional[datetime] = None,
        labels: Optional[Set[str]] = None,
    ) -> None:
        task = self.get_task(task_id)
        self._require_task_owner(owner_id, task)

        changes: Dict[str, object] = {}

        if title is not None:
            old = task.title
            task.rename(title)
            changes["title"] = {"old": old, "new": task.title}

        if description is not None:
            old = task.description
            task.set_description(description)
            changes["description"] = {"old": old, "new": task.description}

        if project_id is not None or project_id is None:
            if project_id is not None:
                project = self.get_project(project_id)
                if project.owner_id != task.owner_id:
                    raise PermissionError("cannot move task to another user's project")
                if project.archived:
                    raise ValidationError("cannot move task to archived project")
            old = task.project_id
            task.set_project(project_id)
            changes["project_id"] = {"old": old, "new": task.project_id}

        if priority is not None:
            old = int(task.priority)
            task.set_priority(priority)
            changes["priority"] = {"old": old, "new": int(task.priority)}

        if due_at is not None or due_at is None:
            old = task.due_at.isoformat() if task.due_at else None
            task.set_due_at(due_at)
            changes["due_at"] = {"old": old, "new": task.due_at.isoformat() if task.due_at else None}

        if labels is not None:
            old = sorted(task.labels)
            task.set_labels(labels)
            changes["labels"] = {"old": old, "new": sorted(task.labels)}

        if changes:
            self._emit("task.updated", "task", task.id, {"changes": changes})

    def complete_task(self, owner_id: int, task_id: int) -> None:
        task = self.get_task(task_id)
        self._require_task_owner(owner_id, task)
        prev = task.status
        task.complete()
        self._emit(
            "task.completed",
            "task",
            task.id,
            {"previous_status": prev.value, "completed_at": task.completed_at.isoformat() if task.completed_at else None},
        )

    def reopen_task(self, owner_id: int, task_id: int) -> None:
        task = self.get_task(task_id)
        self._require_task_owner(owner_id, task)
        prev = task.status
        task.reopen()
        self._emit("task.reopened", "task", task.id, {"previous_status": prev.value})

    def archive_task(self, owner_id: int, task_id: int) -> None:
        task = self.get_task(task_id)
        self._require_task_owner(owner_id, task)
        prev = task.status
        task.archive()
        self._emit("task.archived", "task", task.id, {"previous_status": prev.value})

    def list_projects(self, owner_id: int, *, include_archived: bool = False) -> List[Project]:
        self.get_user(owner_id)
        res = [p for p in self._projects.values() if p.owner_id == int(owner_id)]
        if not include_archived:
            res = [p for p in res if not p.archived]
        res.sort(key=lambda p: (p.archived, p.created_at, p.id))
        return list(res)

    def list_tasks(
        self,
        owner_id: int,
        *,
        project_id: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        label: Optional[str] = None,
    ) -> List[Task]:
        self.get_user(owner_id)
        if project_id is not None:
            project = self.get_project(project_id)
            if project.owner_id != int(owner_id):
                raise PermissionError("not project owner")
        label_norm = _require_optional_str(label, "label")
        res = [t for t in self._tasks.values() if t.owner_id == int(owner_id)]
        if project_id is not None:
            res = [t for t in res if t.project_id == int(project_id)]
        if status is not None:
            if not isinstance(status, TaskStatus):
                raise ValidationError("status must be a TaskStatus")
            res = [t for t in res if t.status == status]
        if label_norm is not None:
            res = [t for t in res if label_norm in t.labels]
        res.sort(key=lambda t: (t.status.value, int(t.priority), t.due_at or datetime.max.replace(tzinfo=timezone.utc), t.created_at, t.id))
        return list(res)