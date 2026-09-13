from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import DateTime, ForeignKey, Integer, String, Boolean, Date, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# -------------------------------------------------------------------
# Define common types
# -------------------------------------------------------------------
NonNegativeInt = int          # could be Annotated[int, Field(ge=0)] but simple alias
GUID = UUID                  # used in SectionModel.parent_id

# -------------------------------------------------------------------
# Domain entities (Pydantic models)
# -------------------------------------------------------------------
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
    period: int
    type: Literal['daily', 'weekly', 'monthly', 'yearly']


class Section(Entity):
    added_at: Optional[datetime] = None
    has_subsections: bool = False
    has_tasks: bool = False
    id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    subsections: List['Section'] = []
    tasks: List['Task'] = []
    title: str
    user_id: UUID

    def check_flags(self) -> 'Section':
        # update flags according to actual content
        self.has_subsections = len(self.subsections) > 0
        self.has_tasks = len(self.tasks) > 0
        return self

    @classmethod
    def create_root_section(cls, user_id: UUID) -> 'Section':
        return cls(title='Root', user_id=user_id, parent_id=None, has_subsections=False, has_tasks=False)

    def insert_subsection(self, subsection: 'Section', index: Optional[NonNegativeInt] = None) -> None:
        if subsection.parent_id is not None and subsection.parent_id != self.id:
            raise ValueError("Subsection already belongs to another parent")
        subsection.parent_id = self.id
        if index is not None:
            self.subsections.insert(index, subsection)
        else:
            self.subsections.append(subsection)
        self.check_flags()

    def insert_task(self, task: Task, index: Optional[NonNegativeInt] = None) -> None:
        if task.section_id != self.id:
            raise ValueError("Task section_id mismatch")
        if index is not None:
            self.tasks.insert(index, task)
        else:
            self.tasks.append(task)
        self.check_flags()

    def is_root(self) -> bool:
        return self.parent_id is None

    @staticmethod
    def move_section(section: 'Section', section_from: 'Section', section_to: 'Section', index: NonNegativeInt) -> None:
        section_to.insert_subsection(section_from.remove_subsection(section), index)

    @staticmethod
    def move_task(task_to_move: Task, section_from: 'Section', section_to: 'Section', index: NonNegativeInt) -> None:
        section_to.insert_task(section_from.remove_task(task_to_move), index)

    def remove_subsection(self, subsection: 'Section') -> 'Section':
        self.subsections = [s for s in self.subsections if s.id != subsection.id]
        subsection.parent_id = None
        self.check_flags()
        return subsection

    def remove_task(self, task: Task) -> Task:
        self.tasks = [t for t in self.tasks if t.id != task.id]
        self.check_flags()
        return task

    def shuffle_tasks(self) -> None:
        # simple random shuffle – real implementation may use a seed
        import random
        random.shuffle(self.tasks)


class Task(Entity):
    added_at: Optional[datetime] = None
    attachments: Optional[List[Attachment]] = None
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
        self.attachments.append(attachment)

    def archive(self) -> None:
        self.is_archived = True

    @field_validator('due_to')
    @classmethod
    def check_recurrence_due_date(cls, v: Any, info) -> Any:
        # Pydantic v2 style validator: can access 'data' for recurrence
        return v   # stub – actual logic would adjust due date based on recurrence

    def mark_completed(self, auto_archive: bool) -> None:
        self.is_completed = True
        if auto_archive:
            self.archive()

    def remove_attachment(self, attachment: Attachment) -> None:
        if self.attachments:
            self.attachments = [a for a in self.attachments if a.id != attachment.id]

    def toggle_archived(self) -> None:
        self.is_archived = not self.is_archived

    def toggle_completed(self, auto_archive: bool) -> None:
        if self.is_completed:
            self.is_completed = False
        else:
            self.mark_completed(auto_archive)

    def unarchive(self) -> None:
        self.is_archived = False


class User(Entity):
    added_at: Optional[datetime] = None
    email: str
    id: Optional[UUID] = None


# -------------------------------------------------------------------
# SQLAlchemy ORM base and models
# -------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


class AccessTokenModel(Base):
    __tablename__ = 'access_tokens'
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # minimal implementation – no other attributes specified in diagram


