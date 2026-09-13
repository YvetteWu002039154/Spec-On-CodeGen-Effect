from __future__ import annotations
from enum import Enum
from datetime import datetime
from typing import Optional, List, Set, Dict, Any

class TaskPriority(Enum):
    """Priority levels inspired by Todoist."""
    P4 = 4  # Low
    P3 = 3  # Medium
    P2 = 2  # High
    P1 = 1  # Urgent

class Task:
    """Represents a single task in the system."""
    _id_counter = 0

    def __init__(
        self,
        title: str,
        description: str = "",
        due_date: Optional[datetime] = None,
        priority: TaskPriority = TaskPriority.P4,
        parent: Optional[Task] = None,
        project: Optional[Project] = None,
        labels: Optional[Set[Label]] = None
    ) -> None:
        self._id = Task._id_counter
        Task._id_counter += 1
        self.title = title
        self.description = description
        self.due_date = due_date
        self.priority = priority
        self.completed = False
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.parent = parent
        self.project = project
        self.labels: Set[Label] = labels or set()
        self.subtasks: List[Task] = []

        if parent:
            parent.add_subtask(self)

    @property
    def id(self) -> int:
        return self._id

    def add_subtask(self, subtask: Task) -> None:
        """Adds a subtask, ensuring no circular dependencies and max depth."""
        if subtask is self:
            raise ValueError("A task cannot be its own subtask.")
        # Check if adding subtask would create a cycle
        if self._is_descendant_of(subtask):
            raise ValueError("Adding this subtask would create a cycle.")
        # Maximum nesting depth of 3
        if self._depth() >= 3:
            raise ValueError("Maximum task nesting depth (3) exceeded.")
        if subtask not in self.subtasks:
            self.subtasks.append(subtask)
            subtask.parent = self
            subtask._update_timestamps()

    def remove_subtask(self, subtask: Task) -> None:
        """Removes a subtask."""
        if subtask in self.subtasks:
            self.subtasks.remove(subtask)
            subtask.parent = None
            subtask._update_timestamps()

    def _is_descendant_of(self, task: Task) -> bool:
        """Check if this task is a descendant of the given task."""
        current = self.parent
        while current is not None:
            if current == task:
                return True
            current = current.parent
        return False

    def _depth(self) -> int:
        """Return the depth of this task in the task tree (root = 1)."""
        depth = 1
        current = self.parent
        while current is not None:
            depth += 1
            current = current.parent
        return depth

    def _update_timestamps(self) -> None:
        self.updated_at = datetime.now()

    def can_complete(self) -> bool:
        """A task can be completed only if all its subtasks are completed."""
        return all(subtask.completed for subtask in self.subtasks)

    def complete(self) -> None:
        """Mark task as completed. Raises ValueError if incomplete subtasks exist."""
        if not self.can_complete():
            raise ValueError("Cannot complete task because it has incomplete subtasks.")
        self.completed = True
        self._update_timestamps()

    def uncomplete(self) -> None:
        """Mark task as not completed. Does not affect parent or subtasks."""
        self.completed = False
        self._update_timestamps()

    def add_label(self, label: Label) -> None:
        self.labels.add(label)
        self._update_timestamps()

    def remove_label(self, label: Label) -> None:
        self.labels.discard(label)
        self._update_timestamps()

    def __repr__(self) -> str:
        status = "✓" if self.completed else " "
        return f"Task({self.id}: '{self.title}' [{status}] )"

class Project:
    """Represents a project that can contain multiple tasks."""
    _id_counter = 0

    def __init__(self, name: str, color: str = "#808080", parent: Optional[Project] = None) -> None:
        self._id = Project._id_counter
        Project._id_counter += 1
        self.name = name
        self.color = color
        self.parent = parent
        self.sub_projects: List[Project] = []
        if parent:
            parent.add_sub_project(self)

    @property
    def id(self) -> int:
        return self._id

    def add_sub_project(self, sub_project: Project) -> None:
        if sub_project is self:
            raise ValueError("A project cannot be its own sub-project.")
        # Check for cycles
        if self._is_descendant_of(sub_project):
            raise ValueError("Adding this sub-project would create a cycle.")
        # Allow any depth for projects? We'll cap at 3 for simplicity.
        if self._depth() >= 3:
            raise ValueError("Maximum project nesting depth (3) exceeded.")
        if sub_project not in self.sub_projects:
            self.sub_projects.append(sub_project)
            sub_project.parent = self

    def _is_descendant_of(self, project: Project) -> bool:
        current = self.parent
        while current is not None:
            if current == project:
                return True
            current = current.parent
        return False

    def _depth(self) -> int:
        depth = 1
        current = self.parent
        while current is not None:
            depth += 1
            current = current.parent
        return depth

    def __repr__(self) -> str:
        return f"Project({self.id}: '{self.name}')"

