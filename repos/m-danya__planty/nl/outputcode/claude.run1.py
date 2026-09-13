from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class TaskStatus(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ARCHIVED = "archived"


class RecurrenceType(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class Label:
    def __init__(self, name: str, color: str = "#000000"):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.color: str = color
        self.created_at: datetime = datetime.now()

    def __repr__(self) -> str:
        return f"Label(name={self.name}, color={self.color})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "created_at": self.created_at.isoformat(),
        }


class Comment:
    def __init__(self, content: str, author: str):
        self.id: str = str(uuid.uuid4())
        self.content: str = content
        self.author: str = author
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

    def edit(self, new_content: str) -> None:
        self.content = new_content
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return f"Comment(author={self.author}, content={self.content[:50]})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Recurrence:
    def __init__(self, recurrence_type: RecurrenceType, interval: int = 1):
        self.recurrence_type: RecurrenceType = recurrence_type
        self.interval: int = interval

    def __repr__(self) -> str:
        return f"Recurrence(type={self.recurrence_type.value}, interval={self.interval})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recurrence_type": self.recurrence_type.value,
            "interval": self.interval,
        }


class Task:
    def __init__(
        self,
        title: str,
        description: str = "",
        due_date: Optional[date] = None,
        priority: Priority = Priority.MEDIUM,
        project_id: Optional[str] = None,
        section_id: Optional[str] = None,
        parent_id: Optional[str] = None,
    ):
        self.id: str = str(uuid.uuid4())
        self.title: str = title
        self.description: str = description
        self.due_date: Optional[date] = due_date
        self.priority: Priority = priority
        self.status: TaskStatus = TaskStatus.TODO
        self.project_id: Optional[str] = project_id
        self.section_id: Optional[str] = section_id
        self.parent_id: Optional[str] = parent_id
        self.labels: List[Label] = []
        self.comments: List[Comment] = []
        self.subtasks: List["Task"] = []
        self.recurrence: Optional[Recurrence] = None
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.order: int = 0

    def complete(self) -> None:
        self.status = TaskStatus.DONE
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()

    def reopen(self) -> None:
        self.status = TaskStatus.TODO
        self.completed_at = None
        self.updated_at = datetime.now()

    def archive(self) -> None:
        self.status = TaskStatus.ARCHIVED
        self.updated_at = datetime.now()

    def start(self) -> None:
        self.status = TaskStatus.IN_PROGRESS
        self.updated_at = datetime.now()

    def update(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        due_date: Optional[date] = None,
        priority: Optional[Priority] = None,
    ) -> None:
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if due_date is not None:
            self.due_date = due_date
        if priority is not None:
            self.priority = priority
        self.updated_at = datetime.now()

    def add_label(self, label: Label) -> None:
        if label not in self.labels:
            self.labels.append(label)
            self.updated_at = datetime.now()

    def remove_label(self, label: Label) -> None:
        if label in self.labels:
            self.labels.remove(label)
            self.updated_at = datetime.now()

    def add_comment(self, comment: Comment) -> None:
        self.comments.append(comment)
        self.updated_at = datetime.now()

    def remove_comment(self, comment_id: str) -> bool:
        for comment in self.comments:
            if comment.id == comment_id:
                self.comments.remove(comment)
                self.updated_at = datetime.now()
                return True
        return False

    def add_subtask(self, task: "Task") -> None:
        task.parent_id = self.id
        task.project_id = self.project_id
        self.subtasks.append(task)
        self.updated_at = datetime.now()

    def remove_subtask(self, task_id: str) -> bool:
        for subtask in self.subtasks:
            if subtask.id == task_id:
                self.subtasks.remove(subtask)
                self.updated_at = datetime.now()
                return True
        return False

    def set_recurrence(self, recurrence: Recurrence) -> None:
        self.recurrence = recurrence
        self.updated_at = datetime.now()

    def remove_recurrence(self) -> None:
        self.recurrence = None
        self.updated_at = datetime.now()

    def is_overdue(self) -> bool:
        if self.due_date and self.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED):
            return self.due_date < date.today()
        return False

    def is_completed(self) -> bool:
        return self.status == TaskStatus.DONE

    def get_completion_percentage(self) -> float:
        if not self.subtasks:
            return 100.0 if self.is_completed() else 0.0
        completed = sum(1 for t in self.subtasks if t.is_completed())
        return (completed / len(self.subtasks)) * 100.0

    def __repr__(self) -> str:
        return f"Task(title={self.title}, status={self.status.value}, priority={self.priority.name})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "priority": self.priority.name,
            "status": self.status.value,
            "project_id": self.project_id,
            "section_id": self.section_id,
            "parent_id": self.parent_id,
            "labels": [label.to_dict() for label in self.labels],
            "comments": [comment.to_dict() for comment in self.comments],
            "subtasks": [subtask.to_dict() for subtask in self.subtasks],
            "recurrence": self.recurrence.to_dict() if self.recurrence else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "order": self.order,
        }


