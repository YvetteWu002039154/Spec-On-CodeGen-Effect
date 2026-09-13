import random
import uuid
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, List, Literal, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, model_validator
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# --- Domain Models ---

class Entity(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Attachment(Entity):
    added_at: Optional[datetime] = None
    aes_iv_b64: str
    aes_key_b64: str
    id: Optional[uuid.UUID] = None
    s3_file_key: str
    task_id: uuid.UUID


class RecurrenceInfo(Entity):
    flexible_mode: bool
    period: int
    type: Literal['daily', 'weekly', 'monthly', 'yearly']


class Task(Entity):
    added_at: Optional[datetime] = None
    attachments: Optional[List[Attachment]] = None
    content: Optional[str] = None
    description: Optional[str] = None
    due_to: Optional[date] = None
    id: Optional[uuid.UUID] = None
    is_archived: bool = False
    is_completed: bool = False
    recurrence: Optional[RecurrenceInfo] = None
    section_id: uuid.UUID
    title: str
    user_id: uuid.UUID

    @model_validator(mode='before')
    @classmethod
    def check_recurrence_due_date(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if values.get('recurrence') is not None and values.get('due_to') is None:
                raise ValueError("due_to must be set if recurrence is set")
        return values

    def add_attachment(self, attachment: Attachment) -> None:
        if self.attachments is None:
            self.attachments = []
        self.attachments.append(attachment)

    def archive(self) -> None:
        self.is_archived = True

    def mark_completed(self, auto_archive: bool) -> None:
        self.is_completed = True
        if auto_archive:
            self.archive()

    def remove_attachment(self, attachment: Attachment) -> None:
        if self.attachments and attachment in self.attachments:
            self.attachments.remove(attachment)

    def toggle_archived(self) -> None:
        self.is_archived = not self.is_archived

    def toggle_completed(self, auto_archive: bool) -> None:
        self.is_completed = not self.is_completed
        if self.is_completed and auto_archive:
            self.archive()

    def unarchive(self) -> None:
        self.is_archived = False


class Section(Entity):
    added_at: Optional[datetime] = None
    has_subsections: bool = False
    has_tasks: bool = False
    id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None
    subsections: List['Section'] = Field(default_factory=list)
    tasks: List[Task] = Field(default_factory=list)
    title: str
    user_id: uuid.UUID

    def check_flags(self) -> 'Section':
        self.has_subsections = len(self.subsections) > 0
        self.has_tasks = len(self.tasks) > 0
        return self

    @classmethod
    def create_root_section(cls, user_id: uuid.UUID) -> 'Section':
        return cls(
            title="Root",
            user_id=user_id,
            id=uuid.uuid4(),
            has_subsections=False,
            has_tasks=False,
            subsections=[],
            tasks=[]
        )

    def insert_subsection(self, subsection: 'Section', index: Optional[NonNegativeInt]) -> None:
        if index is not None:
            self.subsections.insert(index, subsection)
        else:
            self.subsections.append(subsection)
        self.check_flags()

    def insert_task(self, task: Task, index: Optional[NonNegativeInt]) -> None:
        if index is not None:
            self.tasks.insert(index, task)
        else:
            self.tasks.append(task)
        self.check_flags()

    def is_root(self) -> bool:
        return self.parent_id is None

    @staticmethod
    def move_section(section: 'Section', section_from: 'Section', section_to: 'Section', index: NonNegativeInt) -> None:
        section_from.remove_subsection(section)
        section_to.insert_subsection(section, index)

    @staticmethod
    def move_task(task_to_move: Task, section_from: 'Section', section_to: 'Section', index: NonNegativeInt) -> None:
        section_from.remove_task(task_to_move)
        section_to.insert_task(task_to_move, index)

    def remove_subsection(self, subsection: 'Section') -> 'Section':
        self.subsections.remove(subsection)
        self.check_flags()
        return subsection

    def remove_task(self, task: Task) -> Task:
        self.tasks.remove(task)
        self.check_flags()
        return task

    def shuffle_tasks(self) -> None:
        random.shuffle(self.tasks)


class User(Entity):
    added_at: Optional[datetime] = None
    email: str
    id: Optional[uuid.UUID] = None


class UserStats(BaseModel):
    user_id: uuid.UUID


# --- Infrastructure Models ---

class Base(DeclarativeBase):
    pass


class AccessTokenModel(Base):
    __tablename__ = 'access_tokens'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class UserModel(Base):
    __tablename__ = 'users'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    email: Mapped[str] = mapped_column(String)

    sections: Mapped[List['SectionModel']] = relationship(back_populates='user')
    tasks: Mapped[List['TaskModel']] = relationship(back_populates='user')

    def to_entity(self) -> User:
        return User(
            id=self.id,
            added_at=self.added_at,
            email=self.email
        )


class SectionModel(Base):
    __tablename__ = 'sections'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    has_subsections: Mapped[bool] = mapped_column(Boolean, default=False)
    has_tasks: Mapped[bool] = mapped_column(Boolean, default=False)
    index: Mapped[int] = mapped_column(Integer)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey('sections.id'), nullable=True)
    title: Mapped[str] = mapped_column(String)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))

    user: Mapped[UserModel] = relationship(back_populates='sections')
    tasks: Mapped[List['TaskModel']] = relationship(back_populates='section')

    @classmethod
    def from_entity(cls, section: Section, index: NonNegativeInt) -> 'SectionModel':
        return cls(
            id=section.id or uuid.uuid4(),
            added_at=section.added_at or datetime.utcnow(),
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
            index=index,
            parent_id=section.parent_id,
            title=section.title,
            user_id=section.user_id
        )

    def to_entity(self, tasks: list[Task], subsections: list[Section]) -> Section:
        return Section(
            id=self.id,
            added_at=self.added_at,
            has_subsections=self.has_subsections,
            has_tasks=self.has_tasks,
            parent_id=self.parent_id,
            title=self.title,
            user_id=self.user_id,
            tasks=tasks,
            subsections=subsections
        )


