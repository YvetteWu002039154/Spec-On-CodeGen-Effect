from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal, Optional, Sequence, TypeAlias

from pydantic import BaseModel, ConfigDict
from sqlalchemy import ForeignKey, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import UUID as SQL_UUID, Date, DateTime, Boolean, Integer, String

NonNegativeInt: TypeAlias = int


# =============================================================================
# Domain entities (Pydantic models)
# =============================================================================

class Entity(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


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
    type: Literal["daily", "weekly", "monthly", "yearly"]  # type of recurrence


class Section(Entity):
    added_at: Optional[datetime] = None
    has_subsections: bool = False
    has_tasks: bool = False
    id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None
    subsections: list[Section] = []  # populated outside model
    tasks: list[Task] = []            # populated outside model
    title: str
    user_id: uuid.UUID

    def check_flags(self) -> Section:
        """Ensure flags are consistent with actual content."""
        self.has_subsections = bool(self.subsections)
        self.has_tasks = bool(self.tasks)
        return self

    @classmethod
    def create_root_section(cls, user_id: uuid.UUID) -> Section:
        return cls(title="Root", user_id=user_id)

    def insert_subsection(self, subsection: Section, index: Optional[NonNegativeInt] = None) -> None:
        """Insert subsection at given index (or end)."""
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
    def move_section(section: Section, section_from: Section, section_to: Section,
                     index: NonNegativeInt) -> None:
        """Move `section` from `section_from` to `section_to` at `index`."""
        section_from.remove_subsection(section)
        section_to.insert_subsection(section, index)

    @staticmethod
    def move_task(task_to_move: Task, section_from: Section, section_to: Section,
                  index: NonNegativeInt) -> None:
        section_from.remove_task(task_to_move)
        section_to.insert_task(task_to_move, index)

    def remove_subsection(self, subsection: Section) -> Section:
        """Remove a subsection and return it."""
        self.subsections = [s for s in self.subsections if s.id != subsection.id]
        self.check_flags()
        return subsection

    def remove_task(self, task: Task) -> Task:
        self.tasks = [t for t in self.tasks if t.id != task.id]
        self.check_flags()
        return task

    def shuffle_tasks(self) -> None:
        """Randomise task order (placeholder)."""
        import random
        random.shuffle(self.tasks)


class Task(Entity):
    added_at: Optional[datetime] = None
    attachments: Optional[list[Attachment]] = None
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

    def add_attachment(self, attachment: Attachment) -> None:
        if self.attachments is None:
            self.attachments = []
        self.attachments.append(attachment)
        attachment.task_id = self.id

    def archive(self) -> None:
        self.is_archived = True

    def mark_completed(self, auto_archive: bool = False) -> None:
        self.is_completed = True
        if auto_archive:
            self.archive()

    def remove_attachment(self, attachment: Attachment) -> None:
        if self.attachments:
            self.attachments = [a for a in self.attachments if a.id != attachment.id]

    def toggle_archived(self) -> None:
        self.is_archived = not self.is_archived

    def toggle_completed(self, auto_archive: bool = False) -> None:
        if self.is_completed:
            self.is_completed = False
        else:
            self.mark_completed(auto_archive)

    def unarchive(self) -> None:
        self.is_archived = False

    @staticmethod
    def check_recurrence_due_date(values: Any) -> Any:
        """Validator (placeholder) that ensures due date aligns with recurrence."""
        return values


class User(Entity):
    added_at: Optional[datetime] = None
    email: str
    id: Optional[uuid.UUID] = None


# =============================================================================
# Infrastructure models (SQLAlchemy)
# =============================================================================

class Base(DeclarativeBase):
    pass


class AccessTokenModel(Base):
    __tablename__ = "access_tokens"
    id: Mapped[uuid.UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid.uuid4)


class AttachmentModel(Base):
    __tablename__ = "attachments"
    id: Mapped[uuid.UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid.uuid4)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    aes_iv_b64: Mapped[str] = mapped_column(String)
    aes_key_b64: Mapped[str] = mapped_column(String)
    s3_file_key: Mapped[str] = mapped_column(String)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"))
    index: Mapped[int] = mapped_column(Integer)

    task = relationship("TaskModel", back_populates="attachments")

    @classmethod
    def from_entity(cls, attachment: Attachment, index: NonNegativeInt) -> AttachmentModel:
        return cls(
            id=attachment.id or uuid.uuid4(),
            added_at=attachment.added_at or datetime.utcnow(),
            aes_iv_b64=attachment.aes_iv_b64,
            aes_key_b64=attachment.aes_key_b64,
            s3_file_key=attachment.s3_file_key,
            task_id=attachment.task_id,
            index=index,
        )

    def to_entity(self) -> Attachment:
        return Attachment(
            id=self.id,
            added_at=self.added_at,
            aes_iv_b64=self.aes_iv_b64,
            aes_key_b64=self.aes_key_b64,
            s3_file_key=self.s3_file_key,
            task_id=self.task_id,
        )


class UserModel(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid.uuid4)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    email: Mapped[str] = mapped_column(String, unique=True)

    sections = relationship("SectionModel", back_populates="user")
    tasks = relationship("TaskModel", back_populates="user")

    def to_entity(self) -> User:
        return User(
            id=self.id,
            added_at=self.added_at,
            email=self.email,
        )


class SectionModel(Base):
    __tablename__ = "sections"
    id: Mapped[uuid.UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid.uuid4)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    has_subsections: Mapped[bool] = mapped_column(Boolean, default=False)
    has_tasks: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQL_UUID, ForeignKey("sections.id"), nullable=True)
    index: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    user = relationship("UserModel", back_populates="sections")
    tasks: Mapped[list[TaskModel]] = relationship(
        "TaskModel", back_populates="section", order_by="TaskModel.index"
    )

    @classmethod
    def from_entity(cls, section: Section, index: NonNegativeInt) -> SectionModel:
        return cls(
            id=section.id or uuid.uuid4(),
            added_at=section.added_at or datetime.utcnow(),
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
            parent_id=section.parent_id,
            index=index,
            title=section.title,
            user_id=section.user_id,
        )

    def to_entity(self, tasks: list[Task], subsections: list[Section]) -> Section:
        return Section(
            id=self.id,
            added_at=self.added_at,
            has_subsections=self.has_subsections,
            has_tasks=self.has_tasks,
            parent_id=self.parent_id,
            subsections=subsections,
            tasks=tasks,
            title=self.title,
            user_id=self.user_id,
        )