class Section:
    def __init__(self, name: str, project_id: str):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.project_id: str = project_id
        self.tasks: List[Task] = []
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.order: int = 0

    def add_task(self, task: Task) -> None:
        task.project_id = self.project_id
        task.section_id = self.id
        task.order = len(self.tasks)
        self.tasks.append(task)
        self.updated_at = datetime.now()

    def remove_task(self, task_id: str) -> bool:
        for task in self.tasks:
            if task.id == task_id:
                self.tasks.remove(task)
                self.updated_at = datetime.now()
                return True
        return False

    def get_task(self, task_id: str) -> Optional[Task]:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        return [task for task in self.tasks if task.status == status]

    def rename(self, new_name: str) -> None:
        self.name = new_name
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return f"Section(name={self.name}, tasks={len(self.tasks)})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "project_id": self.project_id,
            "tasks": [task.to_dict() for task in self.tasks],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "order": self.order,
        }


class Project:
    def __init__(self, name: str, description: str = "", color: str = "#4CAF50", owner: str = ""):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.description: str = description
        self.color: str = color
        self.owner: str = owner
        self.tasks: List[Task] = []
        self.sections: List[Section] = []
        self.labels: List[Label] = []
        self.members: List[str] = []
        self.is_archived: bool = False
        self.is_favorite: bool = False
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.order: int = 0

    def add_task(self, task: Task) -> None:
        task.project_id = self.id
        task.order = len(self.tasks)
        self.tasks.append(task)
        self.updated_at = datetime.now()

    def remove_task(self, task_id: str) -> bool:
        for task in self.tasks:
            if task.id == task_id:
                self.tasks.remove(task)
                self.updated_at = datetime.now()
                return True
        return False

    def get_task(self, task_id: str) -> Optional[Task]:
        for task in self.tasks:
            if task.id == task_id:
                return task
        for section in self.sections:
            task = section.get_task(task_id)
            if task:
                return task
        return None

    def add_section(self, section: Section) -> None:
        section.project_id = self.id
        section.order = len(self.sections)
        self.sections.append(section)
        self.updated_at = datetime.now()

    def remove_section(self, section_id: str) -> bool:
        for section in self.sections:
            if section.id == section_id:
                self.sections.remove(section)
                self.updated_at = datetime.now()
                return True
        return False

    def get_section(self, section_id: str) -> Optional[Section]:
        for section in self.sections:
            if section.id == section_id:
                return section
        return None

    def add_label(self, label: Label) -> None:
        if label not in self.labels:
            self.labels.append(label)
            self.updated_at = datetime.now()

    def remove_label(self, label_id: str) -> bool:
        for label in self.labels:
            if label.id == label_id:
                self.labels.remove(label)
                self.updated_at = datetime.now()
                return True
        return False

    def add_member(self, member: str) -> None:
        if member not in self.members:
            self.members.append(member)
            self.updated_at = datetime.now()

    def remove_member(self, member: str) -> bool:
        if member in self.members:
            self.members.remove(member)
            self.updated_at = datetime.now()
            return True
        return False

    def archive(self) -> None:
        self.is_archived = True
        self.updated_at = datetime.now()

    def unarchive(self) -> None:
        self.is_archived = False
        self.updated_at = datetime.now()

    def toggle_favorite(self) -> None:
        self.is_favorite = not self.is_favorite
        self.updated_at = datetime.now()

    def update(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
    ) -> None:
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if color is not None:
            self.color = color
        self.updated_at = datetime.now()

    def get_all_tasks(self) -> List[Task]:
        all_tasks = list(self.tasks)
        for section in self.sections:
            all_tasks.extend(section.tasks)
        return all_tasks

    def get_tasks_by_priority(self, priority: Priority) -> List[Task]:
        return [task for task in self.get_all_tasks() if task.priority == priority]

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        return [task for task in self.get_all_tasks() if task.status == status]

    def get_overdue_tasks(self) -> List[Task]:
        return [task for task in self.get_all_tasks() if task.is_overdue()]

    def get_completion_percentage(self) -> float:
        all_tasks = self.get_all_tasks()
        if not all_tasks:
            return 0.0
        completed = sum(1 for task in all_tasks if task.is_completed())
        return (completed / len(all_tasks)) * 100.0

    def __repr__(self) -> str:
        return f"Project(name={self.name}, tasks={len(self.get_all_tasks())})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "owner": self.owner,
            "tasks": [task.to_dict() for task in self.tasks],
            "sections": [section.to_dict() for section in self.sections],
            "labels": [label.to_dict() for label in self.labels],
            "members": self.members,
            "is_archived": self.is_archived,
            "is_favorite": self.is_favorite,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "order": self.order,
        }


