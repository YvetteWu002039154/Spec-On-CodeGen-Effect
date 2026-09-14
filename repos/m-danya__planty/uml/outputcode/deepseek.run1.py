from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Literal, Optional, Any, Sequence
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# ---------------------------------------------------------------------------
# planty/domain/task.py
# ---------------------------------------------------------------------------

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
    flexible_mode: bool = False
    period: int
    type: Literal["daily", "weekly", "monthly", "yearly"]


class User(Entity):
    added_at: Optional[datetime] = None
    email: str
    id: Optional[UUID] = None


class Task(Entity):
    added_at: Optional[datetime] = None
    attachments: list[Attachment] = []
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
        self.attachments.append(attachment)

    def remove_attachment(self, attachment: Attachment) -> None:
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
            if auto_archive:
                self.unarchive()
        else:
            self.mark_completed(auto_archive)

    def check_recurrence_due_date(self, values: Any) -> Any:
        # placeholder – actual logic could compute next due date based on recurrence
        return values


class Section(Entity):
    added_at: Optional[datetime] = None
    has_subsections: bool = False
    has_tasks: bool = False
    id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    subsections: list[Section] = []
    tasks: list[Task] = []
    title: str
    user_id: UUID

    @classmethod
    def create_root_section(cls, user_id: UUID) -> Section:
        return cls(
            id=uuid4(),
            user_id=user_id,
            title="Root",
            parent_id=None,
        )

    def check_flags(self) -> Section:
        self.has_subsections = len(self.subsections) > 0
        self.has_tasks = len(self.tasks) > 0
        return self

    def is_root(self) -> bool:
        return self.parent_id is None

    def insert_subsection(self, subsection: Section, index: Optional[int] = None) -> None:
        if index is None:
            self.subsections.append(subsection)
        else:
            self.subsections.insert(index, subsection)
        subsection.parent_id = self.id
        self.check_flags()

    def remove_subsection(self, subsection: Section) -> Section:
        self.subsections = [s for s in self.subsections if s.id != subsection.id]
        subsection.parent_id = None
        self.check_flags()
        return subsection

    def insert_task(self, task: Task, index: Optional[int] = None) -> None:
        if index is None:
            self.tasks.append(task)
        else:
            self.tasks.insert(index, task)
        task.section_id = self.id
        self.check_flags()

    def remove_task(self, task: Task) -> Task:
        self.tasks = [t for t in self.tasks if t.id != task.id]
        task.section_id = None  # caller should reassign
        self.check_flags()
        return task

    def move_section(self, section: Section, section_from: Section, section_to: Section, index: int) -> None:
        section_from.remove_subsection(section)
        section_to.insert_subsection(section, index)

    def move_task(self, task_to_move: Task, section_from: Section, section_to: Section, index: int) -> None:
        section_from.remove_task(task_to_move)
        section_to.insert_task(task_to_move, index)

    def shuffle_tasks(self) -> None:
        import random
        random.shuffle(self.tasks)


# ---------------------------------------------------------------------------
# planty/infrastructure/models.py
# ---------------------------------------------------------------------------
# Minimal base for SQLAlchemy models
class Base(DeclarativeBase):
    pass


class AccessTokenModel(Base):
    __tablename__ = "access_tokens"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False)
    token: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)


class UserModel(Base):
    __tablename__ = "users"
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    email: Mapped[str] = mapped_column(unique=True)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sections: Mapped[list[SectionModel]] = relationship(back_populates="user")
    tasks: Mapped[list[TaskModel]] = relationship(back_populates="user")

    def to_entity(self) -> User:
        return User(
            added_at=self.added_at,
            email=self.email,
            id=self.id,
        )


class SectionModel(Base):
    __tablename__ = "sections"
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    has_subsections: Mapped[bool] = mapped_column(default=False)
    has_tasks: Mapped[bool] = mapped_column(default=False)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    index: Mapped[int] = mapped_column()
    parent_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID, nullable=True)
    title: Mapped[str] = mapped_column()
    user_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False)
    user: Mapped[UserModel] = relationship(back_populates="sections")
    tasks: Mapped[list[TaskModel]] = relationship(back_populates="section")

    @classmethod
    def from_entity(cls, section: Section, index: int) -> SectionModel:
        return cls(
            added_at=section.added_at or datetime.utcnow(),
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
            id=section.id or uuid4(),
            index=index,
            parent_id=section.parent_id,
            title=section.title,
            user_id=section.user_id,
        )

    def to_entity(self, tasks: list[Task], subsections: list[Section]) -> Section:
        return Section(
            added_at=self.added_at,
            has_subsections=self.has_subsections,
            has_tasks=self.has_tasks,
            id=self.id,
            parent_id=self.parent_id,
            subsections=subsections,
            tasks=tasks,
            title=self.title,
            user_id=self.user_id,
        )