class TaskModel(Base):
    __tablename__ = 'tasks'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    due_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    flexible_recurrence_mode: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    index: Mapped[int] = mapped_column(Integer)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recurrence_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('sections.id'))
    title: Mapped[str] = mapped_column(String)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))

    section: Mapped[SectionModel] = relationship(back_populates='tasks')
    user: Mapped[UserModel] = relationship(back_populates='tasks')
    attachments: Mapped[List['AttachmentModel']] = relationship(back_populates='task')

    @classmethod
    def from_entity(cls, task: Task, index: NonNegativeInt) -> 'TaskModel':
        return cls(
            id=task.id or uuid.uuid4(),
            added_at=task.added_at or datetime.utcnow(),
            description=task.description,
            due_to=task.due_to,
            flexible_recurrence_mode=task.recurrence.flexible_mode if task.recurrence else None,
            index=index,
            is_archived=task.is_archived,
            is_completed=task.is_completed,
            recurrence_period=task.recurrence.period if task.recurrence else None,
            recurrence_type=task.recurrence.type if task.recurrence else None,
            section_id=task.section_id,
            title=task.title,
            user_id=task.user_id
        )

    def to_entity(self, attachments: list[Attachment]) -> Task:
        recurrence = None
        if self.recurrence_type is not None and self.recurrence_period is not None and self.flexible_recurrence_mode is not None:
            recurrence = RecurrenceInfo(
                flexible_mode=self.flexible_recurrence_mode,
                period=self.recurrence_period,
                type=self.recurrence_type
            )
        return Task(
            id=self.id,
            added_at=self.added_at,
            description=self.description,
            due_to=self.due_to,
            is_archived=self.is_archived,
            is_completed=self.is_completed,
            recurrence=recurrence,
            section_id=self.section_id,
            title=self.title,
            user_id=self.user_id,
            attachments=attachments
        )


class AttachmentModel(Base):
    __tablename__ = 'attachments'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    aes_iv_b64: Mapped[str] = mapped_column(String)
    aes_key_b64: Mapped[str] = mapped_column(String)
    index: Mapped[int] = mapped_column(Integer)
    s3_file_key: Mapped[str] = mapped_column(String)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tasks.id'))

    task: Mapped[TaskModel] = relationship(back_populates='attachments')

    @classmethod
    def from_entity(cls, attachment: Attachment, index: NonNegativeInt) -> 'AttachmentModel':
        return cls(
            id=attachment.id or uuid.uuid4(),
            added_at=attachment.added_at or datetime.utcnow(),
            aes_iv_b64=attachment.aes_iv_b64,
            aes_key_b64=attachment.aes_key_b64,
            index=index,
            s3_file_key=attachment.s3_file_key,
            task_id=attachment.task_id
        )

    def to_entity(self) -> Attachment:
        return Attachment(
            id=self.id,
            added_at=self.added_at,
            aes_iv_b64=self.aes_iv_b64,
            aes_key_b64=self.aes_key_b64,
            s3_file_key=self.s3_file_key,
            task_id=self.task_id
        )


# --- Repositories ---

class SQLAlchemySectionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, section: Section, index: NonNegativeInt) -> None:
        model = SectionModel.from_entity(section, index)
        self.session.add(model)

    def construct_sections_tree(self, section_models: list[SectionModel], return_flat: bool) -> list[Section]:
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
        model = TaskModel.from_entity(task, index)
        self.session.add(model)

    async def delete_attachment(self, attachment: Attachment) -> None:
        pass

    async def get(self, task_id: uuid.UUID) -> Task:
        pass

    async def get_archived_tasks(self, user_id: uuid.UUID) -> list[Task]:
        return []

    def get_entities(self, task_models: Sequence[TaskModel]) -> list[Task]:
        return [self.get_entity(m) for m in task_models]

    def get_entity(self, task_model: TaskModel) -> Task:
        attachments = [a.to_entity() for a in task_model.attachments] if task_model.attachments else []
        return task_model.to_entity(attachments)

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


class SQLAlchemyUserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_users(self) -> list[UserStats]:
        return []

    async def verify_user(self, user_id: uuid.UUID) -> None:
        pass


# --- Unit of Work ---

class IUnitOfWork(ABC):
    section_repo: SQLAlchemySectionRepository
    task_repo: SQLAlchemyTaskRepository
    user_repo: SQLAlchemyUserRepository

    @abstractmethod
    async def commit(self) -> None:
        pass

    @abstractmethod
    async def rollback(self) -> None:
        pass


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self.session: AsyncSession = None

    async def __aenter__(self):
        self.session = self.session_factory()
        self.section_repo = SQLAlchemySectionRepository(self.session)
        self.task_repo = SQLAlchemyTaskRepository(self.session)
        self.user_repo = SQLAlchemyUserRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.rollback()
        await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()