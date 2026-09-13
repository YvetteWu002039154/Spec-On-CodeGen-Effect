from __future__ import annotations
from datetime import datetime, date, time, timedelta
from enum import IntEnum
from typing import Optional, List, Set, Dict, Any, Callable, Union
import uuid
import copy


class Priority(IntEnum):
    P1 = 1  # Critical
    P2 = 2  # High
    P3 = 3  # Medium
    P4 = 4  # Low


class Recurrence:
    """Defines how a task repeats."""
    def __init__(
        self,
        interval: int,
        unit: str,  # 'days', 'weeks', 'months', 'years'
        end_date: Optional[date] = None,
        count: Optional[int] = None
    ):
        if interval <= 0:
            raise ValueError("Interval must be positive")
        if unit not in {'days', 'weeks', 'months', 'years'}:
            raise ValueError("Unit must be one of: days, weeks, months, years")
        self.interval = interval
        self.unit = unit
        self.end_date = end_date
        self.count = count
        self._completions = 0

    def next_occurrence(self, after_date: date) -> date:
        """Calculate next date after given date based on this recurrence."""
        if self.unit == 'days':
            delta = timedelta(days=self.interval)
        elif self.unit == 'weeks':
            delta = timedelta(weeks=self.interval)
        elif self.unit == 'months':
            # crude month addition
            month = after_date.month + self.interval
            year = after_date.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            try:
                return date(year, month, after_date.day)
            except ValueError:
                # day out of range for new month, use last day
                import calendar
                _, last_day = calendar.monthrange(year, month)
                return date(year, month, last_day)
        else:  # years
            try:
                return after_date.replace(year=after_date.year + self.interval)
            except ValueError:
                return date(after_date.year + self.interval, 2, 28)
        return after_date + delta

    def has_ended(self, current_date: date) -> bool:
        if self.end_date and current_date > self.end_date:
            return True
        if self.count is not None and self._completions >= self.count:
            return True
        return False

    def increment_completion(self):
        self._completions += 1

    def __repr__(self):
        return f"Recurrence(every {self.interval} {self.unit}, end={self.end_date}, count={self.count})"


class Task:
    """Represents a task, optionally with subtasks."""
    def __init__(
        self,
        title: str,
        description: str = "",
        due_date: Optional[datetime] = None,
        priority: Priority = Priority.P4,
        labels: Optional[Set[str]] = None,
        context: Optional[str] = None,  # GTD context like @work, @home
        recurrence: Optional[Recurrence] = None,
        parent: Optional[Task] = None
    ):
        if not title.strip():
            raise ValueError("Task title cannot be empty")
        self.id: str = uuid.uuid4().hex
        self.title: str = title
        self.description: str = description
        self.due_date: Optional[datetime] = due_date
        self.priority: Priority = priority
        self.labels: Set[str] = labels.copy() if labels else set()
        self.context: Optional[str] = context
        self.recurrence: Optional[Recurrence] = recurrence
        self.completed: bool = False
        self.completed_at: Optional[datetime] = None
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = self.created_at
        self.parent: Optional[Task] = parent
        self.children: List[Task] = []  # subtasks
        if parent:
            parent.add_subtask(self)

    def add_subtask(self, subtask: Task) -> None:
        if subtask is self:
            raise ValueError("A task cannot be a subtask of itself.")
        if subtask in self.children:
            raise ValueError("Subtask already present.")
        # prevent circular parent
        current = self.parent
        while current:
            if current is subtask:
                raise ValueError("Adding this subtask would create a cycle.")
            current = current.parent
        subtask.parent = self
        self.children.append(subtask)

    def remove_subtask(self, subtask: Task) -> None:
        if subtask in self.children:
            self.children.remove(subtask)
            subtask.parent = None

    def add_label(self, label: str) -> None:
        label = label.strip()
        if not label:
            raise ValueError("Label cannot be empty")
        self.labels.add(label)

    def remove_label(self, label: str) -> None:
        self.labels.discard(label)

    def set_due_date(self, due: datetime) -> None:
        self.due_date = due
        self._touch()

    def set_priority(self, priority: Priority) -> None:
        if not isinstance(priority, Priority):
            raise TypeError("priority must be a Priority enum")
        self.priority = priority
        self._touch()

    def mark_complete(self) -> None:
        if not self.completed:
            self.completed = True
            self.completed_at = datetime.now()
            if self.recurrence:
                self.recurrence.increment_completion()
                # When marking complete, if recurrence active, create a next instance?
                # Not creating automatically here, but task can be "reschedule" externally.
            self._touch()

    def mark_incomplete(self) -> None:
        if self.completed:
            self.completed = False
            self.completed_at = None
            self._touch()

    def is_overdue(self, now: Optional[datetime] = None) -> bool:
        if self.completed or self.due_date is None:
            return False
        check_time = now or datetime.now()
        return self.due_date < check_time

    def _touch(self) -> None:
        self.updated_at = datetime.now()
        if self.parent:
            self.parent._touch()

    def __repr__(self):
        status = "✓" if self.completed else "○"
        return f"Task({self.title!r}, id={self.id[:6]}, {status})"


