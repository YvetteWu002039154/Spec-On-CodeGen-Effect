from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Iterable


class PlantyError(Exception):
    pass


class NotFoundError(PlantyError):
    pass


class ValidationError(PlantyError):
    pass


class PermissionError(PlantyError):
    pass


class Status(str, Enum):
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
    actor_id: str
    action: str
    entity_type: str
    entity_id: str
    details: Dict[str, str]


class _IdGenerator:
    def __init__(self, prefix: str) -> None:
        self._prefix = prefix
        self._n = 0

    def next(self) -> str:
        self._n += 1
        return f"{self._prefix}{self._n}"


class User:
    def __init__(self, user_id: str, name: str) -> None:
        if not user_id or not user_id.strip():
            raise ValidationError("user_id is required")
        if not name or not name.strip():
            raise ValidationError("name is required")
        self._id = user_id
        self._name = name.strip()

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name


class Label:
    def __init__(self, label_id: str, name: str) -> None:
        if not label_id or not label_id.strip():
            raise ValidationError("label_id is required")
        if not name or not name.strip():
            raise ValidationError("label name is required")
        self._id = label_id
        self._name = name.strip()

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name


class Project:
    def __init__(self, project_id: str, owner_id: str, name: str) -> None:
        if not project_id or not project_id.strip():
            raise ValidationError("project_id is required")
        if not owner_id or not owner_id.strip():
            raise ValidationError("owner_id is required")
        if not name or not name.strip():
            raise ValidationError("project name is required")
        self._id = project_id
        self._owner_id = owner_id
        self._name = name.strip()
        self._status: Status = Status.ACTIVE

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
    def status(self) -> Status:
        return self._status

    def rename(self, name: str) -> None:
        if not name or not name.strip():
            raise ValidationError("project name is required")
        self._name = name.strip()

    def archive(self) -> None:
        self._status = Status.ARCHIVED

    def unarchive(self) -> None:
        self._status = Status.ACTIVE


class Task:
    def __init__(
        self,
        task_id: str,
        owner_id: str,
        title: str,
        project_id: Optional[str] = None,
        description: str = "",
        priority: Priority = Priority.P4,
        due_at: Optional[datetime] = None,
    ) -> None:
        if not task_id or not task_id.strip():
            raise ValidationError("task_id is required")
        if not owner_id or not owner_id.strip():
            raise ValidationError("owner_id is required")
        if not title or not title.strip():
            raise ValidationError("title is required")
        if description is None:
            raise ValidationError("description cannot be None")
        if project_id is not None and not project_id.strip():
            raise ValidationError("project_id cannot be empty")
        self._id = task_id
        self._owner_id = owner_id
        self._title = title.strip()
        self._description = description
        self._project_id = project_id
        self._priority = Priority(int(priority))
        self._due_at = due_at
        self._status: Status = Status.ACTIVE
        self._label_ids: Set[str] = set()
        self._created_at = datetime.utcnow()
        self._updated_at = self._created_at
        self._completed_at: Optional[datetime] = None

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
    def status(self) -> Status:
        return self._status

    @property
    def label_ids(self) -> Tuple[str, ...]:
        return tuple(sorted(self._label_ids))

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
        self._updated_at = datetime.utcnow()

    def set_title(self, title: str) -> None:
        if not title or not title.strip():
            raise ValidationError("title is required")
        self._title = title.strip()
        self._touch()

    def set_description(self, description: str) -> None:
        if description is None:
            raise ValidationError("description cannot be None")
        self._description = description
        self._touch()

    def set_project(self, project_id: Optional[str]) -> None:
        if project_id is not None and not project_id.strip():
            raise ValidationError("project_id cannot be empty")
        self._project_id = project_id
        self._touch()

    def set_priority(self, priority: Priority) -> None:
        self._priority = Priority(int(priority))
        self._touch()

    def set_due_at(self, due_at: Optional[datetime]) -> None:
        self._due_at = due_at
        self._touch()

    def add_label(self, label_id: str) -> None:
        if not label_id or not label_id.strip():
            raise ValidationError("label_id is required")
        self._label_ids.add(label_id)
        self._touch()

    def remove_label(self, label_id: str) -> None:
        if not label_id or not label_id.strip():
            raise ValidationError("label_id is required")
        self._label_ids.discard(label_id)
        self._touch()

    def complete(self) -> None:
        if self._status == Status.ARCHIVED:
            raise ValidationError("cannot complete an archived task")
        self._status = Status.COMPLETED
        self._completed_at = datetime.utcnow()
        self._touch()

    def reopen(self) -> None:
        if self._status == Status.ARCHIVED:
            raise ValidationError("cannot reopen an archived task")
        self._status = Status.ACTIVE
        self._completed_at = None
        self._touch()

    def archive(self) -> None:
        self._status = Status.ARCHIVED
        self._touch()

    def unarchive(self) -> None:
        if self._status != Status.ARCHIVED:
            return
        self._status = Status.ACTIVE
        self._touch()


