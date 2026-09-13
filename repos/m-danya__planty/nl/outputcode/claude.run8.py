from datetime import datetime, date
from typing import Optional, List
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


class Label:
    def __init__(self, name: str, color: Optional[str] = None):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.color: Optional[str] = color
        self.created_at: datetime = datetime.now()

    def __repr__(self) -> str:
        return f"Label(name={self.name}, color={self.color})"


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
        return f"Comment(author={self.author}, content={self.content[:30]})"


class Task:
    def __init__(
        self,
        title: str,
        description: Optional[str] = None,
        due_date: Optional[date] = None,
        priority: Priority = Priority.MEDIUM,
        project: Optional["Project"] = None,
        section: Optional["Section"] = None,
        parent_task: Optional["Task"] = None,
    ):
        self.id: str = str(uuid.uuid4())
        self.title: str = title
        self.description: Optional[str] = description
        self.due_date: Optional[date] = due_date
        self.priority: Priority = priority
        self.status: TaskStatus = TaskStatus.TODO
        self.project: Optional["Project"] = project
        self.section: Optional["Section"] = section
        self.parent_task: Optional["Task"] = parent_task
        self.subtasks: List["Task"] = []
        self.labels: List[Label] = []
        self.comments: List[Comment] = []
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.assignee: Optional[str] = None
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

    def add_subtask(self, task: "Task") -> None:
        task.parent_task = self
        task.project = self.project
        self.subtasks.append(task)
        self.updated_at = datetime.now()

    def remove_subtask(self, task_id: str) -> bool:
        for i, subtask in enumerate(self.subtasks):
            if subtask.id == task_id:
                self.subtasks.pop(i)
                self.updated_at = datetime.now()
                return True
        return False

    def add_label(self, label: Label) -> None:
        if label not in self.labels:
            self.labels.append(label)
            self.updated_at = datetime.now()

    def remove_label(self, label_id: str) -> bool:
        for i, label in enumerate(self.labels):
            if label.id == label_id:
                self.labels.pop(i)
                self.updated_at = datetime.now()
                return True
        return False

    def add_comment(self, comment: Comment) -> None:
        self.comments.append(comment)
        self.updated_at = datetime.now()

    def remove_comment(self, comment_id: str) -> bool:
        for i, comment in enumerate(self.comments):
            if comment.id == comment_id:
                self.comments.pop(i)
                self.updated_at = datetime.now()
                return True
        return False

    def set_due_date(self, due_date: Optional[date]) -> None:
        self.due_date = due_date
        self.updated_at = datetime.now()

    def set_priority(self, priority: Priority) -> None:
        self.priority = priority
        self.updated_at = datetime.now()

    def assign_to(self, assignee: str) -> None:
        self.assignee = assignee
        self.updated_at = datetime.now()

    def is_overdue(self) -> bool:
        if self.due_date and self.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED):
            return self.due_date < date.today()
        return False

    def is_completed(self) -> bool:
        return self.status == TaskStatus.DONE

    def get_all_subtasks(self) -> List["Task"]:
        all_subtasks = []
        for subtask in self.subtasks:
            all_subtasks.append(subtask)
            all_subtasks.extend(subtask.get_all_subtasks())
        return all_subtasks

    def __repr__(self) -> str:
        return f"Task(title={self.title}, status={self.status.value}, priority={self.priority.name})"


class Section:
    def __init__(self, name: str, project: Optional["Project"] = None):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.project: Optional["Project"] = project
        self.tasks: List[Task] = []
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.order: int = 0

    def add_task(self, task: Task) -> None:
        task.section = self
        task.project = self.project
        self.tasks.append(task)
        self.updated_at = datetime.now()

    def remove_task(self, task_id: str) -> bool:
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                self.tasks.pop(i)
                self.updated_at = datetime.now()
                return True
        return False

    def get_completed_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.is_completed()]

    def get_pending_tasks(self) -> List[Task]:
        return [t for t in self.tasks if not t.is_completed() and t.status != TaskStatus.ARCHIVED]

    def __repr__(self) -> str:
        return f"Section(name={self.name}, tasks={len(self.tasks)})"


