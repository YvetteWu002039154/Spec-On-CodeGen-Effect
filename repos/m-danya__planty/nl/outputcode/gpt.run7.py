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
        raise ValidationError("priority must be 1..4") from e
    return p


def _require_due_at(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise ValidationError("due_at must be a datetime or None")
    if value.tzinfo is None:
        raise ValidationError("due_at must be timezone-aware")
    return value


@dataclass(frozen=True)
class Event:
    at: datetime
    actor_user_id: str
    type: str
    entity: str
    entity_id: str
    details: Dict[str, object]


class User:
    __slots__ = ("_id", "_name", "_created_at")

    def __init__(self, user_id: str, name: str) -> None:
        self._id = _require_non_empty(user_id, "user_id")
        self._name = _require_non_empty(name, "name")
        self._created_at = _now()

    @property
    def id(self) -> str:
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
    __slots__ = ("_id", "_name", "_owner_user_id", "_created_at", "_archived")

    def __init__(self, project_id: str, name: str, owner_user_id: str) -> None:
        self._id = _require_non_empty(project_id, "project_id")
        self._name = _require_non_empty(name, "name")
        self._owner_user_id = _require_non_empty(owner_user_id, "owner_user_id")
        self._created_at = _now()
        self._archived = False

    @property
    def id(self) -> str:
        return self._id

    @property
    def owner_user_id(self) -> str:
        return self._owner_user_id

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
    __slots__ = (
        "_id",
        "_project_id",
        "_title",
        "_description",
        "_priority",
        "_status",
        "_created_at",
        "_updated_at",
        "_completed_at",
        "_due_at",
        "_labels",
    )

    def __init__(
        self,
        task_id: str,
        project_id: str,
        title: str,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        due_at: Optional[datetime] = None,
        labels: Optional[Set[str]] = None,
    ) -> None:
        self._id = _require_non_empty(task_id, "task_id")
        self._project_id = _require_non_empty(project_id, "project_id")
        self._title = _require_non_empty(title, "title")
        self._description = _require_optional_str(description, "description")
        self._priority = _require_priority(priority)
        self._status = TaskStatus.ACTIVE
        now = _now()
        self._created_at = now
        self._updated_at = now
        self._completed_at = None
        self._due_at = _require_due_at(due_at)
        self._labels = set()
        if labels:
            for l in labels:
                self.add_label(l)

    @property
    def id(self) -> str:
        return self._id

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def title(self) -> str:
        return self._title

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def priority(self) -> Priority:
        return self._priority

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

    @property
    def due_at(self) -> Optional[datetime]:
        return self._due_at

    @property
    def labels(self) -> Set[str]:
        return set(self._labels)

    def _touch(self) -> None:
        self._updated_at = _now()

    def set_title(self, title: str) -> None:
        self._title = _require_non_empty(title, "title")
        self._touch()

    def set_description(self, description: Optional[str]) -> None:
        self._description = _require_optional_str(description, "description")
        self._touch()

    def set_priority(self, priority: Optional[int]) -> None:
        self._priority = _require_priority(priority)
        self._touch()

    def set_due_at(self, due_at: Optional[datetime]) -> None:
        self._due_at = _require_due_at(due_at)
        self._touch()

    def add_label(self, label: str) -> None:
        l = _require_non_empty(label, "label")
        self._labels.add(l)
        self._touch()

    def remove_label(self, label: str) -> None:
        l = _require_non_empty(label, "label")
        if l in self._labels:
            self._labels.remove(l)
            self._touch()

    def complete(self) -> None:
        if self._status == TaskStatus.ARCHIVED:
            raise ValidationError("cannot complete an archived task")
        if self._status != TaskStatus.COMPLETED:
            self._status = TaskStatus.COMPLETED
            self._completed_at = _now()
            self._touch()

    def reopen(self) -> None:
        if self._status == TaskStatus.ARCHIVED:
            raise ValidationError("cannot reopen an archived task")
        if self._status != TaskStatus.ACTIVE:
            self._status = TaskStatus.ACTIVE
            self._completed_at = None
            self._touch()

    def archive(self) -> None:
        if self._status != TaskStatus.ARCHIVED:
            self._status = TaskStatus.ARCHIVED
            self._touch()

    def unarchive(self) -> None:
        if self._status == TaskStatus.ARCHIVED:
            self._status = TaskStatus.ACTIVE
            self._completed_at = None
            self._touch()


class PlantyApp:
    def __init__(self) -> None:
        self._users: Dict[str, User] = {}
        self._projects: Dict[str, Project] = {}
        self._tasks: Dict[str, Task] = {}
        self._project_tasks: Dict[str, Set[str]] = {}
        self._events: List[Event] = []

    def _emit(
        self,
        actor_user_id: str,
        type_: str,
        entity: str,
        entity_id: str,
        details: Optional[Dict[str, object]] = None,
    ) -> None:
        self._events.append(
            Event(
                at=_now(),
                actor_user_id=_require_non_empty(actor_user_id, "actor_user_id"),
                type=_require_non_empty(type_, "type"),
                entity=_require_non_empty(entity, "entity"),
                entity_id=_require_non_empty(entity_id, "entity_id"),
                details=dict(details or {}),
            )
        )

    def events(self) -> Tuple[Event, ...]:
        return tuple(self._events)

    def create_user(self, user_id: str, name: str) -> User:
        uid = _require_non_empty(user_id, "user_id")
        if uid in self._users:
            raise ValidationError("user_id already exists")
        user = User(uid, name)
        self._users[uid] = user
        self._emit(uid, "create", "user", uid, {"name": user.name})
        return user

    def get_user(self, user_id: str) -> User:
        uid = _require_non_empty(user_id, "user_id")
        try:
            return self._users[uid]
        except KeyError as e:
            raise NotFoundError("user not found") from e

    def rename_user(self, actor_user_id: str, user_id: str, new_name: str) -> None:
        actor = _require_non_empty(actor_user_id, "actor_user_id")
        if actor != _require_non_empty(user_id, "user_id"):
            raise PermissionError("users can only rename themselves")
        user = self.get_user(user_id)
        old = user.name
        user.rename(new_name)
        self._emit(actor, "update", "user", user.id, {"name_from": old, "name_to": user.name})

    def create_project(self, actor_user_id: str, project_id: str, name: str) -> Project:
        actor = _require_non_empty(actor_user_id, "actor_user_id")
        self.get_user(actor)
        pid = _require_non_empty(project_id, "project_id")
        if pid in self._projects:
            raise ValidationError("project_id already exists")
        project = Project(pid, name, owner_user_id=actor)
        self._projects[pid] = project
        self._project_tasks[pid] = set()
        self._emit(actor, "create", "project", pid, {"name": project.name})
        return project

    def get_project(self, project_id: str) -> Project:
        pid = _require_non_empty(project_id, "project_id")
        try:
            return self._projects[pid]
        except KeyError as e:
            raise NotFoundError("project not found") from e

    def _require_project_owner(self, actor_user_id: str, project_id: str) -> Project:
        actor = _require_non_empty(actor_user_id, "actor_user_id")
        project = self.get_project(project_id)
        if project.owner_user_id != actor:
            raise PermissionError("only the project owner can perform this action")
        return project

    def rename_project(self, actor_user_id: str, project_id: str, name: str) -> None:
        project = self._require_project_owner(actor_user_id, project_id)
        old = project.name
        project.rename(name)
        self._emit(actor_user_id, "update", "project", project.id, {"name_from": old, "name_to": project.name})

    def archive_project(self, actor_user_id: str, project_id: str) -> None:
        project = self._require_project_owner(actor_user_id, project_id)
        if not project.archived:
            project.archive()
            self._emit(actor_user_id, "update", "project", project.id, {"archived": True})

    def unarchive_project(self, actor_user_id: str, project_id: str) -> None:
        project = self._require_project_owner(actor_user_id, project_id)
        if project.archived:
            project.unarchive()
            self._emit(actor_user_id, "update", "project", project.id, {"archived": False})

    def create_task(
        self,
        actor_user_id: str,
        task_id: str,
        project_id: str,
        title: str,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        due_at: Optional[datetime] = None,
        labels: Optional[Set[str]] = None,
    ) -> Task:
        actor = _require_non_empty(actor_user_id, "actor_user_id")
        project = self._require_project_owner(actor, project_id)
        if project.archived:
            raise ValidationError("cannot add tasks to an archived project")
        tid = _require_non_empty(task_id, "task_id")
        if tid in self._tasks:
            raise ValidationError("task_id already exists")
        task = Task(
            task_id=tid,
            project_id=project.id,
            title=title,
            description=description,
            priority=priority,
            due_at=due_at,
            labels=labels,
        )
        self._tasks[tid] = task
        self._project_tasks[project.id].add(tid)
        self._emit(actor, "create", "task", tid, {"project_id": project.id, "title": task.title})
        return task

    def get_task(self, task_id: str) -> Task:
        tid = _require_non_empty(task_id, "task_id")
        try:
            return self._tasks[tid]
        except KeyError as e:
            raise NotFoundError("task not found") from e

    def list_tasks(
        self,
        actor_user_id: str,
        project_id: str,
        status: Optional[TaskStatus] = None,
    ) -> Tuple[Task, ...]:
        actor = _require_non_empty(actor_user_id, "actor_user_id")
        self._require_project_owner(actor, project_id)
        tids = self._project_tasks.get(project_id)
        if tids is None:
            raise NotFoundError("project not found")
        tasks = [self._tasks[tid] for tid in tids]
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        tasks.sort(key=lambda t: (t.status.value, int(t.priority), t.created_at))
        return tuple(tasks)

    def update_task(
        self,
        actor_user_id: str,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        due_at: Optional[datetime] = None,
    ) -> None:
        actor = _require_non_empty(actor_user_id, "actor_user_id")
        task = self.get_task(task_id)
        self._require_project_owner(actor, task.project_id)
        changes: Dict[str, object] = {}
        if title is not None:
            old = task.title
            task.set_title(title)
            changes["title_from"] = old
            changes["title_to"] = task.title
        if description is not None:
            old = task.description
            task.set_description(description)
            changes["description_from"] = old
            changes["description_to"] = task.description
        if priority is not None:
            old = int(task.priority)
            task.set_priority(priority)
            changes["priority_from"] = old
            changes["priority_to"] = int(task.priority)
        if due_at is not None:
            old = task.due_at
            task.set_due_at(due_at)
            changes["due_at_from"] = old
            changes["due_at_to"] = task.due_at
        if changes:
            self._emit(actor, "update", "task", task.id, changes)

    def add_task_label(self, actor_user_id: str, task_id: str, label: str) -> None:
        actor = _require_non_empty(actor_user_id, "actor_user_id")
        task = self.get_task(task_id)
        self._require_project_owner(actor, task.project_id)
        before = task.labels
        task.add_label(label)
        after = task.labels
        if before != after:
            self._emit(actor, "update", "task", task.id, {"labels": sorted(after)})

    def remove_task_label(self, actor_user_id: str, task_id: str, label: str) -> None:
        actor = _require_non_empty(actor_user_id, "actor_user_id")
        task = self.get_task(task_id)
        self._require_project_owner(actor, task.project_id)
        before = task.labels
        task.remove_label(label)
        after = task.labels
        if before != after:
            self._emit(actor, "update", "task", task.id, {"labels": sorted(after)})

    def complete_task(self, actor_user_id: str, task_id: str) -> None:
        actor = _require_non_empty(actor_user_id, "actor_user_id")
        task = self.get_task(task_id)
        self._require_project_owner(actor, task.project_id)
        prev = task.status
        task.complete()
        if task.status != prev:
            self._emit(actor, "update", "task", task.id, {"status": task.status.value})

    def reopen_task(self, actor_user_id: str, task_id: str) -> None:
        actor = _require_non_empty(actor_user_id, "actor_user_id")
        task = self.get_task(task_id)
        self._require_project_owner(actor, task.project_id)
        prev = task.status
        task.reopen()
        if task.status != prev:
            self._emit(actor, "update", "task", task.id, {"status": task.status.value})

    def archive_task(self, actor_user_id: str, task_id: str) -> None:
        actor = _require_non_empty(actor_user_id, "actor_user_id")
        task = self.get_task(task_id)
        self._require_project_owner(actor, task.project_id)
        prev = task.status
        task.archive()
        if task.status != prev:
            self._emit(actor, "update", "task", task.id, {"status": task.status.value})

    def unarchive_task(self, actor_user_id: str, task_id: str) -> None:
        actor = _require_non_empty(actor_user_id, "actor_user_id")
        task = self.get_task(task_id)
        self._require_project_owner(actor, task.project_id)
        prev = task.status
        task.unarchive()
        if task.status != prev:
            self._emit(actor, "update", "task", task.id, {"status": task.status.value})

    def delete_task(self, actor_user_id: str, task_id: str) -> None:
        actor = _require_non_empty(actor_user_id, "actor_user_id")
        task = self.get_task(task_id)
        self._require_project_owner(actor, task.project_id)
        del self._tasks[task.id]
        tids = self._project_tasks.get(task.project_id)
        if tids is not None:
            tids.discard(task.id)
        self._emit(actor, "delete", "task", task.id, {"project_id": task.project_id})

    def delete_project(self, actor_user_id: str, project_id: str) -> None:
        actor = _require_non_empty(actor_user_id, "actor_user_id")
        project = self._require_project_owner(actor, project_id)
        tids = list(self._project_tasks.get(project.id, set()))
        for tid in tids:
            if tid in self._tasks:
                del self._tasks[tid]
        if project.id in self._project_tasks:
            del self._project_tasks[project.id]
        del self._projects[project.id]
        self._emit(actor, "delete", "project", project.id, {"deleted_tasks": len(tids)})

    def list_projects(self, actor_user_id: str) -> Tuple[Project, ...]:
        actor = _require_non_empty(actor_user_id, "actor_user_id")
        self.get_user(actor)
        projects = [p for p in self._projects.values() if p.owner_user_id == actor]
        projects.sort(key=lambda p: (p.archived, p.created_at))
        return tuple(projects)