class Project:
    """A project containing tasks."""
    def __init__(self, name: str, description: str = "", color: str = ""):
        if not name.strip():
            raise ValueError("Project name cannot be empty")
        self.id: str = uuid.uuid4().hex
        self.name: str = name
        self.description: str = description
        self.color: str = color
        self.tasks: Set[Task] = set()
        self.created_at: datetime = datetime.now()

    def add_task(self, task: Task) -> None:
        self.tasks.add(task)

    def remove_task(self, task: Task) -> None:
        self.tasks.discard(task)

    def get_tasks(self, include_completed: bool = False) -> List[Task]:
        if include_completed:
            return list(self.tasks)
        return [t for t in self.tasks if not t.completed]

    def __repr__(self):
        return f"Project({self.name!r}, tasks={len(self.tasks)})"


class TaskManager:
    """Central manager that stores all projects and top-level tasks."""
    def __init__(self):
        self.projects: Dict[str, Project] = {}
        self.inbox: List[Task] = []  # uncategorized tasks

    def create_project(self, name: str, description: str = "", color: str = "") -> Project:
        project = Project(name, description, color)
        self.projects[project.id] = project
        return project

    def delete_project(self, project_id: str) -> None:
        if project_id in self.projects:
            del self.projects[project_id]

    def add_task(self, task: Task, project: Optional[Project] = None) -> None:
        if project:
            project.add_task(task)
        else:
            self.inbox.append(task)

    def move_task(self, task: Task, source_project: Optional[Project], dest_project: Optional[Project]) -> None:
        if source_project:
            source_project.remove_task(task)
        elif task in self.inbox:
            self.inbox.remove(task)
        if dest_project:
            dest_project.add_task(task)
        else:
            self.inbox.append(task)

    def get_all_tasks(self, include_completed: bool = False) -> List[Task]:
        all_tasks: List[Task] = []
        for proj in self.projects.values():
            all_tasks.extend(proj.get_tasks(include_completed))
        all_tasks.extend(self.inbox)
        return all_tasks

    def search_tasks(self, keyword: str) -> List[Task]:
        results = []
        for task in self.get_all_tasks(include_completed=True):
            if keyword.lower() in task.title.lower() or keyword.lower() in task.description.lower():
                results.append(task)
        return results

    def get_tasks_by_label(self, label: str) -> List[Task]:
        results = []
        for task in self.get_all_tasks(include_completed=True):
            if label in task.labels:
                results.append(task)
        return results

    def get_tasks_by_context(self, context: str) -> List[Task]:
        results = []
        for task in self.get_all_tasks(include_completed=True):
            if task.context == context:
                results.append(task)
        return results

    def get_tasks_due_before(self, due_datetime: datetime) -> List[Task]:
        results = []
        for task in self.get_all_tasks(include_completed=False):
            if task.due_date and task.due_date <= due_datetime:
                results.append(task)
        return results

    def __repr__(self):
        return f"TaskManager(projects={len(self.projects)}, inbox={len(self.inbox)})"


def create_recurrence(every: str, end_date: Optional[date] = None, count: Optional[int] = None) -> Recurrence:
    """Helper: 'every' format like '2 days', '1 week', '3 months'."""
    parts = every.strip().split()
    if len(parts) != 2:
        raise ValueError("Format: '<number> <unit>', e.g., '3 days'")
    interval = int(parts[0])
    unit = parts[1].rstrip('s')  # allow plural
    return Recurrence(interval, unit, end_date, count)