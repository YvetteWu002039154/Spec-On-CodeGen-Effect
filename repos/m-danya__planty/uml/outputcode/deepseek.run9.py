from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, cast
from typing import Literal as LiteralType

# Simple definitions for external types
NonNegativeInt = int
UUID = uuid.UUID
GUID = UUID

# Dummy async SQLAlchemy objects to make SqlAlchemyUnitOfWork instantiable
class AsyncSession:
    async def commit(self) -> None:
        pass
    async def rollback(self) -> None:
        pass

class async_sessionmaker:
    def __call__(self) -> AsyncSession:
        return AsyncSession()

# Base class for domain entities
class Entity:
    model_config = {"arbitrary_types_allowed": True}
    def __init__(self, **data: Any):
        for k, v in data.items():
            setattr(self, k, v)

# Domain classes

class Attachment(Entity):
    def __init__(
        self,
        *,
        added_at: Optional[datetime] = None,
        aes_iv_b64: str,
        aes_key_b64: str,
        id: Optional[UUID] = None,
        s3_file_key: str,
        task_id: UUID,
    ):
        super().__init__(
            added_at=added_at,
            aes_iv_b64=aes_iv_b64,
            aes_key_b64=aes_key_b64,
            id=id or uuid.uuid4(),
            s3_file_key=s3_file_key,
            task_id=task_id,
        )

class RecurrenceInfo(Entity):
    def __init__(
        self,
        *,
        flexible_mode: bool = False,
        period: int = 1,
        type: LiteralType["daily", "weekly", "monthly", "yearly"] = "daily",
    ):
        super().__init__(flexible_mode=flexible_mode, period=period, type=type)

class User(Entity):
    def __init__(
        self,
        *,
        email: str,
        added_at: Optional[datetime] = None,
        id: Optional[UUID] = None,
    ):
        super().__init__(added_at=added_at, email=email, id=id or uuid.uuid4())

class Task(Entity):
    def __init__(
        self,
        *,
        title: str,
        user_id: UUID,
        section_id: UUID,
        content: Optional[str] = None,
        description: Optional[str] = None,
        due_to: Optional[date] = None,
        is_completed: bool = False,
        is_archived: bool = False,
        recurrence: Optional[RecurrenceInfo] = None,
        added_at: Optional[datetime] = None,
        id: Optional[UUID] = None,
        attachments: Optional[List[Attachment]] = None,
    ):
        super().__init__(
            added_at=added_at or datetime.now(),
            attachments=attachments or [],
            content=content,
            description=description,
            due_to=due_to,
            id=id or uuid.uuid4(),
            is_archived=is_archived,
            is_completed=is_completed,
            recurrence=recurrence,
            section_id=section_id,
            title=title,
            user_id=user_id,
        )

    def add_attachment(self, attachment: Attachment) -> None:
        if self.attachments is None:
            self.attachments = []
        self.attachments.append(attachment)

    def archive(self) -> None:
        self.is_archived = True

    def unarchive(self) -> None:
        self.is_archived = False

    def toggle_archived(self) -> None:
        self.is_archived = not self.is_archived

    def mark_completed(self, auto_archive: bool = False) -> None:
        self.is_completed = True
        if auto_archive:
            self.archive()

    def toggle_completed(self, auto_archive: bool = False) -> None:
        if self.is_completed:
            self.is_completed = False
            self.unarchive()
        else:
            self.mark_completed(auto_archive=auto_archive)

    def remove_attachment(self, attachment: Attachment) -> None:
        if self.attachments:
            self.attachments = [a for a in self.attachments if a.id != attachment.id]

    def check_recurrence_due_date(self, values: Any) -> Any:
        # Placeholder logic; in production it would compute next due date
        return values

