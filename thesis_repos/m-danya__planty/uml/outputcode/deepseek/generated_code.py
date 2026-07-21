import uuid
from datetime import date, datetime
from typing import Any, Literal, Optional, Sequence, Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import String, ForeignKey, select, update, delete, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.types import TypeDecorator, CHAR

# NonNegativeInt type (alias)
NonNegativeInt = Annotated[int, Field(ge=0)]

# Custom GUID type for SQLAlchemy (from models.py)
class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PGUUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value

# SQLAlchemy Base
class Base(DeclarativeBase):
    pass

# ===========================
# DOMAIN ENTITIES (Pydantic)
# ===========================

class Entity(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

class User(Entity):
    id: Optional[uuid.UUID] = None
    email: str
    added_at: Optional[datetime] = None

class RecurrenceInfo(Entity):
    type: Literal['daily', 'weekly', 'monthly', 'yearly']
    period: int = 1
    flexible_mode: bool = False

class Attachment(Entity):
    id: Optional[uuid.UUID] = None
    task_id: uuid.UUID
    s3_file_key: str
    aes_key_b64: str
    aes_iv_b64: str
    added_at: Optional[datetime] = None

class Task(Entity):
    id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    section_id: uuid.UUID
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
        object.__setattr__(self, 'is_archived', True)

    def unarchive(self) -> None:
        object.__setattr__(self, 'is_archived', False)

    def toggle_archived(self) -> None:
        if self.is_archived:
            self.unarchive()
        else:
            self.archive()

    def mark_completed(self, auto_archive: bool) -> None:
        object.__setattr__(self, 'is_completed', True)
        if auto_archive:
            self.archive()

    def toggle_completed(self, auto_archive: bool) -> None:
        if self.is_completed:
            object.__setattr__(self, 'is_completed', False)
            self.unarchive()
        else:
            self.mark_completed(auto_archive)

    @model_validator(mode='after')
    def check_recurrence_due_date(self) -> 'Task':
        if self.recurrence and not self.due_to:
            raise ValueError("Due date must be set if task has recurrence.")
        return self

    model_config = ConfigDict(validate_assignment=True)

class Section(Entity):
    id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    title: str
    has_subsections: bool = False
    has_tasks: bool = False
    subsections: list['Section'] = []
    tasks: list[Task] = []
    added_at: Optional[datetime] = None

    def check_flags(self) -> 'Section':
        # Enforce flag consistency
        object.__setattr__(self, 'has_subsections', len(self.subsections) > 0)
        object.__setattr__(self, 'has_tasks', len(self.tasks) > 0)
        return self

    @classmethod
    def create_root_section(cls, user_id: uuid.UUID) -> 'Section':
        return cls(user_id=user_id, title="Root", parent_id=None)

    def is_root(self) -> bool:
        return self.parent_id is None

    def insert_subsection(self, subsection: 'Section', index: Optional[NonNegativeInt] = None) -> None:
        subsection.parent_id = self.id
        if index is not None:
            self.subsections.insert(index, subsection)
        else:
            self.subsections.append(subsection)
        self.check_flags()

    def remove_subsection(self, subsection: 'Section') -> 'Section':
        self.subsections = [s for s in self.subsections if s.id != subsection.id]
        self.check_flags()
        subsection.parent_id = None
        return subsection

    def insert_task(self, task: Task, index: Optional[NonNegativeInt] = None) -> None:
        task.section_id = self.id   # type: ignore[assignment]
        if index is not None:
            self.tasks.insert(index, task)
        else:
            self.tasks.append(task)
        self.check_flags()

    def remove_task(self, task: Task) -> Task:
        self.tasks = [t for t in self.tasks if t.id != task.id]
        self.check_flags()
        return task

    def move_section(self, section: 'Section', section_from: 'Section', section_to: 'Section', index: NonNegativeInt) -> None:
        # moving section within same tree? Implementation placeholder
        section_from.remove_subsection(section)
        section_to.insert_subsection(section, index)

    def move_task(self, task_to_move: Task, section_from: 'Section', section_to: 'Section', index: NonNegativeInt) -> None:
        section_from.remove_task(task_to_move)
        section_to.insert_task(task_to_move, index)

    def shuffle_tasks(self) -> None:
        # Placeholder: reorder tasks, e.g., sort by title
        self.tasks.sort(key=lambda t: t.title)

    model_config = ConfigDict(validate_assignment=True)

# Resolve forward references
Section.model_rebuild()
Task.model_rebuild()

# ===========================
# INFRASTRUCTURE MODELS (SQLAlchemy)
# ===========================

class UserModel(Base):
    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True)
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    sections = relationship('SectionModel', back_populates='user', lazy='selectin')
    tasks = relationship('TaskModel', back_populates='user', lazy='selectin')

    def to_entity(self) -> User:
        return User(
            id=self.id,
            email=self.email,
            added_at=self.added_at
        )

