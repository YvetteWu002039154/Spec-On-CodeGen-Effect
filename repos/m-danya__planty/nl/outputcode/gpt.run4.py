from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Iterable
from uuid import uuid4


class PlantyError(Exception):
    pass


class NotFoundError(PlantyError):
    pass


class ValidationError(PlantyError):
    pass


class PermissionError(PlantyError):
    pass


class Status(str, Enum):
    TODO = "todo"
    DONE = "done"


class Priority(int, Enum):
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4


def _now() -> datetime:
    return datetime.utcnow()


def _new_id() -> str:
    return uuid4().hex


@dataclass(frozen=True)
class Event:
    at: datetime
    type: str
    entity: str
    entity_id: str
    data: Dict[str, object] = field(default_factory=dict)


@dataclass
class User:
    id: str
    name: str
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValidationError("User name must be non-empty.")
        self.name = self.name.strip()


@dataclass
class Project:
    id: str
    name: str
    owner_id: str
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValidationError("Project name must be non-empty.")
        self.name = self.name.strip()


@dataclass
class Task:
    id: str
    title: str
    owner_id: str
    project_id: Optional[str] = None
    status: Status = Status.TODO
    priority: Priority = Priority.P4
    created_at: datetime = field(default_factory=_now)
    completed_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise ValidationError("Task title must be non-empty.")
        self.title = self.title.strip()
        if self.completed_at is not None and self.status != Status.DONE:
            raise ValidationError("completed_at can only be set when status is DONE.")
        if self.status == Status.DONE and self.completed_at is None:
            self.completed_at = _now()


