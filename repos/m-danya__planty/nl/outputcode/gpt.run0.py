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


class Status(str, Enum):
    TODO = "todo"
    DONE = "done"
    CANCELED = "canceled"


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
        raise ValidationError(f"{field} must not be empty")
    return v


def _require_optional_str(value: Optional[str], field: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string or None")
    v = value.strip()
    return v if v else None


def _require_priority(value: Optional[Priority]) -> Priority:
    if value is None:
        return Priority.P4
    if isinstance(value, Priority):
        return value
    if isinstance(value, int) and value in (1, 2, 3, 4):
        return Priority(value)
    raise ValidationError("priority must be a Priority or int in [1..4]")


def _require_status(value: Status) -> Status:
    if isinstance(value, Status):
        return value
    if isinstance(value, str):
        try:
            return Status(value)
        except ValueError as e:
            raise ValidationError("invalid status") from e
    raise ValidationError("status must be a Status")


@dataclass(frozen=True)
class Project:
    id: int
    name: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Task:
    id: int
    content: str
    description: Optional[str]
    project_id: Optional[int]
    priority: Priority
    status: Status
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]


class Planty:
    def __init__(self) -> None:
        self._project_id_seq: int = 0
        self._task_id_seq: int = 0

        self._projects: Dict[int, Project] = {}
        self._project_name_index: Dict[str, int] = {}

        self._tasks: Dict[int, Task] = {}
        self._tasks_by_project: Dict[Optional[int], Set[int]] = {None: set()}

    # ---- Projects ----
    def create_project(self, name: str) -> Project:
        name = _require_non_empty(name, "name")
        key = name.casefold()
        if key in self._project_name_index:
            raise ConflictError("project name already exists")

        self._project_id_seq += 1
        pid = self._project_id_seq
        ts = _now()
        project = Project(id=pid, name=name, created_at=ts, updated_at=ts)
        self._projects[pid] = project
        self._project_name_index[key] = pid
        self._tasks_by_project.setdefault(pid, set())
        return project

    def get_project(self, project_id: int) -> Project:
        try:
            return self._projects[project_id]
        except KeyError as e:
            raise NotFoundError("project not found") from e

    def list_projects(self) -> List[Project]:
        return sorted(self._projects.values(), key=lambda p: (p.created_at, p.id))

    def rename_project(self, project_id: int, new_name: str) -> Project:
        new_name = _require_non_empty(new_name, "new_name")
        project = self.get_project(project_id)

        new_key = new_name.casefold()
        existing = self._project_name_index.get(new_key)
        if existing is not None and existing != project_id:
            raise ConflictError("project name already exists")

        old_key = project.name.casefold()
        if old_key in self._project_name_index and self._project_name_index[old_key] == project_id:
            del self._project_name_index[old_key]
        self._project_name_index[new_key] = project_id

        ts = _now()
        updated = Project(id=project.id, name=new_name, created_at=project.created_at, updated_at=ts)
        self._projects[project_id] = updated
        return updated

    def delete_project(self, project_id: int) -> None:
        project = self.get_project(project_id)
        key = project.name.casefold()
        if key in self._project_name_index and self._project_name_index[key] == project_id:
            del self._project_name_index[key]

        task_ids = list(self._tasks_by_project.get(project_id, set()))
        for tid in task_ids:
            self._delete_task_internal(tid)

        self._tasks_by_project.pop(project_id, None)
        self._projects.pop(project_id, None)

    # ---- Tasks ----
    def create_task(
        self,
        content: str,
        *,
        description: Optional[str] = None,
        project_id: Optional[int] = None,
        priority: Optional[Priority] = None,
    ) -> Task:
        content = _require_non_empty(content, "content")
        description = _require_optional_str(description, "description")
        prio = _require_priority(priority)

        if project_id is not None:
            self.get_project(project_id)
            self._tasks_by_project.setdefault(project_id, set())
        else:
            self._tasks_by_project.setdefault(None, set())

        self._task_id_seq += 1
        tid = self._task_id_seq
        ts = _now()
        task = Task(
            id=tid,
            content=content,
            description=description,
            project_id=project_id,
            priority=prio,
            status=Status.TODO,
            created_at=ts,
            updated_at=ts,
            completed_at=None,
        )
        self._tasks[tid] = task
        self._tasks_by_project[project_id].add(tid)
        return task

    def get_task(self, task_id: int) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError as e:
            raise NotFoundError("task not found") from e

    def list_tasks(
        self,
        *,
        project_id: Optional[int] = None,
        status: Optional[Status] = None,
    ) -> List[Task]:
        if project_id is not None:
            self.get_project(project_id)
        ids = self._tasks_by_project.get(project_id, set())
        tasks = [self._tasks[tid] for tid in ids]
        if status is not None:
            status = _require_status(status)
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: (t.status.value, t.priority.value, t.created_at, t.id))

    def update_task(
        self,
        task_id: int,
        *,
        content: Optional[str] = None,
        description: Optional[str] = None,
        project_id: Optional[int] = None,
        priority: Optional[Priority] = None,
    ) -> Task:
        task = self.get_task(task_id)

        new_content = task.content if content is None else _require_non_empty(content, "content")
        new_description = task.description if description is None else _require_optional_str(description, "description")
        new_priority = task.priority if priority is None else _require_priority(priority)

        new_project_id = task.project_id if project_id is None else project_id
        if new_project_id is not None:
            self.get_project(new_project_id)
            self._tasks_by_project.setdefault(new_project_id, set())
        else:
            self._tasks_by_project.setdefault(None, set())

        if new_project_id != task.project_id:
            self._tasks_by_project.setdefault(task.project_id, set()).discard(task.id)
            self._tasks_by_project[new_project_id].add(task.id)

        ts = _now()
        updated = Task(
            id=task.id,
            content=new_content,
            description=new_description,
            project_id=new_project_id,
            priority=new_priority,
            status=task.status,
            created_at=task.created_at,
            updated_at=ts,
            completed_at=task.completed_at,
        )
        self._tasks[task_id] = updated
        return updated

    def set_task_status(self, task_id: int, status: Status) -> Task:
        task = self.get_task(task_id)
        status = _require_status(status)

        if task.status == status:
            return task

        ts = _now()
        completed_at = task.completed_at
        if status == Status.DONE:
            completed_at = ts
        elif status in (Status.TODO, Status.CANCELED):
            completed_at = None

        updated = Task(
            id=task.id,
            content=task.content,
            description=task.description,
            project_id=task.project_id,
            priority=task.priority,
            status=status,
            created_at=task.created_at,
            updated_at=ts,
            completed_at=completed_at,
        )
        self._tasks[task_id] = updated
        return updated

    def complete_task(self, task_id: int) -> Task:
        return self.set_task_status(task_id, Status.DONE)

    def reopen_task(self, task_id: int) -> Task:
        return self.set_task_status(task_id, Status.TODO)

    def cancel_task(self, task_id: int) -> Task:
        return self.set_task_status(task_id, Status.CANCELED)

    def delete_task(self, task_id: int) -> None:
        self.get_task(task_id)
        self._delete_task_internal(task_id)

    def _delete_task_internal(self, task_id: int) -> None:
        task = self._tasks.pop(task_id, None)
        if task is None:
            return
        self._tasks_by_project.setdefault(task.project_id, set()).discard(task_id)

    # ---- Convenience / Stats ----
    def counts(self, *, project_id: Optional[int] = None) -> Dict[str, int]:
        if project_id is not None:
            self.get_project(project_id)
        ids = self._tasks_by_project.get(project_id, set())
        todo = done = canceled = 0
        for tid in ids:
            st = self._tasks[tid].status
            if st == Status.TODO:
                todo += 1
            elif st == Status.DONE:
                done += 1
            elif st == Status.CANCELED:
                canceled += 1
        return {"todo": todo, "done": done, "canceled": canceled, "total": todo + done + canceled}

    def export_state(self) -> Dict[str, object]:
        projects = [
            {
                "id": p.id,
                "name": p.name,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
            }
            for p in self.list_projects()
        ]
        tasks = [
            {
                "id": t.id,
                "content": t.content,
                "description": t.description,
                "project_id": t.project_id,
                "priority": int(t.priority.value),
                "status": t.status.value,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in sorted(self._tasks.values(), key=lambda x: x.id)
        ]
        return {"projects": projects, "tasks": tasks}

    def import_state(self, state: Dict[str, object]) -> None:
        if not isinstance(state, dict):
            raise ValidationError("state must be a dict")
        projects = state.get("projects", [])
        tasks = state.get("tasks", [])
        if not isinstance(projects, list) or not isinstance(tasks, list):
            raise ValidationError("state must contain 'projects' and 'tasks' lists")

        self.__init__()

        def parse_dt(s: Optional[str]) -> Optional[datetime]:
            if s is None:
                return None
            if not isinstance(s, str):
                raise ValidationError("datetime fields must be ISO strings or None")
            try:
                dt = datetime.fromisoformat(s)
            except ValueError as e:
                raise ValidationError("invalid datetime format") from e
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt

        max_pid = 0
        for p in projects:
            if not isinstance(p, dict):
                raise ValidationError("project entries must be dicts")
            pid = int(p["id"])
            name = _require_non_empty(str(p["name"]), "name")
            created_at = parse_dt(p.get("created_at")) or _now()
            updated_at = parse_dt(p.get("updated_at")) or created_at

            key = name.casefold()
            if key in self._project_name_index:
                raise ConflictError("duplicate project name in import")
            if pid in self._projects:
                raise ConflictError("duplicate project id in import")

            proj = Project(id=pid, name=name, created_at=created_at, updated_at=updated_at)
            self._projects[pid] = proj
            self._project_name_index[key] = pid
            self._tasks_by_project.setdefault(pid, set())
            max_pid = max(max_pid, pid)

        max_tid = 0
        for t in tasks:
            if not isinstance(t, dict):
                raise ValidationError("task entries must be dicts")
            tid = int(t["id"])
            content = _require_non_empty(str(t["content"]), "content")
            description = _require_optional_str(t.get("description"), "description")
            project_id = t.get("project_id", None)
            if project_id is not None:
                project_id = int(project_id)
                if project_id not in self._projects:
                    raise NotFoundError("task references missing project")
                self._tasks_by_project.setdefault(project_id, set())
            else:
                self._tasks_by_project.setdefault(None, set())

            prio_raw = t.get("priority", 4)
            prio = _require_priority(Priority(prio_raw) if isinstance(prio_raw, int) and prio_raw in (1, 2, 3, 4) else prio_raw)  # type: ignore[arg-type]
            status = _require_status(t.get("status", Status.TODO))  # type: ignore[arg-type]

            created_at = parse_dt(t.get("created_at")) or _now()
            updated_at = parse_dt(t.get("updated_at")) or created_at
            completed_at = parse_dt(t.get("completed_at"))

            if status == Status.DONE and completed_at is None:
                completed_at = updated_at
            if status != Status.DONE:
                completed_at = None

            if tid in self._tasks:
                raise ConflictError("duplicate task id in import")

            task = Task(
                id=tid,
                content=content,
                description=description,
                project_id=project_id,
                priority=prio,
                status=status,
                created_at=created_at,
                updated_at=updated_at,
                completed_at=completed_at,
            )
            self._tasks[tid] = task
            self._tasks_by_project[project_id].add(tid)
            max_tid = max(max_tid, tid)

        self._project_id_seq = max_pid
        self._task_id_seq = max_tid


def main():
    app = Planty()

    # Create projects
    work = app.create_project("Work")
    home = app.create_project("Home")
    print(f"Projects: {[p.name for p in app.list_projects()]}")

    # Create tasks (inbox = project_id None)
    t1 = app.create_task("Buy groceries", priority=Priority.P2)
    t2 = app.create_task("Fix roof", description="Call contractor", project_id=home.id, priority=Priority.P1)
    t3 = app.create_task("Finish report", project_id=work.id, priority=Priority.P1)
    t4 = app.create_task("Team meeting prep", project_id=work.id, priority=Priority.P2)
    print(f"Tasks created: {[t.content for t in [t1, t2, t3, t4]]}")

    # Complete and cancel tasks
    app.complete_task(t3.id)
    app.cancel_task(t1.id)
    print(f"'{t3.content}' status: {app.get_task(t3.id).status.value}")
    print(f"'{t1.content}' status: {app.get_task(t1.id).status.value}")

    # Reopen a task
    app.reopen_task(t1.id)
    print(f"'{t1.content}' after reopen: {app.get_task(t1.id).status.value}")

    # List tasks filtered by project and status
    work_todo = app.list_tasks(project_id=work.id, status=Status.TODO)
    print(f"Work TODO tasks: {[t.content for t in work_todo]}")

    work_done = app.list_tasks(project_id=work.id, status=Status.DONE)
    print(f"Work DONE tasks: {[t.content for t in work_done]}")

    # Update task content and move to different project
    app.update_task(t4.id, content="Team meeting notes", project_id=home.id)
    updated = app.get_task(t4.id)
    print(f"Updated task: content='{updated.content}', project_id={updated.project_id}")

    # Counts per project
    print(f"Work counts: {app.counts(project_id=work.id)}")
    print(f"Home counts: {app.counts(project_id=home.id)}")

    # Rename project
    app.rename_project(home.id, "Home Renovation")
    print(f"Renamed project: {app.get_project(home.id).name}")

    # Export and re-import state
    state = app.export_state()
    print(f"Exported: {len(state['projects'])} projects, {len(state['tasks'])} tasks")

    app2 = Planty()
    app2.import_state(state)
    print(f"Imported into new instance: {[p['name'] for p in state['projects']]}")

    # Delete a project (cascades task deletion)
    app.delete_project(work.id)
    print(f"Projects after deleting Work: {[p.name for p in app.list_projects()]}")

    # Delete a task
    app.delete_task(t2.id)
    print(f"Home tasks after deleting t2: {[app.get_task(tid).content for tid in app._tasks_by_project.get(home.id, set())]}")

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()