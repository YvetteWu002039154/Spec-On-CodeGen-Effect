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
        return f"Label(name={self.name!r}, color={self.color!r})"


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
        return f"Comment(author={self.author!r}, content={self.content!r})"


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
        self.assignee: Optional[str] = None
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

    def set_due_date(self, due_date: Optional[date]) -> None:
        self.due_date = due_date
        self.updated_at = datetime.now()

    def set_priority(self, priority: Priority) -> None:
        self.priority = priority
        self.updated_at = datetime.now()

    def assign(self, assignee: str) -> None:
        self.assignee = assignee
        self.updated_at = datetime.now()

    def is_overdue(self) -> bool:
        if self.due_date and self.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED):
            return date.today() > self.due_date
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
        return f"Task(title={self.title!r}, status={self.status.value}, priority={self.priority.name})"


class Section:
    def __init__(self, name: str, project: Optional["Project"] = None):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.project: Optional["Project"] = project
        self.tasks: List[Task] = []
        self.order: int = 0
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

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

    def get_active_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED)]

    def get_completed_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status == TaskStatus.DONE]

    def __repr__(self) -> str:
        return f"Section(name={self.name!r}, tasks={len(self.tasks)})"


class Project:
    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        owner: Optional[str] = None,
    ):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.description: Optional[str] = description
        self.color: Optional[str] = color
        self.owner: Optional[str] = owner
        self.members: List[str] = []
        self.tasks: List[Task] = []
        self.sections: List[Section] = []
        self.labels: List[Label] = []
        self.is_archived: bool = False
        self.is_favorite: bool = False
        self.order: int = 0
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

        if owner:
            self.members.append(owner)

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

    def get_task(self, task_id: str) -> Optional[Task]:
        for task in self.tasks:
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

    def get_section(self, section_id: str) -> Optional[Section]:
        for section in self.sections:
            if section.id == section_id:
                return section
        return None

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

    def archive(self) -> None:
        self.is_archived = True
        self.updated_at = datetime.now()

    def unarchive(self) -> None:
        self.is_archived = False
        self.updated_at = datetime.now()

    def toggle_favorite(self) -> None:
        self.is_favorite = not self.is_favorite
        self.updated_at = datetime.now()

    def get_active_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED)]

    def get_completed_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status == TaskStatus.DONE]

    def get_overdue_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.is_overdue()]

    def get_tasks_by_priority(self, priority: Priority) -> List[Task]:
        return [t for t in self.tasks if t.priority == priority]

    def get_tasks_by_label(self, label_id: str) -> List[Task]:
        return [t for t in self.tasks if any(l.id == label_id for l in t.labels)]

    def get_tasks_by_assignee(self, assignee: str) -> List[Task]:
        return [t for t in self.tasks if t.assignee == assignee]

    def get_all_tasks(self) -> List[Task]:
        all_tasks = list(self.tasks)
        for section in self.sections:
            all_tasks.extend(section.tasks)
        return all_tasks

    def __repr__(self) -> str:
        return f"Project(name={self.name!r}, tasks={len(self.tasks)}, sections={len(self.sections)})"


class Workspace:
    def __init__(self, name: str, owner: str):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.owner: str = owner
        self.members: List[str] = [owner]
        self.projects: List[Project] = []
        self.labels: List[Label] = []
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

    def add_member(self, member: str) -> None:
        if member not in self.members:
            self.members.append(member)
            self.updated_at = datetime.now()

    def remove_member(self, member: str) -> bool:
        if member in self.members and member != self.owner:
            self.members.remove(member)
            self.updated_at = datetime.now()
            return True
        return False

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

    def get_favorite_projects(self) -> List[Project]:
        return [p for p in self.projects if p.is_favorite]

    def get_active_projects(self) -> List[Project]:
        return [p for p in self.projects if not p.is_archived]

    def get_archived_projects(self) -> List[Project]:
        return [p for p in self.projects if p.is_archived]

    def search_tasks(self, query: str) -> List[Task]:
        results = []
        query_lower = query.lower()
        for project in self.projects:
            for task in project.get_all_tasks():
                if query_lower in task.title.lower() or (
                    task.description and query_lower in task.description.lower()
                ):
                    results.append(task)
        return results

    def get_all_overdue_tasks(self) -> List[Task]:
        overdue = []
        for project in self.projects:
            overdue.extend(project.get_overdue_tasks())
        return overdue

    def get_tasks_due_today(self) -> List[Task]:
        today = date.today()
        tasks_today = []
        for project in self.projects:
            for task in project.get_all_tasks():
                if task.due_date == today and task.status not in (TaskStatus.DONE, TaskStatus.ARCHIVED):
                    tasks_today.append(task)
        return tasks_today

    def __repr__(self) -> str:
        return f"Workspace(name={self.name!r}, owner={self.owner!r}, projects={len(self.projects)})"


