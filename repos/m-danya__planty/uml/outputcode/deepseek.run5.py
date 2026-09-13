from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Any, ClassVar, Literal, Optional, Sequence
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import ForeignKey, Integer, String, Text, Boolean, DateTime, Date, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, update, delete, func
from abc import ABC, abstractmethod

# Type aliases
GUID = uuid.UUID
NonNegativeInt = int  # we'll enforce non-negative in Pydantic validators

# ---------------------------------------------------------------------------
# Domain model (Pydantic)
# ---------------------------------------------------------------------------

class Entity(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

class RecurrenceInfo(Entity):
    flexible_mode: bool
    period: int = Field(ge=1)
    type: Literal["daily", "weekly", "monthly", "yearly"]

class Attachment(Entity):
    added_at: Optional[datetime] = None
    aes_iv_b64: str
    aes_key_b64: str
    id: Optional[GUID] = None
    s3_file_key: str
    task_id: GUID

class Task(Entity):
    added_at: Optional[datetime] = None
    attachments: Optional[list[Attachment]] = Field(default_factory=list)
    content: Optional[str] = None
    description: Optional[str] = None
    due_to: Optional[date] = None
    id: Optional[GUID] = None
    is_archived: bool = False
    is_completed: bool = False
    recurrence: Optional[RecurrenceInfo] = None
    section_id: GUID
    title: str
    user_id: GUID

    @field_validator("due_to")
    @classmethod
    def check_recurrence_due_date(cls, v: Any, info: Any) -> Any:
        # simplistic validation – full logic would need recurrence context
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

    def toggle_archived(self) -> None:
        self.is_archived = not self.is_archived

class Section(Entity):
    added_at: Optional[datetime] = None
    has_subsections: bool = False
    has_tasks: bool = False
    id: Optional[GUID] = None
    parent_id: Optional[GUID] = None
    subsections: list[Section] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)
    title: str
    user_id: GUID

    def check_flags(self) -> Section:
        self.has_tasks = len(self.tasks) > 0
        self.has_subsections = len(self.subsections) > 0
        return self

    @classmethod
    def create_root_section(cls, user_id: GUID) -> Section:
        return cls(user_id=user_id, title="Root", parent_id=None)

    def is_root(self) -> bool:
        return self.parent_id is None

    def insert_subsection(self, subsection: Section, index: Optional[NonNegativeInt] = None) -> None:
        subsection.parent_id = self.id
        if index is not None and 0 <= index <= len(self.subsections):
            self.subsections.insert(index, subsection)
        else:
            self.subsections.append(subsection)
        self.check_flags()

    def insert_task(self, task: Task, index: Optional[NonNegativeInt] = None) -> None:
        task.section_id = self.id
        if index is not None and 0 <= index <= len(self.tasks):
            self.tasks.insert(index, task)
        else:
            self.tasks.append(task)
        self.check_flags()

    def remove_subsection(self, subsection: Section) -> Section:
        self.subsections = [s for s in self.subsections if s.id != subsection.id]
        self.check_flags()
        return subsection

    def remove_task(self, task: Task) -> Task:
        self.tasks = [t for t in self.tasks if t.id != task.id]
        self.check_flags()
        return task

    def shuffle_tasks(self) -> None:
        # Placeholder: reorder tasks based on some logic (e.g., maintain order)
        self.tasks.sort(key=lambda t: t.added_at or datetime.min)

    @staticmethod
    def move_section(section: Section, section_from: Section, section_to: Section, index: NonNegativeInt) -> None:
        removed = section_from.remove_subsection(section)
        section_to.insert_subsection(removed, index)

    @staticmethod
    def move_task(task_to_move: Task, section_from: Section, section_to: Section, index: NonNegativeInt) -> None:
        removed_task = section_from.remove_task(task_to_move)
        section_to.insert_task(removed_task, index)

class User(Entity):
    added_at: Optional[datetime] = None
    email: str
    id: Optional[GUID] = None

# ---------------------------------------------------------------------------
# Infrastructure: SQLAlchemy base and models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass

