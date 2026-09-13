import uuid
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Literal, Optional, Sequence

from pydantic import BaseModel, ConfigDict
from pydantic.types import NonNegativeInt, UUID4
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, Date, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as SA_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

UUID = uuid.UUID
GUID = SA_UUID


# ---------------------------------------------------------------------------
# Domain entities (Pydantic)
# ---------------------------------------------------------------------------

class Entity(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class RecurrenceInfo(Entity):
    flexible_mode: bool
    period: int
    type: Literal["daily", "weekly", "monthly", "yearly"]


class Attachment(Entity):
    id: Optional[UUID] = None
    task_id: UUID
    s3_file_key: str
    aes_key_b64: str
    aes_iv_b64: str
    added_at: Optional[datetime] = None


class User(Entity):
    id: Optional[UUID] = None
    email: str
    added_at: Optional[datetime] = None


class Task(Entity):
    id: Optional[UUID] = None
    user_id: UUID
    section_id: UUID
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    due_to: Optional[date] = None
    is_completed: bool = False
    is_archived: bool = False
    recurrence: Optional[RecurrenceInfo] = None
    attachments: Optional[list[Attachment]] = None
    added_at: Optional[datetime] = None

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
            self.mark_completed(auto_archive)

    def check_recurrence_due_date(cls, values: Any) -> Any:
        # Placeholder for custom validation logic
        return values


class Section(Entity):
    id: Optional[UUID] = None
    user_id: UUID
    parent_id: Optional[UUID] = None
    title: str
    has_subsections: bool = False
    has_tasks: bool = False
    added_at: Optional[datetime] = None
    subsections: list["Section"] = []
    tasks: list[Task] = []
    # (subsections and tasks are populated lazily by the repository)

    def check_flags(self) -> "Section":
        # Update flags based on contents
        self.has_subsections = bool(self.subsections)
        self.has_tasks = bool(self.tasks)
        return self

    @classmethod
    def create_root_section(cls, user_id: UUID) -> "Section":
        return cls(user_id=user_id, title="Root", parent_id=None)

    def is_root(self) -> bool:
        return self.parent_id is None

    def insert_subsection(self, subsection: "Section", index: Optional[NonNegativeInt] = None) -> None:
        if index is not None:
            self.subsections.insert(index, subsection)
        else:
            self.subsections.append(subsection)
        subsection.parent_id = self.id
        self.check_flags()

    def insert_task(self, task: Task, index: Optional[NonNegativeInt] = None) -> None:
        if index is not None:
            self.tasks.insert(index, task)
        else:
            self.tasks.append(task)
        self.check_flags()

    def remove_subsection(self, subsection: "Section") -> "Section":
        self.subsections = [s for s in self.subsections if s.id != subsection.id]
        self.check_flags()
        return subsection

    def remove_task(self, task: Task) -> Task:
        self.tasks = [t for t in self.tasks if t.id != task.id]
        self.check_flags()
        return task

    def shuffle_tasks(self) -> None:
        # Placeholder for custom shuffle logic
        pass

    @staticmethod
    def move_section(
        section: "Section",
        section_from: "Section",
        section_to: "Section",
        index: NonNegativeInt,
    ) -> None:
        section_from.remove_subsection(section)
        section_to.insert_subsection(section, index)

    @staticmethod
    def move_task(
        task_to_move: Task,
        section_from: "Section",
        section_to: "Section",
        index: NonNegativeInt,
    ) -> None:
        section_from.remove_task(task_to_move)
        section_to.insert_task(task_to_move, index)


# ---------------------------------------------------------------------------
# Infrastructure models (SQLAlchemy)
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class AttachmentModel(Base):
    __tablename__ = "attachments"

    id: Mapped[UUID] = mapped_column(SA_UUID, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    s3_file_key: Mapped[str] = mapped_column(String, nullable=False)
    aes_key_b64: Mapped[str] = mapped_column(String, nullable=False)
    aes_iv_b64: Mapped[str] = mapped_column(String, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    index: Mapped[int] = mapped_column(Integer, nullable=False)

    task = relationship("TaskModel", back_populates="attachments")

    @classmethod
    def from_entity(cls, attachment: Attachment, index: NonNegativeInt) -> "AttachmentModel":
        return cls(
            id=attachment.id or uuid.uuid4(),
            task_id=attachment.task_id,
            s3_file_key=attachment.s3_file_key,
            aes_key_b64=attachment.aes_key_b64,
            aes_iv_b64=attachment.aes_iv_b64,
            added_at=attachment.added_at or datetime.utcnow(),
            index=index,
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


class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(SA_UUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    section_id: Mapped[UUID] = mapped_column(ForeignKey("sections.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    recurrence_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    flexible_recurrence_mode: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    index: Mapped[int] = mapped_column(Integer, nullable=False)

    attachments = relationship("AttachmentModel", back_populates="task")
    section = relationship("SectionModel", back_populates="tasks")
    user = relationship("UserModel", back_populates="tasks")

    @classmethod
    def from_entity(cls, task: Task, index: NonNegativeInt) -> "TaskModel":
        rec = task.recurrence
        return cls(
            id=task.id or uuid.uuid4(),
            user_id=task.user_id,
            section_id=task.section_id,
            title=task.title,
            description=task.description,
            due_to=task.due_to,
            is_completed=task.is_completed,
            is_archived=task.is_archived,
            recurrence_type=rec.type if rec else None,
            recurrence_period=rec.period if rec else None,
            flexible_recurrence_mode=rec.flexible_mode if rec else None,
            added_at=task.added_at or datetime.utcnow(),
            index=index,
        )

    def to_entity(self, attachments: list[Attachment]) -> Task:
        rec = None
        if self.recurrence_type:
            rec = RecurrenceInfo(
                type=self.recurrence_type,  # type: ignore
                period=self.recurrence_period or 0,
                flexible_mode=self.flexible_recurrence_mode or False,
            )
        return Task(
            id=self.id,
            user_id=self.user_id,
            section_id=self.section_id,
            title=self.title,
            description=self.description,
            content=None,  # Content is not stored in model, might be a separate field
            due_to=self.due_to,
            is_completed=self.is_completed,
            is_archived=self.is_archived,
            recurrence=rec,
            attachments=attachments,
            added_at=self.added_at,
        )


class SectionModel(Base):
    __tablename__ = "sections"

    id: Mapped[UUID] = mapped_column(SA_UUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    parent_id: Mapped[Optional[UUID]] = mapped_column(SA_UUID, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    has_subsections: Mapped[bool] = mapped_column(Boolean, default=False)
    has_tasks: Mapped[bool] = mapped_column(Boolean, default=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    index: Mapped[int] = mapped_column(Integer, nullable=False)

    tasks: Mapped[list[TaskModel]] = relationship("TaskModel", back_populates="section")
    user = relationship("UserModel", back_populates="sections")

    @classmethod
    def from_entity(cls, section: Section, index: NonNegativeInt) -> "SectionModel":
        return cls(
            id=section.id or uuid.uuid4(),
            user_id=section.user_id,
            parent_id=section.parent_id,
            title=section.title,
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
            added_at=section.added_at or datetime.utcnow(),
            index=index,
        )

    def to_entity(self, tasks: list[Task], subsections: list[Section]) -> Section:
        section = Section(
            id=self.id,
            user_id=self.user_id,
            parent_id=self.parent_id,
            title=self.title,
            has_subsections=self.has_subsections,
            has_tasks=self.has_tasks,
            added_at=self.added_at,
        )
        section.tasks = tasks
        section.subsections = subsections
        return section


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(SA_UUID, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sections = relationship("SectionModel", back_populates="user")
    tasks = relationship("TaskModel", back_populates="user")

    def to_entity(self) -> User:
        return User(
            id=self.id,
            email=self.email,
            added_at=self.added_at,
        )


class AccessTokenModel(Base):
    __tablename__ = "access_tokens"

    id: Mapped[UUID] = mapped_column(SA_UUID, primary_key=True, default=uuid.uuid4)
    # Minimal implementation, no extra details in diagram
    token: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


# ---------------------------------------------------------------------------
# UserStats (placeholder)
# ---------------------------------------------------------------------------

class UserStats(BaseModel):
    id: UUID
    email: str
    task_count: int
    section_count: int


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------

class SQLAlchemySectionRepository:
    async def add(self, section: Section, index: NonNegativeInt) -> None:
        raise NotImplementedError

    async def construct_sections_tree(
        self, section_models: list[SectionModel], return_flat: bool
    ) -> list[Section]:
        raise NotImplementedError

    async def count_subsections(self, section_id: UUID) -> int:
        raise NotImplementedError

    async def get(self, section_id: UUID, with_direct_subsections: bool) -> Section:
        raise NotImplementedError

    async def get_all_without_tasks(
        self, user_id: UUID, leaves_only: bool, as_tree: bool
    ) -> list[Section]:
        raise NotImplementedError

    async def update(self, section: Section, index: Optional[NonNegativeInt]) -> None:
        raise NotImplementedError


class SQLAlchemyTaskRepository:
    async def add(self, task: Task, index: NonNegativeInt) -> None:
        raise NotImplementedError

    async def delete_attachment(self, attachment: Attachment) -> None:
        raise NotImplementedError

    async def get(self, task_id: UUID) -> Task:
        raise NotImplementedError

    async def get_archived_tasks(self, user_id: UUID) -> list[Task]:
        raise NotImplementedError

    async def get_entities(self, task_models: Sequence[TaskModel]) -> list[Task]:
        raise NotImplementedError

    async def get_entity(self, task_model: TaskModel) -> Task:
        raise NotImplementedError

    async def get_overdue_tasks(self, user_id: UUID) -> list[Task]:
        raise NotImplementedError

    async def get_tasks_by_due_to(
        self, not_before: date, not_after: date, user_id: UUID
    ) -> list[Task]:
        raise NotImplementedError

    async def remove(self, task: Task) -> None:
        raise NotImplementedError

    async def search(self, user_id: UUID, query: str) -> list[Task]:
        raise NotImplementedError

    async def update_or_create(
        self, task: Task, index: Optional[NonNegativeInt], must_exist: bool
    ) -> None:
        raise NotImplementedError

    async def update_or_create_bulk(self, section_tasks: list[Task]) -> None:
        raise NotImplementedError


class SQLAlchemyUserRepository:
    async def get_all_users(self) -> list[UserStats]:
        raise NotImplementedError

    async def verify_user(self, user_id: UUID) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Unit of Work
# ---------------------------------------------------------------------------

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
        self.session: AsyncSession = None  # set in __aenter__
        self.section_repo = SQLAlchemySectionRepository()
        self.task_repo = SQLAlchemyTaskRepository()
        self.user_repo = SQLAlchemyUserRepository()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self.session_factory()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                await self.commit()
            else:
                await self.rollback()
        finally:
            await self.session.close()