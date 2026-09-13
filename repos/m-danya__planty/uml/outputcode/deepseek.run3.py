from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Optional, Literal, Sequence, List

from pydantic import BaseModel, ConfigDict, field_validator, NonNegativeInt
from sqlalchemy import String, Boolean, Integer, DateTime, Date, Uuid, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Type aliases
GUID = uuid.UUID
NonNegativeInt = int  # from pydantic.types.NonNegativeInt, but here just int for simplicity
RecurrenceType = Literal["daily", "weekly", "monthly", "yearly"]

class Entity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class User(Entity):
    id: Optional[uuid.UUID] = None
    email: str
    added_at: Optional[datetime] = None

class Attachment(Entity):
    id: Optional[uuid.UUID] = None
    task_id: uuid.UUID
    s3_file_key: str
    aes_key_b64: str
    aes_iv_b64: str
    added_at: Optional[datetime] = None

class RecurrenceInfo(Entity):
    period: int
    type: RecurrenceType
    flexible_mode: bool

class Task(Entity):
    id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    section_id: uuid.UUID
    title: str
    content: Optional[str] = None
    description: Optional[str] = None
    due_to: Optional[date] = None
    is_completed: bool = False
    is_archived: bool = False
    added_at: Optional[datetime] = None
    recurrence: Optional[RecurrenceInfo] = None
    attachments: Optional[List[Attachment]] = None

    @field_validator('recurrence')
    @classmethod
    def check_recurrence_due_date(cls, v: Any, values: Any) -> Any:
        # Placeholder logic: if recurrence present, due_to must be set
        if v is not None and values.get('due_to') is None:
            raise ValueError('due_to must be set when recurrence is specified')
        return v

    def add_attachment(self, attachment: Attachment) -> None:
        if self.attachments is None:
            self.attachments = []
        self.attachments.append(attachment)

    def remove_attachment(self, attachment: Attachment) -> None:
        if self.attachments:
            self.attachments = [a for a in self.attachments if a.id != attachment.id]

    def archive(self) -> None:
        self.is_archived = True

    def unarchive(self) -> None:
        self.is_archived = False

    def mark_completed(self, auto_archive: bool) -> None:
        self.is_completed = True
        if auto_archive:
            self.archive()

    def toggle_completed(self, auto_archive: bool) -> None:
        if self.is_completed:
            self.is_completed = False
            if self.is_archived:
                self.unarchive()
        else:
            self.mark_completed(auto_archive)

    def toggle_archived(self) -> None:
        if self.is_archived:
            self.unarchive()
        else:
            self.archive()

class Section(Entity):
    id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    title: str
    has_tasks: bool = False
    has_subsections: bool = False
    subsections: List[Section] = []
    tasks: List[Task] = []
    added_at: Optional[datetime] = None

    def check_flags(self) -> Section:
        self.has_tasks = len(self.tasks) > 0
        self.has_subsections = len(self.subsections) > 0
        return self

    @staticmethod
    def create_root_section(user_id: uuid.UUID) -> Section:
        return Section(user_id=user_id, title="Root", parent_id=None)

    def insert_subsection(self, subsection: Section, index: Optional[NonNegativeInt] = None) -> None:
        if index is None:
            self.subsections.append(subsection)
        else:
            self.subsections.insert(index, subsection)
        subsection.parent_id = self.id
        self.check_flags()

    def insert_task(self, task: Task, index: Optional[NonNegativeInt] = None) -> None:
        if index is None:
            self.tasks.append(task)
        else:
            self.tasks.insert(index, task)
        task.section_id = self.id
        self.check_flags()

    def is_root(self) -> bool:
        return self.parent_id is None

    @staticmethod
    def move_section(section: Section, section_from: Section, section_to: Section, index: NonNegativeInt) -> None:
        if section in section_from.subsections:
            section_from.remove_subsection(section)
        section.parent_id = section_to.id
        section_to.subsections.insert(index, section)
        section_to.check_flags()
        section_from.check_flags()

    @staticmethod
    def move_task(task_to_move: Task, section_from: Section, section_to: Section, index: NonNegativeInt) -> None:
        if task_to_move in section_from.tasks:
            section_from.remove_task(task_to_move)
        task_to_move.section_id = section_to.id
        section_to.tasks.insert(index, task_to_move)
        section_to.check_flags()
        section_from.check_flags()

    def remove_subsection(self, subsection: Section) -> Section:
        self.subsections = [s for s in self.subsections if s.id != subsection.id]
        self.check_flags()
        return subsection

    def remove_task(self, task: Task) -> Task:
        self.tasks = [t for t in self.tasks if t.id != task.id]
        self.check_flags()
        return task

    def shuffle_tasks(self) -> None:
        # Placeholder: reorder tasks based on some logic, here we keep same order
        pass

