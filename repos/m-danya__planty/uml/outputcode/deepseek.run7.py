# planty/domain/__init__.py

# planty/domain/task.py

from datetime import datetime, date
from typing import Optional, Literal, Any, Union
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, NonNegativeInt


class Entity(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Attachment(Entity):
    added_at: Optional[datetime] = None
    aes_iv_b64: str
    aes_key_b64: str
    id: Optional[UUID] = None
    s3_file_key: str
    task_id: UUID


class RecurrenceInfo(Entity):
    flexible_mode: bool
    period: int  # NonNegativeInt?
    type: Literal['daily', 'weekly', 'monthly', 'yearly']  # allowed types


class Section(Entity):
    added_at: Optional[datetime] = None
    has_subsections: bool = False
    has_tasks: bool = False
    id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    subsections: list['Section'] = []
    tasks: list['Task'] = []
    title: str
    user_id: UUID

    def check_flags(self) -> 'Section':
        # presumably updates has_subsections/has_tasks based on contents
        self.has_subsections = len(self.subsections) > 0
        self.has_tasks = len(self.tasks) > 0
        return self

    @staticmethod
    def create_root_section(user_id: UUID) -> 'Section':
        return Section(
            title='Root',
            user_id=user_id,
            parent_id=None
        )

    def insert_subsection(self, subsection: 'Section', index: Optional[NonNegativeInt] = None) -> None:
        if index is not None:
            self.subsections.insert(index, subsection)
        else:
            self.subsections.append(subsection)
        subsection.parent_id = self.id
        self.check_flags()

    def insert_task(self, task: 'Task', index: Optional[NonNegativeInt] = None) -> None:
        if index is not None:
            self.tasks.insert(index, task)
        else:
            self.tasks.append(task)
        task.section_id = self.id
        self.check_flags()

    def is_root(self) -> bool:
        return self.parent_id is None

    def move_section(self, section: 'Section', section_from: 'Section', section_to: 'Section', index: NonNegativeInt) -> None:
        # Note: This static-like method appears weird; we'll just implement as a class method
        pass

    def move_task(self, task_to_move: 'Task', section_from: 'Section', section_to: 'Section', index: NonNegativeInt) -> None:
        pass

    def remove_subsection(self, subsection: 'Section') -> 'Section':
        self.subsections.remove(subsection)
        subsection.parent_id = None
        self.check_flags()
        return subsection

    def remove_task(self, task: 'Task') -> 'Task':
        self.tasks.remove(task)
        task.section_id = None  # or keep? assume we detach
        self.check_flags()
        return task

    def shuffle_tasks(self) -> None:
        import random
        random.shuffle(self.tasks)


class Task(Entity):
    added_at: Optional[datetime] = None
    attachments: Optional[list[Attachment]] = None
    content: Optional[str] = None
    description: Optional[str] = None
    due_to: Optional[date] = None
    id: Optional[UUID] = None
    is_archived: bool = False
    is_completed: bool = False
    recurrence: Optional[RecurrenceInfo] = None
    section_id: UUID
    title: str
    user_id: UUID

    def add_attachment(self, attachment: Attachment) -> None:
        if self.attachments is None:
            self.attachments = []
        attachment.task_id = self.id
        self.attachments.append(attachment)

    def archive(self) -> None:
        self.is_archived = True

    def check_recurrence_due_date(self, values: Any) -> Any:
        # placeholder for validation logic
        return values

    def mark_completed(self, auto_archive: bool = False) -> None:
        self.is_completed = True
        if auto_archive:
            self.archive()

    def remove_attachment(self, attachment: Attachment) -> None:
        if self.attachments:
            self.attachments.remove(attachment)

    def toggle_archived(self) -> None:
        self.is_archived = not self.is_archived

    def toggle_completed(self, auto_archive: bool = False) -> None:
        self.is_completed = not self.is_completed
        if auto_archive and self.is_completed:
            self.archive()

    def unarchive(self) -> None:
        self.is_archived = False


class User(Entity):
    added_at: Optional[datetime] = None
    email: str
    id: Optional[UUID] = None


# planty/infrastructure/__init__.py

# planty/infrastructure/models.py

from datetime import datetime, date
from typing import Optional, Literal, List, Sequence
from uuid import UUID, uuid4
from sqlalchemy import String, DateTime, Boolean, Integer, Date, ForeignKey, Text, TypeDecorator, CHAR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import sqlalchemy.types
from pydantic import NonNegativeInt

# We'll need to import domain classes later; use forward references
# For now, declare Base

class Base(DeclarativeBase):
    pass

# Custom GUID type, though we can use PG_UUID
class UUIDType(TypeDecorator):
    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return UUID(value)
        return value

# AccessTokenModel (empty in diagram, we'll just add an id and token)
class AccessTokenModel(Base):
    __tablename__ = 'access_tokens'

    id: Mapped[UUID] = mapped_column(PG_UUID, primary_key=True, default=uuid4)
    # other fields might exist but not specified; keep minimal
    token: Mapped[str] = mapped_column(String, nullable=False)
    # ...

class AttachmentModel(Base):
    __tablename__ = 'attachments'

    id: Mapped[UUID] = mapped_column(PG_UUID, primary_key=True, default=uuid4)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    aes_iv_b64: Mapped[str] = mapped_column(String)
    aes_key_b64: Mapped[str] = mapped_column(String)
    s3_file_key: Mapped[str] = mapped_column(String)
    index: Mapped[int] = mapped_column(Integer)
    task_id: Mapped[UUID] = mapped_column(PG_UUID, ForeignKey('tasks.id'))
    task: Mapped['TaskModel'] = relationship(back_populates='attachments')

    @classmethod
    def from_entity(cls, attachment: 'Attachment', index: NonNegativeInt) -> 'AttachmentModel':
        # Attachment is domain entity
        return cls(
            id=attachment.id,
            added_at=attachment.added_at,
            aes_iv_b64=attachment.aes_iv_b64,
            aes_key_b64=attachment.aes_key_b64,
            s3_file_key=attachment.s3_file_key,
            task_id=attachment.task_id,
            index=index
        )

    def to_entity(self) -> 'Attachment':
        from planty.domain.task import Attachment
        # We'll import domain inside to avoid circular imports on module level
        return Attachment(
            id=self.id,
            added_at=self.added_at,
            aes_iv_b64=self.aes_iv_b64,
            aes_key_b64=self.aes_key_b64,
            s3_file_key=self.s3_file_key,
            task_id=self.task_id
        )


class TaskModel(Base):
    __tablename__ = 'tasks'

    id: Mapped[UUID] = mapped_column(PG_UUID, primary_key=True, default=uuid4)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    due_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    flexible_recurrence_mode: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    recurrence_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recurrence_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    title: Mapped[str] = mapped_column(String)
    index: Mapped[int] = mapped_column(Integer)
    section_id: Mapped[UUID] = mapped_column(PG_UUID, ForeignKey('sections.id'))
    user_id: Mapped[UUID] = mapped_column(PG_UUID, ForeignKey('users.id'))

    section: Mapped['SectionModel'] = relationship(back_populates='tasks')
    user: Mapped['UserModel'] = relationship(back_populates='tasks')
    attachments: Mapped[List['AttachmentModel']] = relationship(back_populates='task')

    @classmethod
    def from_entity(cls, task: 'Task', index: NonNegativeInt) -> 'TaskModel':
        from planty.domain.task import Task, RecurrenceInfo
        rec = task.recurrence
        return cls(
            id=task.id,
            added_at=task.added_at,
            description=task.description,
            due_to=task.due_to,
            flexible_recurrence_mode=rec.flexible_mode if rec else None,
            recurrence_period=rec.period if rec else None,
            recurrence_type=rec.type if rec else None,
            is_archived=task.is_archived,
            is_completed=task.is_completed,
            title=task.title,
            index=index,
            section_id=task.section_id,
            user_id=task.user_id,
        )

    def to_entity(self, attachments: List['Attachment']) -> 'Task':
        from planty.domain.task import Task, RecurrenceInfo
        rec = None
        if self.recurrence_type is not None:
            rec = RecurrenceInfo(
                flexible_mode=self.flexible_recurrence_mode or False,
                period=self.recurrence_period or 1,
                type=self.recurrence_type
            )
        return Task(
            id=self.id,
            added_at=self.added_at,
            attachments=attachments if attachments else None,
            content=None,  # Not stored? not in model. Keep None.
            description=self.description,
            due_to=self.due_to,
            is_archived=self.is_archived,
            is_completed=self.is_completed,
            recurrence=rec,
            section_id=self.section_id,
            title=self.title,
            user_id=self.user_id,
        )


class SectionModel(Base):
    __tablename__ = 'sections'

    id: Mapped[UUID] = mapped_column(PG_UUID, primary_key=True, default=uuid4)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    has_subsections: Mapped[bool] = mapped_column(Boolean, default=False)
    has_tasks: Mapped[bool] = mapped_column(Boolean, default=False)
    title: Mapped[str] = mapped_column(String)
    index: Mapped[int] = mapped_column(Integer)
    parent_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID, ForeignKey('sections.id'), nullable=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID, ForeignKey('users.id'))

    user: Mapped['UserModel'] = relationship(back_populates='sections')
    tasks: Mapped[List['TaskModel']] = relationship(back_populates='section')
    # self-referential relationship for subsections/parent
    parent: Mapped[Optional['SectionModel']] = relationship(remote_side=[id], back_populates='subsections')
    subsections: Mapped[List['SectionModel']] = relationship(back_populates='parent')

    @classmethod
    def from_entity(cls, section: 'Section', index: NonNegativeInt) -> 'SectionModel':
        return cls(
            id=section.id,
            added_at=section.added_at,
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
            title=section.title,
            index=index,
            parent_id=section.parent_id,
            user_id=section.user_id,
        )

    def to_entity(self, tasks: List['Task'], subsections: List['Section']) -> 'Section':
        from planty.domain.task import Section
        return Section(
            id=self.id,
            added_at=self.added_at,
            has_subsections=self.has_subsections,
            has_tasks=self.has_tasks,
            title=self.title,
            parent_id=self.parent_id,
            user_id=self.user_id,
            subsections=subsections,
            tasks=tasks,
        )