class SectionModel(Base):
    __tablename__ = 'sections'

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey('users.id'))
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey('sections.id'), nullable=True)
    title: Mapped[str]
    has_subsections: Mapped[bool] = mapped_column(default=False)
    has_tasks: Mapped[bool] = mapped_column(default=False)
    index: Mapped[int] = mapped_column(default=0)
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user = relationship('UserModel', back_populates='sections')
    tasks = relationship('TaskModel', back_populates='section', lazy='selectin',
                         order_by='TaskModel.index')

    def to_entity(self, tasks: list[Task], subsections: list[Section]) -> Section:
        return Section(
            id=self.id,
            user_id=self.user_id,
            parent_id=self.parent_id,
            title=self.title,
            has_subsections=self.has_subsections,
            has_tasks=self.has_tasks,
            subsections=subsections,
            tasks=tasks,
            added_at=self.added_at
        )

    @staticmethod
    def from_entity(section: Section, index: NonNegativeInt) -> 'SectionModel':
        return SectionModel(
            id=section.id if section.id else uuid.uuid4(),
            user_id=section.user_id,
            parent_id=section.parent_id,
            title=section.title,
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
            index=index,
            added_at=section.added_at or datetime.utcnow()
        )

class TaskModel(Base):
    __tablename__ = 'tasks'

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey('users.id'))
    section_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey('sections.id'))
    title: Mapped[str]
    description: Mapped[Optional[str]]
    due_to: Mapped[Optional[date]]
    is_completed: Mapped[bool] = mapped_column(default=False)
    is_archived: Mapped[bool] = mapped_column(default=False)
    recurrence_type: Mapped[Optional[str]]
    recurrence_period: Mapped[Optional[int]]
    flexible_recurrence_mode: Mapped[Optional[bool]]
    index: Mapped[int] = mapped_column(default=0)
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user = relationship('UserModel', back_populates='tasks')
    section = relationship('SectionModel', back_populates='tasks')
    attachments = relationship('AttachmentModel', back_populates='task', lazy='selectin',
                               order_by='AttachmentModel.index')

    def to_entity(self, attachments: list[Attachment]) -> Task:
        recurrence = None
        if self.recurrence_type:
            recurrence = RecurrenceInfo(
                type=self.recurrence_type,  # type: ignore[arg-type]
                period=self.recurrence_period or 1,
                flexible_mode=self.flexible_recurrence_mode or False
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
            recurrence=recurrence,
            attachments=attachments,
            added_at=self.added_at
        )

    @staticmethod
    def from_entity(task: Task, index: NonNegativeInt) -> 'TaskModel':
        rec = task.recurrence
        return TaskModel(
            id=task.id if task.id else uuid.uuid4(),
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
            index=index,
            added_at=task.added_at or datetime.utcnow()
        )

class AttachmentModel(Base):
    __tablename__ = 'attachments'

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey('tasks.id'))
    s3_file_key: Mapped[str]
    aes_key_b64: Mapped[str]
    aes_iv_b64: Mapped[str]
    index: Mapped[int] = mapped_column(default=0)
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    task = relationship('TaskModel', back_populates='attachments')

    def to_entity(self) -> Attachment:
        return Attachment(
            id=self.id,
            task_id=self.task_id,
            s3_file_key=self.s3_file_key,
            aes_key_b64=self.aes_key_b64,
            aes_iv_b64=self.aes_iv_b64,
            added_at=self.added_at
        )

    @staticmethod
    def from_entity(attachment: Attachment, index: NonNegativeInt) -> 'AttachmentModel':
        return AttachmentModel(
            id=attachment.id if attachment.id else uuid.uuid4(),
            task_id=attachment.task_id,
            s3_file_key=attachment.s3_file_key,
            aes_key_b64=attachment.aes_key_b64,
            aes_iv_b64=attachment.aes_iv_b64,
            index=index,
            added_at=attachment.added_at or datetime.utcnow()
        )

