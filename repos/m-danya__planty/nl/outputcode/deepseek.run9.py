from __future__ import annotations
from datetime import datetime, date, time
from enum import Enum
import uuid
from typing import List, Optional, Dict, Set, Union, Any, Callable


class Priority(Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class TaskStatus(Enum):
    TODO = "todo"
    DONE = "done"
    CANCELLED = "cancelled"


class Label:
    def __init__(self, name: str, color: str = "#808080") -> None:
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.color: str = color

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Label):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"Label(id={self.id}, name={self.name}, color={self.color})"


class Project:
    def __init__(self, name: str, color: str = "#808080") -> None:
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.color: str = color
        self.is_archived: bool = False
        self._tasks: Set[Task] = set()

    def add_task(self, task: Task) -> None:
        if task in self._tasks:
            return
        task.project = self
        self._tasks.add(task)

    def remove_task(self, task: Task) -> None:
        if task in self._tasks:
            self._tasks.remove(task)
            task.project = None

    @property
    def tasks(self) -> List[Task]:
        return list(self._tasks)

    def __repr__(self) -> str:
        return f"Project(id={self.id}, name={self.name}, archived={self.is_archived})"


class Task:
    MAX_SUBTASK_DEPTH = 5

    def __init__(
        self,
        title: str,
        description: str = "",
        due_date: Optional[date] = None,
        priority: Priority = Priority.P4,
        project: Optional[Project] = None,
        parent: Optional[Task] = None,
    ) -> None:
        self.id: str = str(uuid.uuid4())
        self.title: str = title
        self.description: str = description
        self.due_date: Optional[date] = due_date
        self.priority: Priority = priority
        self.status: TaskStatus = TaskStatus.TODO
        self.created_at: datetime = datetime.now()
        self.completed_at: Optional[datetime] = None

        self._project: Optional[Project] = None
        if project:
            project.add_task(self)

        self._parent: Optional[Task] = None
        self._subtasks: Set[Task] = set()
        if parent:
            parent.add_subtask(self)

        self.labels: Set[Label] = set()
        self._history: List[Dict[str, Any]] = []  # status change history

    def add_subtask(self, subtask: Task) -> None:
        if subtask == self:
            raise ValueError("A task cannot be a subtask of itself.")
        if self._depth() >= self.MAX_SUBTASK_DEPTH:
            raise ValueError(f"Maximum subtask depth of {self.MAX_SUBTASK_DEPTH} reached.")
        if subtask._parent is not None:
            subtask._parent._subtasks.discard(subtask)
        subtask._parent = self
        self._subtasks.add(subtask)

    def remove_subtask(self, subtask: Task) -> None:
        if subtask in self._subtasks:
            self._subtasks.remove(subtask)
            subtask._parent = None

    def _depth(self) -> int:
        depth = 0
        current = self
        while current._parent:
            current = current._parent
            depth += 1
        return depth

    @property
    def parent(self) -> Optional[Task]:
        return self._parent

    @property
    def subtasks(self) -> List[Task]:
        return list(self._subtasks)

    @property
    def project(self) -> Optional[Project]:
        return self._project

    @project.setter
    def project(self, value: Optional[Project]) -> None:
        if self._project is value:
            return
        if self._project:
            self._project.remove_task(self)
        if value:
            value.add_task(self)
        self._project = value

    def mark_complete(self) -> None:
        if self.status == TaskStatus.DONE:
            return
        self._log_status_change(TaskStatus.DONE)
        self.status = TaskStatus.DONE
        self.completed_at = datetime.now()

    def mark_todo(self) -> None:
        if self.status == TaskStatus.TODO:
            return
        self._log_status_change(TaskStatus.TODO)
        self.status = TaskStatus.TODO
        self.completed_at = None

    def mark_cancelled(self) -> None:
        if self.status == TaskStatus.CANCELLED:
            return
        self._log_status_change(TaskStatus.CANCELLED)
        self.status = TaskStatus.CANCELLED
        self.completed_at = None

    def _log_status_change(self, new_status: TaskStatus) -> None:
        entry = {
            "timestamp": datetime.now(),
            "from_status": self.status,
            "to_status": new_status,
        }
        self._history.append(entry)

    def get_history(self) -> List[Dict[str, Any]]:
        return self._history.copy()

    def add_label(self, label: Label) -> None:
        self.labels.add(label)

    def remove_label(self, label: Label) -> None:
        self.labels.discard(label)

    def is_overdue(self) -> bool:
        if self.status != TaskStatus.TODO or self.due_date is None:
            return False
        return self.due_date < date.today()

    def __repr__(self) -> str:
        return f"Task(id={self.id}, title={self.title}, status={self.status})"


