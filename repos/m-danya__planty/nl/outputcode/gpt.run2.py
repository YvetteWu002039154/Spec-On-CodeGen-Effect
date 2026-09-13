from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class PlantyError(Exception):
    pass


class ValidationError(PlantyError):
    pass


class NotFoundError(PlantyError):
    pass


class ConflictError(PlantyError):
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
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be a non-empty string")
    return value.strip()


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
        raise ValidationError("priority must be an integer in [1,2,3,4]") from e
    return p


def _require_optional_datetime(value: Optional[datetime], field: str) -> Optional[datetime]:
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
    def __init__(self, start: int = 1) -> None:
        self._next = start

    def next(self) -> int:
        v = self._next
        self._next += 1
        return v


class User:
    def __init__(self, user_id: int, username: str) -> None:
        self._id = user_id
        self._username = _require_non_empty(username, "username")

    @property
    def id(self) -> int:
        return self._id

    @property
    def username(self) -> str:
        return self._username


class Project:
    def __init__(self, project_id: int, owner_id: int, name: str, description: Optional[str] = None) -> None:
        self._id = project_id
        self._owner_id = owner_id
        self._name = _require_non_empty(name, "name")
        self._description = _require_optional_str(description, "description")
        self._archived = False
        self._created_at = _now()
        self._updated_at = self._created_at

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
    def description(self) -> Optional[str]:
        return self._description

    @property
    def archived(self) -> bool:
        return self._archived

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def rename(self, name: str) -> None:
        self._name = _require_non_empty(name, "name")
        self._updated_at = _now()

    def set_description(self, description: Optional[str]) -> None:
        self._description = _require_optional_str(description, "description")
        self._updated_at = _now()

    def archive(self) -> None:
        self._archived = True
        self._updated_at = _now()

    def unarchive(self) -> None:
        self._archived = False
        self._updated_at = _now()


class Label:
    def __init__(self, label_id: int, owner_id: int, name: str) -> None:
        self._id = label_id
        self._owner_id = owner_id
        self._name = _require_non_empty(name, "name")
        self._created_at = _now()
        self._updated_at = self._created_at

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
    def updated_at(self) -> datetime:
        return self._updated_at

    def rename(self, name: str) -> None:
        self._name = _require_non_empty(name, "name")
        self._updated_at = _now()


class Task:
    def __init__(
        self,
        task_id: int,
        owner_id: int,
        content: str,
        project_id: Optional[int] = None,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        due_at: Optional[datetime] = None,
        parent_id: Optional[int] = None,
    ) -> None:
        self._id = task_id
        self._owner_id = owner_id
        self._content = _require_non_empty(content, "content")
        self._description = _require_optional_str(description, "description")
        self._project_id = project_id
        self._priority = _require_priority(priority)
        self._due_at = _require_optional_datetime(due_at, "due_at")
        self._parent_id = parent_id
        self._status = TaskStatus.ACTIVE
        self._completed_at: Optional[datetime] = None
        self._archived_at: Optional[datetime] = None
        self._labels: Set[int] = set()
        self._created_at = _now()
        self._updated_at = self._created_at

    @property
    def id(self) -> int:
        return self._id

    @property
    def owner_id(self) -> int:
        return self._owner_id

    @property
    def content(self) -> str:
        return self._content

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def project_id(self) -> Optional[int]:
        return self._project_id

    @property
    def parent_id(self) -> Optional[int]:
        return self._parent_id

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
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    @property
    def archived_at(self) -> Optional[datetime]:
        return self._archived_at

    @property
    def labels(self) -> Tuple[int, ...]:
        return tuple(sorted(self._labels))

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def set_content(self, content: str) -> None:
        self._content = _require_non_empty(content, "content")
        self._updated_at = _now()

    def set_description(self, description: Optional[str]) -> None:
        self._description = _require_optional_str(description, "description")
        self._updated_at = _now()

    def set_project(self, project_id: Optional[int]) -> None:
        self._project_id = project_id
        self._updated_at = _now()

    def set_parent(self, parent_id: Optional[int]) -> None:
        self._parent_id = parent_id
        self._updated_at = _now()

    def set_priority(self, priority: Optional[int]) -> None:
        self._priority = _require_priority(priority)
        self._updated_at = _now()

    def set_due_at(self, due_at: Optional[datetime]) -> None:
        self._due_at = _require_optional_datetime(due_at, "due_at")
        self._updated_at = _now()

    def add_label(self, label_id: int) -> None:
        self._labels.add(label_id)
        self._updated_at = _now()

    def remove_label(self, label_id: int) -> None:
        self._labels.discard(label_id)
        self._updated_at = _now()

    def clear_labels(self) -> None:
        self._labels.clear()
        self._updated_at = _now()

    def complete(self) -> None:
        if self._status == TaskStatus.ARCHIVED:
            raise ConflictError("cannot complete an archived task")
        if self._status != TaskStatus.COMPLETED:
            self._status = TaskStatus.COMPLETED
            self._completed_at = _now()
            self._updated_at = self._completed_at

    def reopen(self) -> None:
        if self._status == TaskStatus.ARCHIVED:
            raise ConflictError("cannot reopen an archived task")
        if self._status != TaskStatus.ACTIVE:
            self._status = TaskStatus.ACTIVE
            self._completed_at = None
            self._updated_at = _now()

    def archive(self) -> None:
        if self._status != TaskStatus.ARCHIVED:
            self._status = TaskStatus.ARCHIVED
            self._archived_at = _now()
            self._updated_at = self._archived_at

    def unarchive(self) -> None:
        if self._status == TaskStatus.ARCHIVED:
            self._status = TaskStatus.ACTIVE
            self._archived_at = None
            self._updated_at = _now()


