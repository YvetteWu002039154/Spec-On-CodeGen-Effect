from __future__ import annotations

import datetime
import uuid
from abc import ABC, abstractmethod
from typing import Any, Literal, Optional, Sequence, Union

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import ForeignKey, Integer, String, Date, DateTime, Boolean, Uuid
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NonNegativeInt = int  # simplified, expected to be >=0


# ==========================
# Domain Layer (domain/task.py)
# ==========================

class Entity(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)


class Attachment(Entity):
    id: Optional[uuid.UUID] = None
    task_id: uuid.UUID
    s3_file_key: str
    aes_key_b64: str
    aes_iv_b64: str
    added_at: Optional[datetime.datetime] = None


class RecurrenceInfo(Entity):
    type: Literal['daily', 'weekly', 'monthly', 'yearly']
    period: int
    flexible_mode: bool


class Section(Entity):
    id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    title: str
    added_at: Optional[datetime.datetime] = None
    has_subsections: bool = False
    has_tasks: bool = False
    subsections: list[Section] = []
    tasks: list[Task] = []

    def check_flags(self) -> Section:
        if self.has_subsections != (len(self.subsections) > 0):
            raise ValueError("has_subsections flag mismatch with subsections list")
        if self.has_tasks != (len(self.tasks) > 0):
            raise ValueError("has_tasks flag mismatch with tasks list")
        return self

    def is_root(self) -> bool:
        return self.parent_id is None

    @classmethod
    def create_root_section(cls, user_id: uuid.UUID) -> Section:
        return cls(user_id=user_id, parent_id=None, title="Root", has_subsections=False, has_tasks=False)

    def insert_subsection(self, subsection: Section, index: Optional[NonNegativeInt] = None) -> None:
        if index is None:
            self.subsections.append(subsection)
        else:
            self.subsections.insert(index, subsection)
        subsection.parent_id = self.id
        self.has_subsections = True

    def insert_task(self, task: Task, index: Optional[NonNegativeInt] = None) -> None:
        if index is None:
            self.tasks.append(task)
        else:
            self.tasks.insert(index, task)
        task.section_id = self.id
        self.has_tasks = True

    def remove_subsection(self, subsection: Section) -> Section:
        self.subsections.remove(subsection)
        self.has_subsections = len(self.subsections) > 0
        subsection.parent_id = None
        return subsection

    def remove_task(self, task: Task) -> Task:
        self.tasks.remove(task)
        self.has_tasks = len(self.tasks) > 0
        return task

    @staticmethod
    def move_section(section: Section, section_from: Section, section_to: Section, index: NonNegativeInt) -> None:
        section_from.subsections.remove(section)
        section_to.subsections.insert(index, section)
        section.parent_id = section_to.id
        section_from.has_subsections = len(section_from.subsections) > 0
        section_to.has_subsections = True

    @staticmethod
    def move_task(task_to_move: Task, section_from: Section, section_to: Section, index: NonNegativeInt) -> None:
        section_from.tasks.remove(task_to_move)
        section_to.tasks.insert(index, task_to_move)
        task_to_move.section_id = section_to.id
        section_from.has_tasks = len(section_from.tasks) > 0
        section_to.has_tasks = True

    def shuffle_tasks(self) -> None:
        # simple in-place reversal as placeholder for shuffle
        self.tasks.reverse()


class Task(Entity):
    id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    section_id: uuid.UUID
    title: str
    content: Optional[str] = None
    description: Optional[str] = None
    due_to: Optional[datetime.date] = None
    added_at: Optional[datetime.datetime] = None
    is_completed: bool = False
    is_archived: bool = False
    recurrence: Optional[RecurrenceInfo] = None
    attachments: Optional[list[Attachment]] = None

    def add_attachment(self, attachment: Attachment) -> None:
        if self.attachments is None:
            self.attachments = []
        attachment.task_id = self.id
        self.attachments.append(attachment)

    def remove_attachment(self, attachment: Attachment) -> None:
        if self.attachments:
            self.attachments.remove(attachment)

    def mark_completed(self, auto_archive: bool) -> None:
        self.is_completed = True
        if auto_archive:
            self.archive()

    def archive(self) -> None:
        self.is_archived = True

    def unarchive(self) -> None:
        self.is_archived = False

    def toggle_completed(self, auto_archive: bool) -> None:
        if self.is_completed:
            self.is_completed = False
        else:
            self.mark_completed(auto_archive)

    def toggle_archived(self) -> None:
        self.is_archived = not self.is_archived

    @field_validator('due_to')
    @classmethod
    def check_recurrence_due_date(cls, v: Any, info: Any) -> Any:
        values = info.data
        if values.get('recurrence') and v is None:
            raise ValueError('due_to must be set when recurrence is present')
        return v