class TaskModel(Base):
    __tablename__ = "tasks"
    id: Mapped[uuid.UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid.uuid4)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    due_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    flexible_recurrence_mode: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    index: Mapped[int] = mapped_column(Integer)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recurrence_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String)
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sections.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    section = relationship("SectionModel", back_populates="tasks")
    user = relationship("UserModel", back_populates="tasks")
    attachments: Mapped[list[AttachmentModel]] = relationship(
        "AttachmentModel", back_populates="task", order_by="AttachmentModel.index"
    )

    @classmethod
    def from_entity(cls, task: Task, index: NonNegativeInt) -> TaskModel:
        rec = task.recurrence
        return cls(
            id=task.id or uuid.uuid4(),
            added_at=task.added_at or datetime.utcnow(),
            description=task.description,
            due_to=task.due_to,
            flexible_recurrence_mode=rec.flexible_mode if rec else None,
            index=index,
            is_archived=task.is_archived,
            is_completed=task.is_completed,
            recurrence_period=rec.period if rec else None,
            recurrence_type=rec.type if rec else None,
            title=task.title,
            section_id=task.section_id,
            user_id=task.user_id,
        )

    def to_entity(self, attachments: list[Attachment]) -> Task:
        recurrence = None
        if self.recurrence_type is not None and self.recurrence_period is not None:
            recurrence = RecurrenceInfo(
                flexible_mode=self.flexible_recurrence_mode or False,
                period=self.recurrence_period,
                type=self.recurrence_type,
            )
        return Task(
            id=self.id,
            added_at=self.added_at,
            attachments=attachments,
            content=None,  # content not stored in DB model
            description=self.description,
            due_to=self.due_to,
            is_archived=self.is_archived,
            is_completed=self.is_completed,
            recurrence=recurrence,
            section_id=self.section_id,
            title=self.title,
            user_id=self.user_id,
        )


