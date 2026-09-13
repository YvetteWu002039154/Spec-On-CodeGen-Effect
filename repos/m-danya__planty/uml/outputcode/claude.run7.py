from __future__ import annotations

import abc
import random
from datetime import date, datetime
from typing import Any, Literal, Optional, Sequence
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, model_validator


# ---------------------------------------------------------------------------
# Domain layer
# ---------------------------------------------------------------------------

class Entity(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class RecurrenceInfo(Entity):
    type: Literal["days", "weeks", "months", "years"]
    period: int
    flexible_mode: bool = False


class Attachment(Entity):
    id: Optional[UUID] = None
    task_id: UUID
    s3_file_key: str
    aes_key_b64: str
    aes_iv_b64: str
    added_at: Optional[datetime] = None


class Task(Entity):
    id: Optional[UUID] = None
    section_id: UUID
    user_id: UUID
    title: str
    content: Optional[str] = None
    description: Optional[str] = None
    due_to: Optional[date] = None
    is_completed: bool = False
    is_archived: bool = False
    recurrence: Optional[RecurrenceInfo] = None
    attachments: Optional[list[Attachment]] = None
    added_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def check_recurrence_due_date(cls, values: Any) -> Any:
        recurrence = values.get("recurrence") if isinstance(values, dict) else getattr(values, "recurrence", None)
        due_to = values.get("due_to") if isinstance(values, dict) else getattr(values, "due_to", None)
        if recurrence is not None and due_to is None:
            raise ValueError("A task with recurrence must have a due_to date.")
        return values

    def add_attachment(self, attachment: Attachment) -> None:
        if self.attachments is None:
            self.attachments = []
        self.attachments.append(attachment)

    def remove_attachment(self, attachment: Attachment) -> None:
        if self.attachments is not None:
            self.attachments = [a for a in self.attachments if a.id != attachment.id]

    def mark_completed(self, auto_archive: bool = False) -> None:
        if self.recurrence is not None and self.due_to is not None:
            import datetime as dt
            period = self.recurrence.period
            rtype = self.recurrence.type
            if self.recurrence.flexible_mode:
                base = date.today()
            else:
                base = self.due_to
            if rtype == "days":
                self.due_to = base + dt.timedelta(days=period)
            elif rtype == "weeks":
                self.due_to = base + dt.timedelta(weeks=period)
            elif rtype == "months":
                month = base.month + period
                year = base.year + (month - 1) // 12
                month = (month - 1) % 12 + 1
                day = min(base.day, [31,29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,31,30,31,30,31,31,30,31,30,31][month-1])
                self.due_to = date(year, month, day)
            elif rtype == "years":
                try:
                    self.due_to = date(base.year + period, base.month, base.day)
                except ValueError:
                    self.due_to = date(base.year + period, base.month, 28)
        else:
            self.is_completed = True
            if auto_archive:
                self.is_archived = True

    def toggle_completed(self, auto_archive: bool = False) -> None:
        if self.is_completed:
            self.is_completed = False
        else:
            self.mark_completed(auto_archive=auto_archive)

    def archive(self) -> None:
        self.is_archived = True

    def unarchive(self) -> None:
        self.is_archived = False

    def toggle_archived(self) -> None:
        self.is_archived = not self.is_archived


class Section(Entity):
    id: Optional[UUID] = None
    user_id: UUID
    parent_id: Optional[UUID] = None
    title: str
    tasks: list[Task] = []
    subsections: list[Section] = []
    has_tasks: bool = False
    has_subsections: bool = False
    added_at: Optional[datetime] = None

    @model_validator(mode="after")
    def check_flags(self) -> Section:
        self.has_tasks = len(self.tasks) > 0
        self.has_subsections = len(self.subsections) > 0
        return self

    @classmethod
    def create_root_section(cls, user_id: UUID) -> Section:
        return cls(
            id=uuid4(),
            user_id=user_id,
            parent_id=None,
            title="root",
            tasks=[],
            subsections=[],
        )

    def is_root(self) -> bool:
        return self.parent_id is None

    def insert_task(self, task: Task, index: Optional[int] = None) -> None:
        if index is None:
            self.tasks.append(task)
        else:
            self.tasks.insert(index, task)
        self.has_tasks = True

    def remove_task(self, task: Task) -> Task:
        self.tasks = [t for t in self.tasks if t.id != task.id]
        self.has_tasks = len(self.tasks) > 0
        return task

    def insert_subsection(self, subsection: Section, index: Optional[int] = None) -> None:
        if index is None:
            self.subsections.append(subsection)
        else:
            self.subsections.insert(index, subsection)
        self.has_subsections = True

    def remove_subsection(self, subsection: Section) -> Section:
        self.subsections = [s for s in self.subsections if s.id != subsection.id]
        self.has_subsections = len(self.subsections) > 0
        return subsection

    def shuffle_tasks(self) -> None:
        random.shuffle(self.tasks)

    @staticmethod
    def move_task(
        task_to_move: Task,
        section_from: Section,
        section_to: Section,
        index: int,
    ) -> None:
        section_from.remove_task(task_to_move)
        task_to_move.section_id = section_to.id  # type: ignore[assignment]
        section_to.insert_task(task_to_move, index)

    @staticmethod
    def move_section(
        section: Section,
        section_from: Section,
        section_to: Section,
        index: int,
    ) -> None:
        section_from.remove_subsection(section)
        section.parent_id = section_to.id
        section_to.insert_subsection(section, index)


class User(Entity):
    id: Optional[UUID] = None
    email: str
    added_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Infrastructure – Models (SQLAlchemy-style, but implemented as plain classes
# since we have no DB engine wired up here)
# ---------------------------------------------------------------------------

try:
    from sqlalchemy import (
        Boolean,
        Column,
        DateTime,
        ForeignKey,
        Integer,
        String,
        Date,
    )
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    import uuid as _uuid

    class Base(DeclarativeBase):
        pass

    GUID = PG_UUID(as_uuid=True)

    class UserModel(Base):
        __tablename__ = "users"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
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

    class SectionModel(Base):
        __tablename__ = "sections"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
        user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
        parent_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("sections.id"), nullable=True)
        title: Mapped[str] = mapped_column(String, nullable=False)
        index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
        has_tasks: Mapped[bool] = mapped_column(Boolean, default=False)
        has_subsections: Mapped[bool] = mapped_column(Boolean, default=False)
        added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

        user = relationship("UserModel", back_populates="sections")
        tasks: Mapped[list[TaskModel]] = relationship("TaskModel", back_populates="section", order_by="TaskModel.index")

        @classmethod
        def from_entity(cls, section: Section, index: int) -> SectionModel:
            return cls(
                id=section.id or uuid4(),
                user_id=section.user_id,
                parent_id=section.parent_id,
                title=section.title,
                index=index,
                has_tasks=section.has_tasks,
                has_subsections=section.has_subsections,
                added_at=section.added_at or datetime.utcnow(),
            )

        def to_entity(self, tasks: list[Task], subsections: list[Section]) -> Section:
            return Section(
                id=self.id,
                user_id=self.user_id,
                parent_id=self.parent_id,
                title=self.title,
                has_tasks=self.has_tasks,
                has_subsections=self.has_subsections,
                added_at=self.added_at,
                tasks=tasks,
                subsections=subsections,
            )

    class TaskModel(Base):
        __tablename__ = "tasks"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
        section_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("sections.id"), nullable=False)
        user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
        title: Mapped[str] = mapped_column(String, nullable=False)
        description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
        due_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
        is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
        is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
        recurrence_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
        recurrence_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
        flexible_recurrence_mode: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
        index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
        added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

        section = relationship("SectionModel", back_populates="tasks")
        user = relationship("UserModel", back_populates="tasks")
        attachments = relationship("AttachmentModel", back_populates="task", order_by="AttachmentModel.index")

        @classmethod
        def from_entity(cls, task: Task, index: int) -> TaskModel:
            recurrence_type = None
            recurrence_period = None
            flexible_recurrence_mode = None
            if task.recurrence is not None:
                recurrence_type = task.recurrence.type
                recurrence_period = task.recurrence.period
                flexible_recurrence_mode = task.recurrence.flexible_mode

            return cls(
                id=task.id or uuid4(),
                section_id=task.section_id,
                user_id=task.user_id,
                title=task.title,
                description=task.description,
                due_to=task.due_to,
                is_completed=task.is_completed,
                is_archived=task.is_archived,
                recurrence_type=recurrence_type,
                recurrence_period=recurrence_period,
                flexible_recurrence_mode=flexible_recurrence_mode,
                index=index,
                added_at=task.added_at or datetime.utcnow(),
            )

        def to_entity(self, attachments: list[Attachment]) -> Task:
            recurrence = None
            if self.recurrence_type is not None and self.recurrence_period is not None:
                recurrence = RecurrenceInfo(
                    type=self.recurrence_type,  # type: ignore[arg-type]
                    period=self.recurrence_period,
                    flexible_mode=self.flexible_recurrence_mode or False,
                )
            return Task(
                id=self.id,
                section_id=self.section_id,
                user_id=self.user_id,
                title=self.title,
                description=self.description,
                due_to=self.due_to,
                is_completed=self.is_completed,
                is_archived=self.is_archived,
                recurrence=recurrence,
                attachments=attachments,
                added_at=self.added_at,
            )

    class AttachmentModel(Base):
        __tablename__ = "attachments"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
        task_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
        s3_file_key: Mapped[str] = mapped_column(String, nullable=False)
        aes_key_b64: Mapped[str] = mapped_column(String, nullable=False)
        aes_iv_b64: Mapped[str] = mapped_column(String, nullable=False)
        index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
        added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

        task = relationship("TaskModel", back_populates="attachments")

        @classmethod
        def from_entity(cls, attachment: Attachment, index: int) -> AttachmentModel:
            return cls(
                id=attachment.id or uuid4(),
                task_id=attachment.task_id,
                s3_file_key=attachment.s3_file_key,
                aes_key_b64=attachment.aes_key_b64,
                aes_iv_b64=attachment.aes_iv_b64,
                index=index,
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
        __tablename__ = "access_tokens"

        id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
        token: Mapped[str] = mapped_column(String, unique=True, nullable=False)
        user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
        created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

except ImportError:
    # Fallback plain-Python implementations when SQLAlchemy is not installed

    class Base:  # type: ignore[no-redef]
        pass

    class UserModel(Base):  # type: ignore[no-redef]
        def __init__(
            self,
            id: Optional[UUID] = None,
            email: str = "",
            added_at: Optional[datetime] = None,
        ):
            self.id = id or uuid4()
            self.email = email
            self.added_at = added_at or datetime.utcnow()
            self.sections: list = []
            self.tasks: list = []

        def to_entity(self) -> User:
            return User(id=self.id, email=self.email, added_at=self.added_at)

    class SectionModel(Base):  # type: ignore[no-redef]
        def __init__(
            self,
            id: Optional[UUID] = None,
            user_id: Optional[UUID] = None,
            parent_id: Optional[UUID] = None,
            title: str = "",
            index: int = 0,
            has_tasks: bool = False,
            has_subsections: bool = False,
            added_at: Optional[datetime] = None,
        ):
            self.id = id or uuid4()
            self.user_id = user_id
            self.parent_id = parent_id
            self.title = title
            self.index = index
            self.has_tasks = has_tasks
            self.has_subsections = has_subsections
            self.added_at = added_at or datetime.utcnow()
            self.tasks: list = []
            self.user = None

        @classmethod
        def from_entity(cls, section: Section, index: int) -> SectionModel:
            return cls(
                id=section.id or uuid4(),
                user_id=section.user_id,
                parent_id=section.parent_id,
                title=section.title,
                index=index,
                has_tasks=section.has_tasks,
                has_subsections=section.has_subsections,
                added_at=section.added_at or datetime.utcnow(),
            )

        def to_entity(self, tasks: list[Task], subsections: list[Section]) -> Section:
            return Section(
                id=self.id,
                user_id=self.user_id,
                parent_id=self.parent_id,
                title=self.title,
                has_tasks=self.has_tasks,
                has_subsections=self.has_subsections,
                added_at=self.added_at,
                tasks=tasks,
                subsections=subsections,
            )

    class TaskModel(Base):  # type: ignore[no-redef]
        def __init__(
            self,
            id: Optional[UUID] = None,
            section_id: Optional[UUID] = None,
            user_id: Optional[UUID] = None,
            title: str = "",
            description: Optional[str] = None,
            due_to: Optional[date] = None,
            is_completed: bool = False,
            is_archived: bool = False,
            recurrence_type: Optional[str] = None,
            recurrence_period: Optional[int] = None,
            flexible_recurrence_mode: Optional[bool] = None,
            index: int = 0,
            added_at: Optional[datetime] = None,
        ):
            self.id = id or uuid4()
            self.section_id = section_id
            self.user_id = user_id
            self.title = title
            self.description = description
            self.due_to = due_to
            self.is_completed = is_completed
            self.is_archived = is_archived
            self.recurrence_type = recurrence_type
            self.recurrence_period = recurrence_period
            self.flexible_recurrence_mode = flexible_recurrence_mode
            self.index = index
            self.added_at = added_at or datetime.utcnow()
            self.attachments: list = []
            self.section = None
            self.user = None

        @classmethod
        def from_entity(cls, task: Task, index: int) -> TaskModel:
            recurrence_type = None
            recurrence_period = None
            flexible_recurrence_mode = None
            if task.recurrence is not None:
                recurrence_type = task.recurrence.type
                recurrence_period = task.recurrence.period
                flexible_recurrence_mode = task.recurrence.flexible_mode
            return cls(
                id=task.id or uuid4(),
                section_id=task.section_id,
                user_id=task.user_id,
                title=task.title,
                description=task.description,
                due_to=task.due_to,
                is_completed=task.is_completed,
                is_archived=task.is_archived,
                recurrence_type=recurrence_type,
                recurrence_period=recurrence_period,
                flexible_recurrence_mode=flexible_recurrence_mode,
                index=index,
                added_at=task.added_at or datetime.utcnow(),
            )

        def to_entity(self, attachments: list[Attachment]) -> Task:
            recurrence = None
            if self.recurrence_type is not None and self.recurrence_period is not None:
                recurrence = RecurrenceInfo(
                    type=self.recurrence_type,  # type: ignore[arg-type]
                    period=self.recurrence_period,
                    flexible_mode=self.flexible_recurrence_mode or False,
                )
            return Task(
                id=self.id,
                section_id=self.section_id,
                user_id=self.user_id,
                title=self.title,
                description=self.description,
                due_to=self.due_to,
                is_completed=self.is_completed,
                is_archived=self.is_archived,
                recurrence=recurrence,
                attachments=attachments,
                added_at=self.added_at,
            )

    class AttachmentModel(Base):  # type: ignore[no-redef]
        def __init__(
            self,
            id: Optional[UUID] = None,
            task_id: Optional[UUID] = None,
            s3_file_key: str = "",
            aes_key_b64: str = "",
            aes_iv_b64: str = "",
            index: int = 0,
            added_at: Optional[datetime] = None,
        ):
            self.id = id or uuid4()
            self.task_id = task_id
            self.s3_file_key = s3_file_key
            self.aes_key_b64 = aes_key_b64
            self.aes_iv_b64 = aes_iv_b64
            self.index = index
            self.added_at = added_at or datetime.utcnow()
            self.task = None

        @classmethod
        def from_entity(cls, attachment: Attachment, index: int) -> AttachmentModel:
            return cls(
                id=attachment.id or uuid4(),
                task_id=attachment.task_id,
                s3_file_key=attachment.s3_file_key,
                aes_key_b64=attachment.aes_key_b64,
                aes_iv_b64=attachment.aes_iv_b64,
                index=index,
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

    class AccessTokenModel(Base):  # type: ignore[no-redef]
        def __init__(
            self,
            id: Optional[UUID] = None,
            token: str = "",
            user_id: Optional[UUID] = None,
            created_at: Optional[datetime] = None,
        ):
            self.id = id or uuid4()
            self.token = token
            self.user_id = user_id
            self.created_at = created_at or datetime.utcnow()


# ---------------------------------------------------------------------------
# Infrastructure – Repositories
# ---------------------------------------------------------------------------

class UserStats(BaseModel):
    user_id: UUID
    email: str
    task_count: int = 0
    section_count: int = 0


class SQLAlchemyUserRepository:
    def __init__(self, session: Any) -> None:
        self._session = session

    async def get_all_users(self) -> list[UserStats]:
        raise NotImplementedError

    async def verify_user(self, user_id: UUID) -> None:
        raise NotImplementedError


class SQLAlchemyTaskRepository:
    def __init__(self, session: Any) -> None:
        self._session = session

    async def add(self, task: Task, index: int) -> None:
        raise NotImplementedError

    async def get(self, task_id: UUID) -> Task:
        raise NotImplementedError

    async def remove(self, task: Task) -> None:
        raise NotImplementedError

    async def update_or_create(
        self,
        task: Task,
        index: Optional[int],
        must_exist: bool = True,
    ) -> None:
        raise NotImplementedError

    async def update_or_create_bulk(self, section_tasks: list[Task]) -> None:
        raise NotImplementedError

    async def delete_attachment(self, attachment: Attachment) -> None:
        raise NotImplementedError

    async def get_archived_tasks(self, user_id: UUID) -> list[Task]:
        raise NotImplementedError

    async def get_overdue_tasks(self, user_id: UUID) -> list[Task]:
        raise NotImplementedError

    async def get_tasks_by_due_to(
        self,
        not_before: date,
        not_after: date,
        user_id: UUID,
    ) -> list[Task]:
        raise NotImplementedError

    async def search(self, user_id: UUID, query: str) -> list[Task]:
        raise NotImplementedError

    def get_entities(self, task_models: Sequence[TaskModel]) -> list[Task]:
        raise NotImplementedError

    def get_entity(self, task_model: TaskModel) -> Task:
        raise NotImplementedError


class SQLAlchemySectionRepository:
    def __init__(self, session: Any) -> None:
        self._session = session

    async def add(self, section: Section, index: int) -> None:
        raise NotImplementedError

    async def get(self, section_id: UUID, with_direct_subsections: bool = False) -> Section:
        raise NotImplementedError

    async def update(self, section: Section, index: Optional[int] = None) -> None:
        raise NotImplementedError

    async def get_all_without_tasks(
        self,
        user_id: UUID,
        leaves_only: bool = False,
        as_tree: bool = False,
    ) -> list[Section]:
        raise NotImplementedError

    async def count_subsections(self, section_id: UUID) -> int:
        raise NotImplementedError

    def construct_sections_tree(
        self,
        section_models: list[SectionModel],
        return_flat: bool = False,
    ) -> list[Section]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Application – Unit of Work
# ---------------------------------------------------------------------------

class IUnitOfWork(abc.ABC):
    section_repo: SQLAlchemySectionRepository
    task_repo: SQLAlchemyTaskRepository
    user_repo: SQLAlchemyUserRepository

    @abc.abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError

    async def __aenter__(self) -> IUnitOfWork:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session_factory: Any) -> None:
        self.session_factory = session_factory
        self.session: Any = None
        self.task_repo: SQLAlchemyTaskRepository = None  # type: ignore[assignment]
        self.section_repo: SQLAlchemySectionRepository = None  # type: ignore[assignment]
        self.user_repo: SQLAlchemyUserRepository = None  # type: ignore[assignment]

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self.session = self.session_factory()
        self.task_repo = SQLAlchemyTaskRepository(self.session)
        self.section_repo = SQLAlchemySectionRepository(self.session)
        self.user_repo = SQLAlchemyUserRepository(self.session)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await super().__aexit__(exc_type, exc_val, exc_tb)
        if self.session is not None:
            try:
                await self.session.close()
            except Exception:
                pass

    async def commit(self) -> None:
        if self.session is not None:
            try:
                await self.session.commit()
            except Exception:
                pass

    async def rollback(self) -> None:
        if self.session is not None:
            try:
                await self.session.rollback()
            except Exception:
                pass