# Infrastructure models
class Base(DeclarativeBase):
    pass

class UserModel(Base):
    __tablename__ = 'users'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sections: Mapped[List[SectionModel]] = relationship(back_populates='user')
    tasks: Mapped[List[TaskModel]] = relationship(back_populates='user')

    def to_entity(self) -> User:
        return User.model_validate(self)

class SectionModel(Base):
    __tablename__ = 'sections'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey('sections.id'), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('users.id'))
    user: Mapped[UserModel] = relationship(back_populates='sections')
    has_subsections: Mapped[bool] = mapped_column(Boolean, default=False)
    has_tasks: Mapped[bool] = mapped_column(Boolean, default=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    tasks: Mapped[List[TaskModel]] = relationship(back_populates='section')

    @staticmethod
    def from_entity(section: Section, index: NonNegativeInt) -> SectionModel:
        return SectionModel(
            id=section.id or uuid.uuid4(),
            index=index,
            title=section.title,
            parent_id=section.parent_id,
            user_id=section.user_id,
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
            added_at=section.added_at or datetime.utcnow(),
        )

    def to_entity(self, tasks: List[Task], subsections: List[Section]) -> Section:
        return Section(
            id=self.id,
            user_id=self.user_id,
            parent_id=self.parent_id,
            title=self.title,
            has_tasks=self.has_tasks,
            has_subsections=self.has_subsections,
            subsections=subsections,
            tasks=tasks,
            added_at=self.added_at,
        )

class TaskModel(Base):
    __tablename__ = 'tasks'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    flexible_recurrence_mode: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    recurrence_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recurrence_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('users.id'))
    section_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('sections.id'))
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user: Mapped[UserModel] = relationship(back_populates='tasks')
    section: Mapped[SectionModel] = relationship(back_populates='tasks')
    attachments: Mapped[List[AttachmentModel]] = relationship(back_populates='task')

    @staticmethod
    def from_entity(task: Task, index: NonNegativeInt) -> TaskModel:
        recurrence = task.recurrence
        return TaskModel(
            id=task.id or uuid.uuid4(),
            index=index,
            title=task.title,
            description=task.description,
            due_to=task.due_to,
            is_completed=task.is_completed,
            is_archived=task.is_archived,
            flexible_recurrence_mode=recurrence.flexible_mode if recurrence else None,
            recurrence_period=recurrence.period if recurrence else None,
            recurrence_type=recurrence.type if recurrence else None,
            user_id=task.user_id,
            section_id=task.section_id,
            added_at=task.added_at or datetime.utcnow(),
        )

    def to_entity(self, attachments: List[Attachment]) -> Task:
        recurrence = None
        if self.recurrence_type is not None:
            recurrence = RecurrenceInfo(
                period=self.recurrence_period,
                type=self.recurrence_type,  # type: ignore
                flexible_mode=bool(self.flexible_recurrence_mode),
            )
        return Task(
            id=self.id,
            user_id=self.user_id,
            section_id=self.section_id,
            title=self.title,
            description=self.description,
            due_to=self.due_to,
            is_completed=self.is_completed,
            is_archived=self.is_archived,
            added_at=self.added_at,
            recurrence=recurrence,
            attachments=attachments,
        )

