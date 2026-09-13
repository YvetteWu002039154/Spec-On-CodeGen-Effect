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
    def __init__(self, name: str, color: str = "#000000"):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.color: str = color
        self.created_at: datetime = datetime.now()

    def __repr__(self):
        return f"Label(name={self.name}, color={self.color})"


class Comment:
    def __init__(self, content: str, author: str):
        self.id: str = str(uuid.uuid4())
        self.content: str = content
        self.author: str = author
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

    def edit(self, new_content: str):
        self.content = new_content
        self.updated_at = datetime.now()

    def __repr__(self):
        return f"Comment(author={self.author}, content={self.content[:30]})"


class Task:
    def __init__(
        self,
        title: str,
        description: str = "",
        priority: Priority = Priority.LOW,
        due_date: Optional[date] = None,
        project: Optional["Project"] = None,
        section: Optional["Section"] = None,
    ):
        self.id: str = str(uuid.uuid4())
        self.title: str = title
        self.description: str = description
        self.priority: Priority = priority
        self.status: TaskStatus = TaskStatus.TODO
        self.due_date: Optional[date] = due_date
        self.project: Optional["Project"] = project
        self.section: Optional["Section"] = section
        self.labels: List[Label] = []
        self.comments: List[Comment] = []
        self.subtasks: List["Task"] = []
        self.parent_task: Optional["Task"] = None
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.order: int = 0

    def complete(self):
        self.status = TaskStatus.DONE
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()

    def reopen(self):
        self.status = TaskStatus.TODO
        self.completed_at = None
        self.updated_at = datetime.now()

    def archive(self):
        self.status = TaskStatus.ARCHIVED
        self.updated_at = datetime.now()

    def start(self):
        self.status = TaskStatus.IN_PROGRESS
        self.updated_at = datetime.now()

    def add_label(self, label: Label):
        if label not in self.labels:
            self.labels.append(label)
            self.updated_at = datetime.now()

    def remove_label(self, label: Label):
        if label in self.labels:
            self.labels.remove(label)
            self.updated_at = datetime.now()

    def add_comment(self, comment: Comment):
        self.comments.append(comment)
        self.updated_at = datetime.now()

    def remove_comment(self, comment_id: str):
        self.comments = [c for c in self.comments if c.id != comment_id]
        self.updated_at = datetime.now()

    def add_subtask(self, task: "Task"):
        task.parent_task = self
        task.project = self.project
        self.subtasks.append(task)
        self.updated_at = datetime.now()

    def remove_subtask(self, task_id: str):
        for subtask in self.subtasks:
            if subtask.id == task_id:
                subtask.parent_task = None
                break
        self.subtasks = [t for t in self.subtasks if t.id != task_id]
        self.updated_at = datetime.now()

    def set_due_date(self, due_date: Optional[date]):
        self.due_date = due_date
        self.updated_at = datetime.now()

    def set_priority(self, priority: Priority):
        self.priority = priority
        self.updated_at = datetime.now()

    def update(self, title: Optional[str] = None, description: Optional[str] = None):
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        self.updated_at = datetime.now()

    def is_overdue(self) -> bool:
        if self.due_date and self.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED):
            return self.due_date < date.today()
        return False

    def is_completed(self) -> bool:
        return self.status == TaskStatus.DONE

    def __repr__(self):
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

    def add_task(self, task: Task):
        task.section = self
        task.project = self.project
        task.order = len(self.tasks)
        self.tasks.append(task)
        self.updated_at = datetime.now()

    def remove_task(self, task_id: str):
        for task in self.tasks:
            if task.id == task_id:
                task.section = None
                break
        self.tasks = [t for t in self.tasks if t.id != task_id]
        self.updated_at = datetime.now()

    def get_task(self, task_id: str) -> Optional[Task]:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_active_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED)]

    def get_completed_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status == TaskStatus.DONE]

    def rename(self, new_name: str):
        self.name = new_name
        self.updated_at = datetime.now()

    def __repr__(self):
        return f"Section(name={self.name}, tasks={len(self.tasks)})"