class PlantyApp:
    def __init__(self) -> None:
        self._users: Dict[str, User] = {}
        self._projects: Dict[str, Project] = {}
        self._tasks: Dict[str, Task] = {}
        self._labels: Dict[str, Label] = {}
        self._events: List[Event] = []

        self._project_ids = _IdGenerator("p")
        self._task_ids = _IdGenerator("t")
        self._label_ids = _IdGenerator("l")

    def _now(self) -> datetime:
        return datetime.utcnow()

    def _record(self, actor_id: str, action: str, entity_type: str, entity_id: str, details: Optional[Dict[str, str]] = None) -> None:
        if details is None:
            details = {}
        self._events.append(
            Event(
                at=self._now(),
                actor_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=dict(details),
            )
        )

    def register_user(self, user_id: str, name: str) -> User:
        if user_id in self._users:
            raise ValidationError("user_id already exists")
        user = User(user_id=user_id, name=name)
        self._users[user.id] = user
        self._record(actor_id=user.id, action="user_registered", entity_type="user", entity_id=user.id, details={"name": user.name})
        return user

    def get_user(self, user_id: str) -> User:
        try:
            return self._users[user_id]
        except KeyError as e:
            raise NotFoundError("user not found") from e

    def create_project(self, owner_id: str, name: str) -> Project:
        self.get_user(owner_id)
        project_id = self._project_ids.next()
        project = Project(project_id=project_id, owner_id=owner_id, name=name)
        self._projects[project.id] = project
        self._record(actor_id=owner_id, action="project_created", entity_type="project", entity_id=project.id, details={"name": project.name})
        return project

    def get_project(self, project_id: str) -> Project:
        try:
            return self._projects[project_id]
        except KeyError as e:
            raise NotFoundError("project not found") from e

    def rename_project(self, actor_id: str, project_id: str, name: str) -> None:
        self.get_user(actor_id)
        project = self.get_project(project_id)
        if project.owner_id != actor_id:
            raise PermissionError("only the owner can rename the project")
        old = project.name
        project.rename(name)
        self._record(actor_id=actor_id, action="project_renamed", entity_type="project", entity_id=project.id, details={"from": old, "to": project.name})

    def archive_project(self, actor_id: str, project_id: str) -> None:
        self.get_user(actor_id)
        project = self.get_project(project_id)
        if project.owner_id != actor_id:
            raise PermissionError("only the owner can archive the project")
        project.archive()
        self._record(actor_id=actor_id, action="project_archived", entity_type="project", entity_id=project.id, details={})

    def unarchive_project(self, actor_id: str, project_id: str) -> None:
        self.get_user(actor_id)
        project = self.get_project(project_id)
        if project.owner_id != actor_id:
            raise PermissionError("only the owner can unarchive the project")
        project.unarchive()
        self._record(actor_id=actor_id, action="project_unarchived", entity_type="project", entity_id=project.id, details={})

    def create_label(self, owner_id: str, name: str) -> Label:
        self.get_user(owner_id)
        label_id = self._label_ids.next()
        label = Label(label_id=label_id, name=name)
        self._labels[label.id] = label
        self._record(actor_id=owner_id, action="label_created", entity_type="label", entity_id=label.id, details={"name": label.name})
        return label

    def get_label(self, label_id: str) -> Label:
        try:
            return self._labels[label_id]
        except KeyError as e:
            raise NotFoundError("label not found") from e

    def create_task(
        self,
        owner_id: str,
        title: str,
        project_id: Optional[str] = None,
        description: str = "",
        priority: Priority = Priority.P4,
        due_at: Optional[datetime] = None,
    ) -> Task:
        self.get_user(owner_id)
        if project_id is not None:
            project = self.get_project(project_id)
            if project.owner_id != owner_id:
                raise PermissionError("cannot create task in a project you do not own")
            if project.status == Status.ARCHIVED:
                raise ValidationError("cannot create task in an archived project")
        task_id = self._task_ids.next()
        task = Task(
            task_id=task_id,
            owner_id=owner_id,
            title=title,
            project_id=project_id,
            description=description,
            priority=priority,
            due_at=due_at,
        )
        self._tasks[task.id] = task
        self._record(actor_id=owner_id, action="task_created", entity_type="task", entity_id=task.id, details={"title": task.title})
        return task

    def get_task(self, task_id: str) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError as e:
            raise NotFoundError("task not found") from e

    def _ensure_task_owner(self, actor_id: str, task: Task) -> None:
        if task.owner_id != actor_id:
            raise PermissionError("only the owner can modify the task")

    def update_task_title(self, actor_id: str, task_id: str, title: str) -> None:
        self.get_user(actor_id)
        task = self.get_task(task_id)
        self._ensure_task_owner(actor_id, task)
        old = task.title
        task.set_title(title)
        self._record(actor_id=actor_id, action="task_title_updated", entity_type="task", entity_id=task.id, details={"from": old, "to": task.title})

    def update_task_description(self, actor_id: str, task_id: str, description: str) -> None:
        self.get_user(actor_id)
        task = self.get_task(task_id)
        self._ensure_task_owner(actor_id, task)
        task.set_description(description)
        self._record(actor_id=actor_id, action="task_description_updated", entity_type="task", entity_id=task.id, details={})

    def update_task_priority(self, actor_id: str, task_id: str, priority: Priority) -> None:
        self.get_user(actor_id)
        task = self.get_task(task_id)
        self._ensure_task_owner(actor_id, task)
        old = str(int(task.priority))
        task.set_priority(priority)
        self._record(actor_id=actor_id, action="task_priority_updated", entity_type="task", entity_id=task.id, details={"from": old, "to": str(int(task.priority))})

    def update_task_due_at(self, actor_id: str, task_id: str, due_at: Optional[datetime]) -> None:
        self.get_user(actor_id)
        task = self.get_task(task_id)
        self._ensure_task_owner(actor_id, task)
        task.set_due_at(due_at)
        self._record(actor_id=actor_id, action="task_due_updated", entity_type="task", entity_id=task.id, details={})

    def move_task_to_project(self, actor_id: str, task_id: str, project_id: Optional[str]) -> None:
        self.get_user(actor_id)
        task = self.get_task(task_id)
        self._ensure_task_owner(actor_id, task)
        if project_id is not None:
            project = self.get_project(project_id)
            if project.owner_id != actor_id:
                raise PermissionError("cannot move task to a project you do not own")
            if project.status == Status.ARCHIVED:
                raise ValidationError("cannot move task to an archived project")
        old = task.project_id or ""
        task.set_project(project_id)
        self._record(actor_id=actor_id, action="task_moved", entity_type="task", entity_id=task.id, details={"from": old, "to": task.project_id or ""})

    def add_label_to_task(self, actor_id: str, task_id: str, label_id: str) -> None:
        self.get_user(actor_id)
        task = self.get_task(task_id)
        self._ensure_task_owner(actor_id, task)
        self.get_label(label_id)
        task.add_label(label_id)
        self._record(actor_id=actor_id, action="task_label_added", entity_type="task", entity_id=task.id, details={"label_id": label_id})

    def remove_label_from_task(self, actor_id: str, task_id: str, label_id: str) -> None:
        self.get_user(actor_id)
        task = self.get_task(task_id)
        self._ensure_task_owner(actor_id, task)
        self.get_label(label_id)
        task.remove_label(label_id)
        self._record(actor_id=actor_id, action="task_label_removed", entity_type="task", entity_id=task.id, details={"label_id": label_id})

    def complete_task(self, actor_id: str, task_id: str) -> None:
        self.get_user(actor_id)
        task = self.get_task(task_id)
        self._ensure_task_owner(actor_id, task)
        task.complete()
        self._record(actor_id=actor_id, action="task_completed", entity_type="task", entity_id=task.id, details={})

    def reopen_task(self, actor_id: str, task_id: str) -> None:
        self.get_user(actor_id)
        task = self.get_task(task_id)
        self._ensure_task_owner(actor_id, task)
        task.reopen()
        self._record(actor_id=actor_id, action="task_reopened", entity_type="task", entity_id=task.id, details={})

    def archive_task(self, actor_id: str, task_id: str) -> None:
        self.get_user(actor_id)
        task = self.get_task(task_id)
        self._ensure_task_owner(actor_id, task)
        task.archive()
        self._record(actor_id=actor_id, action="task_archived", entity_type="task", entity_id=task.id, details={})

    def unarchive_task(self, actor_id: str, task_id: str) -> None:
        self.get_user(actor_id)
        task = self.get_task(task_id)
        self._ensure_task_owner(actor_id, task)
        task.unarchive()
        self._record(actor_id=actor_id, action="task_unarchived", entity_type="task", entity_id=task.id, details={})

    def list_tasks(
        self,
        owner_id: str,
        project_id: Optional[str] = None,
        status: Optional[Status] = None,
        label_ids: Optional[Iterable[str]] = None,
    ) -> List[Task]:
        self.get_user(owner_id)
        if project_id is not None:
            project = self.get_project(project_id)
            if project.owner_id != owner_id:
                raise PermissionError("cannot list tasks for a project you do not own")
        label_set: Optional[Set[str]] = None
        if label_ids is not None:
            label_set = set(label_ids)
            for lid in label_set:
                self.get_label(lid)

        out: List[Task] = []
        for task in self._tasks.values():
            if task.owner_id != owner_id:
                continue
            if project_id is not None and task.project_id != project_id:
                continue
            if status is not None and task.status != status:
                continue
            if label_set is not None and not label_set.issubset(set(task.label_ids)):
                continue
            out.append(task)
        out.sort(key=lambda t: (t.status.value, int(t.priority), t.due_at or datetime.max, t.created_at))
        return out

    def list_projects(self, owner_id: str, status: Optional[Status] = None) -> List[Project]:
        self.get_user(owner_id)
        out = [p for p in self._projects.values() if p.owner_id == owner_id and (status is None or p.status == status)]
        out.sort(key=lambda p: (p.status.value, p.name.lower(), p.id))
        return out

    def list_labels(self) -> List[Label]:
        out = list(self._labels.values())
        out.sort(key=lambda l: (l.name.lower(), l.id))
        return out

    def events(self) -> Tuple[Event, ...]:
        return tuple(self._events)

    def events_for_entity(self, entity_type: str, entity_id: str) -> Tuple[Event, ...]:
        return tuple(e for e in self._events if e.entity_type == entity_type and e.entity_id == entity_id)