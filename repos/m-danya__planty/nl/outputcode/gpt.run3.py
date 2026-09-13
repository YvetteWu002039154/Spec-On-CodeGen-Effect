from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Iterable
from uuid import UUID, uuid4


class PlantyError(Exception):
    pass


class NotFoundError(PlantyError):
    pass


class ValidationError(PlantyError):
    pass


class ConflictError(PlantyError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_non_empty_str(value: str, field: str) -> str:
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


class TaskStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class Event:
    id: UUID
    type: str
    timestamp: datetime
    entity_type: str
    entity_id: UUID
    data: Dict[str, object]


class EventLog:
    def __init__(self) -> None:
        self._events: List[Event] = []

    def append(self, event_type: str, entity_type: str, entity_id: UUID, data: Optional[Dict[str, object]] = None) -> Event:
        ev = Event(
            id=uuid4(),
            type=_require_non_empty_str(event_type, "event_type"),
            timestamp=_utcnow(),
            entity_type=_require_non_empty_str(entity_type, "entity_type"),
            entity_id=entity_id,
            data=dict(data or {}),
        )
        self._events.append(ev)
        return ev

    def list(self) -> Tuple[Event, ...]:
        return tuple(self._events)

    def list_for_entity(self, entity_type: str, entity_id: UUID) -> Tuple[Event, ...]:
        entity_type = _require_non_empty_str(entity_type, "entity_type")
        return tuple(e for e in self._events if e.entity_type == entity_type and e.entity_id == entity_id)


class Task:
    def __init__(
        self,
        title: str,
        *,
        description: Optional[str] = None,
        project_id: Optional[UUID] = None,
        labels: Optional[Iterable[str]] = None,
        task_id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        self._id: UUID = task_id or uuid4()
        self._title: str = _require_non_empty_str(title, "title")
        self._description: Optional[str] = _require_optional_str(description, "description")
        self._project_id: Optional[UUID] = project_id
        self._labels: Set[str] = set()
        if labels is not None:
            for l in labels:
                self.add_label(l)
        self._status: TaskStatus = TaskStatus.ACTIVE
        self._created_at: datetime = created_at or _utcnow()
        self._updated_at: datetime = self._created_at
        self._completed_at: Optional[datetime] = None
        self._archived_at: Optional[datetime] = None

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def project_id(self) -> Optional[UUID]:
        return self._project_id

    @property
    def labels(self) -> Tuple[str, ...]:
        return tuple(sorted(self._labels))

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
    def archived_at(self) -> Optional[datetime]:
        return self._archived_at

    def rename(self, title: str) -> None:
        self._title = _require_non_empty_str(title, "title")
        self._touch()

    def set_description(self, description: Optional[str]) -> None:
        self._description = _require_optional_str(description, "description")
        self._touch()

    def move_to_project(self, project_id: Optional[UUID]) -> None:
        self._project_id = project_id
        self._touch()

    def add_label(self, label: str) -> None:
        label = _require_non_empty_str(label, "label")
        self._labels.add(label)
        self._touch()

    def remove_label(self, label: str) -> None:
        label = _require_non_empty_str(label, "label")
        if label in self._labels:
            self._labels.remove(label)
            self._touch()

    def complete(self) -> None:
        if self._status == TaskStatus.ARCHIVED:
            raise ConflictError("Cannot complete an archived task")
        if self._status != TaskStatus.COMPLETED:
            self._status = TaskStatus.COMPLETED
            self._completed_at = _utcnow()
            self._touch()

    def reopen(self) -> None:
        if self._status == TaskStatus.ARCHIVED:
            raise ConflictError("Cannot reopen an archived task")
        if self._status != TaskStatus.ACTIVE:
            self._status = TaskStatus.ACTIVE
            self._completed_at = None
            self._touch()

    def archive(self) -> None:
        if self._status != TaskStatus.ARCHIVED:
            self._status = TaskStatus.ARCHIVED
            self._archived_at = _utcnow()
            self._touch()

    def _touch(self) -> None:
        self._updated_at = _utcnow()


class Project:
    def __init__(
        self,
        name: str,
        *,
        project_id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        self._id: UUID = project_id or uuid4()
        self._name: str = _require_non_empty_str(name, "name")
        self._status: ProjectStatus = ProjectStatus.ACTIVE
        self._created_at: datetime = created_at or _utcnow()
        self._updated_at: datetime = self._created_at
        self._archived_at: Optional[datetime] = None

    @property
    def id(self) -> UUID:
        return self._id

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
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def archived_at(self) -> Optional[datetime]:
        return self._archived_at

    def rename(self, name: str) -> None:
        self._name = _require_non_empty_str(name, "name")
        self._touch()

    def archive(self) -> None:
        if self._status != ProjectStatus.ARCHIVED:
            self._status = ProjectStatus.ARCHIVED
            self._archived_at = _utcnow()
            self._touch()

    def reopen(self) -> None:
        if self._status != ProjectStatus.ACTIVE:
            self._status = ProjectStatus.ACTIVE
            self._archived_at = None
            self._touch()

    def _touch(self) -> None:
        self._updated_at = _utcnow()


class PlantyApp:
    def __init__(self) -> None:
        self._projects: Dict[UUID, Project] = {}
        self._tasks: Dict[UUID, Task] = {}
        self._event_log: EventLog = EventLog()

    @property
    def events(self) -> EventLog:
        return self._event_log

    def create_project(self, name: str) -> Project:
        project = Project(name=name)
        self._projects[project.id] = project
        self._event_log.append("project.created", "project", project.id, {"name": project.name})
        return project

    def get_project(self, project_id: UUID) -> Project:
        try:
            return self._projects[project_id]
        except KeyError as e:
            raise NotFoundError("Project not found") from e

    def list_projects(self, *, include_archived: bool = False) -> Tuple[Project, ...]:
        if include_archived:
            return tuple(self._projects.values())
        return tuple(p for p in self._projects.values() if p.status == ProjectStatus.ACTIVE)

    def rename_project(self, project_id: UUID, name: str) -> None:
        project = self.get_project(project_id)
        old = project.name
        project.rename(name)
        self._event_log.append("project.renamed", "project", project.id, {"old_name": old, "new_name": project.name})

    def archive_project(self, project_id: UUID) -> None:
        project = self.get_project(project_id)
        if project.status != ProjectStatus.ARCHIVED:
            project.archive()
            self._event_log.append("project.archived", "project", project.id, {})

    def reopen_project(self, project_id: UUID) -> None:
        project = self.get_project(project_id)
        if project.status != ProjectStatus.ACTIVE:
            project.reopen()
            self._event_log.append("project.reopened", "project", project.id, {})

    def delete_project(self, project_id: UUID) -> None:
        project = self.get_project(project_id)
        for t in self._tasks.values():
            if t.project_id == project.id:
                t.move_to_project(None)
                self._event_log.append("task.moved", "task", t.id, {"project_id": None})
        del self._projects[project.id]
        self._event_log.append("project.deleted", "project", project.id, {"name": project.name})

    def create_task(
        self,
        title: str,
        *,
        description: Optional[str] = None,
        project_id: Optional[UUID] = None,
        labels: Optional[Iterable[str]] = None,
    ) -> Task:
        if project_id is not None:
            project = self.get_project(project_id)
            if project.status == ProjectStatus.ARCHIVED:
                raise ConflictError("Cannot add task to an archived project")
        task = Task(title=title, description=description, project_id=project_id, labels=labels)
        self._tasks[task.id] = task
        self._event_log.append(
            "task.created",
            "task",
            task.id,
            {
                "title": task.title,
                "description": task.description,
                "project_id": str(task.project_id) if task.project_id else None,
                "labels": list(task.labels),
            },
        )
        return task

    def get_task(self, task_id: UUID) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError as e:
            raise NotFoundError("Task not found") from e

    def list_tasks(
        self,
        *,
        project_id: Optional[UUID] = None,
        status: Optional[TaskStatus] = None,
        label: Optional[str] = None,
        include_archived: bool = False,
    ) -> Tuple[Task, ...]:
        if label is not None:
            label = _require_non_empty_str(label, "label")

        tasks = list(self._tasks.values())

        if project_id is not None:
            tasks = [t for t in tasks if t.project_id == project_id]

        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        elif not include_archived:
            tasks = [t for t in tasks if t.status != TaskStatus.ARCHIVED]

        if label is not None:
            tasks = [t for t in tasks if label in set(t.labels)]

        tasks.sort(key=lambda t: (t.created_at, str(t.id)))
        return tuple(tasks)

    def rename_task(self, task_id: UUID, title: str) -> None:
        task = self.get_task(task_id)
        old = task.title
        task.rename(title)
        self._event_log.append("task.renamed", "task", task.id, {"old_title": old, "new_title": task.title})

    def set_task_description(self, task_id: UUID, description: Optional[str]) -> None:
        task = self.get_task(task_id)
        old = task.description
        task.set_description(description)
        self._event_log.append(
            "task.description_set",
            "task",
            task.id,
            {"old_description": old, "new_description": task.description},
        )

    def move_task(self, task_id: UUID, project_id: Optional[UUID]) -> None:
        task = self.get_task(task_id)
        if project_id is not None:
            project = self.get_project(project_id)
            if project.status == ProjectStatus.ARCHIVED:
                raise ConflictError("Cannot move task to an archived project")
        task.move_to_project(project_id)
        self._event_log.append(
            "task.moved",
            "task",
            task.id,
            {"project_id": str(project_id) if project_id else None},
        )

    def add_task_label(self, task_id: UUID, label: str) -> None:
        task = self.get_task(task_id)
        before = set(task.labels)
        task.add_label(label)
        after = set(task.labels)
        if after != before:
            self._event_log.append("task.label_added", "task", task.id, {"label": label})

    def remove_task_label(self, task_id: UUID, label: str) -> None:
        task = self.get_task(task_id)
        before = set(task.labels)
        task.remove_label(label)
        after = set(task.labels)
        if after != before:
            self._event_log.append("task.label_removed", "task", task.id, {"label": label})

    def complete_task(self, task_id: UUID) -> None:
        task = self.get_task(task_id)
        prev = task.status
        task.complete()
        if task.status != prev:
            self._event_log.append("task.completed", "task", task.id, {"completed_at": task.completed_at.isoformat() if task.completed_at else None})

    def reopen_task(self, task_id: UUID) -> None:
        task = self.get_task(task_id)
        prev = task.status
        task.reopen()
        if task.status != prev:
            self._event_log.append("task.reopened", "task", task.id, {})

    def archive_task(self, task_id: UUID) -> None:
        task = self.get_task(task_id)
        prev = task.status
        task.archive()
        if task.status != prev:
            self._event_log.append("task.archived", "task", task.id, {"archived_at": task.archived_at.isoformat() if task.archived_at else None})

    def delete_task(self, task_id: UUID) -> None:
        task = self.get_task(task_id)
        del self._tasks[task.id]
        self._event_log.append("task.deleted", "task", task.id, {"title": task.title})

    def get_inbox_tasks(self, *, include_archived: bool = False) -> Tuple[Task, ...]:
        return self.list_tasks(project_id=None, include_archived=include_archived)

    def search_tasks(self, query: str, *, include_archived: bool = False) -> Tuple[Task, ...]:
        q = _require_non_empty_str(query, "query").lower()
        tasks = self.list_tasks(include_archived=include_archived)
        matched: List[Task] = []
        for t in tasks:
            hay = " ".join([t.title, t.description or "", " ".join(t.labels)]).lower()
            if q in hay:
                matched.append(t)
        return tuple(matched)