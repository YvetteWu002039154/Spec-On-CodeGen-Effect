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
    def __init__(self, name: str, color: Optional[str] = None):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.color: Optional[str] = color
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
    def __init__(self, content: str, author: Optional[str] = None):
        self.id: str = str(uuid.uuid4())
        self.content: str = content
        self.author: Optional[str] = author
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

    def edit(self, new_content: str) -> None:
        self.content = new_content
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return f"Comment(author={self.author}, content={self.content[:30]})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Recurrence:
    def __init__(
        self,
        recurrence_type: RecurrenceType,
        interval: int = 1,
        end_date: Optional[date] = None,
    ):
        self.recurrence_type: RecurrenceType = recurrence_type
        self.interval: int = interval
        self.end_date: Optional[date] = end_date

    def __repr__(self) -> str:
        return f"Recurrence(type={self.recurrence_type.value}, interval={self.interval})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recurrence_type": self.recurrence_type.value,
            "interval": self.interval,
            "end_date": self.end_date.isoformat() if self.end_date else None,
        }


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

    def add_subtask(self, task: "Task") -> None:
        task.parent_task = self
        task.project = self.project
        self.subtasks.append(task)
        self.updated_at = datetime.now()

    def remove_subtask(self, task_id: str) -> Optional["Task"]:
        for i, subtask in enumerate(self.subtasks):
            if subtask.id == task_id:
                removed = self.subtasks.pop(i)
                removed.parent_task = None
                self.updated_at = datetime.now()
                return removed
        return None

    def add_label(self, label: Label) -> None:
        if label not in self.labels:
            self.labels.append(label)
            self.updated_at = datetime.now()

    def remove_label(self, label_id: str) -> Optional[Label]:
        for i, label in enumerate(self.labels):
            if label.id == label_id:
                removed = self.labels.pop(i)
                self.updated_at = datetime.now()
                return removed
        return None

    def add_comment(self, comment: Comment) -> None:
        self.comments.append(comment)
        self.updated_at = datetime.now()

    def remove_comment(self, comment_id: str) -> Optional[Comment]:
        for i, comment in enumerate(self.comments):
            if comment.id == comment_id:
                removed = self.comments.pop(i)
                self.updated_at = datetime.now()
                return removed
        return None

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

    def get_all_subtasks(self) -> List["Task"]:
        all_subtasks = []
        for subtask in self.subtasks:
            all_subtasks.append(subtask)
            all_subtasks.extend(subtask.get_all_subtasks())
        return all_subtasks

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
            "project_id": self.project.id if self.project else None,
            "section_id": self.section.id if self.section else None,
            "parent_task_id": self.parent_task.id if self.parent_task else None,
            "subtasks": [t.to_dict() for t in self.subtasks],
            "labels": [l.to_dict() for l in self.labels],
            "comments": [c.to_dict() for c in self.comments],
            "recurrence": self.recurrence.to_dict() if self.recurrence else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "order": self.order,
        }


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
        task.order = len(self.tasks)
        self.tasks.append(task)
        self.updated_at = datetime.now()

    def remove_task(self, task_id: str) -> Optional[Task]:
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                removed = self.tasks.pop(i)
                removed.section = None
                self.updated_at = datetime.now()
                return removed
        return None

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        return [t for t in self.tasks if t.status == status]

    def get_pending_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED)]

    def rename(self, new_name: str) -> None:
        self.name = new_name
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return f"Section(name={self.name}, tasks={len(self.tasks)})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "project_id": self.project.id if self.project else None,
            "tasks": [t.to_dict() for t in self.tasks],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "order": self.order,
        }


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
        self.order: int = 0

    def add_task(self, task: Task) -> None:
        task.project = self
        task.order = len(self.tasks)
        self.tasks.append(task)
        self.updated_at = datetime.now()

    def remove_task(self, task_id: str) -> Optional[Task]:
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                removed = self.tasks.pop(i)
                removed.project = None
                self.updated_at = datetime.now()
                return removed
        return None

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        for task in self.tasks:
            if task.id == task_id:
                return task
        for section in self.sections:
            for task in section.tasks:
                if task.id == task_id:
                    return task
        return None

    def add_section(self, section: Section) -> None:
        section.project = self
        section.order = len(self.sections)
        self.sections.append(section)
        self.updated_at = datetime.now()

    def remove_section(self, section_id: str) -> Optional[Section]:
        for i, section in enumerate(self.sections):
            if section.id == section_id:
                removed = self.sections.pop(i)
                removed.project = None
                self.updated_at = datetime.now()
                return removed
        return None

    def get_section_by_id(self, section_id: str) -> Optional[Section]:
        for section in self.sections:
            if section.id == section_id:
                return section
        return None

    def add_label(self, label: Label) -> None:
        if label not in self.labels:
            self.labels.append(label)
            self.updated_at = datetime.now()

    def remove_label(self, label_id: str) -> Optional[Label]:
        for i, label in enumerate(self.labels):
            if label.id == label_id:
                removed = self.labels.pop(i)
                self.updated_at = datetime.now()
                return removed
        return None

    def get_all_tasks(self) -> List[Task]:
        all_tasks = list(self.tasks)
        for section in self.sections:
            all_tasks.extend(section.tasks)
        return all_tasks

    def get_tasks_by_priority(self, priority: Priority) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.priority == priority]

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.status == status]

    def get_overdue_tasks(self) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.is_overdue()]

    def get_tasks_due_today(self) -> List[Task]:
        today = date.today()
        return [
            t for t in self.get_all_tasks()
            if t.due_date == today and t.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED)
        ]

    def get_completed_tasks(self) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.is_completed()]

    def get_pending_tasks(self) -> List[Task]:
        return [
            t for t in self.get_all_tasks()
            if t.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED)
        ]

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

    def archive(self) -> None:
        self.is_archived = True
        self.updated_at = datetime.now()

    def unarchive(self) -> None:
        self.is_archived = False
        self.updated_at = datetime.now()

    def toggle_favorite(self) -> None:
        self.is_favorite = not self.is_favorite
        self.updated_at = datetime.now()

    def get_completion_percentage(self) -> float:
        all_tasks = self.get_all_tasks()
        if not all_tasks:
            return 0.0
        completed = sum(1 for t in all_tasks if t.is_completed())
        return (completed / len(all_tasks)) * 100

    def __repr__(self) -> str:
        return f"Project(name={self.name}, tasks={len(self.get_all_tasks())})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "is_favorite": self.is_favorite,
            "is_archived": self.is_archived,
            "tasks": [t.to_dict() for t in self.tasks],
            "sections": [s.to_dict() for s in self.sections],
            "labels": [l.to_dict() for l in self.labels],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "order": self.order,
        }