class TaskManager:
    """
    Central manager for all tasks, projects, labels.
    Implements GTD-inspired views: inbox, next actions, waiting, someday.
    """
    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._projects: Dict[str, Project] = {}
        self._labels: Dict[str, Label] = {}

    # Task CRUD
    def create_task(
        self,
        title: str,
        description: str = "",
        due_date: Optional[date] = None,
        priority: Priority = Priority.P4,
        project: Optional[Project] = None,
        parent: Optional[Task] = None,
    ) -> Task:
        task = Task(title, description, due_date, priority, project, parent)
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def delete_task(self, task_id: str) -> bool:
        task = self._tasks.pop(task_id, None)
        if task is None:
            return False
        # Remove from parent's subtasks
        if task.parent:
            task.parent.remove_subtask(task)
        # Remove from project
        if task.project:
            task.project.remove_task(task)
        return True

    def update_task_title(self, task_id: str, new_title: str) -> bool:
        task = self.get_task(task_id)
        if task:
            task.title = new_title
            return True
        return False

    def add_subtask(self, parent_id: str, subtask_id: str) -> bool:
        parent = self.get_task(parent_id)
        subtask = self.get_task(subtask_id)
        if parent and subtask:
            try:
                parent.add_subtask(subtask)
                return True
            except ValueError:
                return False
        return False

    # Project CRUD
    def create_project(self, name: str, color: str = "#808080") -> Project:
        project = Project(name, color)
        self._projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)

    def archive_project(self, project_id: str) -> bool:
        project = self.get_project(project_id)
        if project:
            project.is_archived = True
            return True
        return False

    def unarchive_project(self, project_id: str) -> bool:
        project = self.get_project(project_id)
        if project:
            project.is_archived = False
            return True
        return False

    # Label CRUD
    def create_label(self, name: str, color: str = "#808080") -> Label:
        label = Label(name, color)
        self._labels[label.id] = label
        return label

    def get_label(self, label_id: str) -> Optional[Label]:
        return self._labels.get(label_id)

    # Task queries / GTD views
    @property
    def all_tasks(self) -> List[Task]:
        return list(self._tasks.values())

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        return [t for t in self._tasks.values() if t.status == status]

    def get_tasks_by_project(self, project_id: str) -> List[Task]:
        project = self._projects.get(project_id)
        if project:
            return project.tasks
        return []

    def get_tasks_by_label(self, label_id: str) -> List[Task]:
        label = self._labels.get(label_id)
        if not label:
            return []
        return [t for t in self._tasks.values() if label in t.labels]

    def get_overdue_tasks(self) -> List[Task]:
        return [t for t in self._tasks.values() if t.is_overdue()]

    def search_tasks(self, query: str) -> List[Task]:
        query = query.lower()
        results = []
        for task in self._tasks.values():
            if query in task.title.lower() or query in task.description.lower():
                results.append(task)
        return results

    def inbox_tasks(self) -> List[Task]:
        """Tasks without a project, considered GTD inbox."""
        return [t for t in self._tasks.values() if t.project is None and t.status == TaskStatus.TODO]

    def next_actions(self) -> List[Task]:
        """Tasks that are actionable, not in a waiting state, and sorted by priority."""
        actionable = [t for t in self._tasks.values() if t.status == TaskStatus.TODO]
        actionable.sort(key=lambda t: (t.priority.value, t.due_date or date.max))
        return actionable

    def waiting_tasks(self) -> List[Task]:
        """Tasks that are 'waiting' - marked with label 'waiting'."""
        waiting_label = next((l for l in self._labels.values() if l.name.lower() == "waiting"), None)
        if waiting_label:
            return [t for t in self._tasks.values() if waiting_label in t.labels and t.status == TaskStatus.TODO]
        return []

    def someday_tasks(self) -> List[Task]:
        """Tasks with label 'someday'."""
        someday_label = next((l for l in self._labels.values() if l.name.lower() == "someday"), None)
        if someday_label:
            return [t for t in self._tasks.values() if someday_label in t.labels and t.status == TaskStatus.TODO]
        return []

    def get_completed_tasks(self, since: Optional[date] = None) -> List[Task]:
        completed = [t for t in self._tasks.values() if t.status == TaskStatus.DONE]
        if since:
            completed = [t for t in completed if t.completed_at and t.completed_at.date() >= since]
        return completed


# ---------- Demostration of usage ----------
if __name__ == "__main__":
    manager = TaskManager()

    # Create labels
    label_waiting = manager.create_label("waiting", "#FFA500")
    label_someday = manager.create_label("someday", "#ADD8E6")
    label_urgent = manager.create_label("urgent", "#FF0000")

    # Create projects
    project_work = manager.create_project("Work", "#0000FF")
    project_personal = manager.create_project("Personal", "#008000")

    # Create tasks
    task1 = manager.create_task("Finish report", "Q3 financial report", due_date=date(2025, 3, 15), priority=Priority.P2, project=project_work)
    task2 = manager.create_task("Buy groceries", "", due_date=date(2025, 3, 10), priority=Priority.P3)
    task3 = manager.create_task("Read book", "GTD book", priority=Priority.P4)
    task4 = manager.create_task("Call dentist", "", priority=Priority.P1, project=project_personal)

    # Add labels
    task2.add_label(label_urgent)
    task3.add_label(label_someday)
    task4.add_label(label_waiting)

    # Create subtask
    task5 = manager.create_task("Draft outline", parent=task1)

    # Complete a task
    task2.mark_complete()

    # Display views
    print("Inbox (no project):")
    for t in manager.inbox_tasks():
        print(f" - {t.title} ({t.priority})")

    print("\nNext Actions (sorted):")
    for t in manager.next_actions():
        print(f" - {t.title} ({t.priority}) {'[OVERDUE]' if t.is_overdue() else ''}")

    print("\nWaiting:")
    for t in manager.waiting_tasks():
        print(f" - {t.title}")

    print("\nSomeday:")
    for t in manager.someday_tasks():
        print(f" - {t.title}")

    print("\nOverdue tasks:")
    for t in manager.get_overdue_tasks():
        print(f" - {t.title}")

    print("\nCompleted tasks:")
    for t in manager.get_completed_tasks():
        print(f" - {t.title}")

    # Search
    print("\nSearch 'dentist':")
    for t in manager.search_tasks("dentist"):
        print(f" - {t.title}")