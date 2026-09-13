from __future__ import annotations
from enum import Enum, auto
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Set
import uuid

class TaskStatus(Enum):
    INBOX = auto()
    NEXT_ACTION = auto()
    WAITING = auto()
    SOMEDAY = auto()
    DONE = auto()
    ARCHIVED = auto()

class Priority(Enum):
    P1 = 1  # High
    P2 = 2
    P3 = 3
    P4 = 4  # Low

class RecurrenceRule:
    def __init__(self, frequency: str, interval: int = 1):
        valid = {'daily', 'weekly', 'monthly', 'yearly'}
        if frequency not in valid:
            raise ValueError(f"Invalid frequency: {frequency}")
        self.frequency = frequency
        self.interval = interval

    def next_date(self, from_date: datetime) -> datetime:
        if self.frequency == 'daily':
            return from_date + timedelta(days=self.interval)
        elif self.frequency == 'weekly':
            return from_date + timedelta(weeks=self.interval)
        elif self.frequency == 'monthly':
            # Approximate: add 30 days * interval
            return from_date + timedelta(days=30 * self.interval)
        elif self.frequency == 'yearly':
            return from_date.replace(year=from_date.year + self.interval)
        return from_date

class Task:
    def __init__(
        self,
        title: str,
        description: str = "",
        due_date: Optional[datetime] = None,
        priority: Optional[Priority] = None,
        project_id: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
        context_id: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        status: TaskStatus = TaskStatus.INBOX,
        recurrence: Optional[RecurrenceRule] = None,
    ):
        if not title.strip():
            raise ValueError("Task title cannot be empty")
        self.id: str = uuid.uuid4().hex[:8]
        self.title: str = title
        self.description: str = description
        self.due_date: Optional[datetime] = due_date
        self.priority: Optional[Priority] = priority
        self.project_id: Optional[str] = project_id
        self.label_ids: Set[str] = set(label_ids) if label_ids else set()
        self.context_id: Optional[str] = context_id
        self.parent_task_id: Optional[str] = parent_task_id
        self.subtask_ids: List[str] = []
        self.status: TaskStatus = status
        self.recurrence: Optional[RecurrenceRule] = recurrence
        self.created_at: datetime = datetime.now()
        self.modified_at: datetime = self.created_at
        self.completed_at: Optional[datetime] = None

    def add_subtask(self, subtask_id: str):
        if subtask_id not in self.subtask_ids:
            self.subtask_ids.append(subtask_id)

    def remove_subtask(self, subtask_id: str):
        if subtask_id in self.subtask_ids:
            self.subtask_ids.remove(subtask_id)

class Project:
    def __init__(self, name: str, color: str = "#808080"):
        if not name.strip():
            raise ValueError("Project name cannot be empty")
        self.id: str = uuid.uuid4().hex[:8]
        self.name: str = name
        self.color: str = color
        self.task_ids: List[str] = []

    def add_task(self, task_id: str):
        if task_id not in self.task_ids:
            self.task_ids.append(task_id)

    def remove_task(self, task_id: str):
        if task_id in self.task_ids:
            self.task_ids.remove(task_id)

class Label:
    def __init__(self, name: str, color: str = "#808080"):
        if not name.strip():
            raise ValueError("Label name cannot be empty")
        self.id: str = uuid.uuid4().hex[:8]
        self.name: str = name
        self.color: str = color

class Context:
    def __init__(self, name: str):
        if not name.strip():
            raise ValueError("Context name cannot be empty")
        self.id: str = uuid.uuid4().hex[:8]
        self.name: str = name