class Filter:
    def __init__(self, name: str, query: str, color: Optional[str] = None):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.query: str = query
        self.color: Optional[str] = color
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

    def update(
        self,
        name: Optional[str] = None,
        query: Optional[str] = None,
        color: Optional[str] = None,
    ) -> None:
        if name is not None:
            self.name = name
        if query is not None:
            self.query = query
        if color is not None:
            self.color = color
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return f"Filter(name={self.name}, query={self.query})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "query": self.query,
            "color": self.color,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class User:
    def __init__(self, username: str, email: str, full_name: Optional[str] = None):
        self.id: str = str(uuid.uuid4())
        self.username: str = username
        self.email: str = email
        self.full_name: Optional[str] = full_name
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

    def update(
        self,
        username: Optional[str] = None,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> None:
        if username is not None:
            self.username = username
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
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Workspace:
    def __init__(self, name: str, owner: User):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.owner: User = owner
        self.projects: List[Project] = []
        self.labels: List[Label] = []
        self.filters: List[Filter] = []
        self.members: List[User] = [owner]
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

    def add_project(self, project: Project) -> None:
        project.order = len(self.projects)
        self.projects.append(project)
        self.updated_at = datetime.now()

    def remove_project(self, project_id: str) -> Optional[Project]:
        for i, project in enumerate(self.projects):
            if project.id == project_id:
                removed = self.projects.pop(i)
                self.updated_at = datetime.now()
                return removed
        return None

    def get_project_by_id(self, project_id: str) -> Optional[Project]:
        for project in self.projects:
            if project.id == project_id:
                return project
        return None

    def get_project_by_name(self, name: str) -> Optional[Project]:
        for project in self.projects:
            if project.name == name:
                return project
        return None

    def get_active_projects(self) -> List[Project]:
        return [p for p in self.projects if not p.is_archived]

    def get_archived_projects(self) -> List[Project]:
        return [p for p in self.projects if p.is_archived]

    def get_favorite_projects(self) -> List[Project]:
        return [p for p in self.projects if p.is_favorite]

    def add_label(self, label: Label) -> None:
        if label not in self.labels:
            self.labels.append(label)
            self.updated_at = datetime.now()

    def remove_label(self, label_id: str) -> Optional[Label]:
        for i, label in enumerate(self.labels):
            if label.id == label_id:
                removed = self.labels.pop(i)
                self.updated_at = datetime.now()
                return removed
        return None

    def get_label_by_id(self, label_id: str) -> Optional[Label]:
        for label in self.labels:
            if label.id == label_id:
                return label
        return None

    def get_label_by_name(self, name: str) -> Optional[Label]:
        for label in self.labels:
            if label.name == name:
                return label
        return None

    def add_filter(self, filter_obj: Filter) -> None:
        self.filters.append(filter_obj)
        self.updated_at = datetime.now()

    def remove_filter(self, filter_id: str) -> Optional[Filter]:
        for i, f in enumerate(self.filters):
            if f.id == filter_id:
                removed = self.filters.pop(i)
                self.updated_at = datetime.now()
                return removed
        return None

    def get_filter_by_id(self, filter_id: str) -> Optional[Filter]:
        for f in self.filters:
            if f.id == filter_id:
                return f
        return None

    def add_member(self, user: User) -> None:
        if user not in self.members:
            self.members.append(user)
            self.updated_at = datetime.now()

    def remove_member(self, user_id: str) -> Optional[User]:
        if self.owner.id == user_id:
            raise ValueError("Cannot remove the owner from the workspace.")
        for i, member in enumerate(self.members):
            if member.id == user_id:
                removed = self.members.pop(i)
                self.updated_at = datetime.now()
                return removed
        return None

    def get_all_tasks(self) -> List[Task]:
        all_tasks = []
        for project in self.projects:
            all_tasks.extend(project.get_all_tasks())
        return all_tasks

    def get_tasks_due_today(self) -> List[Task]:
        today = date.today()
        return [
            t for t in self.get_all_tasks()
            if t.due_date == today and t.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED)
        ]

    def get_overdue_tasks(self) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.is_overdue()]

    def get_tasks_by_label(self, label_id: str) -> List[Task]:
        return [
            t for t in self.get_all_tasks()
            if any(l.id == label_id for l in t.labels)
        ]

    def get_tasks_by_priority(self, priority: Priority) -> List[Task]:
        return [t for t in self.get_all_tasks() if t.priority == priority]

    def search_tasks(self, query: str) -> List[Task]:
        query_lower = query.lower()
        results = []
        for task in self.get_all_tasks():
            if query_lower in task.title.lower():
                results.append(task)
            elif task.description and query_lower in task.description.lower():
                results.append(task)
        return results

    def rename(self, new_name: str) -> None:
        self.name = new_name
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return f"Workspace(name={self.name}, owner={self.owner.username}, projects={len(self.projects)})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "owner": self.owner.to_dict(),
            "projects": [p.to_dict() for p in self.projects],
            "labels": [l.to_dict() for l in self.labels],
            "filters": [f.to_dict() for f in self.filters],
            "members": [m.to_dict() for m in self.members],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Planty:
    def __init__(self):
        self.workspaces: List[Workspace] = []
        self.users: List[User] = []

    def create_user(self, username: str, email: str, full_name: Optional[str] = None) -> User:
        for user in self.users:
            if user.email == email:
                raise ValueError(f"User with email '{email}' already exists.")
            if user.username == username:
                raise ValueError(f"User with username '{username}' already exists.")
        user = User(username=username, email=email, full_name=full_name)
        self.users.append(user)
        return user

    def get_user_by_id(self, user_id: str) -> Optional[User]:
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

    def create_workspace(self, name: str, owner: User) -> Workspace:
        workspace = Workspace(name=name, owner=owner)
        self.workspaces.append(workspace)
        return workspace

    def get_workspace_by_id(self, workspace_id: str) -> Optional[Workspace]:
        for workspace in self.workspaces:
            if workspace.id == workspace_id:
                return workspace
        return None

    def get_workspaces_for_user(self, user_id: str) -> List[Workspace]:
        return [
            w for w in self.workspaces
            if any(m.id == user_id for m in w.members)
        ]

    def create_project(
        self,
        workspace: Workspace,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        is_favorite: bool = False,
    ) -> Project:
        project = Project(
            name=name,
            description=description,
            color=color,
            is_favorite=is_favorite,
        )
        workspace.add_project(project)
        return project

    def create_section(self, project: Project, name: str) -> Section:
        section = Section(name=name, project=project)
        project.add_section(section)
        return section

    def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        due_date: Optional[date] = None,
        priority: Priority = Priority.MEDIUM,
        project: Optional[Project] = None,
        section: Optional[Section] = None,
        parent_task: Optional[Task] = None,
    ) -> Task:
        task = Task(
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            project=project,
            section=section,
            parent_task=parent_task,
        )
        if section is not None:
            section.add_task(task)
        elif project is not None:
            project.add_task(task)
        if parent_task is not None:
            parent_task.add_subtask(task)
        return task

    def create_label(
        self,
        name: str,
        color: Optional[str] = None,
        workspace: Optional[Workspace] = None,
    ) -> Label:
        label = Label(name=name, color=color)
        if workspace is not None:
            workspace.add_label(label)
        return label

    def create_filter(
        self,
        name: str,
        query: str,
        color: Optional[str] = None,
        workspace: Optional[Workspace] = None,
    ) -> Filter:
        filter_obj = Filter(name=name, query=query, color=color)
        if workspace is not None:
            workspace.add_filter(filter_obj)
        return filter_obj

    def delete_user(self, user_id: str) -> Optional[User]:
        for i, user in enumerate(self.users):
            if user.id == user_id:
                return self.users.pop(i)
        return None

    def delete_workspace(self, workspace_id: str) -> Optional[Workspace]:
        for i, workspace in enumerate(self.workspaces):
            if workspace.id == workspace_id:
                return self.workspaces.pop(i)
        return None

    def __repr__(self) -> str:
        return f"Planty(users={len(self.users)}, workspaces={len(self.workspaces)})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "users": [u.to_dict() for u in self.users],
            "workspaces": [w.to_dict() for w in self.workspaces],
        }