class AttachmentModel(Base):
    __tablename__ = 'attachments'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(ForeignKey('tasks.id'))
    index: Mapped[int] = mapped_column(Integer)
    added_at: Mapped[datetime] = mapped_column(DateTime)
    aes_iv_b64: Mapped[str]
    aes_key_b64: Mapped[str]
    s3_file_key: Mapped[str]

    task: Mapped[TaskModel] = relationship(back_populates='attachments')

    @classmethod
    def from_entity(cls, attachment: Attachment, index: NonNegativeInt) -> 'AttachmentModel':
        return cls(
            id=attachment.id or uuid4(),
            task_id=attachment.task_id,
            index=index,
            added_at=attachment.added_at or datetime.utcnow(),
            aes_iv_b64=attachment.aes_iv_b64,
            aes_key_b64=attachment.aes_key_b64,
            s3_file_key=attachment.s3_file_key,
        )

    def to_entity(self) -> Attachment:
        return Attachment(
            id=self.id,
            task_id=self.task_id,
            added_at=self.added_at,
            aes_iv_b64=self.aes_iv_b64,
            aes_key_b64=self.aes_key_b64,
            s3_file_key=self.s3_file_key,
        )


class SectionModel(Base):
    __tablename__ = 'sections'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    parent_id: Mapped[Optional[GUID]] = mapped_column(ForeignKey('sections.id'), nullable=True)
    index: Mapped[int] = mapped_column(Integer)
    title: Mapped[str]
    added_at: Mapped[datetime] = mapped_column(DateTime)
    has_subsections: Mapped[bool] = mapped_column(Boolean, default=False)
    has_tasks: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[UserModel] = relationship(back_populates='sections')
    tasks: Mapped[List[TaskModel]] = relationship(back_populates='section')
    # self-referential relationship for subsections can be added, but we store flat lists

    @classmethod
    def from_entity(cls, section: Section, index: NonNegativeInt) -> 'SectionModel':
        return cls(
            id=section.id or uuid4(),
            user_id=section.user_id,
            parent_id=section.parent_id,
            index=index,
            title=section.title,
            added_at=section.added_at or datetime.utcnow(),
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
        )

    def to_entity(self, tasks: List[Task], subsections: List[Section]) -> Section:
        return Section(
            id=self.id,
            user_id=self.user_id,
            parent_id=self.parent_id,
            title=self.title,
            added_at=self.added_at,
            has_subsections=self.has_subsections,
            has_tasks=self.has_tasks,
            subsections=subsections,
            tasks=tasks,
        )


class TaskModel(Base):
    __tablename__ = 'tasks'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    section_id: Mapped[UUID] = mapped_column(ForeignKey('sections.id'))
    index: Mapped[int] = mapped_column(Integer)
    title: Mapped[str]
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    recurrence_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    flexible_recurrence_mode: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    user: Mapped[UserModel] = relationship(back_populates='tasks')
    section: Mapped[SectionModel] = relationship(back_populates='tasks')
    attachments: Mapped[List[AttachmentModel]] = relationship(back_populates='task')

    @classmethod
    def from_entity(cls, task: Task, index: NonNegativeInt) -> 'TaskModel':
        recurrence_type = task.recurrence.type if task.recurrence else None
        recurrence_period = task.recurrence.period if task.recurrence else None
        flexible_recurrence_mode = task.recurrence.flexible_mode if task.recurrence else None
        return cls(
            id=task.id or uuid4(),
            user_id=task.user_id,
            section_id=task.section_id,
            index=index,
            title=task.title,
            description=task.description,
            due_to=task.due_to,
            added_at=task.added_at or datetime.utcnow(),
            is_completed=task.is_completed,
            is_archived=task.is_archived,
            recurrence_type=recurrence_type,
            recurrence_period=recurrence_period,
            flexible_recurrence_mode=flexible_recurrence_mode,
        )

    def to_entity(self, attachments: List[Attachment]) -> Task:
        recurrence = None
        if self.recurrence_type:
            recurrence = RecurrenceInfo(
                type=self.recurrence_type,
                period=self.recurrence_period or 0,
                flexible_mode=self.flexible_recurrence_mode or False,
            )
        return Task(
            id=self.id,
            user_id=self.user_id,
            section_id=self.section_id,
            title=self.title,
            description=self.description,
            due_to=self.due_to,
            added_at=self.added_at,
            is_completed=self.is_completed,
            is_archived=self.is_archived,
            recurrence=recurrence,
            attachments=attachments,
        )