class PlantyApp:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.projects: Dict[str, Project] = {}
        self.labels: Dict[str, Label] = {}
        self.contexts: Dict[str, Context] = {}
        self.inbox_order: List[str] = []       # For GTD inbox processing

    def create_task(self, title: str, **kwargs) -> Task:
        task = Task(title, **kwargs)
        self.tasks[task.id] = task
        if task.status == TaskStatus.INBOX:
            self.inbox_order.append(task.id)
        if task.project_id and task.project_id in self.projects:
            self.projects[task.project_id].add_task(task.id)
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        task = self.tasks.get(task_id)
        if not task:
            return None
        allowed = {'title', 'description', 'due_date', 'priority', 'status',
                   'project_id', 'context_id', 'label_ids', 'recurrence'}
        for key, value in kwargs.items():
            if key in allowed:
                if key == 'label_ids' and isinstance(value, list):
                    task.label_ids = set(value)
                elif key == 'status' and isinstance(value, TaskStatus):
                    old_status = task.status
                    if old_status != value:
                        if value == TaskStatus.INBOX:
                            if task.id not in self.inbox_order:
                                self.inbox_order.append(task.id)
                        elif old_status == TaskStatus.INBOX and value != TaskStatus.INBOX:
                            if task.id in self.inbox_order:
                                self.inbox_order.remove(task.id)
                        if value == TaskStatus.DONE and task.recurrence and task.due_date:
                            # Handle recurrence: create next instance
                            next_date = task.recurrence.next_date(task.due_date)
                            self.create_task(
                                title=task.title,
                                description=task.description,
                                due_date=next_date,
                                priority=task.priority,
                                project_id=task.project_id,
                                label_ids=list(task.label_ids),
                                context_id=task.context_id,
                                parent_task_id=task.parent_task_id,
                                status=TaskStatus.INBOX,
                                recurrence=task.recurrence,
                            )
                        task.status = value
                        if value == TaskStatus.DONE:
                            task.completed_at = datetime.now()
                        else:
                            task.completed_at = None
                else:
                    setattr(task, key, value)
        task.modified_at = datetime.now()
        # Handle project change
        if 'project_id' in kwargs:
            new_proj = kwargs['project_id']
            old_proj = task.project_id
            if old_proj and old_proj in self.projects:
                self.projects[old_proj].remove_task(task.id)
            task.project_id = new_proj
            if new_proj and new_proj in self.projects:
                self.projects[new_proj].add_task(task.id)
        return task

    def complete_task(self, task_id: str) -> Optional[Task]:
        return self.update_task(task_id, status=TaskStatus.DONE)

    def archive_task(self, task_id: str) -> Optional[Task]:
        return self.update_task(task_id, status=TaskStatus.ARCHIVED)

    def delete_task(self, task_id: str) -> bool:
        task = self.tasks.pop(task_id, None)
        if task:
            if task.project_id and task.project_id in self.projects:
                self.projects[task.project_id].remove_task(task.id)
            if task.parent_task_id and task.parent_task_id in self.tasks:
                parent = self.tasks[task.parent_task_id]
                parent.remove_subtask(task.id)
            for subtask_id in task.subtask_ids:
                self.delete_task(subtask_id)
            if task.id in self.inbox_order:
                self.inbox_order.remove(task.id)
            return True
        return False

    def add_subtask(self, parent_id: str, title: str, **kwargs) -> Optional[Task]:
        parent = self.tasks.get(parent_id)
        if not parent:
            return None
        subtask = Task(title, parent_task_id=parent_id, **kwargs)
        self.tasks[subtask.id] = subtask
        parent.add_subtask(subtask.id)
        if subtask.project_id is None and parent.project_id:
            subtask.project_id = parent.project_id
            if parent.project_id in self.projects:
                self.projects[parent.project_id].add_task(subtask.id)
        return subtask

    def create_project(self, name: str, color: str = "#808080") -> Project:
        project = Project(name, color)
        self.projects[project.id] = project
        return project

    def delete_project(self, project_id: str) -> bool:
        project = self.projects.pop(project_id, None)
        if project:
            for task_id in project.task_ids:
                task = self.tasks.get(task_id)
                if task:
                    task.project_id = None
            return True
        return False

    def create_label(self, name: str, color: str = "#808080") -> Label:
        label = Label(name, color)
        self.labels[label.id] = label
        return label

    def delete_label(self, label_id: str) -> bool:
        label = self.labels.pop(label_id, None)
        if label:
            for task in self.tasks.values():
                task.label_ids.discard(label_id)
            return True
        return False

    def create_context(self, name: str) -> Context:
        context = Context(name)
        self.contexts[context.id] = context
        return context

    def delete_context(self, context_id: str) -> bool:
        context = self.contexts.pop(context_id, None)
        if context:
            for task in self.tasks.values():
                if task.context_id == context_id:
                    task.context_id = None
            return True
        return False

    def get_tasks_by_filter(
        self,
        status: Optional[TaskStatus] = None,
        project_id: Optional[str] = None,
        context_id: Optional[str] = None,
        label_id: Optional[str] = None,
        priority: Optional[Priority] = None,
        due_before: Optional[datetime] = None,
        due_after: Optional[datetime] = None,
        parent_task_id: Optional[str] = None,      # None for root tasks, set to id for subtasks
    ) -> List[Task]:
        result = []
        for task in self.tasks.values():
            if status is not None and task.status != status:
                continue
            if project_id is not None and task.project_id != project_id:
                continue
            if context_id is not None and task.context_id != context_id:
                continue
            if label_id is not None and label_id not in task.label_ids:
                continue
            if priority is not None and task.priority != priority:
                continue
            if due_before is not None:
                if task.due_date is None or task.due_date > due_before:
                    continue
            if due_after is not None:
                if task.due_date is None or task.due_date < due_after:
                    continue
            if parent_task_id is not None:
                if task.parent_task_id != parent_task_id:
                    continue
            else:
                # If parent_task_id is None and we want root tasks, skip subtasks
                if task.parent_task_id is not None:
                    continue
            result.append(task)
        return result

    def sort_tasks(self, tasks: List[Task], by: str = "due_date") -> List[Task]:
        if by == "due_date":
            return sorted(tasks, key=lambda t: (t.due_date is None, t.due_date or datetime.max))
        elif by == "priority":
            def priority_val(t: Task):
                if t.priority is None:
                    return 5
                return t.priority.value
            return sorted(tasks, key=priority_val)
        elif by == "created_at":
            return sorted(tasks, key=lambda t: t.created_at)
        elif by == "title":
            return sorted(tasks, key=lambda t: t.title.lower())
        return tasks

    def search_tasks(self, keyword: str) -> List[Task]:
        keyword_lower = keyword.lower()
        result = []
        for task in self.tasks.values():
            if keyword_lower in task.title.lower() or keyword_lower in task.description.lower():
                result.append(task)
        return result

    def get_all_inbox(self) -> List[Task]:
        return [self.tasks[tid] for tid in self.inbox_order if tid in self.tasks and self.tasks[tid].status == TaskStatus.INBOX]

    def move_to_next_action(self, task_id: str) -> Optional[Task]:
        return self.update_task(task_id, status=TaskStatus.NEXT_ACTION)

    def move_to_waiting(self, task_id: str) -> Optional[Task]:
        return self.update_task(task_id, status=TaskStatus.WAITING)

    def move_to_someday(self, task_id: str) -> Optional[Task]:
        return self.update_task(task_id, status=TaskStatus.SOMEDAY)