class Project:
    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        is_favorite: bool = False,
    ):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.description: Optional[str] = description
        self.color: Optional[str] = color
        self.is_favorite: bool = is_favorite
        self.is_archived: bool = False
        self.tasks: List[Task] = []
        self.sections: List[Section] = []
        self.labels: List[Label] = []
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.owner: Optional[str] = None
        self.members: List[str] = []
        self.order: int = 0

    def add_task(self, task: Task) -> None:
        task.project = self
        self.tasks.append(task)
        self.updated_at = datetime.now()

    def remove_task(self, task_id: str) -> bool:
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                self.tasks.pop(i)
                self.updated_at = datetime.now()
                return True
        return False

    def add_section(self, section: Section) -> None:
        section.project = self
        section.order = len(self.sections)
        self.sections.append(section)
        self.updated_at = datetime.now()

    def remove_section(self, section_id: str) -> bool:
        for i, section in enumerate(self.sections):
            if section.id == section_id:
                self.sections.pop(i)
                self.updated_at = datetime.now()
                return True
        return False

    def get_section_by_name(self, name: str) -> Optional[Section]:
        for section in self.sections:
            if section.name == name:
                return section
        return None

    def add_label(self, label: Label) -> None:
        if label not in self.labels:
            self.labels.append(label)
            self.updated_at = datetime.now()

    def remove_label(self, label_id: str) -> bool:
        for i, label in enumerate(self.labels):
            if label.id == label_id:
                self.labels.pop(i)
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

    def get_all_tasks(self) -> List[Task]:
        all_tasks = list(self.tasks)
        for section in self.sections:
            all_tasks.extend(section.tasks)
        return all_tasks

    def get_completed_tasks(self) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.is_completed()]

    def get_pending_tasks(self) -> List[Task]:
        return [t for t in self.get_all_tasks() if not t.is_completed() and t.status != TaskStatus.ARCHIVED]

    def get_overdue_tasks(self) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.is_overdue()]

    def get_tasks_by_priority(self, priority: Priority) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.priority == priority]

    def get_tasks_by_label(self, label_name: str) -> List[Task]:
        return [t for t in self.get_all_tasks() if any(l.name == label_name for l in t.labels)]

    def get_tasks_by_assignee(self, assignee: str) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.assignee == assignee]

    def completion_percentage(self) -> float:
        all_tasks = self.get_all_tasks()
        if not all_tasks:
            return 0.0
        completed = len(self.get_completed_tasks())
        return (completed / len(all_tasks)) * 100

    def __repr__(self) -> str:
        return f"Project(name={self.name}, tasks={len(self.get_all_tasks())})"


class User:
    def __init__(self, username: str, email: str, full_name: Optional[str] = None):
        self.id: str = str(uuid.uuid4())
        self.username: str = username
        self.email: str = email
        self.full_name: Optional[str] = full_name
        self.projects: List[Project] = []
        self.labels: List[Label] = []
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.is_active: bool = True

    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
    ) -> Project:
        project = Project(name=name, description=description, color=color)
        project.owner = self.username
        project.order = len(self.projects)
        self.projects.append(project)
        self.updated_at = datetime.now()
        return project

    def delete_project(self, project_id: str) -> bool:
        for i, project in enumerate(self.projects):
            if project.id == project_id:
                self.projects.pop(i)
                self.updated_at = datetime.now()
                return True
        return False

    def get_project_by_name(self, name: str) -> Optional[Project]:
        for project in self.projects:
            if project.name == name:
                return project
        return None

    def get_project_by_id(self, project_id: str) -> Optional[Project]:
        for project in self.projects:
            if project.id == project_id:
                return project
        return None

    def create_label(self, name: str, color: Optional[str] = None) -> Label:
        label = Label(name=name, color=color)
        self.labels.append(label)
        self.updated_at = datetime.now()
        return label

    def delete_label(self, label_id: str) -> bool:
        for i, label in enumerate(self.labels):
            if label.id == label_id:
                self.labels.pop(i)
                self.updated_at = datetime.now()
                return True
        return False

    def get_label_by_name(self, name: str) -> Optional[Label]:
        for label in self.labels:
            if label.name == name:
                return label
        return None

    def get_favorite_projects(self) -> List[Project]:
        return [p for p in self.projects if p.is_favorite and not p.is_archived]

    def get_active_projects(self) -> List[Project]:
        return [p for p in self.projects if not p.is_archived]

    def get_archived_projects(self) -> List[Project]:
        return [p for p in self.projects if p.is_archived]

    def get_all_tasks(self) -> List[Task]:
        all_tasks = []
        for project in self.projects:
            all_tasks.extend(project.get_all_tasks())
        return all_tasks

    def get_tasks_due_today(self) -> List[Task]:
        today = date.today()
        return [t for t in self.get_all_tasks() if t.due_date == today and not t.is_completed()]

    def get_overdue_tasks(self) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.is_overdue()]

    def get_tasks_by_priority(self, priority: Priority) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.priority == priority]

    def get_inbox_tasks(self) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.project is None or t.section is None]

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = datetime.now()

    def activate(self) -> None:
        self.is_active = True
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return f"User(username={self.username}, email={self.email})"


class Planty:
    def __init__(self):
        self.users: List[User] = []
        self.created_at: datetime = datetime.now()

    def register_user(
        self,
        username: str,
        email: str,
        full_name: Optional[str] = None,
    ) -> User:
        for user in self.users:
            if user.username == username:
                raise ValueError(f"Username '{username}' already exists.")
            if user.email == email:
                raise ValueError(f"Email '{email}' already registered.")
        user = User(username=username, email=email, full_name=full_name)
        self.users.append(user)
        return user

    def get_user_by_username(self, username: str) -> Optional[User]:
        for user in self.users:
            if user.username == username:
                return user
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        for user in self.users:
            if user.email == email:
                return user
        return None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        for user in self.users:
            if user.id == user_id:
                return user
        return None

    def delete_user(self, user_id: str) -> bool:
        for i, user in enumerate(self.users):
            if user.id == user_id:
                self.users.pop(i)
                return True
        return False

    def get_all_users(self) -> List[User]:
        return list(self.users)

    def get_active_users(self) -> List[User]:
        return [u for u in self.users if u.is_active]

    def __repr__(self) -> str:
        return f"Planty(users={len(self.users)})"