class TaskModel(Base):
    __tablename__ = "tasks"
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    description: Mapped[Optional[str]] = mapped_column()
    due_to: Mapped[Optional[date]] = mapped_column()
    flexible_recurrence_mode: Mapped[Optional[bool]] = mapped_column()
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    index: Mapped[int] = mapped_column()
    is_archived: Mapped[bool] = mapped_column(default=False)
    is_completed: Mapped[bool] = mapped_column(default=False)
    recurrence_period: Mapped[Optional[int]] = mapped_column()
    recurrence_type: Mapped[Optional[str]] = mapped_column()
    section_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False)
    title: Mapped[str] = mapped_column()
    user_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False)
    section: Mapped[SectionModel] = relationship(back_populates="tasks")
    user: Mapped[UserModel] = relationship(back_populates="tasks")
    attachments: Mapped[list[AttachmentModel]] = relationship(back_populates="task")

    @classmethod
    def from_entity(cls, task: Task, index: int) -> TaskModel:
        return cls(
            added_at=task.added_at or datetime.utcnow(),
            description=task.description,
            due_to=task.due_to,
            flexible_recurrence_mode=task.recurrence.flexible_mode if task.recurrence else None,
            id=task.id or uuid4(),
            index=index,
            is_archived=task.is_archived,
            is_completed=task.is_completed,
            recurrence_period=task.recurrence.period if task.recurrence else None,
            recurrence_type=task.recurrence.type if task.recurrence else None,
            section_id=task.section_id,
            title=task.title,
            user_id=task.user_id,
        )

    def to_entity(self, attachments: list[Attachment]) -> Task:
        recurrence = None
        if self.recurrence_type:
            recurrence = RecurrenceInfo(
                flexible_mode=self.flexible_recurrence_mode or False,
                period=self.recurrence_period or 0,
                type=self.recurrence_type,  # type: ignore
            )
        return Task(
            added_at=self.added_at,
            attachments=attachments,
            description=self.description,
            due_to=self.due_to,
            id=self.id,
            is_archived=self.is_archived,
            is_completed=self.is_completed,
            recurrence=recurrence,
            section_id=self.section_id,
            title=self.title,
            user_id=self.user_id,
        )