if __name__ == "__main__":
    app = PlantyApp()

    # Basic workflow
    task1 = app.create_task("Buy groceries", description="Milk, eggs, bread", priority=Priority.P2,
                            due_date=datetime.now() + timedelta(days=1))
    task2 = app.create_task("Read book", status=TaskStatus.NEXT_ACTION)
    proj = app.create_project("Home", color="#34a853")
    app.update_task(task1.id, project_id=proj.id)

    app.add_subtask(task1.id, "Check fridge inventory")
    app.create_label("urgent", color="#ea4335")
    app.update_task(task1.id, label_ids=["urgent"])

    ctx = app.create_context("@computer")
    app.update_task(task2.id, context_id=ctx.id)

    print("Inbox:", [t.title for t in app.get_all_inbox()])
    print("Next actions:", [t.title for t in app.get_tasks_by_filter(status=TaskStatus.NEXT_ACTION)])
    app.complete_task(task2.id)
    print("Completed:", task2.status, task2.completed_at)

    # Recurring task
    app.create_task("Water plants", due_date=datetime.now(), recurrence=RecurrenceRule("daily", interval=1), status=TaskStatus.INBOX)
    recurring_task = app.tasks[next(iter(app.tasks))]  # fragile but demo
    # Force complete a recurring
    app.complete_task(recurring_task.id) if recurring_task.recurrence else None
    print("Tasks after completing recurring:", [t.title for t in app.tasks.values()])