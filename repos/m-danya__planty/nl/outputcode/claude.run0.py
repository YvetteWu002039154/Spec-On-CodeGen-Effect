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

    def update(self, content: str) -> None:
        self.content = content
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return f"Comment(content={self.content[:50]}, author={self.author})"

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
        project_id: Optional[str] = None,
        section_id: Optional[str] = None,
        parent_id: Optional[str] = None,
    ):
        self.id: str = str(uuid.uuid4())
        self.title: str = title
        self.description: Optional[str] = description
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
    def __init__(self, name: str, project_id: str, order: int = 0):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.project_id: str = project_id
        self.order: int = order
        self.tasks: List[Task] = []
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

    def add_task(self, task: Task) -> None:
        task.section_id = self.id
        task.project_id = self.project_id
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

    def rename(self, name: str) -> None:
        self.name = name
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return f"Section(name={self.name}, tasks={len(self.tasks)})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "project_id": self.project_id,
            "order": self.order,
            "tasks": [task.to_dict() for task in self.tasks],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Project:
    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        is_favorite: bool = False,
        parent_id: Optional[str] = None,
    ):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.description: Optional[str] = description
        self.color: Optional[str] = color
        self.is_favorite: bool = is_favorite
        self.is_archived: bool = False
        self.parent_id: Optional[str] = parent_id
        self.sections: List[Section] = []
        self.tasks: List[Task] = []
        self.sub_projects: List["Project"] = []
        self.labels: List[Label] = []
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.order: int = 0

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

    def get_section_by_name(self, name: str) -> Optional[Section]:
        for section in self.sections:
            if section.name == name:
                return section
        return None

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
        for section in self.sections:
            if section.remove_task(task_id):
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

    def add_sub_project(self, project: "Project") -> None:
        project.parent_id = self.id
        self.sub_projects.append(project)
        self.updated_at = datetime.now()

    def remove_sub_project(self, project_id: str) -> bool:
        for project in self.sub_projects:
            if project.id == project_id:
                self.sub_projects.remove(project)
                self.updated_at = datetime.now()
                return True
        return False

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
            "is_favorite": self.is_favorite,
            "is_archived": self.is_archived,
            "parent_id": self.parent_id,
            "sections": [section.to_dict() for section in self.sections],
            "tasks": [task.to_dict() for task in self.tasks],
            "sub_projects": [p.to_dict() for p in self.sub_projects],
            "labels": [label.to_dict() for label in self.labels],
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

    def remove_project(self, project_id: str) -> bool:
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

    def get_favorite_projects(self) -> List[Project]:
        return [p for p in self.projects if p.is_favorite]

    def get_archived_projects(self) -> List[Project]:
        return [p for p in self.projects if p.is_archived]

    def get_active_projects(self) -> List[Project]:
        return [p for p in self.projects if not p.is_archived]

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

    def add_filter(self, filter_obj: Filter) -> None:
        self.filters.append(filter_obj)
        self.updated_at = datetime.now()

    def remove_filter(self, filter_id: str) -> bool:
        for filter_obj in self.filters:
            if filter_obj.id == filter_id:
                self.filters.remove(filter_obj)
                self.updated_at = datetime.now()
                return True
        return False

    def get_filter(self, filter_id: str) -> Optional[Filter]:
        for filter_obj in self.filters:
            if filter_obj.id == filter_id:
                return filter_obj
        return None

    def add_member(self, user: User) -> None:
        if user not in self.members:
            self.members.append(user)
            self.updated_at = datetime.now()

    def remove_member(self, user_id: str) -> bool:
        for member in self.members:
            if member.id == user_id and member.id != self.owner.id:
                self.members.remove(member)
                self.updated_at = datetime.now()
                return True
        return False

    def get_all_tasks(self) -> List[Task]:
        all_tasks = []
        for project in self.projects:
            all_tasks.extend(project.get_all_tasks())
        return all_tasks

    def get_tasks_due_today(self) -> List[Task]:
        today = date.today()
        return [
            task
            for task in self.get_all_tasks()
            if task.due_date == today
            and task.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED)
        ]

    def get_tasks_due_this_week(self) -> List[Task]:
        today = date.today()
        from datetime import timedelta

        end_of_week = today + timedelta(days=7)
        return [
            task
            for task in self.get_all_tasks()
            if task.due_date
            and today <= task.due_date <= end_of_week
            and task.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED)
        ]

    def get_overdue_tasks(self) -> List[Task]:
        return [task for task in self.get_all_tasks() if task.is_overdue()]

    def search_tasks(self, query: str) -> List[Task]:
        query_lower = query.lower()
        results = []
        for task in self.get_all_tasks():
            if query_lower in task.title.lower() or (
                task.description and query_lower in task.description.lower()
            ):
                results.append(task)
        return results

    def get_tasks_by_label(self, label: Label) -> List[Task]:
        return [task for task in self.get_all_tasks() if label in task.labels]

    def get_tasks_by_priority(self, priority: Priority) -> List[Task]:
        return [task for task in self.get_all_tasks() if task.priority == priority]

    def rename(self, name: str) -> None:
        self.name = name
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return f"Workspace(name={self.name}, owner={self.owner.username}, projects={len(self.projects)})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "owner": self.owner.to_dict(),
            "projects": [project.to_dict() for project in self.projects],
            "labels": [label.to_dict() for label in self.labels],
            "filters": [f.to_dict() for f in self.filters],
            "members": [member.to_dict() for member in self.members],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Planty:
    def __init__(self):
        self.users: List[User] = []
        self.workspaces: List[Workspace] = []

    def create_user(
        self, username: str, email: str, full_name: Optional[str] = None
    ) -> User:
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

    def delete_user(self, user_id: str) -> bool:
        for user in self.users:
            if user.id == user_id:
                self.users.remove(user)
                return True
        return False

    def create_workspace(self, name: str, owner: User) -> Workspace:
        workspace = Workspace(name=name, owner=owner)
        self.workspaces.append(workspace)
        return workspace

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        for workspace in self.workspaces:
            if workspace.id == workspace_id:
                return workspace
        return None

    def get_workspaces_for_user(self, user_id: str) -> List[Workspace]:
        result = []
        for workspace in self.workspaces:
            for member in workspace.members:
                if member.id == user_id:
                    result.append(workspace)
                    break
        return result

    def delete_workspace(self, workspace_id: str) -> bool:
        for workspace in self.workspaces:
            if workspace.id == workspace_id:
                self.workspaces.remove(workspace)
                return True
        return False

    def create_project(
        self,
        workspace: Workspace,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        is_favorite: bool = False,
        parent_id: Optional[str] = None,
    ) -> Project:
        project = Project(
            name=name,
            description=description,
            color=color,
            is_favorite=is_favorite,
            parent_id=parent_id,
        )
        workspace.add_project(project)
        return project

    def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        due_date: Optional[date] = None,
        priority: Priority = Priority.MEDIUM,
        project: Optional[Project] = None,
        section: Optional[Section] = None,
    ) -> Task:
        project_id = project.id if project else None
        section_id = section.id if section else None
        task = Task(
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            project_id=project_id,
            section_id=section_id,
        )
        if section:
            section.add_task(task)
        elif project:
            project.add_task(task)
        return task

    def create_label(
        self,
        name: str,
        color: Optional[str] = None,
        workspace: Optional[Workspace] = None,
    ) -> Label:
        label = Label(name=name, color=color)
        if workspace:
            workspace.add_label(label)
        return label

    def create_section(
        self, name: str, project: Project, order: int = 0
    ) -> Section:
        section = Section(name=name, project_id=project.id, order=order)
        project.add_section(section)
        return section

    def create_filter(
        self,
        name: str,
        query: str,
        color: Optional[str] = None,
        workspace: Optional[Workspace] = None,
    ) -> Filter:
        filter_obj = Filter(name=name, query=query, color=color)
        if workspace:
            workspace.add_filter(filter_obj)
        return filter_obj

    def __repr__(self) -> str:
        return f"Planty(users={len(self.users)}, workspaces={len(self.workspaces)})"