class PlantyApp:
    def __init__(self) -> None:
        self._user_ids = _IdGen()
        self._project_ids = _IdGen()
        self._label_ids = _IdGen()
        self._task_ids = _IdGen()
        self._users: Dict[int, User] = {}
        self._projects: Dict[int, Project] = {}
        self._labels: Dict[int, Label] = {}
        self._tasks: Dict[int, Task] = {}
        self._events: List[Event] = []

        self._username_index: Dict[str, int] = {}
        self._project_name_index: Dict[Tuple[int, str], int] = {}
        self._label_name_index: Dict[Tuple[int, str], int] = {}

    @property
    def events(self) -> Tuple[Event, ...]:
        return tuple(self._events)

    def _emit(self, type_: str, entity: str, entity_id: int, data: Optional[Dict[str, object]] = None) -> None:
        self._events.append(Event(at=_now(), type=type_, entity=entity, entity_id=entity_id, data=data or {}))

    def create_user(self, username: str) -> User:
        username = _require_non_empty(username, "username")
        key = username.lower()
        if key in self._username_index:
            raise ConflictError("username already exists")
        uid = self._user_ids.next()
        user = User(uid, username)
        self._users[uid] = user
        self._username_index[key] = uid
        self._emit("created", "user", uid, {"username": username})
        return user

    def get_user(self, user_id: int) -> User:
        try:
            return self._users[user_id]
        except KeyError as e:
            raise NotFoundError("user not found") from e

    def create_project(self, owner_id: int, name: str, description: Optional[str] = None) -> Project:
        self.get_user(owner_id)
        name = _require_non_empty(name, "name")
        key = (owner_id, name.lower())
        if key in self._project_name_index:
            raise ConflictError("project name already exists for owner")
        pid = self._project_ids.next()
        project = Project(pid, owner_id, name, description)
        self._projects[pid] = project
        self._project_name_index[key] = pid
        self._emit("created", "project", pid, {"owner_id": owner_id, "name": name})
        return project

    def get_project(self, project_id: int) -> Project:
        try:
            return self._projects[project_id]
        except KeyError as e:
            raise NotFoundError("project not found") from e

    def rename_project(self, owner_id: int, project_id: int, new_name: str) -> None:
        project = self.get_project(project_id)
        if project.owner_id != owner_id:
            raise PermissionError("not project owner")
        new_name = _require_non_empty(new_name, "name")
        old_key = (owner_id, project.name.lower())
        new_key = (owner_id, new_name.lower())
        if new_key in self._project_name_index and self._project_name_index[new_key] != project_id:
            raise ConflictError("project name already exists for owner")
        if old_key in self._project_name_index:
            del self._project_name_index[old_key]
        self._project_name_index[new_key] = project_id
        project.rename(new_name)
        self._emit("updated", "project", project_id, {"name": new_name})

    def set_project_description(self, owner_id: int, project_id: int, description: Optional[str]) -> None:
        project = self.get_project(project_id)
        if project.owner_id != owner_id:
            raise PermissionError("not project owner")
        project.set_description(description)
        self._emit("updated", "project", project_id, {"description": project.description})

    def archive_project(self, owner_id: int, project_id: int) -> None:
        project = self.get_project(project_id)
        if project.owner_id != owner_id:
            raise PermissionError("not project owner")
        project.archive()
        self._emit("archived", "project", project_id, {})

    def unarchive_project(self, owner_id: int, project_id: int) -> None:
        project = self.get_project(project_id)
        if project.owner_id != owner_id:
            raise PermissionError("not project owner")
        project.unarchive()
        self._emit("unarchived", "project", project_id, {})

    def create_label(self, owner_id: int, name: str) -> Label:
        self.get_user(owner_id)
        name = _require_non_empty(name, "name")
        key = (owner_id, name.lower())
        if key in self._label_name_index:
            raise ConflictError("label name already exists for owner")
        lid = self._label_ids.next()
        label = Label(lid, owner_id, name)
        self._labels[lid] = label
        self._label_name_index[key] = lid
        self._emit("created", "label", lid, {"owner_id": owner_id, "name": name})
        return label

    def get_label(self, label_id: int) -> Label:
        try:
            return self._labels[label_id]
        except KeyError as e:
            raise NotFoundError("label not found") from e

    def rename_label(self, owner_id: int, label_id: int, new_name: str) -> None:
        label = self.get_label(label_id)
        if label.owner_id != owner_id:
            raise PermissionError("not label owner")
        new_name = _require_non_empty(new_name, "name")
        old_key = (owner_id, label.name.lower())
        new_key = (owner_id, new_name.lower())
        if new_key in self._label_name_index and self._label_name_index[new_key] != label_id:
            raise ConflictError("label name already exists for owner")
        if old_key in self._label_name_index:
            del self._label_name_index[old_key]
        self._label_name_index[new_key] = label_id
        label.rename(new_name)
        self._emit("updated", "label", label_id, {"name": new_name})

    def create_task(
        self,
        owner_id: int,
        content: str,
        project_id: Optional[int] = None,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        due_at: Optional[datetime] = None,
        parent_id: Optional[int] = None,
        label_ids: Optional[List[int]] = None,
    ) -> Task:
        self.get_user(owner_id)
        if project_id is not None:
            project = self.get_project(project_id)
            if project.owner_id != owner_id:
                raise PermissionError("not project owner")
        if parent_id is not None:
            parent = self.get_task(parent_id)
            if parent.owner_id != owner_id:
                raise PermissionError("not task owner")
            if parent_id == parent.parent_id:
                raise ValidationError("invalid parent relationship")
        tid = self._task_ids.next()
        task = Task(
            tid,
            owner_id,
            content=content,
            project_id=project_id,
            description=description,
            priority=priority,
            due_at=due_at,
            parent_id=parent_id,
        )
        if label_ids:
            for lid in label_ids:
                label = self.get_label(lid)
                if label.owner_id != owner_id:
                    raise PermissionError("not label owner")
                task.add_label(lid)
        self._tasks[tid] = task
        self._emit("created", "task", tid, {"owner_id": owner_id, "content": task.content})
        return task

    def get_task(self, task_id: int) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError as e:
            raise NotFoundError("task not found") from e

    def update_task_content(self, owner_id: int, task_id: int, content: str) -> None:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("not task owner")
        task.set_content(content)
        self._emit("updated", "task", task_id, {"content": task.content})

    def update_task_description(self, owner_id: int, task_id: int, description: Optional[str]) -> None:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("not task owner")
        task.set_description(description)
        self._emit("updated", "task", task_id, {"description": task.description})

    def move_task_to_project(self, owner_id: int, task_id: int, project_id: Optional[int]) -> None:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("not task owner")
        if project_id is not None:
            project = self.get_project(project_id)
            if project.owner_id != owner_id:
                raise PermissionError("not project owner")
        task.set_project(project_id)
        self._emit("updated", "task", task_id, {"project_id": project_id})

    def set_task_parent(self, owner_id: int, task_id: int, parent_id: Optional[int]) -> None:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("not task owner")
        if parent_id is None:
            task.set_parent(None)
            self._emit("updated", "task", task_id, {"parent_id": None})
            return
        parent = self.get_task(parent_id)
        if parent.owner_id != owner_id:
            raise PermissionError("not task owner")
        if parent_id == task_id:
            raise ValidationError("task cannot be its own parent")
        cur = parent
        while cur.parent_id is not None:
            if cur.parent_id == task_id:
                raise ValidationError("cycle detected in parent relationship")
            cur = self.get_task(cur.parent_id)
        task.set_parent(parent_id)
        self._emit("updated", "task", task_id, {"parent_id": parent_id})

    def set_task_priority(self, owner_id: int, task_id: int, priority: Optional[int]) -> None:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("not task owner")
        task.set_priority(priority)
        self._emit("updated", "task", task_id, {"priority": int(task.priority)})

    def set_task_due_at(self, owner_id: int, task_id: int, due_at: Optional[datetime]) -> None:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("not task owner")
        task.set_due_at(due_at)
        self._emit("updated", "task", task_id, {"due_at": task.due_at.isoformat() if task.due_at else None})

    def add_label_to_task(self, owner_id: int, task_id: int, label_id: int) -> None:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("not task owner")
        label = self.get_label(label_id)
        if label.owner_id != owner_id:
            raise PermissionError("not label owner")
        task.add_label(label_id)
        self._emit("updated", "task", task_id, {"labels": list(task.labels)})

    def remove_label_from_task(self, owner_id: int, task_id: int, label_id: int) -> None:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("not task owner")
        task.remove_label(label_id)
        self._emit("updated", "task", task_id, {"labels": list(task.labels)})

    def complete_task(self, owner_id: int, task_id: int) -> None:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("not task owner")
        task.complete()
        self._emit("completed", "task", task_id, {"completed_at": task.completed_at.isoformat() if task.completed_at else None})

    def reopen_task(self, owner_id: int, task_id: int) -> None:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("not task owner")
        task.reopen()
        self._emit("reopened", "task", task_id, {})

    def archive_task(self, owner_id: int, task_id: int) -> None:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("not task owner")
        task.archive()
        self._emit("archived", "task", task_id, {"archived_at": task.archived_at.isoformat() if task.archived_at else None})

    def unarchive_task(self, owner_id: int, task_id: int) -> None:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("not task owner")
        task.unarchive()
        self._emit("unarchived", "task", task_id, {})

    def list_projects(self, owner_id: int, include_archived: bool = False) -> List[Project]:
        self.get_user(owner_id)
        projects = [p for p in self._projects.values() if p.owner_id == owner_id and (include_archived or not p.archived)]
        projects.sort(key=lambda p: (p.archived, p.name.lower(), p.id))
        return projects

    def list_labels(self, owner_id: int) -> List[Label]:
        self.get_user(owner_id)
        labels = [l for l in self._labels.values() if l.owner_id == owner_id]
        labels.sort(key=lambda l: (l.name.lower(), l.id))
        return labels

    def list_tasks(
        self,
        owner_id: int,
        project_id: Optional[int] = None,
        label_id: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        include_archived: bool = False,
    ) -> List[Task]:
        self.get_user(owner_id)
        if project_id is not None:
            project = self.get_project(project_id)
            if project.owner_id != owner_id:
                raise PermissionError("not project owner")
        if label_id is not None:
            label = self.get_label(label_id)
            if label.owner_id != owner_id:
                raise PermissionError("not label owner")

        tasks = [t for t in self._tasks.values() if t.owner_id == owner_id]
        if project_id is not None:
            tasks = [t for t in tasks if t.project_id == project_id]
        if label_id is not None:
            tasks = [t for t in tasks if label_id in set(t.labels)]
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if not include_archived:
            tasks = [t for t in tasks if t.status != TaskStatus.ARCHIVED]

        def sort_key(t: Task) -> Tuple[int, int, int, str, int]:
            due_rank = 0 if t.due_at is not None else 1
            due_ts = int(t.due_at.timestamp()) if t.due_at is not None else 0
            return (due_rank, due_ts, int(t.priority), t.content.lower(), t.id)

        tasks.sort(key=sort_key)
        return tasks