class Planty:
    def __init__(self) -> None:
        self._users: Dict[str, User] = {}
        self._projects: Dict[str, Project] = {}
        self._tasks: Dict[str, Task] = {}
        self._project_tasks: Dict[str, Set[str]] = {}
        self._user_projects: Dict[str, Set[str]] = {}
        self._user_tasks: Dict[str, Set[str]] = {}
        self._events: List[Event] = []

    @property
    def events(self) -> Tuple[Event, ...]:
        return tuple(self._events)

    def _emit(self, type_: str, entity: str, entity_id: str, data: Optional[Dict[str, object]] = None) -> None:
        self._events.append(Event(at=_now(), type=type_, entity=entity, entity_id=entity_id, data=data or {}))

    def create_user(self, name: str) -> User:
        user = User(id=_new_id(), name=name)
        self._users[user.id] = user
        self._user_projects.setdefault(user.id, set())
        self._user_tasks.setdefault(user.id, set())
        self._emit("created", "user", user.id, {"name": user.name})
        return user

    def get_user(self, user_id: str) -> User:
        user = self._users.get(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user

    def create_project(self, owner_id: str, name: str) -> Project:
        owner = self._users.get(owner_id)
        if owner is None:
            raise NotFoundError("Owner user not found.")
        project = Project(id=_new_id(), name=name, owner_id=owner_id)
        self._projects[project.id] = project
        self._project_tasks.setdefault(project.id, set())
        self._user_projects.setdefault(owner_id, set()).add(project.id)
        self._emit("created", "project", project.id, {"name": project.name, "owner_id": owner_id})
        return project

    def get_project(self, project_id: str) -> Project:
        project = self._projects.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.")
        return project

    def list_projects(self, owner_id: str) -> List[Project]:
        if owner_id not in self._users:
            raise NotFoundError("User not found.")
        ids = self._user_projects.get(owner_id, set())
        return [self._projects[i] for i in ids if i in self._projects]

    def rename_project(self, owner_id: str, project_id: str, new_name: str) -> Project:
        project = self.get_project(project_id)
        if project.owner_id != owner_id:
            raise PermissionError("Only the owner can rename the project.")
        if not new_name or not new_name.strip():
            raise ValidationError("Project name must be non-empty.")
        project.name = new_name.strip()
        self._emit("updated", "project", project.id, {"name": project.name})
        return project

    def delete_project(self, owner_id: str, project_id: str) -> None:
        project = self.get_project(project_id)
        if project.owner_id != owner_id:
            raise PermissionError("Only the owner can delete the project.")
        task_ids = list(self._project_tasks.get(project_id, set()))
        for tid in task_ids:
            task = self._tasks.get(tid)
            if task is not None:
                self._unlink_task_from_project(task)
        self._projects.pop(project_id, None)
        self._project_tasks.pop(project_id, None)
        self._user_projects.get(owner_id, set()).discard(project_id)
        self._emit("deleted", "project", project_id, {"owner_id": owner_id})

    def create_task(
        self,
        owner_id: str,
        title: str,
        project_id: Optional[str] = None,
        priority: Priority = Priority.P4,
    ) -> Task:
        if owner_id not in self._users:
            raise NotFoundError("Owner user not found.")
        if project_id is not None:
            project = self._projects.get(project_id)
            if project is None:
                raise NotFoundError("Project not found.")
            if project.owner_id != owner_id:
                raise PermissionError("Cannot create task in a project you do not own.")
        task = Task(id=_new_id(), title=title, owner_id=owner_id, project_id=project_id, priority=priority)
        self._tasks[task.id] = task
        self._user_tasks.setdefault(owner_id, set()).add(task.id)
        if project_id is not None:
            self._project_tasks.setdefault(project_id, set()).add(task.id)
        self._emit(
            "created",
            "task",
            task.id,
            {"title": task.title, "owner_id": owner_id, "project_id": project_id, "priority": int(task.priority)},
        )
        return task

    def get_task(self, task_id: str) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.")
        return task

    def list_tasks(
        self,
        owner_id: str,
        project_id: Optional[str] = None,
        status: Optional[Status] = None,
    ) -> List[Task]:
        if owner_id not in self._users:
            raise NotFoundError("User not found.")
        task_ids = self._user_tasks.get(owner_id, set())
        tasks = [self._tasks[tid] for tid in task_ids if tid in self._tasks]
        if project_id is not None:
            if project_id not in self._projects:
                raise NotFoundError("Project not found.")
            tasks = [t for t in tasks if t.project_id == project_id]
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        tasks.sort(key=lambda t: (int(t.priority), t.created_at, t.id))
        return tasks

    def update_task_title(self, owner_id: str, task_id: str, new_title: str) -> Task:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("Only the owner can update the task.")
        if not new_title or not new_title.strip():
            raise ValidationError("Task title must be non-empty.")
        task.title = new_title.strip()
        self._emit("updated", "task", task.id, {"title": task.title})
        return task

    def set_task_priority(self, owner_id: str, task_id: str, priority: Priority) -> Task:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("Only the owner can update the task.")
        task.priority = priority
        self._emit("updated", "task", task.id, {"priority": int(task.priority)})
        return task

    def move_task(self, owner_id: str, task_id: str, project_id: Optional[str]) -> Task:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("Only the owner can move the task.")
        if project_id is not None:
            project = self._projects.get(project_id)
            if project is None:
                raise NotFoundError("Project not found.")
            if project.owner_id != owner_id:
                raise PermissionError("Cannot move task into a project you do not own.")
        old_project_id = task.project_id
        if old_project_id == project_id:
            return task
        self._unlink_task_from_project(task)
        task.project_id = project_id
        if project_id is not None:
            self._project_tasks.setdefault(project_id, set()).add(task.id)
        self._emit("updated", "task", task.id, {"project_id": project_id, "old_project_id": old_project_id})
        return task

    def complete_task(self, owner_id: str, task_id: str) -> Task:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("Only the owner can complete the task.")
        if task.status == Status.DONE:
            return task
        task.status = Status.DONE
        task.completed_at = _now()
        self._emit("updated", "task", task.id, {"status": task.status.value, "completed_at": task.completed_at.isoformat()})
        return task

    def reopen_task(self, owner_id: str, task_id: str) -> Task:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("Only the owner can reopen the task.")
        if task.status == Status.TODO:
            return task
        task.status = Status.TODO
        task.completed_at = None
        self._emit("updated", "task", task.id, {"status": task.status.value, "completed_at": None})
        return task

    def delete_task(self, owner_id: str, task_id: str) -> None:
        task = self.get_task(task_id)
        if task.owner_id != owner_id:
            raise PermissionError("Only the owner can delete the task.")
        self._unlink_task_from_project(task)
        self._tasks.pop(task_id, None)
        self._user_tasks.get(owner_id, set()).discard(task_id)
        self._emit("deleted", "task", task_id, {"owner_id": owner_id})

    def _unlink_task_from_project(self, task: Task) -> None:
        if task.project_id is None:
            return
        self._project_tasks.get(task.project_id, set()).discard(task.id)
        task.project_id = None

    def export_state(self) -> Dict[str, object]:
        return {
            "users": [
                {"id": u.id, "name": u.name, "created_at": u.created_at.isoformat()}
                for u in self._users.values()
            ],
            "projects": [
                {"id": p.id, "name": p.name, "owner_id": p.owner_id, "created_at": p.created_at.isoformat()}
                for p in self._projects.values()
            ],
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "owner_id": t.owner_id,
                    "project_id": t.project_id,
                    "status": t.status.value,
                    "priority": int(t.priority),
                    "created_at": t.created_at.isoformat(),
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                }
                for t in self._tasks.values()
            ],
            "events": [
                {
                    "at": e.at.isoformat(),
                    "type": e.type,
                    "entity": e.entity,
                    "entity_id": e.entity_id,
                    "data": dict(e.data),
                }
                for e in self._events
            ],
        }

    def import_state(self, state: Dict[str, object]) -> None:
        self._users.clear()
        self._projects.clear()
        self._tasks.clear()
        self._project_tasks.clear()
        self._user_projects.clear()
        self._user_tasks.clear()
        self._events.clear()

        users = state.get("users", [])
        projects = state.get("projects", [])
        tasks = state.get("tasks", [])
        events = state.get("events", [])

        if not isinstance(users, list) or not isinstance(projects, list) or not isinstance(tasks, list) or not isinstance(events, list):
            raise ValidationError("Invalid state format.")

        for u in users:
            if not isinstance(u, dict):
                raise ValidationError("Invalid user record.")
            user = User(
                id=str(u["id"]),
                name=str(u["name"]),
                created_at=datetime.fromisoformat(str(u["created_at"])),
            )
            self._users[user.id] = user
            self._user_projects.setdefault(user.id, set())
            self._user_tasks.setdefault(user.id, set())

        for p in projects:
            if not isinstance(p, dict):
                raise ValidationError("Invalid project record.")
            owner_id = str(p["owner_id"])
            if owner_id not in self._users:
                raise ValidationError("Project owner missing.")
            project = Project(
                id=str(p["id"]),
                name=str(p["name"]),
                owner_id=owner_id,
                created_at=datetime.fromisoformat(str(p["created_at"])),
            )
            self._projects[project.id] = project
            self._project_tasks.setdefault(project.id, set())
            self._user_projects.setdefault(owner_id, set()).add(project.id)

        for t in tasks:
            if not isinstance(t, dict):
                raise ValidationError("Invalid task record.")
            owner_id = str(t["owner_id"])
            if owner_id not in self._users:
                raise ValidationError("Task owner missing.")
            project_id = t.get("project_id", None)
            if project_id is not None:
                project_id = str(project_id)
                if project_id not in self._projects:
                    raise ValidationError("Task project missing.")
                if self._projects[project_id].owner_id != owner_id:
                    raise ValidationError("Task project owner mismatch.")
            status = Status(str(t["status"]))
            priority = Priority(int(t["priority"]))
            completed_at_raw = t.get("completed_at", None)
            completed_at = datetime.fromisoformat(str(completed_at_raw)) if completed_at_raw else None
            task = Task(
                id=str(t["id"]),
                title=str(t["title"]),
                owner_id=owner_id,
                project_id=project_id,
                status=status,
                priority=priority,
                created_at=datetime.fromisoformat(str(t["created_at"])),
                completed_at=completed_at,
            )
            self._tasks[task.id] = task
            self._user_tasks.setdefault(owner_id, set()).add(task.id)
            if project_id is not None:
                self._project_tasks.setdefault(project_id, set()).add(task.id)

        for e in events:
            if not isinstance(e, dict):
                raise ValidationError("Invalid event record.")
            ev = Event(
                at=datetime.fromisoformat(str(e["at"])),
                type=str(e["type"]),
                entity=str(e["entity"]),
                entity_id=str(e["entity_id"]),
                data=dict(e.get("data", {})),
            )
            self._events.append(ev)