class AttachmentModel(Base):
    __tablename__ = "attachments"
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    aes_iv_b64: Mapped[str] = mapped_column()
    aes_key_b64: Mapped[str] = mapped_column()
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    index: Mapped[int] = mapped_column()
    s3_file_key: Mapped[str] = mapped_column()
    task_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False)
    task: Mapped[TaskModel] = relationship(back_populates="attachments")

    @classmethod
    def from_entity(cls, attachment: Attachment, index: int) -> AttachmentModel:
        return cls(
            added_at=attachment.added_at or datetime.utcnow(),
            aes_iv_b64=attachment.aes_iv_b64,
            aes_key_b64=attachment.aes_key_b64,
            id=attachment.id or uuid4(),
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


# ---------------------------------------------------------------------------
# planty/application/uow.py  (IUnitOfWork + SqlAlchemyUnitOfWork)
# ---------------------------------------------------------------------------

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
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory
        self.session: Optional[AsyncSession] = None

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self.session = self.session_factory()
        self.section_repo = SQLAlchemySectionRepository(self.session)
        self.task_repo = SQLAlchemyTaskRepository(self.session)
        self.user_repo = SQLAlchemyUserRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        if self.session:
            await self.session.close()

    async def commit(self) -> None:
        if self.session:
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session:
            await self.session.rollback()


# ---------------------------------------------------------------------------
# planty/infrastructure/repositories.py
# ---------------------------------------------------------------------------

from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

# Simple UserStats DTO
class UserStats:
    def __init__(self, user_id: UUID, email: str, task_count: int, section_count: int):
        self.user_id = user_id
        self.email = email
        self.task_count = task_count
        self.section_count = section_count


class SQLAlchemySectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, section: Section, index: int) -> None:
        model = SectionModel.from_entity(section, index)
        self.session.add(model)

    async def get(self, section_id: UUID, with_direct_subsections: bool = False) -> Section:
        stmt = select(SectionModel).where(SectionModel.id == section_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        # fetch tasks and subsections if needed
        task_models = []
        subsection_models = []
        if with_direct_subsections:
            subsection_models = (await self.session.execute(
                select(SectionModel).where(SectionModel.parent_id == section_id)
            )).scalars().all()
        # tasks are loaded via relationship, but we'll build entity from model
        tasks = [t.to_entity([]) for t in model.tasks]  # attachments not loaded
        subsections = [s.to_entity([], []) for s in subsection_models]
        return model.to_entity(tasks, subsections)

    async def get_all_without_tasks(self, user_id: UUID, leaves_only: bool = False, as_tree: bool = False) -> list[Section]:
        stmt = select(SectionModel).where(SectionModel.user_id == user_id)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        # simplified: just convert to entities without full nesting
        sections = [m.to_entity([], []) for m in models]
        if leaves_only:
            sections = [s for s in sections if s.has_tasks or s.has_subsections]
        return sections

    async def count_subsections(self, section_id: UUID) -> int:
        stmt = select(func.count(SectionModel.id)).where(SectionModel.parent_id == section_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def construct_sections_tree(self, section_models: list[SectionModel], return_flat: bool = False) -> list[Section]:
        # placeholder
        sections = [m.to_entity([], []) for m in section_models]
        if return_flat:
            return sections
        # simplified: no tree building; just return list
        return sections

    async def update(self, section: Section, index: Optional[int] = None) -> None:
        stmt = (
            update(SectionModel)
            .where(SectionModel.id == section.id)
            .values(
                title=section.title,
                has_subsections=section.has_subsections,
                has_tasks=section.has_tasks,
            )
        )
        if index is not None:
            stmt = stmt.values(index=index)
        await self.session.execute(stmt)


class SQLAlchemyTaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, task: Task, index: int) -> None:
        model = TaskModel.from_entity(task, index)
        self.session.add(model)

    async def get(self, task_id: UUID) -> Task:
        stmt = select(TaskModel).where(TaskModel.id == task_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        attachments = [a.to_entity() for a in model.attachments]
        return model.to_entity(attachments)

    async def get_entity(self, task_model: TaskModel) -> Task:
        attachments = [a.to_entity() for a in task_model.attachments]
        return task_model.to_entity(attachments)

    async def get_entities(self, task_models: Sequence[TaskModel]) -> list[Task]:
        return [await self.get_entity(m) for m in task_models]

    async def get_archived_tasks(self, user_id: UUID) -> list[Task]:
        stmt = select(TaskModel).where(and_(TaskModel.user_id == user_id, TaskModel.is_archived == True))
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return await self.get_entities(models)

    async def get_overdue_tasks(self, user_id: UUID) -> list[Task]:
        today = date.today()
        stmt = select(TaskModel).where(and_(
            TaskModel.user_id == user_id,
            TaskModel.due_to < today,
            TaskModel.is_completed == False,
        ))
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return await self.get_entities(models)

    async def get_tasks_by_due_to(self, not_before: date, not_after: date, user_id: UUID) -> list[Task]:
        stmt = select(TaskModel).where(and_(
            TaskModel.user_id == user_id,
            TaskModel.due_to >= not_before,
            TaskModel.due_to <= not_after,
        ))
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return await self.get_entities(models)

    async def search(self, user_id: UUID, query: str) -> list[Task]:
        pattern = f"%{query}%"
        stmt = select(TaskModel).where(and_(
            TaskModel.user_id == user_id,
            TaskModel.title.ilike(pattern),
        ))
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return await self.get_entities(models)

    async def remove(self, task: Task) -> None:
        stmt = delete(TaskModel).where(TaskModel.id == task.id)
        await self.session.execute(stmt)

    async def update_or_create(self, task: Task, index: Optional[int] = None, must_exist: bool = False) -> None:
        stmt = select(TaskModel).where(TaskModel.id == task.id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            # update
            values = {
                "title": task.title,
                "description": task.description,
                "due_to": task.due_to,
                "is_archived": task.is_archived,
                "is_completed": task.is_completed,
                "section_id": task.section_id,
            }
            if task.recurrence:
                values.update({
                    "flexible_recurrence_mode": task.recurrence.flexible_mode,
                    "recurrence_period": task.recurrence.period,
                    "recurrence_type": task.recurrence.type,
                })
            if index is not None:
                values["index"] = index
            stmt = update(TaskModel).where(TaskModel.id == task.id).values(**values)
            await self.session.execute(stmt)
        else:
            if must_exist:
                raise ValueError("Task does not exist")
            model = TaskModel.from_entity(task, index if index is not None else 0)
            self.session.add(model)

    async def update_or_create_bulk(self, section_tasks: list[Task]) -> None:
        for task in section_tasks:
            await self.update_or_create(task)

    async def delete_attachment(self, attachment: Attachment) -> None:
        stmt = delete(AttachmentModel).where(AttachmentModel.id == attachment.id)
        await self.session.execute(stmt)


class SQLAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def verify_user(self, user_id: UUID) -> None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        if not result.scalar_one_or_none():
            raise ValueError("User not found")

    async def get_all_users(self) -> list[UserStats]:
        stmt = select(UserModel)
        result = await self.session.execute(stmt)
        users = result.scalars().all()
        stats = []
        for u in users:
            task_count = len(u.tasks)
            section_count = len(u.sections)
            stats.append(UserStats(u.id, u.email, task_count, section_count))
        return stats