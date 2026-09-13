from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4


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
    id: UUID
    timestamp: datetime
    actor_id: UUID
    type: str
    entity_type: str
    entity_id: UUID
    data: Dict[str, object]


class Entity:
    def __init__(self, entity_id: Optional[UUID] = None) -> None:
        self._id: UUID = entity_id or uuid4()

    @property
    def id(self) -> UUID:
        return self._id


class User(Entity):
    def __init__(self, name: str, email: str, user_id: Optional[UUID] = None) -> None:
        super().__init__(user_id)
        self._name = self._validate_non_empty(name, "name")
        self._email = self._validate_email(email)

    @staticmethod
    def _validate_non_empty(value: str, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{field} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _validate_email(email: str) -> str:
        email = User._validate_non_empty(email, "email")
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValidationError("email must be a valid email address")
        return email

    @property
    def name(self) -> str:
        return self._name

    @property
    def email(self) -> str:
        return self._email

    def rename(self, new_name: str) -> None:
        self._name = self._validate_non_empty(new_name, "name")

    def change_email(self, new_email: str) -> None:
        self._email = self._validate_email(new_email)


class Project(Entity):
    def __init__(
        self,
        owner_id: UUID,
        name: str,
        project_id: Optional[UUID] = None,
    ) -> None:
        super().__init__(project_id)
        self._owner_id = owner_id
        self._name = self._validate_name(name)
        self._status: ProjectStatus = ProjectStatus.ACTIVE
        self._created_at: datetime = datetime.utcnow()
        self._updated_at: datetime = self._created_at

    @staticmethod
    def _validate_name(name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("project name must be a non-empty string")
        return name.strip()

    @property
    def owner_id(self) -> UUID:
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
    def updated_at(self) -> datetime:
        return self._updated_at

    def rename(self, name: str) -> None:
        self._name = self._validate_name(name)
        self._updated_at = datetime.utcnow()

    def archive(self) -> None:
        if self._status != ProjectStatus.ARCHIVED:
            self._status = ProjectStatus.ARCHIVED
            self._updated_at = datetime.utcnow()

    def unarchive(self) -> None:
        if self._status != ProjectStatus.ACTIVE:
            self._status = ProjectStatus.ACTIVE
            self._updated_at = datetime.utcnow()


class Task(Entity):
    def __init__(
        self,
        owner_id: UUID,
        title: str,
        description: str = "",
        project_id: Optional[UUID] = None,
        due_at: Optional[datetime] = None,
        priority: Priority = Priority.P4,
        task_id: Optional[UUID] = None,
    ) -> None:
        super().__init__(task_id)
        self._owner_id = owner_id
        self._project_id = project_id
        self._title = self._validate_title(title)
        self._description = self._validate_description(description)
        self._due_at = self._validate_due_at(due_at)
        self._priority = self._validate_priority(priority)
        self._status: TaskStatus = TaskStatus.ACTIVE
        self._created_at: datetime = datetime.utcnow()
        self._updated_at: datetime = self._created_at
        self._completed_at: Optional[datetime] = None
        self._labels: Set[str] = set()

    @staticmethod
    def _validate_title(title: str) -> str:
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("task title must be a non-empty string")
        return title.strip()

    @staticmethod
    def _validate_description(description: str) -> str:
        if description is None:
            return ""
        if not isinstance(description, str):
            raise ValidationError("task description must be a string")
        return description

    @staticmethod
    def _validate_due_at(due_at: Optional[datetime]) -> Optional[datetime]:
        if due_at is None:
            return None
        if not isinstance(due_at, datetime):
            raise ValidationError("due_at must be a datetime or None")
        return due_at

    @staticmethod
    def _validate_priority(priority: Priority) -> Priority:
        if isinstance(priority, Priority):
            return priority
        if isinstance(priority, int) and priority in (1, 2, 3, 4):
            return Priority(priority)
        raise ValidationError("priority must be one of Priority.P1..Priority.P4")

    @staticmethod
    def _validate_label(label: str) -> str:
        if not isinstance(label, str) or not label.strip():
            raise ValidationError("label must be a non-empty string")
        return label.strip()

    @property
    def owner_id(self) -> UUID:
        return self._owner_id

    @property
    def project_id(self) -> Optional[UUID]:
        return self._project_id

    @property
    def title(self) -> str:
        return self._title

    @property
    def description(self) -> str:
        return self._description

    @property
    def due_at(self) -> Optional[datetime]:
        return self._due_at

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
    def labels(self) -> Tuple[str, ...]:
        return tuple(sorted(self._labels))

    def set_project(self, project_id: Optional[UUID]) -> None:
        self._project_id = project_id
        self._touch()

    def rename(self, title: str) -> None:
        self._title = self._validate_title(title)
        self._touch()

    def set_description(self, description: str) -> None:
        self._description = self._validate_description(description)
        self._touch()

    def set_due_at(self, due_at: Optional[datetime]) -> None:
        self._due_at = self._validate_due_at(due_at)
        self._touch()

    def set_priority(self, priority: Priority) -> None:
        self._priority = self._validate_priority(priority)
        self._touch()

    def add_label(self, label: str) -> None:
        self._labels.add(self._validate_label(label))
        self._touch()

    def remove_label(self, label: str) -> None:
        label = self._validate_label(label)
        if label in self._labels:
            self._labels.remove(label)
            self._touch()

    def complete(self) -> None:
        if self._status == TaskStatus.ARCHIVED:
            raise ValidationError("cannot complete an archived task")
        if self._status != TaskStatus.COMPLETED:
            self._status = TaskStatus.COMPLETED
            self._completed_at = datetime.utcnow()
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

    def _touch(self) -> None:
        self._updated_at = datetime.utcnow()


class PlantyApp:
    def __init__(self) -> None:
        self._users: Dict[UUID, User] = {}
        self._projects: Dict[UUID, Project] = {}
        self._tasks: Dict[UUID, Task] = {}
        self._events: List[Event] = []

    @property
    def events(self) -> Tuple[Event, ...]:
        return tuple(self._events)

    def _emit(
        self,
        actor_id: UUID,
        type: str,
        entity_type: str,
        entity_id: UUID,
        data: Optional[Dict[str, object]] = None,
    ) -> None:
        self._events.append(
            Event(
                id=uuid4(),
                timestamp=datetime.utcnow(),
                actor_id=actor_id,
                type=type,
                entity_type=entity_type,
                entity_id=entity_id,
                data=dict(data or {}),
            )
        )

    def create_user(self, name: str, email: str) -> User:
        user = User(name=name, email=email)
        if any(u.email.lower() == user.email.lower() for u in self._users.values()):
            raise ValidationError("email already exists")
        self._users[user.id] = user
        self._emit(actor_id=user.id, type="user.created", entity_type="user", entity_id=user.id, data={"email": user.email, "name": user.name})
        return user

    def get_user(self, user_id: UUID) -> User:
        user = self._users.get(user_id)
        if not user:
            raise NotFoundError("user not found")
        return user

    def create_project(self, actor_id: UUID, name: str) -> Project:
        self.get_user(actor_id)
        project = Project(owner_id=actor_id, name=name)
        self._projects[project.id] = project
        self._emit(actor_id=actor_id, type="project.created", entity_type="project", entity_id=project.id, data={"name": project.name})
        return project

    def get_project(self, project_id: UUID) -> Project:
        project = self._projects.get(project_id)
        if not project:
            raise NotFoundError("project not found")
        return project

    def rename_project(self, actor_id: UUID, project_id: UUID, name: str) -> None:
        project = self.get_project(project_id)
        self._require_owner(actor_id, project.owner_id)
        old = project.name
        project.rename(name)
        self._emit(actor_id=actor_id, type="project.renamed", entity_type="project", entity_id=project.id, data={"old_name": old, "new_name": project.name})

    def archive_project(self, actor_id: UUID, project_id: UUID) -> None:
        project = self.get_project(project_id)
        self._require_owner(actor_id, project.owner_id)
        project.archive()
        self._emit(actor_id=actor_id, type="project.archived", entity_type="project", entity_id=project.id, data={})

    def unarchive_project(self, actor_id: UUID, project_id: UUID) -> None:
        project = self.get_project(project_id)
        self._require_owner(actor_id, project.owner_id)
        project.unarchive()
        self._emit(actor_id=actor_id, type="project.unarchived", entity_type="project", entity_id=project.id, data={})

    def create_task(
        self,
        actor_id: UUID,
        title: str,
        description: str = "",
        project_id: Optional[UUID] = None,
        due_at: Optional[datetime] = None,
        priority: Priority = Priority.P4,
    ) -> Task:
        self.get_user(actor_id)
        if project_id is not None:
            project = self.get_project(project_id)
            self._require_owner(actor_id, project.owner_id)
            if project.status == ProjectStatus.ARCHIVED:
                raise ValidationError("cannot add tasks to an archived project")
        task = Task(
            owner_id=actor_id,
            title=title,
            description=description,
            project_id=project_id,
            due_at=due_at,
            priority=priority,
        )
        self._tasks[task.id] = task
        self._emit(
            actor_id=actor_id,
            type="task.created",
            entity_type="task",
            entity_id=task.id,
            data={
                "title": task.title,
                "project_id": str(task.project_id) if task.project_id else None,
                "priority": int(task.priority),
            },
        )
        return task

    def get_task(self, task_id: UUID) -> Task:
        task = self._tasks.get(task_id)
        if not task:
            raise NotFoundError("task not found")
        return task

    def update_task_title(self, actor_id: UUID, task_id: UUID, title: str) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        old = task.title
        task.rename(title)
        self._emit(actor_id=actor_id, type="task.renamed", entity_type="task", entity_id=task.id, data={"old_title": old, "new_title": task.title})

    def update_task_description(self, actor_id: UUID, task_id: UUID, description: str) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        old = task.description
        task.set_description(description)
        self._emit(actor_id=actor_id, type="task.description_updated", entity_type="task", entity_id=task.id, data={"old_description": old, "new_description": task.description})

    def update_task_due_at(self, actor_id: UUID, task_id: UUID, due_at: Optional[datetime]) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        old = task.due_at.isoformat() if task.due_at else None
        task.set_due_at(due_at)
        new = task.due_at.isoformat() if task.due_at else None
        self._emit(actor_id=actor_id, type="task.due_updated", entity_type="task", entity_id=task.id, data={"old_due_at": old, "new_due_at": new})

    def update_task_priority(self, actor_id: UUID, task_id: UUID, priority: Priority) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        old = int(task.priority)
        task.set_priority(priority)
        self._emit(actor_id=actor_id, type="task.priority_updated", entity_type="task", entity_id=task.id, data={"old_priority": old, "new_priority": int(task.priority)})

    def move_task_to_project(self, actor_id: UUID, task_id: UUID, project_id: Optional[UUID]) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        old_project = task.project_id
        if project_id is not None:
            project = self.get_project(project_id)
            self._require_owner(actor_id, project.owner_id)
            if project.status == ProjectStatus.ARCHIVED:
                raise ValidationError("cannot move task to an archived project")
        task.set_project(project_id)
        self._emit(
            actor_id=actor_id,
            type="task.moved",
            entity_type="task",
            entity_id=task.id,
            data={"old_project_id": str(old_project) if old_project else None, "new_project_id": str(task.project_id) if task.project_id else None},
        )

    def add_task_label(self, actor_id: UUID, task_id: UUID, label: str) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        before = set(task.labels)
        task.add_label(label)
        if set(task.labels) != before:
            self._emit(actor_id=actor_id, type="task.label_added", entity_type="task", entity_id=task.id, data={"label": label})

    def remove_task_label(self, actor_id: UUID, task_id: UUID, label: str) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        before = set(task.labels)
        task.remove_label(label)
        if set(task.labels) != before:
            self._emit(actor_id=actor_id, type="task.label_removed", entity_type="task", entity_id=task.id, data={"label": label})

    def complete_task(self, actor_id: UUID, task_id: UUID) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        task.complete()
        self._emit(actor_id=actor_id, type="task.completed", entity_type="task", entity_id=task.id, data={"completed_at": task.completed_at.isoformat() if task.completed_at else None})

    def reopen_task(self, actor_id: UUID, task_id: UUID) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        task.reopen()
        self._emit(actor_id=actor_id, type="task.reopened", entity_type="task", entity_id=task.id, data={})

    def archive_task(self, actor_id: UUID, task_id: UUID) -> None:
        task = self.get_task(task_id)
        self._require_owner(actor_id, task.owner_id)
        task.archive()
        self._emit(actor_id=actor_id, type="task.archived", entity_type="task", entity_id=task.id, data={})

    def list_projects(self, actor_id: UUID, include_archived: bool = False) -> Tuple[Project, ...]:
        self.get_user(actor_id)
        projects = [p for p in self._projects.values() if p.owner_id == actor_id and (include_archived or p.status == ProjectStatus.ACTIVE)]
        projects.sort(key=lambda p: (p.created_at, str(p.id)))
        return tuple(projects)

    def list_tasks(
        self,
        actor_id: UUID,
        project_id: Optional[UUID] = None,
        include_completed: bool = True,
        include_archived: bool = False,
    ) -> Tuple[Task, ...]:
        self.get_user(actor_id)
        if project_id is not None:
            project = self.get_project(project_id)
            self._require_owner(actor_id, project.owner_id)
        tasks = [t for t in self._tasks.values() if t.owner_id == actor_id]
        if project_id is not None:
            tasks = [t for t in tasks if t.project_id == project_id]
        if not include_archived:
            tasks = [t for t in tasks if t.status != TaskStatus.ARCHIVED]
        if not include_completed:
            tasks = [t for t in tasks if t.status != TaskStatus.COMPLETED]
        tasks.sort(key=lambda t: (t.created_at, str(t.id)))
        return tuple(tasks)

    def _require_owner(self, actor_id: UUID, owner_id: UUID) -> None:
        self.get_user(actor_id)
        if actor_id != owner_id:
            raise PermissionError("actor is not the owner")