class Project:
    def __init__(self, name: str, description: str = "", color: str = "#4CAF50", owner: Optional["User"] = None):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.description: str = description
        self.color: str = color
        self.owner: Optional["User"] = owner
        self.members: List["User"] = []
        self.sections: List[Section] = []
        self.tasks: List[Task] = []
        self.labels: List[Label] = []
        self.is_archived: bool = False
        self.is_favorite: bool = False
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.order: int = 0

    def add_section(self, section: Section):
        section.project = self
        section.order = len(self.sections)
        self.sections.append(section)
        self.updated_at = datetime.now()

    def remove_section(self, section_id: str):
        for section in self.sections:
            if section.id == section_id:
                section.project = None
                for task in section.tasks:
                    task.section = None
                break
        self.sections = [s for s in self.sections if s.id != section_id]
        self.updated_at = datetime.now()

    def get_section(self, section_id: str) -> Optional[Section]:
        for section in self.sections:
            if section.id == section_id:
                return section
        return None

    def add_task(self, task: Task, section: Optional[Section] = None):
        task.project = self
        if section:
            section.add_task(task)
        else:
            task.order = len(self.tasks)
            self.tasks.append(task)
        self.updated_at = datetime.now()

    def remove_task(self, task_id: str):
        for task in self.tasks:
            if task.id == task_id:
                task.project = None
                break
        self.tasks = [t for t in self.tasks if t.id != task_id]
        for section in self.sections:
            section.remove_task(task_id)
        self.updated_at = datetime.now()

    def get_task(self, task_id: str) -> Optional[Task]:
        for task in self.tasks:
            if task.id == task_id:
                return task
        for section in self.sections:
            task = section.get_task(task_id)
            if task:
                return task
        return None

    def get_all_tasks(self) -> List[Task]:
        all_tasks = list(self.tasks)
        for section in self.sections:
            all_tasks.extend(section.tasks)
        return all_tasks

    def get_active_tasks(self) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED)]

    def get_completed_tasks(self) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.status == TaskStatus.DONE]

    def get_overdue_tasks(self) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.is_overdue()]

    def add_label(self, label: Label):
        if label not in self.labels:
            self.labels.append(label)
            self.updated_at = datetime.now()

    def remove_label(self, label_id: str):
        self.labels = [l for l in self.labels if l.id != label_id]
        self.updated_at = datetime.now()

    def add_member(self, user: "User"):
        if user not in self.members:
            self.members.append(user)
            self.updated_at = datetime.now()

    def remove_member(self, user_id: str):
        self.members = [m for m in self.members if m.id != user_id]
        self.updated_at = datetime.now()

    def archive(self):
        self.is_archived = True
        self.updated_at = datetime.now()

    def unarchive(self):
        self.is_archived = False
        self.updated_at = datetime.now()

    def toggle_favorite(self):
        self.is_favorite = not self.is_favorite
        self.updated_at = datetime.now()

    def update(self, name: Optional[str] = None, description: Optional[str] = None, color: Optional[str] = None):
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if color is not None:
            self.color = color
        self.updated_at = datetime.now()

    def __repr__(self):
        return f"Project(name={self.name}, sections={len(self.sections)}, tasks={len(self.tasks)})"


class User:
    def __init__(self, username: str, email: str, full_name: str = ""):
        self.id: str = str(uuid.uuid4())
        self.username: str = username
        self.email: str = email
        self.full_name: str = full_name
        self.projects: List[Project] = []
        self.inbox: List[Task] = []
        self.labels: List[Label] = []
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

    def create_project(self, name: str, description: str = "", color: str = "#4CAF50") -> Project:
        project = Project(name=name, description=description, color=color, owner=self)
        self.projects.append(project)
        self.updated_at = datetime.now()
        return project

    def delete_project(self, project_id: str):
        self.projects = [p for p in self.projects if p.id != project_id]
        self.updated_at = datetime.now()

    def get_project(self, project_id: str) -> Optional[Project]:
        for project in self.projects:
            if project.id == project_id:
                return project
        return None

    def add_to_inbox(self, task: Task):
        self.inbox.append(task)
        self.updated_at = datetime.now()

    def remove_from_inbox(self, task_id: str):
        self.inbox = [t for t in self.inbox if t.id != task_id]
        self.updated_at = datetime.now()

    def get_inbox_task(self, task_id: str) -> Optional[Task]:
        for task in self.inbox:
            if task.id == task_id:
                return task
        return None

    def create_label(self, name: str, color: str = "#000000") -> Label:
        label = Label(name=name, color=color)
        self.labels.append(label)
        self.updated_at = datetime.now()
        return label

    def delete_label(self, label_id: str):
        self.labels = [l for l in self.labels if l.id != label_id]
        self.updated_at = datetime.now()

    def get_label(self, label_id: str) -> Optional[Label]:
        for label in self.labels:
            if label.id == label_id:
                return label
        return None

    def get_all_tasks(self) -> List[Task]:
        all_tasks = list(self.inbox)
        for project in self.projects:
            all_tasks.extend(project.get_all_tasks())
        return all_tasks

    def get_tasks_due_today(self) -> List[Task]:
        today = date.today()
        return [t for t in self.get_all_tasks() if t.due_date == today and t.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED)]

    def get_overdue_tasks(self) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.is_overdue()]

    def get_tasks_by_priority(self, priority: Priority) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.priority == priority and t.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED)]

    def get_tasks_by_label(self, label: Label) -> List[Task]:
        return [t for t in self.get_all_tasks() if label in t.labels]

    def get_favorite_projects(self) -> List[Project]:
        return [p for p in self.projects if p.is_favorite]

    def get_active_projects(self) -> List[Project]:
        return [p for p in self.projects if not p.is_archived]

    def update(self, full_name: Optional[str] = None, email: Optional[str] = None):
        if full_name is not None:
            self.full_name = full_name
        if email is not None:
            self.email = email
        self.updated_at = datetime.now()

    def __repr__(self):
        return f"User(username={self.username}, email={self.email})"


class Planty:
    def __init__(self):
        self.users: List[User] = []
        self.created_at: datetime = datetime.now()

    def register_user(self, username: str, email: str, full_name: str = "") -> User:
        for user in self.users:
            if user.username == username:
                raise ValueError(f"Username '{username}' already exists.")
            if user.email == email:
                raise ValueError(f"Email '{email}' already registered.")
        user = User(username=username, email=email, full_name=full_name)
        self.users.append(user)
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        for user in self.users:
            if user.id == user_id:
                return user
        return None

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

    def delete_user(self, user_id: str):
        self.users = [u for u in self.users if u.id != user_id]

    def __repr__(self):
        return f"Planty(users={len(self.users)})"