class Label:
    """A tag or context label for tasks (e.g., @home, @office)."""
    _id_counter = 0

    def __init__(self, name: str, color: str = "#FFFFFF") -> None:
        self._id = Label._id_counter
        Label._id_counter += 1
        self.name = name
        self.color = color

    @property
    def id(self) -> int:
        return self._id

    def __repr__(self) -> str:
        return f"Label({self.id}: '{self.name}')"

class ActivityAction(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    COMPLETED = "completed"
    UNCOMPLETED = "uncompleted"

class ActivityLogEntry:
    """Represents a single activity log entry for a task."""
    def __init__(self, action: ActivityAction, task_id: int, details: Dict[str, Any] = None):
        self.action = action
        self.task_id = task_id
        self.timestamp = datetime.now()
        self.details = details or {}

    def __repr__(self) -> str:
        return f"{self.timestamp} - Task {self.task_id} {self.action.value}"

class Planty:
    """Main application class managing tasks, projects, labels, and activity logs."""

    def __init__(self) -> None:
        self.tasks: Dict[int, Task] = {}
        self.projects: Dict[int, Project] = {}
        self.labels: Dict[int, Label] = {}
        self.activity_log: List[ActivityLogEntry] = []

    # Task management
    def create_task(
        self,
        title: str,
        description: str = "",
        due_date: Optional[datetime] = None,
        priority: TaskPriority = TaskPriority.P4,
        parent_id: Optional[int] = None,
        project_id: Optional[int] = None,
        label_ids: Optional[List[int]] = None
    ) -> Task:
        """Create a new task and add to the system. Returns the created Task."""
        parent = None
        if parent_id is not None:
            parent = self._get_task_by_id(parent_id)
        project = None
        if project_id is not None:
            project = self._get_project_by_id(project_id)
        labels = set()
        if label_ids:
            for lid in label_ids:
                labels.add(self._get_label_by_id(lid))

        task = Task(title, description, due_date, priority, parent, project, labels)
        self.tasks[task.id] = task
        self._log_activity(ActivityAction.CREATED, task.id, {"title": title})
        return task

    def update_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        due_date: Optional[datetime] = None,
        priority: Optional[TaskPriority] = None,
        parent_id: Optional[int] = None,
        project_id: Optional[int] = None,
        add_label_ids: Optional[List[int]] = None,
        remove_label_ids: Optional[List[int]] = None,
    ) -> Task:
        """Update fields of an existing task."""
        task = self._get_task_by_id(task_id)
        changes = {}

        if title is not None:
            task.title = title
            changes["title"] = title
        if description is not None:
            task.description = description
            changes["description"] = description
        if due_date is not None:
            task.due_date = due_date
            changes["due_date"] = due_date
        if priority is not None:
            task.priority = priority
            changes["priority"] = priority.name
        if project_id is not None:
            project = self._get_project_by_id(project_id) if project_id else None
            task.project = project
            changes["project"] = project.name if project else None
        if parent_id is not None:
            new_parent = self._get_task_by_id(parent_id) if parent_id else None
            old_parent = task.parent
            if old_parent:
                old_parent.remove_subtask(task)
            if new_parent:
                new_parent.add_subtask(task)
            else:
                task.parent = None
            changes["parent"] = new_parent.id if new_parent else None

        if add_label_ids:
            for lid in add_label_ids:
                label = self._get_label_by_id(lid)
                task.add_label(label)
            changes["added_labels"] = [self._get_label_by_id(lid).name for lid in add_label_ids]
        if remove_label_ids:
            for lid in remove_label_ids:
                label = self._get_label_by_id(lid)
                task.remove_label(label)
            changes["removed_labels"] = [self._get_label_by_id(lid).name for lid in remove_label_ids]

        task._update_timestamps()
        self._log_activity(ActivityAction.UPDATED, task.id, changes)
        return task

    def delete_task(self, task_id: int) -> None:
        """Delete a task and all its subtasks recursively."""
        task = self._get_task_by_id(task_id)
        # Remove all subtasks recursively
        for subtask in list(task.subtasks):
            self.delete_task(subtask.id)
        # Remove from parent's subtask list
        if task.parent:
            task.parent.remove_subtask(task)
        # Remove reference from labels
        for label in task.labels:
            label.tasks.discard(task)  # Label doesn't maintain task list, but we can skip.
        del self.tasks[task_id]
        self._log_activity(ActivityAction.DELETED, task_id, {"title": task.title})

    def complete_task(self, task_id: int) -> None:
        """Mark a task as completed."""
        task = self._get_task_by_id(task_id)
        task.complete()
        self._log_activity(ActivityAction.COMPLETED, task.id, {})

    def uncomplete_task(self, task_id: int) -> None:
        """Unmark a completed task."""
        task = self._get_task_by_id(task_id)
        task.uncomplete()
        self._log_activity(ActivityAction.UNCOMPLETED, task.id, {})

    # Project management
    def create_project(self, name: str, color: str = "#808080", parent_id: Optional[int] = None) -> Project:
        parent = None
        if parent_id is not None:
            parent = self._get_project_by_id(parent_id)
        project = Project(name, color, parent)
        self.projects[project.id] = project
        return project

    # Label management
    def create_label(self, name: str, color: str = "#FFFFFF") -> Label:
        label = Label(name, color)
        self.labels[label.id] = label
        return label

    # Query methods
    def get_task(self, task_id: int) -> Task:
        return self._get_task_by_id(task_id)

    def get_tasks_by_project(self, project_id: int, include_subprojects: bool = False) -> List[Task]:
        project = self._get_project_by_id(project_id)
        result = [task for task in self.tasks.values() if task.project == project]
        if include_subprojects:
            for sp in project.sub_projects:
                result.extend(self.get_tasks_by_project(sp.id, include_subprojects=True))
        return result

    def get_tasks_by_label(self, label_id: int) -> List[Task]:
        label = self._get_label_by_id(label_id)
        return [task for task in self.tasks.values() if label in task.labels]

    def get_overdue_tasks(self) -> List[Task]:
        now = datetime.now()
        return [task for task in self.tasks.values()
                if not task.completed and task.due_date is not None and task.due_date < now]

    def get_all_tasks(self) -> List[Task]:
        return list(self.tasks.values())

    def search_tasks(self, keyword: str) -> List[Task]:
        keyword_lower = keyword.lower()
        return [task for task in self.tasks.values()
                if keyword_lower in task.title.lower() or keyword_lower in task.description.lower()]

    # Activity log retrieval
    def get_activity_log(self, task_id: Optional[int] = None) -> List[ActivityLogEntry]:
        if task_id is None:
            return self.activity_log[:]
        return [entry for entry in self.activity_log if entry.task_id == task_id]

    # Private helpers
    def _log_activity(self, action: ActivityAction, task_id: int, details: Dict[str, Any]) -> None:
        self.activity_log.append(ActivityLogEntry(action, task_id, details))

    def _get_task_by_id(self, task_id: int) -> Task:
        task = self.tasks.get(task_id)
        if not task:
            raise KeyError(f"Task with id {task_id} not found.")
        return task

    def _get_project_by_id(self, project_id: int) -> Project:
        project = self.projects.get(project_id)
        if not project:
            raise KeyError(f"Project with id {project_id} not found.")
        return project

    def _get_label_by_id(self, label_id: int) -> Label:
        label = self.labels.get(label_id)
        if not label:
            raise KeyError(f"Label with id {label_id} not found.")
        return label