class User(Entity):
    id: Optional[uuid.UUID] = None
    email: str
    added_at: Optional[datetime.datetime] = None


# ==========================
# Infrastructure Models (infrastructure/models.py)
# ==========================

class Base(DeclarativeBase):
    pass


class AccessTokenModel(Base):
    __tablename__ = 'access_tokens'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class UserModel(Base):
    __tablename__ = 'users'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255))
    added_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    sections: Mapped[list['SectionModel']] = relationship(back_populates='user')
    tasks: Mapped[list['TaskModel']] = relationship(back_populates='user')

    def to_entity(self) -> User:
        return User(
            id=self.id,
            email=self.email,
            added_at=self.added_at
        )


class SectionModel(Base):
    __tablename__ = 'sections'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    index: Mapped[int] = mapped_column(Integer)
    added_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    has_subsections: Mapped[bool] = mapped_column(Boolean, default=False)
    has_tasks: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped[UserModel] = relationship(back_populates='sections')
    tasks: Mapped[list['TaskModel']] = relationship(back_populates='section')

    @classmethod
    def from_entity(cls, section: Section, index: NonNegativeInt) -> SectionModel:
        return cls(
            id=section.id or uuid.uuid4(),
            user_id=section.user_id,
            parent_id=section.parent_id,
            title=section.title,
            index=index,
            added_at=section.added_at or datetime.datetime.utcnow(),
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
        )

    def to_entity(self, tasks: list[Task], subsections: list[Section]) -> Section:
        return Section(
            id=self.id,
            user_id=self.user_id,
            parent_id=self.parent_id,
            title=self.title,
            added_at=self.added_at,
            has_subsections=self.has_subsections,
            has_tasks=self.has_tasks,
            subsections=subsections,
            tasks=tasks
        )


class TaskModel(Base):
    __tablename__ = 'tasks'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('sections.id'))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    due_to: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    index: Mapped[int] = mapped_column(Integer)
    added_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    recurrence_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    flexible_recurrence_mode: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    user: Mapped[UserModel] = relationship(back_populates='tasks')
    section: Mapped[SectionModel] = relationship(back_populates='tasks')
    attachments: Mapped[list['AttachmentModel']] = relationship(back_populates='task')

    @classmethod
    def from_entity(cls, task: Task, index: NonNegativeInt) -> TaskModel:
        recurrence = task.recurrence
        return cls(
            id=task.id or uuid.uuid4(),
            user_id=task.user_id,
            section_id=task.section_id,
            title=task.title,
            description=task.description,
            due_to=task.due_to,
            index=index,
            added_at=task.added_at or datetime.datetime.utcnow(),
            is_completed=task.is_completed,
            is_archived=task.is_archived,
            recurrence_type=recurrence.type if recurrence else None,
            recurrence_period=recurrence.period if recurrence else None,
            flexible_recurrence_mode=recurrence.flexible_mode if recurrence else None,
        )

    def to_entity(self, attachments: list[Attachment]) -> Task:
        recurrence = None
        if self.recurrence_type:
            recurrence = RecurrenceInfo(
                type=self.recurrence_type,  # type: ignore
                period=self.recurrence_period,
                flexible_mode=self.flexible_recurrence_mode
            )
        return Task(
            id=self.id,
            user_id=self.user_id,
            section_id=self.section_id,
            title=self.title,
            content=None,  # not stored in model
            description=self.description,
            due_to=self.due_to,
            added_at=self.added_at,
            is_completed=self.is_completed,
            is_archived=self.is_archived,
            recurrence=recurrence,
            attachments=attachments,
        )


