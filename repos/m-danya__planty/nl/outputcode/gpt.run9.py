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


class ConflictError(PlantyError):
    pass


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


class TaskStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Priority(int, Enum):
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4


@dataclass(frozen=True)
class Event:
    at: datetime
    type: str
    entity: str
    entity_id: int
    data: Dict[str, object]


class _IdGenerator:
    def __init__(self, start: int = 1) -> None:
        self._next = start

    def next(self) -> int:
        v = self._next
        self._next += 1
        return v


class Project:
    def __init__(self, project_id: int, name: str, description: Optional[str] = None) -> None:
        self._id = project_id
        self._name = _require_non_empty(name, "project.name")
        self._description = _require_optional_str(description, "project.description")
        self._created_at = _now()
        self._updated_at = self._created_at
        self._archived = False

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def archived(self) -> bool:
        return self._archived

    def rename(self, name: str) -> None:
        self._name = _require_non_empty(name, "project.name")
        self._updated_at = _now()

    def set_description(self, description: Optional[str]) -> None:
        self._description = _require_optional_str(description, "project.description")
        self._updated_at = _now()

    def archive(self) -> None:
        self._archived = True
        self._updated_at = _now()

    def unarchive(self) -> None:
        self._archived = False
        self._updated_at = _now()


class Label:
    def __init__(self, label_id: int, name: str, color: Optional[str] = None) -> None:
        self._id = label_id
        self._name = _require_non_empty(name, "label.name")
        self._color = _require_optional_str(color, "label.color")
        self._created_at = _now()
        self._updated_at = self._created_at

    @property
    def id(self) -> int:
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

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def rename(self, name: str) -> None:
        self._name = _require_non_empty(name, "label.name")
        self._updated_at = _now()

    def set_color(self, color: Optional[str]) -> None:
        self._color = _require_optional_str(color, "label.color")
        self._updated_at = _now()


class Task:
    def __init__(
        self,
        task_id: int,
        title: str,
        description: Optional[str] = None,
        project_id: Optional[int] = None,
        priority: Priority = Priority.P4,
        due_at: Optional[datetime] = None,
    ) -> None:
        self._id = task_id
        self._title = _require_non_empty(title, "task.title")
        self._description = _require_optional_str(description, "task.description")
        self._project_id = project_id
        self._priority = Priority(int(priority))
        self._due_at = due_at
        self._status = TaskStatus.ACTIVE
        self._label_ids: Set[int] = set()
        self._created_at = _now()
        self._updated_at = self._created_at
        self._completed_at: Optional[datetime] = None

    @property
    def id(self) -> int:
        return self._id

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
    def status(self) -> TaskStatus:
        return self._status

    @property
    def label_ids(self) -> Set[int]:
        return set(self._label_ids)

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    def set_title(self, title: str) -> None:
        self._title = _require_non_empty(title, "task.title")
        self._updated_at = _now()

    def set_description(self, description: Optional[str]) -> None:
        self._description = _require_optional_str(description, "task.description")
        self._updated_at = _now()

    def set_project(self, project_id: Optional[int]) -> None:
        self._project_id = project_id
        self._updated_at = _now()

    def set_priority(self, priority: Priority) -> None:
        self._priority = Priority(int(priority))
        self._updated_at = _now()

    def set_due_at(self, due_at: Optional[datetime]) -> None:
        self._due_at = due_at
        self._updated_at = _now()

    def add_label(self, label_id: int) -> None:
        self._label_ids.add(label_id)
        self._updated_at = _now()

    def remove_label(self, label_id: int) -> None:
        self._label_ids.discard(label_id)
        self._updated_at = _now()

    def complete(self) -> None:
        if self._status == TaskStatus.ARCHIVED:
            raise ConflictError("Cannot complete an archived task")
        self._status = TaskStatus.COMPLETED
        self._completed_at = _now()
        self._updated_at = self._completed_at

    def reopen(self) -> None:
        if self._status == TaskStatus.ARCHIVED:
            raise ConflictError("Cannot reopen an archived task")
        self._status = TaskStatus.ACTIVE
        self._completed_at = None
        self._updated_at = _now()

    def archive(self) -> None:
        self._status = TaskStatus.ARCHIVED
        self._updated_at = _now()

    def unarchive(self) -> None:
        if self._status != TaskStatus.ARCHIVED:
            return
        self._status = TaskStatus.ACTIVE
        self._updated_at = _now()