class UserModel(Base):
    __tablename__ = 'users'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    added_at: Mapped[datetime] = mapped_column(DateTime)

    sections: Mapped[List[SectionModel]] = relationship(back_populates='user')
    tasks: Mapped[List[TaskModel]] = relationship(back_populates='user')

    def to_entity(self) -> User:
        # email is not stored in this simple model – we could add a field
        return User(
            id=self.id,
            added_at=self.added_at,
            email='',  # placeholder, as email is not mapped in UserModel in diagram
        )


# -------------------------------------------------------------------
# Repositories
# -------------------------------------------------------------------
class SQLAlchemySectionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, section: Section, index: NonNegativeInt) -> None:
        model = SectionModel.from_entity(section, index)
        self.session.add(model)
        await self.session.flush()

    async def construct_sections_tree(
        self, section_models: List[SectionModel], return_flat: bool
    ) -> List[Section]:
        # simple mapping without tree building – real implementation would nest
        sections = []
        for sm in section_models:
            sections.append(sm.to_entity([], []))
        return sections

    async def count_subsections(self, section_id: UUID) -> int:
        # placeholder
        return 0

    async def get(self, section_id: UUID, with_direct_subsections: bool) -> Section:
        # stub
        return Section(id=section_id, title='stub', user_id=UUID('00000000-0000-0000-0000-000000000000'))

    async def get_all_without_tasks(
        self, user_id: UUID, leaves_only: bool, as_tree: bool
    ) -> List[Section]:
        return []

    async def update(self, section: Section, index: Optional[NonNegativeInt] = None) -> None:
        pass


class SQLAlchemyTaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, task: Task, index: NonNegativeInt) -> None:
        model = TaskModel.from_entity(task, index)
        self.session.add(model)
        await self.session.flush()

    async def delete_attachment(self, attachment: Attachment) -> None:
        pass

    async def get(self, task_id: UUID) -> Task:
        return Task(id=task_id, title='stub', user_id=UUID('00000000-0000-0000-0000-000000000000'), section_id=UUID('00000000-0000-0000-0000-000000000000'))

    async def get_archived_tasks(self, user_id: UUID) -> list[Task]:
        return []

    async def get_entities(self, task_models: List[TaskModel]) -> list[Task]:
        return [tm.to_entity([]) for tm in task_models]

    async def get_entity(self, task_model: TaskModel) -> Task:
        return task_model.to_entity([])

    async def get_overdue_tasks(self, user_id: UUID) -> list[Task]:
        return []

    async def get_tasks_by_due_to(
        self, not_before: date, not_after: date, user_id: UUID
    ) -> list[Task]:
        return []

    async def remove(self, task: Task) -> None:
        pass

    async def search(self, user_id: UUID, query: str) -> list[Task]:
        return []

    async def update_or_create(
        self, task: Task, index: Optional[NonNegativeInt] = None, must_exist: bool = False
    ) -> None:
        pass

    async def update_or_create_bulk(self, section_tasks: list[Task]) -> None:
        pass


class SQLAlchemyUserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_users(self) -> List[User]:
        # returns list[User] – diagram says list[UserStats], but UserStats is not defined
        return []

    async def verify_user(self, user_id: UUID) -> None:
        # maybe raises if not exists
        pass


# -------------------------------------------------------------------
# Unit of Work
# -------------------------------------------------------------------
class IUnitOfWork(ABC):
    section_repo: SQLAlchemySectionRepository
    task_repo: SQLAlchemyTaskRepository
    user_repo: SQLAlchemyUserRepository

    @abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self.session = self.session_factory()
        self.section_repo = SQLAlchemySectionRepository(self.session)
        self.task_repo = SQLAlchemyTaskRepository(self.session)
        self.user_repo = SQLAlchemyUserRepository(self.session)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()