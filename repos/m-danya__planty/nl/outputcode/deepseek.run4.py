from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Set, Any

class IDGenerator:
    _next_id: int = 1

    @classmethod
    def get_next_id(cls) -> int:
        next_id = cls._next_id
        cls._next_id += 1
        return next_id

class Priority(Enum):
    P1 = 1  # highest
    P2 = 2
    P3 = 3
    P4 = 4  # lowest

class Label:
    def __init__(self, name: str, color: str = "#808080"):
        self.id: int = IDGenerator.get_next_id()
        self.name: str = name
        self.color: str = color
        self._task_ids: Set[int] = set()

    def add_task(self, task_id: int):
        self._task_ids.add(task_id)

    def remove_task(self, task_id: int):
        self._task_ids.discard(task_id)

class Project:
    def __init__(self, name: str, description: str = ""):
        self.id: int = IDGenerator.get_next_id()
        self.name: str = name
        self.description: str = description
        self._task_ids: Set[int] = set()

    def add_task(self, task_id: int):
        self._task_ids.add(task_id)

    def remove_task(self, task_id: int):
        self._task_ids.discard(task_id)

class Task:
    def __init__(self, title: str, description: str = "", due_date: Optional[datetime] = None,
                 priority: Priority = Priority.P4):
        self.id: int = IDGenerator.get_next_id()
        self.title: str = title
        self.description: str = description
        self.due_date: Optional[datetime] = due_date
        self.priority: Priority = priority
        self._completed: bool = False
        self._project_id: Optional[int] = None
        self._parent_id: Optional[int] = None
        self._subtask_ids: List[int] = []
        self._label_ids: Set[int] = set()
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = self.created_at

    @property
    def completed(self) -> bool:
        return self._completed

    def mark_done(self):
        self._completed = True
        self.updated_at = datetime.now()

    def mark_uncompleted(self):
        self._completed = False
        self.updated_at = datetime.now()

    def add_subtask(self, subtask: 'Task', task_manager: Optional['TaskManager'] = None):
        if subtask.id == self.id:
            raise ValueError("Cannot add task as subtask of itself")
        self._subtask_ids.append(subtask.id)
        subtask._parent_id = self.id
        self.updated_at = datetime.now()

    def remove_subtask(self, subtask: 'Task'):
        if subtask.id in self._subtask_ids:
            self._subtask_ids.remove(subtask.id)
            subtask._parent_id = None
            self.updated_at = datetime.now()

    def add_label(self, label: Label, task_manager: Optional['TaskManager'] = None):
        self._label_ids.add(label.id)
        label.add_task(self.id)
        self.updated_at = datetime.now()

    def remove_label(self, label: Label):
        if label.id in self._label_ids:
            self._label_ids.remove(label.id)
            label.remove_task(self.id)
            self.updated_at = datetime.now()

    def set_due_date(self, due_date: Optional[datetime]):
        self.due_date = due_date
        self.updated_at = datetime.now()