# =============================================================================
# Repositories
# =============================================================================

class SQLAlchemySectionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, section: Section, index: NonNegativeInt) -> None:
        model = SectionModel.from_entity(section, index)
        self.session.add(model)

    async def construct_sections_tree(
        self, section_models: list[SectionModel], return_flat: bool
    ) -> list[Section]:
        # Build domain sections with populated subsections/tasks
        # This is a simplified conversion; a real tree builder would link children
        entities = []
        id_map = {}
        for model in section_models:
            # tasks and subsections will be populated in second pass
            entities.append(model.to_entity(tasks=[], subsections=[]))
            id_map[model.id] = entities[-1]
        # Second pass: link parent/children
        for model, section in zip(section_models, entities):
            if model.parent_id and model.parent_id in id_map:
                parent_section = id_map[model.parent_id]
                parent_section.subsections.append(section)
                parent_section.has_subsections = True
            # tasks are already attached when constructing from joined load
            # but we need to populate tasks from model.tasks
            # We can do that here:
            section.tasks = []  # clear placeholder
            for task_model in model.tasks:
                task_entity = await self._session_get_task_entity(task_model)
                section.tasks.append(task_entity)
            section.check_flags()
        return entities

    async def count_subsections(self, section_id: uuid.UUID) -> int:
        stmt = select(SectionModel).where(SectionModel.parent_id == section_id)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def get(self, section_id: uuid.UUID, with_direct_subsections: bool) -> Section:
        stmt = select(SectionModel).where(SectionModel.id == section_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        subsections = []
        if with_direct_subsections:
            sub_models = await self._get_direct_subsections(model.id)
            subsections = [m.to_entity([], []) for m in sub_models]  # simplified
        tasks = [await self._model_to_task(m) for m in model.tasks]
        return model.to_entity(tasks=tasks, subsections=subsections)

    async def get_all_without_tasks(
        self, user_id: uuid.UUID, leaves_only: bool, as_tree: bool
    ) -> list[Section]:
        stmt = select(SectionModel).where(SectionModel.user_id == user_id)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        # Apply filters if needed (leaves_only: only those with has_tasks==False and has_subsections==False)
        if leaves_only:
            models = [m for m in models if not m.has_tasks and not m.has_subsections]
        return [m.to_entity([], []) for m in models]

    async def update(self, section: Section, index: Optional[NonNegativeInt]) -> None:
        model = await self.session.get(SectionModel, section.id)
        if model:
            for key, value in section.dict(exclude_unset=True).items():
                setattr(model, key, value)
            if index is not None:
                model.index = index

    async def _get_direct_subsections(self, parent_id: uuid.UUID) -> list[SectionModel]:
        stmt = select(SectionModel).where(SectionModel.parent_id == parent_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _model_to_task(self, model: TaskModel) -> Task:
        attachments = [am.to_entity() for am in model.attachments]
        return model.to_entity(attachments)

    async def _session_get_task_entity(self, model: TaskModel) -> Task:
        # For in-memory conversion; avoid extra query if already loaded
        attachments = [am.to_entity() for am in model.attachments]
        return model.to_entity(attachments)


class SQLAlchemyTaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, task: Task, index: NonNegativeInt) -> None:
        model = TaskModel.from_entity(task, index)
        self.session.add(model)

    async def delete_attachment(self, attachment: Attachment) -> None:
        model = await self.session.get(AttachmentModel, attachment.id)
        if model:
            await self.session.delete(model)

    async def get(self, task_id: uuid.UUID) -> Task:
        stmt = select(TaskModel).where(TaskModel.id == task_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        attachments = [a.to_entity() for a in model.attachments]
        return model.to_entity(attachments)

    async def get_archived_tasks(self, user_id: uuid.UUID) -> list[Task]:
        stmt = select(TaskModel).where(TaskModel.user_id == user_id, TaskModel.is_archived == True)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [m.to_entity([a.to_entity() for a in m.attachments]) for m in models]

    async def get_entities(self, task_models: Sequence[TaskModel]) -> list[Task]:
        return [m.to_entity([a.to_entity() for a in m.attachments]) for m in task_models]

    async def get_entity(self, task_model: TaskModel) -> Task:
        return task_model.to_entity([a.to_entity() for a in task_model.attachments])

    async def get_overdue_tasks(self, user_id: uuid.UUID) -> list[Task]:
        today = date.today()
        stmt = select(TaskModel).where(
            TaskModel.user_id == user_id,
            TaskModel.due_to < today,
            TaskModel.is_completed == False,
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [m.to_entity([a.to_entity() for a in m.attachments]) for m in models]

    async def get_tasks_by_due_to(
        self, not_before: date, not_after: date, user_id: uuid.UUID
    ) -> list[Task]:
        stmt = select(TaskModel).where(
            TaskModel.user_id == user_id,
            TaskModel.due_to >= not_before,
            TaskModel.due_to <= not_after,
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [m.to_entity([a.to_entity() for a in m.attachments]) for m in models]

    async def remove(self, task: Task) -> None:
        model = await self.session.get(TaskModel, task.id)
        if model:
            await self.session.delete(model)

    async def search(self, user_id: uuid.UUID, query: str) -> list[Task]:
        stmt = select(TaskModel).where(
            TaskModel.user_id == user_id,
            TaskModel.title.ilike(f"%{query}%"),
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [m.to_entity([a.to_entity() for a in m.attachments]) for m in models]

    async def update_or_create(
        self, task: Task, index: Optional[NonNegativeInt], must_exist: bool
    ) -> None:
        model = None
        if task.id:
            model = await self.session.get(TaskModel, task.id)
        if model:
            for key, value in task.dict(exclude_unset=True).items():
                if key in {"attachments", "recurrence", "content"}:
                    continue
                setattr(model, key, value)
            if task.recurrence:
                model.recurrence_type = task.recurrence.type
                model.recurrence_period = task.recurrence.period
                model.flexible_recurrence_mode = task.recurrence.flexible_mode
            if index is not None:
                model.index = index
        elif must_exist:
            raise ValueError("Task must exist but not found")
        else:
            new_model = TaskModel.from_entity(task, index or 0)
            self.session.add(new_model)

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

    async def verify_user(self, user_id: uuid.UUID) -> None:
        model = await self.session.get(UserModel, user_id)
        if not model:
            raise ValueError("User does not exist")


# =============================================================================
# Unit of Work
# =============================================================================

class IUnitOfWork:
    section_repo: SQLAlchemySectionRepository
    task_repo: SQLAlchemyTaskRepository
    user_repo: SQLAlchemyUserRepository

    async def commit(self) -> None:
        raise NotImplementedError

    async def rollback(self) -> None:
        raise NotImplementedError


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self.session: Optional[AsyncSession] = None

    async def __aenter__(self):
        self.session = self.session_factory()
        self.section_repo = SQLAlchemySectionRepository(self.session)
        self.task_repo = SQLAlchemyTaskRepository(self.session)
        self.user_repo = SQLAlchemyUserRepository(self.session)
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def commit(self) -> None:
        if self.session:
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session:
            await self.session.rollback()