def main():
    app = Planty()

    # Create users
    alice = app.create_user("alice", "alice@example.com", "Alice Smith")
    bob = app.create_user("bob", "bob@example.com", "Bob Jones")
    print(f"Created users: {alice}, {bob}")

    # Create workspace
    workspace = app.create_workspace("My Workspace", alice)
    workspace.add_member(bob)
    print(f"Created workspace: {workspace}")

    # Create labels
    urgent_label = app.create_label("urgent", "#ff0000", workspace)
    work_label = app.create_label("work", "#0000ff", workspace)
    print(f"Created labels: {urgent_label}, {work_label}")

    # Create project with sections
    project = app.create_project(workspace, "Home Renovation", description="Track renovation tasks", color="#green", is_favorite=True)
    backlog = app.create_section("Backlog", project)
    in_progress_section = app.create_section("In Progress", project)
    done_section = app.create_section("Done", project)
    print(f"Created project: {project}")

    # Create tasks
    task1 = app.create_task(
        "Buy paint",
        description="Get exterior paint from hardware store",
        due_date=date(2026, 7, 10),
        priority=Priority.HIGH,
        section=backlog,
    )
    task1.add_label(work_label)

    task2 = app.create_task(
        "Fix roof leak",
        description="Call contractor for inspection",
        due_date=date(2026, 6, 30),
        priority=Priority.URGENT,
        section=in_progress_section,
    )
    task2.add_label(urgent_label)
    task2.start()

    task3 = app.create_task("Clear gutters", priority=Priority.LOW, section=done_section)
    task3.complete()

    # Add subtask
    subtask = app.create_task("Research contractor options", project=project)
    task2.add_subtask(subtask)

    # Add comment
    comment = Comment("Called 3 contractors, waiting for quotes", author="alice")
    task2.add_comment(comment)

    # Add recurrence to task1
    task1.set_recurrence(Recurrence(RecurrenceType.WEEKLY, interval=2))

    # Create a filter
    app.create_filter("Urgent tasks", "priority:urgent", color="#ff0000", workspace=workspace)

    # Print project summary
    print(f"\nProject: {project.name}")
    print(f"  Completion: {project.get_completion_percentage():.1f}%")
    print(f"  All tasks: {[t.title for t in project.get_all_tasks()]}")
    print(f"  Overdue tasks: {[t.title for t in project.get_overdue_tasks()]}")

    # Workspace queries
    print(f"\nWorkspace: {workspace.name}")
    print(f"  Tasks due today: {[t.title for t in workspace.get_tasks_due_today()]}")
    print(f"  Overdue tasks: {[t.title for t in workspace.get_overdue_tasks()]}")
    print(f"  Search 'contractor': {[t.title for t in workspace.search_tasks('contractor')]}")
    print(f"  Urgent priority tasks: {[t.title for t in workspace.get_tasks_by_priority(Priority.URGENT)]}")
    print(f"  Tasks with 'urgent' label: {[t.title for t in workspace.get_tasks_by_label(urgent_label)]}")

    # Task status checks
    print(f"\nTask '{task2.title}':")
    print(f"  Status: {task2.status.value}")
    print(f"  Overdue: {task2.is_overdue()}")
    print(f"  Subtask completion: {task2.get_completion_percentage():.1f}%")
    print(f"  Comments: {task2.comments}")
    print(f"  Recurrence on task1: {task1.recurrence}")

    # Archive project
    project.archive()
    print(f"\nArchived projects: {[p.name for p in workspace.get_archived_projects()]}")
    print(f"Active projects: {[p.name for p in workspace.get_active_projects()]}")

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()