class TaskManager:
    def __init__(self):
        self._tasks: Dict[int, Task] = {}
        self._projects: Dict[int, Project] = {}
        self._labels: Dict[int, Label] = {}

    def create_task(self, title: str, description: str = "", due_date: Optional[datetime] = None,
                    priority: Priority = Priority.P4) -> Task:
        task = Task(title, description, due_date, priority)
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: int) -> Optional[Task]:
        return self._tasks.get(task_id)

    def delete_task(self, task_id: int):
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError("Task not found")
        for subtask_id in task._subtask_ids[:]:
            self.delete_task(subtask_id)
        if task._project_id:
            project = self._projects.get(task._project_id)
            if project:
                project.remove_task(task_id)
        for label_id in list(task._label_ids):
            label = self._labels.get(label_id)
            if label:
                label.remove_task(task_id)
        if task._parent_id:
            parent = self._tasks.get(task._parent_id)
            if parent:
                parent._subtask_ids.remove(task_id)
        del self._tasks[task_id]

    def create_project(self, name: str, description: str = "") -> Project:
        project = Project(name, description)
        self._projects[project.id] = project
        return project

    def get_project(self, project_id: int) -> Optional[Project]:
        return self._projects.get(project_id)

    def delete_project(self, project_id: int):
        project = self._projects.get(project_id)
        if not project:
            raise ValueError("Project not found")
        for task_id in list(project._task_ids):
            task = self._tasks.get(task_id)
            if task:
                task._project_id = None
            project.remove_task(task_id)
        del self._projects[project_id]

    def add_task_to_project(self, task_id: int, project_id: int):
        task = self._tasks.get(task_id)
        project = self._projects.get(project_id)
        if not task or not project:
            raise ValueError("Task or Project not found")
        if task._project_id and task._project_id != project_id:
            old_project = self._projects.get(task._project_id)
            if old_project:
                old_project.remove_task(task.id)
        task._project_id = project_id
        project.add_task(task.id)

    def remove_task_from_project(self, task_id: int):
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError("Task not found")
        if task._project_id:
            project = self._projects.get(task._project_id)
            if project:
                project.remove_task(task.id)
            task._project_id = None

    def create_label(self, name: str, color: str = "#808080") -> Label:
        label = Label(name, color)
        self._labels[label.id] = label
        return label

    def get_label(self, label_id: int) -> Optional[Label]:
        return self._labels.get(label_id)

    def delete_label(self, label_id: int):
        label = self._labels.get(label_id)
        if not label:
            raise ValueError("Label not found")
        for task_id in list(label._task_ids):
            task = self._tasks.get(task_id)
            if task:
                task._label_ids.discard(label_id)
        del self._labels[label_id]

    def add_subtask(self, parent_id: int, child_id: int):
        parent = self._tasks.get(parent_id)
        child = self._tasks.get(child_id)
        if not parent or not child:
            raise ValueError("Parent or child task not found")
        if parent_id == child_id:
            raise ValueError("Cannot add task as subtask of itself")
        if self._is_ancestor(child_id, parent_id):
            raise ValueError("Cannot add subtask: circular reference detected")
        if child._parent_id:
            old_parent = self._tasks.get(child._parent_id)
            if old_parent:
                old_parent._subtask_ids.remove(child_id)
            child._parent_id = None
        parent._subtask_ids.append(child_id)
        child._parent_id = parent_id

    def _is_ancestor(self, ancestor_id: int, task_id: int) -> bool:
        current = self._tasks.get(task_id)
        while current and current._parent_id:
            if current._parent_id == ancestor_id:
                return True
            current = self._tasks.get(current._parent_id)
        return False

    def get_subtasks(self, task_id: int) -> List[Task]:
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError("Task not found")
        return [self._tasks[sid] for sid in task._subtask_ids if sid in self._tasks]

    def get_tasks_by_project(self, project_id: int) -> List[Task]:
        project = self._projects.get(project_id)
        if not project:
            raise ValueError("Project not found")
        return [self._tasks[task_id] for task_id in project._task_ids if task_id in self._tasks]

    def get_tasks_by_label(self, label_id: int) -> List[Task]:
        label = self._labels.get(label_id)
        if not label:
            raise ValueError("Label not found")
        return [self._tasks[task_id] for task_id in label._task_ids if task_id in self._tasks]

    def to_dict(self) -> dict:
        tasks = {tid: {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "priority": t.priority.name,
            "completed": t._completed,
            "project_id": t._project_id,
            "parent_id": t._parent_id,
            "subtask_ids": t._subtask_ids.copy(),
            "label_ids": list(t._label_ids),
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat()
        } for tid, t in self._tasks.items()}
        projects = {pid: {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "task_ids": list(p._task_ids)
        } for pid, p in self._projects.items()}
        labels = {lid: {
            "id": l.id,
            "name": l.name,
            "color": l.color,
            "task_ids": list(l._task_ids)
        } for lid, l in self._labels.items()}
        return {"tasks": tasks, "projects": projects, "labels": labels}

    @classmethod
    def from_dict(cls, data: dict) -> 'TaskManager':
        manager = cls()
        for label_data in data.get("labels", {}).values():
            label = Label.__new__(Label)
            label.id = label_data["id"]
            label.name = label_data["name"]
            label.color = label_data.get("color", "#808080")
            label._task_ids = set(label_data.get("task_ids", []))
            manager._labels[label.id] = label
            IDGenerator._next_id = max(IDGenerator._next_id, label.id + 1)
        for proj_data in data.get("projects", {}).values():
            project = Project.__new__(Project)
            project.id = proj_data["id"]
            project.name = proj_data["name"]
            project.description = proj_data.get("description", "")
            project._task_ids = set(proj_data.get("task_ids", []))
            manager._projects[project.id] = project
            IDGenerator._next_id = max(IDGenerator._next_id, project.id + 1)
        for task_data in data.get("tasks", {}).values():
            task = Task.__new__(Task)
            task.id = task_data["id"]
            task.title = task_data["title"]
            task.description = task_data.get("description", "")
            task.due_date = datetime.fromisoformat(task_data["due_date"]) if task_data.get("due_date") else None
            task.priority = Priority[task_data["priority"]]
            task._completed = task_data.get("completed", False)
            task._project_id = task_data.get("project_id")
            task._parent_id = task_data.get("parent_id")
            task._subtask_ids = task_data.get("subtask_ids", [])
            task._label_ids = set(task_data.get("label_ids", []))
            task.created_at = datetime.fromisoformat(task_data["created_at"])
            task.updated_at = datetime.fromisoformat(task_data["updated_at"])
            manager._tasks[task.id] = task
            IDGenerator._next_id = max(IDGenerator._next_id, task.id + 1)
        return manager


if __name__ == "__main__":
    # Minimal demonstration
    mgr = TaskManager()
    inbox = mgr.create_task("Buy milk", priority=Priority.P2)
    proj = mgr.create_project("Home")
    mgr.add_task_to_project(inbox.id, proj.id)
    label = mgr.create_label("groceries", "#00FF00")
    mgr.get_task(inbox.id).add_label(label)

    subtask = mgr.create_task("Check discounts")
    mgr.add_subtask(inbox.id, subtask.id)

    print("Tasks in Home project:")
    for t in mgr.get_tasks_by_project(proj.id):
        print(f"- {t.title} ({t.priority.name})")

    print("Serialized:")
    print(mgr.to_dict())