class Inbox:
    def __init__(self, owner: str):
        self.id: str = str(uuid.uuid4())
        self.owner: str = owner
        self.tasks: List[Task] = []
        self.created_at: datetime = datetime.now()

    def add_task(self, task: Task) -> None:
        task.order = len(self.tasks)
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> bool:
        for task in self.tasks:
            if task.id == task_id:
                self.tasks.remove(task)
                return True
        return False

    def get_task(self, task_id: str) -> Optional[Task]:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        return [task for task in self.tasks if task.status == status]

    def get_overdue_tasks(self) -> List[Task]:
        return [task for task in self.tasks if task.is_overdue()]

    def __repr__(self) -> str:
        return f"Inbox(owner={self.owner}, tasks={len(self.tasks)})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner": self.owner,
            "tasks": [task.to_dict() for task in self.tasks],
            "created_at": self.created_at.isoformat(),
        }


class Filter:
    def __init__(self, name: str, query: str, owner: str):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.query: str = query
        self.owner: str = owner
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

    def update(self, name: Optional[str] = None, query: Optional[str] = None) -> None:
        if name is not None:
            self.name = name
        if query is not None:
            self.query = query
        self.updated_at = datetime.now()

    def apply(self, tasks: List[Task]) -> List[Task]:
        filtered = []
        query_lower = self.query.lower()
        for task in tasks:
            if query_lower in task.title.lower() or query_lower in task.description.lower():
                filtered.append(task)
        return filtered

    def __repr__(self) -> str:
        return f"Filter(name={self.name}, query={self.query})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "query": self.query,
            "owner": self.owner,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class User:
    def __init__(self, username: str, email: str, full_name: str = ""):
        self.id: str = str(uuid.uuid4())
        self.username: str = username
        self.email: str = email
        self.full_name: str = full_name
        self.projects: List[Project] = []
        self.inbox: Inbox = Inbox(owner=username)
        self.labels: List[Label] = []
        self.filters: List[Filter] = []
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

    def create_project(self, name: str, description: str = "", color: str = "#4CAF50") -> Project:
        project = Project(name=name, description=description, color=color, owner=self.username)
        project.order = len(self.projects)
        self.projects.append(project)
        self.updated_at = datetime.now()
        return project

    def delete_project(self, project_id: str) -> bool:
        for project in self.projects:
            if project.id == project_id:
                self.projects.remove(project)
                self.updated_at = datetime.now()
                return True
        return False

    def get_project(self, project_id: str) -> Optional[Project]:
        for project in self.projects:
            if project.id == project_id:
                return project
        return None

    def get_project_by_name(self, name: str) -> Optional[Project]:
        for project in self.projects:
            if project.name == name:
                return project
        return None

    def add_task_to_inbox(self, task: Task) -> None:
        self.inbox.add_task(task)
        self.updated_at = datetime.now()

    def create_label(self, name: str, color: str = "#000000") -> Label:
        label = Label(name=name, color=color)
        self.labels.append(label)
        self.updated_at = datetime.now()
        return label

    def delete_label(self, label_id: str) -> bool:
        for label in self.labels:
            if label.id == label_id:
                self.labels.remove(label)
                self.updated_at = datetime.now()
                return True
        return False

    def get_label(self, label_id: str) -> Optional[Label]:
        for label in self.labels:
            if label.id == label_id:
                return label
        return None

    def get_label_by_name(self, name: str) -> Optional[Label]:
        for label in self.labels:
            if label.name == name:
                return label
        return None

    def create_filter(self, name: str, query: str) -> Filter:
        f = Filter(name=name, query=query, owner=self.username)
        self.filters.append(f)
        self.updated_at = datetime.now()
        return f

    def delete_filter(self, filter_id: str) -> bool:
        for f in self.filters:
            if f.id == filter_id:
                self.filters.remove(f)
                self.updated_at = datetime.now()
                return True
        return False

    def get_filter(self, filter_id: str) -> Optional[Filter]:
        for f in self.filters:
            if f.id == filter_id:
                return f
        return None

    def get_all_tasks(self) -> List[Task]:
        all_tasks = list(self.inbox.tasks)
        for project in self.projects:
            all_tasks.extend(project.get_all_tasks())
        return all_tasks

    def get_today_tasks(self) -> List[Task]:
        today = date.today()
        return [task for task in self.get_all_tasks() if task.due_date == today]

    def get_upcoming_tasks(self) -> List[Task]:
        today = date.today()
        return [
            task for task in self.get_all_tasks()
            if task.due_date and task.due_date >= today and task.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED)
        ]

    def get_overdue_tasks(self) -> List[Task]:
        return [task for task in self.get_all_tasks() if task.is_overdue()]

    def get_tasks_by_label(self, label: Label) -> List[Task]:
        return [task for task in self.get_all_tasks() if label in task.labels]

    def get_tasks_by_priority(self, priority: Priority) -> List[Task]:
        return [task for task in self.get_all_tasks() if task.priority == priority]

    def get_favorite_projects(self) -> List[Project]:
        return [project for project in self.projects if project.is_favorite]

    def get_archived_projects(self) -> List[Project]:
        return [project for project in self.projects if project.is_archived]

    def get_active_projects(self) -> List[Project]:
        return [project for project in self.projects if not project.is_archived]

    def update(
        self,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> None:
        if email is not None:
            self.email = email
        if full_name is not None:
            self.full_name = full_name
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return f"User(username={self.username}, email={self.email})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "projects": [project.to_dict() for project in self.projects],
            "inbox": self.inbox.to_dict(),
            "labels": [label.to_dict() for label in self.labels],
            "filters": [f.to_dict() for f in self.filters],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Planty:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.created_at: datetime = datetime.now()

    def register_user(self, username: str, email: str, full_name: str = "") -> User:
        if username in self.users:
            raise ValueError(f"User '{username}' already exists.")
        user = User(username=username, email=email, full_name=full_name)
        self.users[username] = user
        return user

    def delete_user(self, username: str) -> bool:
        if username in self.users:
            del self.users[username]
            return True
        return False

    def get_user(self, username: str) -> Optional[User]:
        return self.users.get(username)

    def get_all_users(self) -> List[User]:
        return list(self.users.values())

    def search_tasks(self, query: str) -> List[Task]:
        results = []
        query_lower = query.lower()
        for user in self.users.values():
            for task in user.get_all_tasks():
                if query_lower in task.title.lower() or query_lower in task.description.lower():
                    results.append(task)
        return results

    def __repr__(self) -> str:
        return f"Planty(users={len(self.users)})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "users": {username: user.to_dict() for username, user in self.users.items()},
            "created_at": self.created_at.isoformat(),
        }