class Section(Entity):
    def __init__(
        self,
        *,
        title: str,
        user_id: UUID,
        parent_id: Optional[UUID] = None,
        has_subsections: bool = False,
        has_tasks: bool = False,
        added_at: Optional[datetime] = None,
        id: Optional[UUID] = None,
        subsections: Optional[List[Section]] = None,
        tasks: Optional[List[Task]] = None,
    ):
        super().__init__(
            added_at=added_at or datetime.now(),
            has_subsections=has_subsections,
            has_tasks=has_tasks,
            id=id or uuid.uuid4(),
            parent_id=parent_id,
            subsections=subsections or [],
            tasks=tasks or [],
            title=title,
            user_id=user_id,
        )

    @staticmethod
    def create_root_section(user_id: UUID) -> Section:
        return Section(title="Root", user_id=user_id, parent_id=None)

    def is_root(self) -> bool:
        return self.parent_id is None

    def check_flags(self) -> Section:
        self.has_subsections = len(self.subsections) > 0
        self.has_tasks = len(self.tasks) > 0
        return self

    def insert_subsection(self, subsection: Section, index: Optional[NonNegativeInt] = None) -> None:
        if subsection.id in [s.id for s in self.subsections]:
            raise ValueError("Subsection already present")
        self.subsections.insert(
            len(self.subsections) if index is None or index >= len(self.subsections) else index,
            subsection,
        )
        subsection.parent_id = self.id
        self.check_flags()

    def insert_task(self, task: Task, index: Optional[NonNegativeInt] = None) -> None:
        if task.id in [t.id for t in self.tasks]:
            raise ValueError("Task already present")
        self.tasks.insert(
            len(self.tasks) if index is None or index >= len(self.tasks) else index,
            task,
        )
        task.section_id = self.id
        self.check_flags()

    def remove_subsection(self, subsection: Section) -> Section:
        self.subsections = [s for s in self.subsections if s.id != subsection.id]
        subsection.parent_id = None
        self.check_flags()
        return subsection

    def remove_task(self, task: Task) -> Task:
        self.tasks = [t for t in self.tasks if t.id != task.id]
        task.section_id = self.id  # keep original, but removed from container
        self.check_flags()
        return task

    def move_section(
        self, section: Section, section_from: Section, section_to: Section,
        index: NonNegativeInt = 0,
    ) -> None:
        # Remove from current parent (should be section_from)
        section_from.remove_subsection(section)
        # Insert into new parent
        section_to.insert_subsection(section, index)

    def move_task(
        self, task_to_move: Task, section_from: Section, section_to: Section,
        index: NonNegativeInt = 0,
    ) -> None:
        section_from.remove_task(task_to_move)
        section_to.insert_task(task_to_move, index)

    def shuffle_tasks(self) -> None:
        # Simple shuffle: reverse list for demonstration
        self.tasks.reverse()

# Infrastructure model classes

class AccessTokenModel:
    pass

class AttachmentModel:
    def __init__(
        self,
        *,
        added_at: datetime,
        aes_iv_b64: str,
        aes_key_b64: str,
        id: UUID,
        index: int,
        s3_file_key: str,
        task_id: UUID,
        task: Optional[TaskModel] = None,
    ):
        self.added_at = added_at
        self.aes_iv_b64 = aes_iv_b64
        self.aes_key_b64 = aes_key_b64
        self.id = id
        self.index = index
        self.s3_file_key = s3_file_key
        self.task_id = task_id
        self.task = task

    @classmethod
    def from_entity(cls, attachment: Attachment, index: NonNegativeInt) -> AttachmentModel:
        return cls(
            added_at=attachment.added_at or datetime.now(),
            aes_iv_b64=attachment.aes_iv_b64,
            aes_key_b64=attachment.aes_key_b64,
            id=attachment.id,
            index=index,
            s3_file_key=attachment.s3_file_key,
            task_id=attachment.task_id,
        )

    def to_entity(self) -> Attachment:
        return Attachment(
            added_at=self.added_at,
            aes_iv_b64=self.aes_iv_b64,
            aes_key_b64=self.aes_key_b64,
            id=self.id,
            s3_file_key=self.s3_file_key,
            task_id=self.task_id,
        )

class SectionModel:
    def __init__(
        self,
        *,
        added_at: datetime,
        has_subsections: bool,
        has_tasks: bool,
        id: UUID,
        index: int,
        parent_id: Optional[UUID] = None,
        title: str,
        user_id: UUID,
        tasks: Optional[List[TaskModel]] = None,
        user: Optional[UserModel] = None,
    ):
        self.added_at = added_at
        self.has_subsections = has_subsections
        self.has_tasks = has_tasks
        self.id = id
        self.index = index
        self.parent_id = parent_id
        self.title = title
        self.user_id = user_id
        self.tasks = tasks or []
        self.user = user

    @classmethod
    def from_entity(cls, section: Section, index: NonNegativeInt) -> SectionModel:
        return cls(
            added_at=section.added_at or datetime.now(),
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
            id=section.id,
            index=index,
            parent_id=section.parent_id,
            title=section.title,
            user_id=section.user_id,
        )

    def to_entity(self, tasks: List[Task], subsections: List[Section]) -> Section:
        return Section(
            added_at=self.added_at,
            has_subsections=self.has_subsections,
            has_tasks=self.has_tasks,
            id=self.id,
            parent_id=self.parent_id,
            title=self.title,
            user_id=self.user_id,
            tasks=tasks,
            subsections=subsections,
        )