class UserModel(Base):
    __tablename__ = 'users'

    id: Mapped[UUID] = mapped_column(PG_UUID, primary_key=True, default=uuid4)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    email: Mapped[str] = mapped_column(String, unique=True)

    sections: Mapped[List['SectionModel']] = relationship(back_populates='user')
    tasks: Mapped[List['TaskModel']] = relationship(back_populates='user')

    def to_entity(self) -> 'User':
        from planty.domain.task import User
        return User(
            id=self.id,
            added_at=self.added_at,
            email=self.email,
        )


# planty/infrastructure/repositories.py

from typing import Optional, List, Sequence
from uuid import UUID
from datetime import date, datetime
from pydantic import NonNegativeInt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from planty.domain.task import (
    Section,
    Task,
    Attachment,
    User,
    RecurrenceInfo,
)
from planty.infrastructure.models import (
    SectionModel,
    TaskModel,
    AttachmentModel,
    UserModel,
)


class SQLAlchemySectionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, section: Section, index: NonNegativeInt) -> None:
        model = SectionModel.from_entity(section, index)
        self.session.add(model)
        await self.session.flush()

    async def construct_sections_tree(
        self, section_models: list[SectionModel], return_flat: bool
    ) -> list[Section]:
        # Stub: convert models to entities with hierarchy
        return [
            Section(
                id=m.id,
                added_at=m.added_at,
                has_subsections=m.has_subsections,
                has_tasks=m.has_tasks,
                title=m.title,
                parent_id=m.parent_id,
                user_id=m.user_id,
            )
            for m in section_models
        ]

    async def count_subsections(self, section_id: UUID) -> int:
        stmt = select(SectionModel).where(SectionModel.parent_id == section_id)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def get(self, section_id: UUID, with_direct_subsections: bool = False) -> Section:
        stmt = select(SectionModel).where(SectionModel.id == section_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError("Section not found")
        if with_direct_subsections:
            # fetch subsections
            pass
        return model.to_entity([], [])  # simplified

    async def get_all_without_tasks(
        self, user_id: UUID, leaves_only: bool = False, as_tree: bool = False
    ) -> list[Section]:
        stmt = select(SectionModel).where(SectionModel.user_id == user_id)
        if leaves_only:
            stmt = stmt.where(SectionModel.has_tasks == False)  # naive
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [m.to_entity([], []) for m in models]

    async def update(self, section: Section, index: Optional[NonNegativeInt] = None) -> None:
        model = await self.session.get(SectionModel, section.id)
        if model:
            model.title = section.title
            model.has_subsections = section.has_subsections
            model.has_tasks = section.has_tasks
            if index is not None:
                model.index = index
            await self.session.flush()


class SQLAlchemyTaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, task: Task, index: NonNegativeInt) -> None:
        model = TaskModel.from_entity(task, index)
        self.session.add(model)
        await self.session.flush()

    async def delete_attachment(self, attachment: Attachment) -> None:
        model = await self.session.get(AttachmentModel, attachment.id)
        if model:
            await self.session.delete(model)
            await self.session.flush()

    async def get(self, task_id: UUID) -> Task:
        model = await self.session.get(TaskModel, task_id)
        if model is None:
            raise ValueError("Task not found")
        attachments = [AttachmentModel.to_entity(att) for att in model.attachments]
        return model.to_entity(attachments)

    async def get_archived_tasks(self, user_id: UUID) -> List[Task]:
        stmt = select(TaskModel).where(
            TaskModel.user_id == user_id,
            TaskModel.is_archived == True,
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        tasks = []
        for model in models:
            attachments = [AttachmentModel.to_entity(att) for att in model.attachments]
            tasks.append(model.to_entity(attachments))
        return tasks

    async def get_entities(self, task_models: Sequence[TaskModel]) -> list[Task]:
        tasks = []
        for m in task_models:
            attachments = [AttachmentModel.to_entity(a) for a in m.attachments]
            tasks.append(m.to_entity(attachments))
        return tasks

    async def get_entity(self, task_model: TaskModel) -> Task:
        attachments = [AttachmentModel.to_entity(a) for a in task_model.attachments]
        return task_model.to_entity(attachments)

    async def get_overdue_tasks(self, user_id: UUID) -> List[Task]:
        today = date.today()
        stmt = select(TaskModel).where(
            TaskModel.user_id == user_id,
            TaskModel.due_to < today,
            TaskModel.is_completed == False,
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self.get_entity(m) for m in models]  # simplified

    async def get_tasks_by_due_to(
        self, not_before: date, not_after: date, user_id: UUID
    ) -> List[Task]:
        stmt = select(TaskModel).where(
            TaskModel.user_id == user_id,
            TaskModel.due_to >= not_before,
            TaskModel.due_to <= not_after,
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self.get_entity(m) for m in models]

    async def remove(self, task: Task) -> None:
        model = await self.session.get(TaskModel, task.id)
        if model:
            await self.session.delete(model)
            await self.session.flush()

    async def search(self, user_id: UUID, query: str) -> List[Task]:
        stmt = select(TaskModel).where(
            TaskModel.user_id == user_id,
            TaskModel.title.ilike(f"%{query}%") | (TaskModel.description.ilike(f"%{query}%"))
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self.get_entity(m) for m in models]

    async def update_or_create(
        self, task: Task, index: Optional[NonNegativeInt] = None, must_exist: bool = False
    ) -> None:
        if task.id:
            model = await self.session.get(TaskModel, task.id)
            if model:
                new_model = TaskModel.from_entity(task, index if index is not None else model.index)
                # merge or update
                model.title = new_model.title
                model.description = new_model.description
                model.due_to = new_model.due_to
                model.flexible_recurrence_mode = new_model.flexible_recurrence_mode
                model.recurrence_period = new_model.recurrence_period
                model.recurrence_type = new_model.recurrence_type
                model.is_archived = new_model.is_archived
                model.is_completed = new_model.is_completed
                model.index = new_model.index
                await self.session.flush()
            elif must_exist:
                raise ValueError("Task not found")
            else:
                # create
                self.session.add(TaskModel.from_entity(task, index if index is not None else 0))
                await self.session.flush()
        else:
            # create new
            task.id = uuid4()
            self.session.add(TaskModel.from_entity(task, index if index is not None else 0))
            await self.session.flush()

    async def update_or_create_bulk(self, section_tasks: list[Task]) -> None:
        for task in section_tasks:
            await self.update_or_create(task, index=None, must_exist=False)


class SQLAlchemyUserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_users(self) -> list[User]:
        stmt = select(UserModel)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [m.to_entity() for m in models]

    async def verify_user(self, user_id: UUID) -> None:
        user = await self.session.get(UserModel, user_id)
        if user is None:
            raise ValueError("User not found")


# planty/application/__init__.py

# planty/application/uow.py

from abc import ABC, abstractmethod
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from planty.infrastructure.repositories import (
    SQLAlchemySectionRepository,
    SQLAlchemyTaskRepository,
    SQLAlchemyUserRepository,
)


class IUnitOfWork(ABC):
    section_repo: SQLAlchemySectionRepository
    task_repo: SQLAlchemyTaskRepository
    user_repo: SQLAlchemyUserRepository

    @abstractmethod
    async def commit(self) -> None:
        ...

    @abstractmethod
    async def rollback(self) -> None:
        ...


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self.session: Optional[AsyncSession] = None
        self.section_repo: Optional[SQLAlchemySectionRepository] = None
        self.task_repo: Optional[SQLAlchemyTaskRepository] = None
        self.user_repo: Optional[SQLAlchemyUserRepository] = None

    async def __aenter__(self):
        self.session = self.session_factory()
        self.section_repo = SQLAlchemySectionRepository(self.session)
        self.task_repo = SQLAlchemyTaskRepository(self.session)
        self.user_repo = SQLAlchemyUserRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()