class PlantyApp:
    def __init__(self) -> None:
        self._project_ids = _IdGenerator()
        self._label_ids = _IdGenerator()
        self._task_ids = _IdGenerator()

        self._projects: Dict[int, Project] = {}
        self._labels: Dict[int, Label] = {}
        self._tasks: Dict[int, Task] = {}

        self._events: List[Event] = []

    def _emit(self, type_: str, entity: str, entity_id: int, data: Optional[Dict[str, object]] = None) -> None:
        self._events.append(Event(at=_now(), type=type_, entity=entity, entity_id=entity_id, data=data or {}))

    def events(self) -> Tuple[Event, ...]:
        return tuple(self._events)

    def create_project(self, name: str, description: Optional[str] = None) -> Project:
        pid = self._project_ids.next()
        project = Project(pid, name=name, description=description)
        self._projects[pid] = project
        self._emit("created", "project", pid, {"name": project.name, "description": project.description})
        return project

    def get_project(self, project_id: int) -> Project:
        try:
            return self._projects[project_id]
        except KeyError as e:
            raise NotFoundError(f"Project {project_id} not found") from e

    def list_projects(self, include_archived: bool = False) -> Tuple[Project, ...]:
        if include_archived:
            return tuple(self._projects.values())
        return tuple(p for p in self._projects.values() if not p.archived)

    def rename_project(self, project_id: int, name: str) -> None:
        p = self.get_project(project_id)
        old = p.name
        p.rename(name)
        self._emit("updated", "project", project_id, {"field": "name", "old": old, "new": p.name})

    def set_project_description(self, project_id: int, description: Optional[str]) -> None:
        p = self.get_project(project_id)
        old = p.description
        p.set_description(description)
        self._emit("updated", "project", project_id, {"field": "description", "old": old, "new": p.description})

    def archive_project(self, project_id: int) -> None:
        p = self.get_project(project_id)
        if p.archived:
            return
        p.archive()
        self._emit("archived", "project", project_id, {})

    def unarchive_project(self, project_id: int) -> None:
        p = self.get_project(project_id)
        if not p.archived:
            return
        p.unarchive()
        self._emit("unarchived", "project", project_id, {})

    def delete_project(self, project_id: int) -> None:
        if project_id not in self._projects:
            raise NotFoundError(f"Project {project_id} not found")
        for t in self._tasks.values():
            if t.project_id == project_id:
                t.set_project(None)
        del self._projects[project_id]
        self._emit("deleted", "project", project_id, {})

    def create_label(self, name: str, color: Optional[str] = None) -> Label:
        lid = self._label_ids.next()
        label = Label(lid, name=name, color=color)
        self._labels[lid] = label
        self._emit("created", "label", lid, {"name": label.name, "color": label.color})
        return label

    def get_label(self, label_id: int) -> Label:
        try:
            return self._labels[label_id]
        except KeyError as e:
            raise NotFoundError(f"Label {label_id} not found") from e

    def list_labels(self) -> Tuple[Label, ...]:
        return tuple(self._labels.values())

    def rename_label(self, label_id: int, name: str) -> None:
        l = self.get_label(label_id)
        old = l.name
        l.rename(name)
        self._emit("updated", "label", label_id, {"field": "name", "old": old, "new": l.name})

    def set_label_color(self, label_id: int, color: Optional[str]) -> None:
        l = self.get_label(label_id)
        old = l.color
        l.set_color(color)
        self._emit("updated", "label", label_id, {"field": "color", "old": old, "new": l.color})

    def delete_label(self, label_id: int) -> None:
        if label_id not in self._labels:
            raise NotFoundError(f"Label {label_id} not found")
        for t in self._tasks.values():
            if label_id in t.label_ids:
                t.remove_label(label_id)
        del self._labels[label_id]
        self._emit("deleted", "label", label_id, {})

    def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        project_id: Optional[int] = None,
        priority: Priority = Priority.P4,
        due_at: Optional[datetime] = None,
        label_ids: Optional[Set[int]] = None,
    ) -> Task:
        if project_id is not None and project_id not in self._projects:
            raise NotFoundError(f"Project {project_id} not found")
        if label_ids:
            missing = [lid for lid in label_ids if lid not in self._labels]
            if missing:
                raise NotFoundError(f"Labels not found: {missing}")

        tid = self._task_ids.next()
        task = Task(
            tid,
            title=title,
            description=description,
            project_id=project_id,
            priority=priority,
            due_at=due_at,
        )
        if label_ids:
            for lid in label_ids:
                task.add_label(lid)

        self._tasks[tid] = task
        self._emit(
            "created",
            "task",
            tid,
            {
                "title": task.title,
                "description": task.description,
                "project_id": task.project_id,
                "priority": int(task.priority),
                "due_at": task.due_at.isoformat() if task.due_at else None,
                "label_ids": sorted(task.label_ids),
            },
        )
        return task

    def get_task(self, task_id: int) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError as e:
            raise NotFoundError(f"Task {task_id} not found") from e

    def list_tasks(
        self,
        project_id: Optional[int] = None,
        label_id: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        include_archived: bool = False,
    ) -> Tuple[Task, ...]:
        tasks = list(self._tasks.values())
        if project_id is not None:
            tasks = [t for t in tasks if t.project_id == project_id]
        if label_id is not None:
            tasks = [t for t in tasks if label_id in t.label_ids]
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if not include_archived:
            tasks = [t for t in tasks if t.status != TaskStatus.ARCHIVED]
        return tuple(tasks)

    def update_task_title(self, task_id: int, title: str) -> None:
        t = self.get_task(task_id)
        old = t.title
        t.set_title(title)
        self._emit("updated", "task", task_id, {"field": "title", "old": old, "new": t.title})

    def update_task_description(self, task_id: int, description: Optional[str]) -> None:
        t = self.get_task(task_id)
        old = t.description
        t.set_description(description)
        self._emit("updated", "task", task_id, {"field": "description", "old": old, "new": t.description})

    def move_task(self, task_id: int, project_id: Optional[int]) -> None:
        if project_id is not None and project_id not in self._projects:
            raise NotFoundError(f"Project {project_id} not found")
        t = self.get_task(task_id)
        old = t.project_id
        t.set_project(project_id)
        self._emit("updated", "task", task_id, {"field": "project_id", "old": old, "new": t.project_id})

    def set_task_priority(self, task_id: int, priority: Priority) -> None:
        t = self.get_task(task_id)
        old = int(t.priority)
        t.set_priority(priority)
        self._emit("updated", "task", task_id, {"field": "priority", "old": old, "new": int(t.priority)})

    def set_task_due_at(self, task_id: int, due_at: Optional[datetime]) -> None:
        t = self.get_task(task_id)
        old = t.due_at.isoformat() if t.due_at else None
        t.set_due_at(due_at)
        new = t.due_at.isoformat() if t.due_at else None
        self._emit("updated", "task", task_id, {"field": "due_at", "old": old, "new": new})

    def add_label_to_task(self, task_id: int, label_id: int) -> None:
        if label_id not in self._labels:
            raise NotFoundError(f"Label {label_id} not found")
        t = self.get_task(task_id)
        if label_id in t.label_ids:
            return
        t.add_label(label_id)
        self._emit("updated", "task", task_id, {"field": "label_ids", "action": "add", "label_id": label_id})

    def remove_label_from_task(self, task_id: int, label_id: int) -> None:
        t = self.get_task(task_id)
        if label_id not in t.label_ids:
            return
        t.remove_label(label_id)
        self._emit("updated", "task", task_id, {"field": "label_ids", "action": "remove", "label_id": label_id})

    def complete_task(self, task_id: int) -> None:
        t = self.get_task(task_id)
        if t.status == TaskStatus.COMPLETED:
            return
        t.complete()
        self._emit("completed", "task", task_id, {"completed_at": t.completed_at.isoformat() if t.completed_at else None})

    def reopen_task(self, task_id: int) -> None:
        t = self.get_task(task_id)
        if t.status == TaskStatus.ACTIVE:
            return
        t.reopen()
        self._emit("reopened", "task", task_id, {})

    def archive_task(self, task_id: int) -> None:
        t = self.get_task(task_id)
        if t.status == TaskStatus.ARCHIVED:
            return
        t.archive()
        self._emit("archived", "task", task_id, {})

    def unarchive_task(self, task_id: int) -> None:
        t = self.get_task(task_id)
        if t.status != TaskStatus.ARCHIVED:
            return
        t.unarchive()
        self._emit("unarchived", "task", task_id, {})

    def delete_task(self, task_id: int) -> None:
        if task_id not in self._tasks:
            raise NotFoundError(f"Task {task_id} not found")
        del self._tasks[task_id]
        self._emit("deleted", "task", task_id, {})