class AccessTokenModel(Base):
    __tablename__ = 'access_tokens'

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    # Placeholder fields (not specified)
    token: Mapped[str] = mapped_column(String, unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey('users.id'))

# ===========================
# REPOSITORIES
# ===========================

class SQLAlchemyTaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, task: Task, index: NonNegativeInt) -> None:
        task_model = TaskModel.from_entity(task, index)
        self.session.add(task_model)
        await self.session.flush()

    async def get(self, task_id: uuid.UUID) -> Task:
        stmt = select(TaskModel).where(TaskModel.id == task_id)
        result = await self.session.execute(stmt)
        task_model = result.scalar_one_or_none()
        if task_model is None:
            raise ValueError(f"Task with id {task_id} not found")
        attachments = [att_model.to_entity() for att_model in task_model.attachments]
        return task_model.to_entity(attachments)

    async def get_entity(self, task_model: TaskModel) -> Task:
        # already has attachments loaded via relationship
        attachments = [att_model.to_entity() for att_model in task_model.attachments]
        return task_model.to_entity(attachments)

    async def get_entities(self, task_models: Sequence[TaskModel]) -> list[Task]:
        return [await self.get_entity(tm) for tm in task_models]

    async def get_overdue_tasks(self, user_id: uuid.UUID) -> list[Task]:
        stmt = select(TaskModel).where(
            TaskModel.user_id == user_id,
            TaskModel.due_to < date.today(),
            TaskModel.is_completed == False,
            TaskModel.is_archived == False
        )
        result = await self.session.execute(stmt)
        task_models = result.scalars().all()
        return await self.get_entities(task_models)

    async def get_archived_tasks(self, user_id: uuid.UUID) -> list[Task]:
        stmt = select(TaskModel).where(
            TaskModel.user_id == user_id,
            TaskModel.is_archived == True
        )
        result = await self.session.execute(stmt)
        task_models = result.scalars().all()
        return await self.get_entities(task_models)

    async def get_tasks_by_due_to(self, not_before: date, not_after: date, user_id: uuid.UUID) -> list[Task]:
        stmt = select(TaskModel).where(
            TaskModel.user_id == user_id,
            TaskModel.due_to >= not_before,
            TaskModel.due_to <= not_after,
            TaskModel.is_archived == False
        )
        result = await self.session.execute(stmt)
        task_models = result.scalars().all()
        return await self.get_entities(task_models)

    async def search(self, user_id: uuid.UUID, query: str) -> list[Task]:
        stmt = select(TaskModel).where(
            TaskModel.user_id == user_id,
            TaskModel.title.ilike(f'%{query}%')
        )
        result = await self.session.execute(stmt)
        task_models = result.scalars().all()
        return await self.get_entities(task_models)

    async def remove(self, task: Task) -> None:
        if task.id is None:
            raise ValueError("Task ID required")
        stmt = delete(TaskModel).where(TaskModel.id == task.id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def delete_attachment(self, attachment: Attachment) -> None:
        if attachment.id is None:
            raise ValueError("Attachment ID required")
        stmt = delete(AttachmentModel).where(AttachmentModel.id == attachment.id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def update_or_create(self, task: Task, index: Optional[NonNegativeInt], must_exist: bool) -> None:
        if task.id is None and must_exist:
            raise ValueError("Task ID required but not provided")
        if task.id:
            stmt = select(TaskModel).where(TaskModel.id == task.id)
            result = await self.session.execute(stmt)
            task_model = result.scalar_one_or_none()
            if task_model:
                # update fields
                for key, value in TaskModel.from_entity(task, index or task_model.index).__dict__.items():
                    if not key.startswith('_') and key != 'id':
                        setattr(task_model, key, value)
                await self.session.flush()
                return
            elif must_exist:
                raise ValueError(f"Task with id {task.id} not found")
        # create new
        await self.add(task, index or 0)

    async def update_or_create_bulk(self, section_tasks: list[Task]) -> None:
        for task in section_tasks:
            await self.update_or_create(task, None, must_exist=False)

class SQLAlchemySectionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, section: Section, index: NonNegativeInt) -> None:
        section_model = SectionModel.from_entity(section, index)
        self.session.add(section_model)
        await self.session.flush()

    async def get(self, section_id: uuid.UUID, with_direct_subsections: bool) -> Section:
        stmt = select(SectionModel).where(SectionModel.id == section_id)
        result = await self.session.execute(stmt)
        section_model = result.scalar_one_or_none()
        if section_model is None:
            raise ValueError(f"Section with id {section_id} not found")
        # Load tasks
        task_models = section_model.tasks
        tasks = [await SQLAlchemyTaskRepository(self.session).get_entity(tm) for tm in task_models]
        subsections = []
        if with_direct_subsections:
            # Get direct child sections
            child_stmt = select(SectionModel).where(SectionModel.parent_id == section_id).order_by(SectionModel.index)
            child_result = await self.session.execute(child_stmt)
            child_models = child_result.scalars().all()
            subsections = [await self._build_section_entity(child, with_tasks=False) for child in child_models]
        return self._build_section_entity_from_model(section_model, tasks, subsections)

    async def _build_section_entity(self, model: SectionModel, with_tasks: bool = False) -> Section:
        tasks = []
        if with_tasks:
            task_repo = SQLAlchemyTaskRepository(self.session)
            tasks = [await task_repo.get_entity(tm) for tm in model.tasks]
        return self._build_section_entity_from_model(model, tasks, [])

    def _build_section_entity_from_model(self, model: SectionModel, tasks: list[Task], subsections: list[Section]) -> Section:
        return Section(
            id=model.id,
            user_id=model.user_id,
            parent_id=model.parent_id,
            title=model.title,
            has_subsections=model.has_subsections,
            has_tasks=model.has_tasks,
            subsections=subsections,
            tasks=tasks,
            added_at=model.added_at
        )

    async def get_all_without_tasks(self, user_id: uuid.UUID, leaves_only: bool, as_tree: bool) -> list[Section]:
        stmt = select(SectionModel).where(SectionModel.user_id == user_id).order_by(SectionModel.index)
        result = await self.session.execute(stmt)
        section_models = result.scalars().all()
        if leaves_only:
            section_models = [sm for sm in section_models if not sm.has_subsections]
        if as_tree:
            return await self.construct_sections_tree(section_models, return_flat=False)
        else:
            return [self._build_section_entity_from_model(sm, [], []) for sm in section_models]

    async def construct_sections_tree(self, section_models: list[SectionModel], return_flat: bool) -> list[Section]:
        # Build a tree from flat list; root sections have parent_id None.
        # This is a simplified version.
        models_dict = {sm.id: sm for sm in section_models}
        roots = []
        for sm in section_models:
            if sm.parent_id is None or sm.parent_id not in models_dict:
                roots.append(sm)
        def _build_subtree(model: SectionModel) -> Section:
            children = [child for child in section_models if child.parent_id == model.id]
            child_sections = [_build_subtree(child) for child in children]
            return self._build_section_entity_from_model(model, [], child_sections)
        tree = [_build_subtree(root) for root in roots]
        if return_flat:
            # Flatten the tree
            flat = []
            def _flatten(sec: Section):
                flat.append(sec)
                for sub in sec.subsections:
                    _flatten(sub)
            for sec in tree:
                _flatten(sec)
            return flat
        return tree

    async def count_subsections(self, section_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(SectionModel.parent_id == section_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update(self, section: Section, index: Optional[NonNegativeInt]) -> None:
        if section.id is None:
            raise ValueError("Section ID required")
        stmt = select(SectionModel).where(SectionModel.id == section.id)
        result = await self.session.execute(stmt)
        sm = result.scalar_one_or_none()
        if sm is None:
            raise ValueError("Section not found")
        # Update fields
        sm.title = section.title
        sm.has_subsections = section.has_subsections
        sm.has_tasks = section.has_tasks
        if index is not None:
            sm.index = index
        await self.session.flush()

class SQLAlchemyUserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def verify_user(self, user_id: uuid.UUID) -> None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none() is None:
            raise ValueError("User not found")

    async def get_all_users(self) -> list['UserStats']:
        # UserStats not in original diagram, but method returns list[UserStats]
        # We'll implement a dummy UserStats.
        from dataclasses import dataclass
        @dataclass
        class UserStats:
            user_id: uuid.UUID
            task_count: int
        stmt = select(UserModel)
        result = await self.session.execute(stmt)
        users = result.scalars().all()
        stats = []
        for user in users:
            cnt = len(user.tasks) if user.tasks else 0
            stats.append(UserStats(user_id=user.id, task_count=cnt))
        return stats

# ===========================
# UNIT OF WORK
# ===========================

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

    async def __aexit__(self, exc_type, exc, tb):
        if exc:
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