class AttachmentModel(Base):
    __tablename__ = 'attachments'
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tasks.id'))
    s3_file_key: Mapped[str] = mapped_column(String(512))
    aes_key_b64: Mapped[str] = mapped_column(String(255))
    aes_iv_b64: Mapped[str] = mapped_column(String(255))
    index: Mapped[int] = mapped_column(Integer)
    added_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    task: Mapped[TaskModel] = relationship(back_populates='attachments')

    @classmethod
    def from_entity(cls, attachment: Attachment, index: NonNegativeInt) -> AttachmentModel:
        return cls(
            id=attachment.id or uuid.uuid4(),
            task_id=attachment.task_id,
            s3_file_key=attachment.s3_file_key,
            aes_key_b64=attachment.aes_key_b64,
            aes_iv_b64=attachment.aes_iv_b64,
            index=index,
            added_at=attachment.added_at or datetime.datetime.utcnow(),
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


# ==========================
# Repository interfaces / implementations (infrastructure/repositories.py)
# ==========================

class SQLAlchemySectionRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, section: Section, index: NonNegativeInt) -> None:
        model = SectionModel.from_entity(section, index)
        self._session.add(model)
        await self._session.flush()

    async def get(self, section_id: uuid.UUID, with_direct_subsections: bool = False) -> Section:
        model = await self._session.get(SectionModel, section_id)
        if not model:
            raise ValueError(f"Section {section_id} not found")
        subs = []
        if with_direct_subsections:
            # simplistic: parent_id matching; actual implementation requires query
            pass
        tasks = [t.to_entity([]) for t in model.tasks]  # attachments not loaded
        return model.to_entity(tasks=tasks, subsections=subs)

    async def get_all_without_tasks(self, user_id: uuid.UUID, leaves_only: bool, as_tree: bool) -> list[Section]:
        # stub
        return []

    async def construct_sections_tree(self, section_models: list[SectionModel], return_flat: bool) -> list[Section]:
        # stub: return flat list of Section objects with no subsections
        return [sm.to_entity([], []) for sm in section_models]

    async def count_subsections(self, section_id: uuid.UUID) -> int:
        return 0

    async def update(self, section: Section, index: Optional[NonNegativeInt] = None) -> None:
        model = await self._session.get(SectionModel, section.id)
        if not model:
            raise ValueError(f"Section {section.id} not found")
        for key, value in section.model_dump(exclude={'id', 'subsections', 'tasks'}).items():
            setattr(model, key, value)
        if index is not None:
            model.index = index
        await self._session.flush()


class SQLAlchemyTaskRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, task: Task, index: NonNegativeInt) -> None:
        model = TaskModel.from_entity(task, index)
        self._session.add(model)
        await self._session.flush()
        if task.attachments:
            for att in task.attachments:
                att_model = AttachmentModel.from_entity(att, 0)  # index placeholder
                self._session.add(att_model)

    async def get(self, task_id: uuid.UUID) -> Task:
        model = await self._session.get(TaskModel, task_id)
        if not model:
            raise ValueError(f"Task {task_id} not found")
        attachments = [att.to_entity() for att in model.attachments]
        return model.to_entity(attachments)

    async def get_entities(self, task_models: Sequence[TaskModel]) -> list[Task]:
        return [tm.to_entity([att.to_entity() for att in tm.attachments]) for tm in task_models]

    def get_entity(self, task_model: TaskModel) -> Task:
        attachments = [att.to_entity() for att in task_model.attachments]
        return task_model.to_entity(attachments)

    async def get_archived_tasks(self, user_id: uuid.UUID) -> list[Task]:
        return []

    async def get_overdue_tasks(self, user_id: uuid.UUID) -> list[Task]:
        return []

    async def get_tasks_by_due_to(self, not_before: datetime.date, not_after: datetime.date, user_id: uuid.UUID) -> list[Task]:
        return []

    async def search(self, user_id: uuid.UUID, query: str) -> list[Task]:
        return []

    async def remove(self, task: Task) -> None:
        model = await self._session.get(TaskModel, task.id)
        if model:
            await self._session.delete(model)
            await self._session.flush()

    async def delete_attachment(self, attachment: Attachment) -> None:
        model = await self._session.get(AttachmentModel, attachment.id)
        if model:
            await self._session.delete(model)
            await self._session.flush()

    async def update_or_create(self, task: Task, index: Optional[NonNegativeInt], must_exist: bool) -> None:
        if task.id:
            model = await self._session.get(TaskModel, task.id)
            if model:
                for key, value in task.model_dump(exclude={'id', 'attachments'}).items():
                    setattr(model, key, value)
                if index is not None:
                    model.index = index
                await self._session.flush()
                return
            elif must_exist:
                raise ValueError(f"Task {task.id} not found")
        await self.add(task, index or 0)

    async def update_or_create_bulk(self, section_tasks: list[Task]) -> None:
        for task in section_tasks:
            await self.update_or_create(task, None, must_exist=False)


class SQLAlchemyUserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def verify_user(self, user_id: uuid.UUID) -> None:
        user = await self._session.get(UserModel, user_id)
        if not user:
            raise ValueError("User not found")

    async def get_all_users(self) -> list[UserStats]:
        # placeholder for UserStats
        return []


class UserStats(BaseModel):
    user_id: uuid.UUID
    email: str
    task_count: int
    section_count: int


# ==========================
# Unit of Work (application/uow.py)
# ==========================

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
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self.session: AsyncSession = None  # type: ignore

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
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


# if running as script, code is importable; no main block needed.