class AccessTokenModel(Base):
    __tablename__ = "access_tokens"
    id: Mapped[GUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[GUID] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(String(256))
    expires_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AttachmentModel(Base):
    __tablename__ = "attachments"
    id: Mapped[GUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_id: Mapped[GUID] = mapped_column(ForeignKey("tasks.id"))
    s3_file_key: Mapped[str] = mapped_column(String)
    aes_key_b64: Mapped[str] = mapped_column(String)
    aes_iv_b64: Mapped[str] = mapped_column(String)
    index: Mapped[int] = mapped_column(Integer, default=0)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    task: Mapped[TaskModel] = relationship("TaskModel", back_populates="attachments")

    @classmethod
    def from_entity(cls, attachment: Attachment, index: NonNegativeInt) -> AttachmentModel:
        return cls(
            id=attachment.id or uuid.uuid4(),
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

class TaskModel(Base):
    __tablename__ = "tasks"
    id: Mapped[GUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[GUID] = mapped_column(ForeignKey("users.id"))
    section_id: Mapped[GUID] = mapped_column(ForeignKey("sections.id"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    flexible_recurrence_mode: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    recurrence_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recurrence_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    index: Mapped[int] = mapped_column(Integer, default=0)

    section: Mapped[SectionModel] = relationship("SectionModel", back_populates="tasks")
    user: Mapped[UserModel] = relationship("UserModel", back_populates="tasks")
    attachments: Mapped[list[AttachmentModel]] = relationship("AttachmentModel", back_populates="task", order_by="AttachmentModel.index")

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
            added_at=task.added_at or datetime.utcnow(),
            is_completed=task.is_completed,
            is_archived=task.is_archived,
            flexible_recurrence_mode=recurrence.flexible_mode if recurrence else None,
            recurrence_period=recurrence.period if recurrence else None,
            recurrence_type=recurrence.type if recurrence else None,
            index=index,
        )

    def to_entity(self, attachments: list[Attachment]) -> Task:
        recurrence = None
        if self.recurrence_type:
            recurrence = RecurrenceInfo(
                flexible_mode=self.flexible_recurrence_mode or False,
                period=self.recurrence_period or 1,
                type=self.recurrence_type,
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

class SectionModel(Base):
    __tablename__ = "sections"
    id: Mapped[GUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[GUID] = mapped_column(ForeignKey("users.id"))
    parent_id: Mapped[Optional[GUID]] = mapped_column(ForeignKey("sections.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    index: Mapped[int] = mapped_column(Integer, default=0)
    has_subsections: Mapped[bool] = mapped_column(Boolean, default=False)
    has_tasks: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[UserModel] = relationship("UserModel", back_populates="sections")
    tasks: Mapped[list[TaskModel]] = relationship("TaskModel", back_populates="section", order_by="TaskModel.index")

    @classmethod
    def from_entity(cls, section: Section, index: NonNegativeInt) -> SectionModel:
        return cls(
            id=section.id or uuid.uuid4(),
            user_id=section.user_id,
            parent_id=section.parent_id,
            title=section.title,
            added_at=section.added_at or datetime.utcnow(),
            index=index,
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
            tasks=tasks,
            subsections=subsections,
        )

class UserModel(Base):
    __tablename__ = "users"
    id: Mapped[GUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sections: Mapped[list[SectionModel]] = relationship("SectionModel", back_populates="user")
    tasks: Mapped[list[TaskModel]] = relationship("TaskModel", back_populates="user")

    def to_entity(self) -> User:
        return User(
            id=self.id,
            email=self.email,
            added_at=self.added_at,
        )

# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------

class SQLAlchemySectionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, section: Section, index: NonNegativeInt) -> None:
        model = SectionModel.from_entity(section, index)
        self.session.add(model)

    async def get(self, section_id: GUID, with_direct_subsections: bool = False) -> Section:
        model = await self.session.get(SectionModel, section_id)
        if not model:
            raise ValueError("Section not found")
        # Load subsections and tasks
        subsections = []
        tasks = []
        if with_direct_subsections:
            # fetch direct subsections and tasks (simplified; ignore nested)
            pass
        return model.to_entity(tasks, subsections)

    async def get_all_without_tasks(
        self, user_id: GUID, leaves_only: bool = False, as_tree: bool = False
    ) -> list[Section]:
        stmt = select(SectionModel).where(SectionModel.user_id == user_id)
        if leaves_only:
            stmt = stmt.where(SectionModel.has_tasks == False)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [m.to_entity([], []) for m in models]  # simplified

    async def update(self, section: Section, index: Optional[NonNegativeInt] = None) -> None:
        model = await self.session.get(SectionModel, section.id)
        if not model:
            raise ValueError("Section not found")
        # update fields
        model.title = section.title
        if index is not None:
            model.index = index
        # update flags etc.
        model.has_subsections = section.has_subsections
        model.has_tasks = section.has_tasks

    async def count_subsections(self, section_id: GUID) -> int:
        stmt = select(func.count()).select_from(SectionModel).where(SectionModel.parent_id == section_id)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def construct_sections_tree(
        self, section_models: list[SectionModel], return_flat: bool = False
    ) -> list[Section]:
        # Simplified: just convert each to entity; real tree building would need parent-child mapping
        return [m.to_entity([], []) for m in section_models]

class SQLAlchemyTaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, task: Task, index: NonNegativeInt) -> None:
        model = TaskModel.from_entity(task, index)
        self.session.add(model)

    async def get(self, task_id: GUID) -> Task:
        model = await self.session.get(TaskModel, task_id)
        if not model:
            raise ValueError("Task not found")
        # Load attachments
        attachments = [a.to_entity() for a in (model.attachments or [])]
        return model.to_entity(attachments)

    async def get_entity(self, task_model: TaskModel) -> Task:
        attachments = [a.to_entity() for a in (task_model.attachments or [])]
        return task_model.to_entity(attachments)

    async def get_entities(self, task_models: Sequence[TaskModel]) -> list[Task]:
        return [await self.get_entity(tm) for tm in task_models]

    async def get_archived_tasks(self, user_id: GUID) -> list[Task]:
        stmt = select(TaskModel).where(TaskModel.user_id == user_id, TaskModel.is_archived == True)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return await self.get_entities(models)

    async def get_overdue_tasks(self, user_id: GUID) -> list[Task]:
        today = date.today()
        stmt = select(TaskModel).where(
            TaskModel.user_id == user_id,
            TaskModel.is_archived == False,
            TaskModel.is_completed == False,
            TaskModel.due_to < today,
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return await self.get_entities(models)

    async def get_tasks_by_due_to(self, not_before: date, not_after: date, user_id: GUID) -> list[Task]:
        stmt = select(TaskModel).where(
            TaskModel.user_id == user_id,
            TaskModel.due_to >= not_before,
            TaskModel.due_to <= not_after,
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return await self.get_entities(models)

    async def search(self, user_id: GUID, query: str) -> list[Task]:
        stmt = select(TaskModel).where(
            TaskModel.user_id == user_id,
            (TaskModel.title.ilike(f"%{query}%") | TaskModel.description.ilike(f"%{query}%")),
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return await self.get_entities(models)

    async def remove(self, task: Task) -> None:
        model = await self.session.get(TaskModel, task.id)
        if model:
            await self.session.delete(model)

    async def delete_attachment(self, attachment: Attachment) -> None:
        model = await self.session.get(AttachmentModel, attachment.id)
        if model:
            await self.session.delete(model)

    async def update_or_create(self, task: Task, index: Optional[NonNegativeInt] = None, must_exist: bool = False) -> None:
        if task.id:
            model = await self.session.get(TaskModel, task.id)
            if model:
                # update
                model.title = task.title
                model.description = task.description
                model.due_to = task.due_to
                model.is_completed = task.is_completed
                model.is_archived = task.is_archived
                if index is not None:
                    model.index = index
                # update recurrence fields
                if task.recurrence:
                    model.flexible_recurrence_mode = task.recurrence.flexible_mode
                    model.recurrence_period = task.recurrence.period
                    model.recurrence_type = task.recurrence.type
                else:
                    model.flexible_recurrence_mode = None
                    model.recurrence_period = None
                    model.recurrence_type = None
                return
            elif must_exist:
                raise ValueError("Task not found")
        # create new
        model = TaskModel.from_entity(task, index or 0)
        self.session.add(model)

    async def update_or_create_bulk(self, section_tasks: list[Task]) -> None:
        for i, task in enumerate(section_tasks):
            await self.update_or_create(task, index=i)

class SQLAlchemyUserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def verify_user(self, user_id: GUID) -> None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        if not result.scalar():
            raise ValueError("User not found")

    async def get_all_users(self) -> list[User]:
        stmt = select(UserModel)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [m.to_entity() for m in models]

# ---------------------------------------------------------------------------
# Unit of Work
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
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self.session: AsyncSession | None = None

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
        if self.session:
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session:
            await self.session.rollback()