class AttachmentModel(Base):
    __tablename__ = 'attachments'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('tasks.id'))
    s3_file_key: Mapped[str] = mapped_column(String, nullable=False)
    aes_key_b64: Mapped[str] = mapped_column(String, nullable=False)
    aes_iv_b64: Mapped[str] = mapped_column(String, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    task: Mapped[TaskModel] = relationship(back_populates='attachments')

    @staticmethod
    def from_entity(attachment: Attachment, index: NonNegativeInt) -> AttachmentModel:
        return AttachmentModel(
            id=attachment.id or uuid.uuid4(),
            index=index,
            task_id=attachment.task_id,
            s3_file_key=attachment.s3_file_key,
            aes_key_b64=attachment.aes_key_b64,
            aes_iv_b64=attachment.aes_iv_b64,
            added_at=attachment.added_at or datetime.utcnow(),
        )

    def to_entity(self) -> Attachment:
        return Attachment(
            id=self.id,
            task_id=self.task_id,
            s3_file_key=self.s3_file_key,
            aes_key_b64=self.aes_key_b64,
            aes_iv_b64=self.aes_iv_b64,
            added_at=self.added_at,
        )

class AccessTokenModel(Base):
    __tablename__ = 'access_tokens'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # user_id or additional fields can be added if needed

# Repository interfaces & implementations
class UserStats:
    pass  # Not defined in diagram, placeholder

class SQLAlchemyUserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_users(self) -> list[UserStats]:
        # Implement query
        return []

    async def verify_user(self, user_id: uuid.UUID) -> None:
        # Check if user exists
        pass

class SQLAlchemySectionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, section: Section, index: NonNegativeInt) -> None:
        pass

    async def construct_sections_tree(self, section_models: list[SectionModel], return_flat: bool) -> list[Section]:
        return []

    async def count_subsections(self, section_id: uuid.UUID) -> int:
        return 0

    async def get(self, section_id: uuid.UUID, with_direct_subsections: bool) -> Section:
        pass

    async def get_all_without_tasks(self, user_id: uuid.UUID, leaves_only: bool, as_tree: bool) -> list[Section]:
        return []

    async def update(self, section: Section, index: Optional[NonNegativeInt]) -> None:
        pass

class SQLAlchemyTaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, task: Task, index: NonNegativeInt) -> None:
        pass

    async def delete_attachment(self, attachment: Attachment) -> None:
        pass

    async def get(self, task_id: uuid.UUID) -> Task:
        pass

    async def get_archived_tasks(self, user_id: uuid.UUID) -> list[Task]:
        return []

    async def get_entities(self, task_models: Sequence[TaskModel]) -> list[Task]:
        return []

    async def get_entity(self, task_model: TaskModel) -> Task:
        pass

    async def get_overdue_tasks(self, user_id: uuid.UUID) -> list[Task]:
        return []

    async def get_tasks_by_due_to(self, not_before: date, not_after: date, user_id: uuid.UUID) -> list[Task]:
        return []

    async def remove(self, task: Task) -> None:
        pass

    async def search(self, user_id: uuid.UUID, query: str) -> list[Task]:
        return []

    async def update_or_create(self, task: Task, index: Optional[NonNegativeInt], must_exist: bool) -> None:
        pass

    async def update_or_create_bulk(self, section_tasks: list[Task]) -> None:
        pass

class IUnitOfWork:
    section_repo: SQLAlchemySectionRepository
    task_repo: SQLAlchemyTaskRepository
    user_repo: SQLAlchemyUserRepository

    async def commit(self) -> None:
        raise NotImplementedError

    async def rollback(self) -> None:
        raise NotImplementedError

class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self.session: AsyncSession = None  # type: ignore
        self.section_repo: SQLAlchemySectionRepository = None  # type: ignore
        self.task_repo: SQLAlchemyTaskRepository = None  # type: ignore
        self.user_repo: SQLAlchemyUserRepository = None  # type: ignore

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self.session = self.session_factory()
        self.section_repo = SQLAlchemySectionRepository(self.session)
        self.task_repo = SQLAlchemyTaskRepository(self.session)
        self.user_repo = SQLAlchemyUserRepository(self.session)
        return self

    async def __aexit__(self, *args) -> None:
        await self.rollback()
        await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()