class User:
    def __init__(self, username: str, email: str, full_name: Optional[str] = None):
        self.id: str = str(uuid.uuid4())
        self.username: str = username
        self.email: str = email
        self.full_name: Optional[str] = full_name
        self.workspaces: List[Workspace] = []
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

    def create_workspace(self, name: str) -> Workspace:
        workspace = Workspace(name=name, owner=self.username)
        self.workspaces.append(workspace)
        self.updated_at = datetime.now()
        return workspace

    def join_workspace(self, workspace: Workspace) -> None:
        if workspace not in self.workspaces:
            workspace.add_member(self.username)
            self.workspaces.append(workspace)
            self.updated_at = datetime.now()

    def leave_workspace(self, workspace_id: str) -> bool:
        for i, workspace in enumerate(self.workspaces):
            if workspace.id == workspace_id:
                workspace.remove_member(self.username)
                self.workspaces.pop(i)
                self.updated_at = datetime.now()
                return True
        return False

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        for workspace in self.workspaces:
            if workspace.id == workspace_id:
                return workspace
        return None

    def create_project(self, workspace: Workspace, name: str, description: Optional[str] = None, color: Optional[str] = None) -> Project:
        project = Project(name=name, description=description, color=color, owner=self.username)
        workspace.add_project(project)
        return project

    def create_task(
        self,
        title: str,
        project: Optional[Project] = None,
        section: Optional[Section] = None,
        description: Optional[str] = None,
        due_date: Optional[date] = None,
        priority: Priority = Priority.MEDIUM,
    ) -> Task:
        task = Task(
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            project=project,
            section=section,
        )
        task.assignee = self.username
        if section:
            section.add_task(task)
        elif project:
            project.add_task(task)
        return task

    def get_all_assigned_tasks(self) -> List[Task]:
        assigned = []
        for workspace in self.workspaces:
            for project in workspace.projects:
                for task in project.get_all_tasks():
                    if task.assignee == self.username:
                        assigned.append(task)
        return assigned

    def get_tasks_due_today(self) -> List[Task]:
        today = date.today()
        tasks_today = []
        for workspace in self.workspaces:
            for task in workspace.get_tasks_due_today():
                if task.assignee == self.username:
                    tasks_today.append(task)
        return tasks_today

    def __repr__(self) -> str:
        return f"User(username={self.username!r}, email={self.email!r})"


class PlantyApp:
    def __init__(self):
        self.users: List[User] = []
        self.created_at: datetime = datetime.now()

    def register_user(self, username: str, email: str, full_name: Optional[str] = None) -> User:
        for user in self.users:
            if user.username == username:
                raise ValueError(f"Username '{username}' already exists.")
            if user.email == email:
                raise ValueError(f"Email '{email}' already registered.")
        user = User(username=username, email=email, full_name=full_name)
        self.users.append(user)
        return user

    def get_user(self, username: str) -> Optional[User]:
        for user in self.users:
            if user.username == username:
                return user
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        for user in self.users:
            if user.email == email:
                return user
        return None

    def remove_user(self, username: str) -> bool:
        for i, user in enumerate(self.users):
            if user.username == username:
                self.users.pop(i)
                return True
        return False

    def create_label(self, name: str, color: Optional[str] = None) -> Label:
        return Label(name=name, color=color)

    def __repr__(self) -> str:
        return f"PlantyApp(users={len(self.users)})"