class TaskModel:
    def __init__(
        self,
        *,
        added_at: datetime,
        description: Optional[str] = None,
        due_to: Optional[date] = None,
        flexible_recurrence_mode: Optional[bool] = None,
        id: UUID,
        index: int,
        is_archived: bool,
        is_completed: bool,
        recurrence_period: Optional[int] = None,
        recurrence_type: Optional[str] = None,
        section_id: UUID,
        title: str,
        user_id: UUID,
        attachments: Optional[List[AttachmentModel]] = None,
        section: Optional[SectionModel] = None,
        user: Optional[UserModel] = None,
    ):
        self.added_at = added_at
        self.description = description
        self.due_to = due_to
        self.flexible_recurrence_mode = flexible_recurrence_mode
        self.id = id
        self.index = index
        self.is_archived = is_archived
        self.is_completed = is_completed
        self.recurrence_period = recurrence_period
        self.recurrence_type = recurrence_type
        self.section_id = section_id
        self.title = title
        self.user_id = user_id
        self.attachments = attachments or []
        self.section = section
        self.user = user

    @classmethod
    def from_entity(cls, task: Task, index: NonNegativeInt) -> TaskModel:
        rec = task.recurrence
        return cls(
            added_at=task.added_at or datetime.now(),
            description=task.description,
            due_to=task.due_to,
            flexible_recurrence_mode=rec.flexible_mode if rec else None,
            id=task.id,
            index=index,
            is_archived=task.is_archived,
            is_completed=task.is_completed,
            recurrence_period=rec.period if rec else None,
            recurrence_type=rec.type if rec else None,
            section_id=task.section_id,
            title=task.title,
            user_id=task.user_id,
        )

    def to_entity(self, attachments: List[Attachment]) -> Task:
        rec = None
        if self.recurrence_type is not None:
            rec = RecurrenceInfo(
                flexible_mode=self.flexible_recurrence_mode or False,
                period=self.recurrence_period or 1,
                type=self.recurrence_type,  # type: ignore
            )
        return Task(
            added_at=self.added_at,
            attachments=attachments,
            content=None,  # not directly in model
            description=self.description,
            due_to=self.due_to,
            id=self.id,
            is_archived=self.is_archived,
            is_completed=self.is_completed,
            recurrence=rec,
            section_id=self.section_id,
            title=self.title,
            user_id=self.user_id,
        )

class UserModel:
    def __init__(
        self,
        *,
        added_at: datetime,
        sections: Optional[List[SectionModel]] = None,
        tasks: Optional[List[TaskModel]] = None,
    ):
        self.added_at = added_at
        self.sections = sections or []
        self.tasks = tasks or []

    def to_entity(self) -> User:
        # Note: email missing from UserModel? The diagram shows no email, but User needs it.
        # We'll simulate with a placeholder
        return User(email="unknown@example.com", added_at=self.added_at)

# Application unit of work

class IUnitOfWork:
    def __init__(self):
        self.section_repo: SQLAlchemySectionRepository
        self.task_repo: SQLAlchemyTaskRepository
        self.user_repo: SQLAlchemyUserRepository

    def commit(self) -> None:
        raise NotImplementedError

    def rollback(self) -> None:
        raise NotImplementedError

class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(
        self,
        session_factory: async_sessionmaker,
    ):
        super().__init__()
        self.session_factory = session_factory
        self.session: AsyncSession = self.session_factory()
        self.section_repo = SQLAlchemySectionRepository(self.session)
        self.task_repo = SQLAlchemyTaskRepository(self.session)
        self.user_repo = SQLAlchemyUserRepository(self.session)

    def commit(self) -> None:
        asyncio.run(self.session.commit())

    def rollback(self) -> None:
        asyncio.run(self.session.rollback())

# In-memory storage for repositories

class UserStats:
    def __init__(self, user: User, task_count: int, section_count: int):
        self.user = user
        self.task_count = task_count
        self.section_count = section_count