if __name__ == "__main__":
    # Example usage
    planty = Planty()
    inbox = planty.create_project("Inbox", color="#0000FF")
    work = planty.create_project("Work", color="#FF0000")
    health = planty.create_project("Health", parent_id=work.id)  # sub-project under Work

    label_home = planty.create_label("@home", "#AAAAAA")
    label_office = planty.create_label("@office", "#BBBBBB")

    # Create a task
    task1 = planty.create_task("Buy groceries", due_date=datetime(2025, 1, 5), priority=TaskPriority.P2, project_id=inbox.id, label_ids=[label_home.id])
    task2 = planty.create_task("Prepare report", description="Q4 report", priority=TaskPriority.P1, project_id=work.id)
    subtask = planty.create_task("Gather data", parent_id=task2.id)
    planty.create_task("Review data", parent_id=task2.id)

    print("All tasks:")
    for t in planty.get_all_tasks():
        print(t)

    print("\nOverdue tasks (none now):", planty.get_overdue_tasks())

    # Complete subtask
    planty.complete_task(subtask.id)
    # Try to complete task2 (should fail because Review data is incomplete)
    try:
        planty.complete_task(task2.id)
    except ValueError as e:
        print("Error:", e)

    planty.complete_task(
        planty.get_tasks_by_project(work.id)[-1].id  # Review data
    )
    # Now complete task2
    planty.complete_task(task2.id)
    print("\nAfter completions:")
    for t in planty.get_all_tasks():
        print(t)