class SQLAlchemySectionRepository:
    def __init__(self, session: AsyncSession):
        self._session = session
        # Simple key-value store for demonstration
        self._store: Dict[UUID, SectionModel] = {}

    def add(self, section: Section, index: NonNegativeInt) -> None:
        model = SectionModel.from_entity(section, index)
        self._store[model.id] = model

    def get(self, section_id: UUID, with_direct_subsections: bool = False) -> Section:
        model = self._store[section_id]
        tasks = []  # would load from task repo
        subsections = []  # would load
        return model.to_entity(tasks, subsections)

    def get_all_without_tasks(
        self, user_id: UUID, leaves_only: bool = False, as_tree: bool = False
    ) -> List[Section]:
        # Simplified
        return [m.to_entity([], []) for m in self._store.values() if m.user_id == user_id]

    def update(self, section: Section, index: Optional[NonNegativeInt] = None) -> None:
        if section.id in self._store:
            model = SectionModel.from_entity(section, index if index is not None else 0)
            self._store[section.id] = model
        else:
            raise KeyError("Section not found")

    def construct_sections_tree(
        self, section_models: List[SectionModel], return_flat: bool = False
    ) -> List[Section]:
        # Build tree from flat list; simplistic
        return [m.to_entity([], []) for m in section_models]

    def count_subsections(self, section_id: UUID) -> int:
        return len([m for m in self._store.values() if m.parent_id == section_id])

class SQLAlchemyTaskRepository:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._store: Dict[UUID, TaskModel] = {}
        self._attachments: Dict[UUID, List[AttachmentModel]] = {}

    def add(self, task: Task, index: NonNegativeInt) -> None:
        model = TaskModel.from_entity(task, index)
        self._store[model.id] = model
        if task.attachments:
            attachment_models = [AttachmentModel.from_entity(a, i) for i, a in enumerate(task.attachments)]
            self._attachments[model.id] = attachment_models

    def get(self, task_id: UUID) -> Task:
        model = self._store[task_id]
        attachments = [am.to_entity() for am in self._attachments.get(task_id, [])]
        return model.to_entity(attachments)

    def get_entity(self, task_model: TaskModel) -> Task:
        attachments = [am.to_entity() for am in self._attachments.get(task_model.id, [])]
        return task_model.to_entity(attachments)

    def get_entities(self, task_models: List[TaskModel]) -> List[Task]:
        return [self.get_entity(tm) for tm in task_models]

    def get_archived_tasks(self, user_id: UUID) -> List[Task]:
        return [self.get(tm.id) for tm in self._store.values() if tm.is_archived and tm.user_id == user_id]

    def get_overdue_tasks(self, user_id: UUID) -> List[Task]:
        today = date.today()
        return [
            self.get(tm.id) for tm in self._store.values()
            if tm.due_to and tm.due_to < today and tm.user_id == user_id
        ]

    def get_tasks_by_due_to(
        self, not_before: date, not_after: date, user_id: UUID
    ) -> List[Task]:
        return [
            self.get(tm.id) for tm in self._store.values()
            if tm.due_to and not_before <= tm.due_to <= not_after and tm.user_id == user_id
        ]

    def search(self, user_id: UUID, query: str) -> List[Task]:
        qlower = query.lower()
        return [
            self.get(tm.id) for tm in self._store.values()
            if tm.user_id == user_id and (
                qlower in tm.title.lower() or
                (tm.description and qlower in tm.description.lower())
            )
        ]

    def update_or_create(
        self, task: Task, index: Optional[NonNegativeInt] = None, must_exist: bool = False
    ) -> None:
        idx = index if index is not None else 0
        if task.id in self._store:
            if must_exist is False:
                raise KeyError("Task already exists")
            model = TaskModel.from_entity(task, idx)
            self._store[task.id] = model
        else:
            if must_exist:
                raise KeyError("Task not found")
            self.add(task, idx)

    def update_or_create_bulk(self, section_tasks: List[Task]) -> None:
        for task in section_tasks:
            self.update_or_create(task, index=None)

    def remove(self, task: Task) -> None:
        if task.id in self._store:
            del self._store[task.id]
            self._attachments.pop(task.id, None)

    def delete_attachment(self, attachment: Attachment) -> None:
        for task_id, attachments in self._attachments.items():
            self._attachments[task_id] = [a for a in attachments if a.id != attachment.id]

class SQLAlchemyUserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._store: Dict[UUID, User] = {}

    def get_all_users(self) -> List[UserStats]:
        # Simulate: return stats for each stored user
        return [UserStats(user=u, task_count=0, section_count=0) for u in self._store.values()]

    def verify_user(self, user_id: UUID) -> None:
        if user_id not in self._store:
            raise ValueError("User not found")