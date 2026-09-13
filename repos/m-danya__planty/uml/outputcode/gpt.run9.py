from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, ClassVar, Dict, Generic, Iterable, Literal, Optional, Sequence, TypeVar, Union
from uuid import UUID, uuid4

try:
    from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
except Exception:  # pragma: no cover
    BaseModel = object  # type: ignore
    ConfigDict = dict  # type: ignore

    def Field(*args: Any, **kwargs: Any) -> Any:  # type: ignore
        return None

    def field_validator(*args: Any, **kwargs: Any):  # type: ignore
        def deco(fn):
            return fn

        return deco

    def model_validator(*args: Any, **kwargs: Any):  # type: ignore
        def deco(fn):
            return fn

        return deco


NonNegativeInt = int


class Entity(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RecurrenceInfo(Entity):
    type: Literal["daily", "weekly", "monthly", "yearly"]
    period: int
    flexible_mode: bool

    @field_validator("period")
    @classmethod
    def _validate_period(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("period must be positive")
        return v


class Attachment(Entity):
    id: Optional[UUID] = None
    task_id: UUID
    s3_file_key: str
    aes_key_b64: str
    aes_iv_b64: str
    added_at: Optional[datetime] = None

    @field_validator("s3_file_key", "aes_key_b64", "aes_iv_b64")
    @classmethod
    def _non_empty_str(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("must be a non-empty string")
        return v


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

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("title must be a non-empty string")
        return v

    @model_validator(mode="before")
    @classmethod
    def check_recurrence_due_date(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values
        recurrence = values.get("recurrence")
        due_to = values.get("due_to")
        if recurrence is not None and due_to is None:
            raise ValueError("due_to must be set when recurrence is provided")
        return values

    def add_attachment(self, attachment: Attachment) -> None:
        if attachment.task_id != (self.id or attachment.task_id):
            if self.id is not None and attachment.task_id != self.id:
                raise ValueError("attachment.task_id must match task.id")
        if self.attachments is None:
            self.attachments = []
        self.attachments.append(attachment)

    def remove_attachment(self, attachment: Attachment) -> None:
        if not self.attachments:
            raise ValueError("no attachments to remove")
        try:
            self.attachments.remove(attachment)
        except ValueError as e:
            raise ValueError("attachment not found") from e

    def archive(self) -> None:
        self.is_archived = True

    def unarchive(self) -> None:
        self.is_archived = False

    def toggle_archived(self) -> None:
        self.is_archived = not self.is_archived

    def mark_completed(self, auto_archive: bool) -> None:
        self.is_completed = True
        if auto_archive:
            self.is_archived = True

    def toggle_completed(self, auto_archive: bool) -> None:
        self.is_completed = not self.is_completed
        if self.is_completed and auto_archive:
            self.is_archived = True


class Section(Entity):
    id: Optional[UUID] = None
    user_id: UUID
    title: str
    parent_id: Optional[UUID] = None
    has_tasks: bool = False
    has_subsections: bool = False
    tasks: list[Task] = Field(default_factory=list)
    subsections: list["Section"] = Field(default_factory=list)
    added_at: Optional[datetime] = None

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("title must be a non-empty string")
        return v

    def is_root(self) -> bool:
        return self.parent_id is None

    @classmethod
    def create_root_section(cls, user_id: UUID) -> "Section":
        return cls(id=None, user_id=user_id, title="Root", parent_id=None, tasks=[], subsections=[]).check_flags()

    def check_flags(self) -> "Section":
        self.has_tasks = bool(self.tasks)
        self.has_subsections = bool(self.subsections)
        return self

    def insert_task(self, task: Task, index: Optional[NonNegativeInt]) -> None:
        if task.section_id != (self.id or task.section_id):
            if self.id is not None and task.section_id != self.id:
                raise ValueError("task.section_id must match section.id")
        if index is None:
            self.tasks.append(task)
        else:
            if index < 0:
                raise ValueError("index must be non-negative")
            if index > len(self.tasks):
                raise ValueError("index out of range")
            self.tasks.insert(index, task)
        self.check_flags()

    def remove_task(self, task: Task) -> Task:
        try:
            self.tasks.remove(task)
        except ValueError as e:
            raise ValueError("task not found") from e
        self.check_flags()
        return task

    def insert_subsection(self, subsection: "Section", index: Optional[NonNegativeInt]) -> None:
        if subsection.user_id != self.user_id:
            raise ValueError("subsection.user_id must match section.user_id")
        if self.id is not None:
            if subsection.parent_id is not None and subsection.parent_id != self.id:
                raise ValueError("subsection.parent_id must match section.id")
            subsection.parent_id = self.id
        if index is None:
            self.subsections.append(subsection)
        else:
            if index < 0:
                raise ValueError("index must be non-negative")
            if index > len(self.subsections):
                raise ValueError("index out of range")
            self.subsections.insert(index, subsection)
        self.check_flags()

    def remove_subsection(self, subsection: "Section") -> "Section":
        try:
            self.subsections.remove(subsection)
        except ValueError as e:
            raise ValueError("subsection not found") from e
        self.check_flags()
        return subsection

    def shuffle_tasks(self) -> None:
        self.tasks = list(reversed(self.tasks))
        self.check_flags()

    @staticmethod
    def move_task(task_to_move: Task, section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if index < 0:
            raise ValueError("index must be non-negative")
        section_from.remove_task(task_to_move)
        if section_to.id is not None:
            task_to_move.section_id = section_to.id
        section_to.insert_task(task_to_move, index)

    @staticmethod
    def move_section(section: "Section", section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if index < 0:
            raise ValueError("index must be non-negative")
        if section.user_id != section_to.user_id or section.user_id != section_from.user_id:
            raise ValueError("section.user_id must match both source and destination")
        section_from.remove_subsection(section)
        if section_to.id is not None:
            section.parent_id = section_to.id
        section_to.insert_subsection(section, index)


class User(Entity):
    id: Optional[UUID] = None
    email: str
    added_at: Optional[datetime] = None

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("email must be a non-empty string")
        return v


@dataclass(frozen=True)
class UserStats:
    user: User
    sections_count: int
    tasks_count: int


T = TypeVar("T")


class Mapped(Generic[T]):
    def __init__(self, value: Optional[T] = None):
        self.value = value

    def __repr__(self) -> str:
        return f"Mapped({self.value!r})"


GUID = UUID


class AccessTokenModel:
    pass


class AttachmentModel:
    def __init__(
        self,
        id: UUID,
        task_id: UUID,
        s3_file_key: str,
        aes_key_b64: str,
        aes_iv_b64: str,
        added_at: datetime,
        index: int,
        task: Optional["TaskModel"] = None,
    ):
        self.id: UUID = id
        self.task_id: UUID = task_id
        self.s3_file_key: str = s3_file_key
        self.aes_key_b64: str = aes_key_b64
        self.aes_iv_b64: str = aes_iv_b64
        self.added_at: datetime = added_at
        self.index: int = index
        self.task: Optional["TaskModel"] = task

    @staticmethod
    def from_entity(attachment: Attachment, index: NonNegativeInt) -> "AttachmentModel":
        if index < 0:
            raise ValueError("index must be non-negative")
        return AttachmentModel(
            id=attachment.id or uuid4(),
            task_id=attachment.task_id,
            s3_file_key=attachment.s3_file_key,
            aes_key_b64=attachment.aes_key_b64,
            aes_iv_b64=attachment.aes_iv_b64,
            added_at=attachment.added_at or datetime.utcnow(),
            index=index,
            task=None,
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


class TaskModel:
    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        section_id: UUID,
        title: str,
        description: Optional[str],
        due_to: Optional[date],
        is_completed: bool,
        is_archived: bool,
        recurrence_type: Optional[str],
        recurrence_period: Optional[int],
        flexible_recurrence_mode: Optional[bool],
        added_at: datetime,
        index: int,
        attachments: Optional[list[AttachmentModel]] = None,
        section: Optional["SectionModel"] = None,
        user: Optional["UserModel"] = None,
    ):
        self.id: UUID = id
        self.user_id: UUID = user_id
        self.section_id: UUID = section_id
        self.title: str = title
        self.description: Optional[str] = description
        self.due_to: Optional[date] = due_to
        self.is_completed: bool = is_completed
        self.is_archived: bool = is_archived
        self.recurrence_type: Optional[str] = recurrence_type
        self.recurrence_period: Optional[int] = recurrence_period
        self.flexible_recurrence_mode: Optional[bool] = flexible_recurrence_mode
        self.added_at: datetime = added_at
        self.index: int = index
        self.attachments: list[AttachmentModel] = attachments or []
        self.section: Optional["SectionModel"] = section
        self.user: Optional["UserModel"] = user

    @staticmethod
    def from_entity(task: Task, index: NonNegativeInt) -> "TaskModel":
        if index < 0:
            raise ValueError("index must be non-negative")
        recurrence_type: Optional[str] = None
        recurrence_period: Optional[int] = None
        flexible_mode: Optional[bool] = None
        if task.recurrence is not None:
            recurrence_type = str(task.recurrence.type)
            recurrence_period = int(task.recurrence.period)
            flexible_mode = bool(task.recurrence.flexible_mode)
        model = TaskModel(
            id=task.id or uuid4(),
            user_id=task.user_id,
            section_id=task.section_id,
            title=task.title,
            description=task.description,
            due_to=task.due_to,
            is_completed=task.is_completed,
            is_archived=task.is_archived,
            recurrence_type=recurrence_type,
            recurrence_period=recurrence_period,
            flexible_recurrence_mode=flexible_mode,
            added_at=task.added_at or datetime.utcnow(),
            index=index,
            attachments=[],
            section=None,
            user=None,
        )
        if task.attachments:
            model.attachments = [AttachmentModel.from_entity(a, i) for i, a in enumerate(task.attachments)]
        return model

    def to_entity(self, attachments: list[Attachment]) -> Task:
        recurrence: Optional[RecurrenceInfo] = None
        if self.recurrence_type is not None and self.recurrence_period is not None and self.flexible_recurrence_mode is not None:
            recurrence = RecurrenceInfo(
                type=self.recurrence_type,  # type: ignore[arg-type]
                period=self.recurrence_period,
                flexible_mode=self.flexible_recurrence_mode,
            )
        return Task(
            id=self.id,
            user_id=self.user_id,
            section_id=self.section_id,
            title=self.title,
            description=self.description,
            content=None,
            due_to=self.due_to,
            is_completed=self.is_completed,
            is_archived=self.is_archived,
            recurrence=recurrence,
            attachments=attachments,
            added_at=self.added_at,
        )


class SectionModel:
    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        title: str,
        parent_id: Optional[GUID],
        has_tasks: bool,
        has_subsections: bool,
        added_at: datetime,
        index: int,
        tasks: Optional[list[TaskModel]] = None,
        user: Optional["UserModel"] = None,
    ):
        self.id: UUID = id
        self.user_id: UUID = user_id
        self.title: str = title
        self.parent_id: Optional[GUID] = parent_id
        self.has_tasks: bool = has_tasks
        self.has_subsections: bool = has_subsections
        self.added_at: datetime = added_at
        self.index: int = index
        self.tasks: list[TaskModel] = tasks or []
        self.user: Optional["UserModel"] = user

    @staticmethod
    def from_entity(section: Section, index: NonNegativeInt) -> "SectionModel":
        if index < 0:
            raise ValueError("index must be non-negative")
        return SectionModel(
            id=section.id or uuid4(),
            user_id=section.user_id,
            title=section.title,
            parent_id=section.parent_id,
            has_tasks=section.has_tasks,
            has_subsections=section.has_subsections,
            added_at=section.added_at or datetime.utcnow(),
            index=index,
            tasks=[],
            user=None,
        )

    def to_entity(self, tasks: list[Task], subsections: list[Section]) -> Section:
        return Section(
            id=self.id,
            user_id=self.user_id,
            title=self.title,
            parent_id=self.parent_id,
            has_tasks=self.has_tasks,
            has_subsections=self.has_subsections,
            tasks=tasks,
            subsections=subsections,
            added_at=self.added_at,
        ).check_flags()


class UserModel:
    def __init__(
        self,
        id: UUID,
        email: str,
        added_at: datetime,
        sections: Optional[list[SectionModel]] = None,
        tasks: Optional[list[TaskModel]] = None,
    ):
        self.id: UUID = id
        self.email: str = email
        self.added_at: datetime = added_at
        self.sections: list[SectionModel] = sections or []
        self.tasks: list[TaskModel] = tasks or []

    def to_entity(self) -> User:
        return User(id=self.id, email=self.email, added_at=self.added_at)


class AsyncSession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class async_sessionmaker:
    def __init__(self, factory: Any = None):
        self._factory = factory

    def __call__(self) -> AsyncSession:
        if callable(self._factory):
            return self._factory()
        return AsyncSession()


class SQLAlchemyTaskRepository:
    def __init__(self):
        self._tasks: Dict[UUID, TaskModel] = {}
        self._attachments: Dict[UUID, AttachmentModel] = {}

    def add(self, task: Task, index: NonNegativeInt) -> None:
        model = TaskModel.from_entity(task, index)
        self._tasks[model.id] = model
        if task.attachments:
            for i, a in enumerate(task.attachments):
                am = AttachmentModel.from_entity(a, i)
                am.task_id = model.id
                self._attachments[am.id] = am
                model.attachments.append(am)

    def get(self, task_id: UUID) -> Task:
        model = self._tasks.get(task_id)
        if model is None:
            raise KeyError("task not found")
        return self.get_entity(model)

    def get_entity(self, task_model: TaskModel) -> Task:
        attachments = [am.to_entity() for am in sorted(task_model.attachments, key=lambda x: x.index)]
        return task_model.to_entity(attachments=attachments)

    def get_entities(self, task_models: Sequence[TaskModel]) -> list[Task]:
        return [self.get_entity(m) for m in task_models]

    def remove(self, task: Task) -> None:
        if task.id is None:
            raise ValueError("task.id is required")
        model = self._tasks.pop(task.id, None)
        if model is None:
            raise KeyError("task not found")
        for am in list(model.attachments):
            self._attachments.pop(am.id, None)

    def delete_attachment(self, attachment: Attachment) -> None:
        if attachment.id is None:
            raise ValueError("attachment.id is required")
        am = self._attachments.pop(attachment.id, None)
        if am is None:
            raise KeyError("attachment not found")
        tm = self._tasks.get(am.task_id)
        if tm is not None:
            tm.attachments = [x for x in tm.attachments if x.id != am.id]

    def update_or_create(self, task: Task, index: Optional[NonNegativeInt], must_exist: bool) -> None:
        if task.id is None:
            if must_exist:
                raise KeyError("task must exist")
            idx = 0 if index is None else index
            self.add(task, idx)
            return
        existing = self._tasks.get(task.id)
        if existing is None:
            if must_exist:
                raise KeyError("task not found")
            idx = 0 if index is None else index
            self.add(task, idx)
            return
        if index is not None:
            if index < 0:
                raise ValueError("index must be non-negative")
            existing.index = index
        existing.user_id = task.user_id
        existing.section_id = task.section_id
        existing.title = task.title
        existing.description = task.description
        existing.due_to = task.due_to
        existing.is_completed = task.is_completed
        existing.is_archived = task.is_archived
        if task.recurrence is None:
            existing.recurrence_type = None
            existing.recurrence_period = None
            existing.flexible_recurrence_mode = None
        else:
            existing.recurrence_type = str(task.recurrence.type)
            existing.recurrence_period = int(task.recurrence.period)
            existing.flexible_recurrence_mode = bool(task.recurrence.flexible_mode)

    def update_or_create_bulk(self, section_tasks: list[Task]) -> None:
        for i, t in enumerate(section_tasks):
            self.update_or_create(t, index=i, must_exist=False)

    def get_archived_tasks(self, user_id: UUID) -> list[Task]:
        models = [m for m in self._tasks.values() if m.user_id == user_id and m.is_archived]
        models.sort(key=lambda x: (x.section_id, x.index))
        return self.get_entities(models)

    def get_overdue_tasks(self, user_id: UUID) -> list[Task]:
        today = date.today()
        models = [
            m
            for m in self._tasks.values()
            if m.user_id == user_id and not m.is_completed and m.due_to is not None and m.due_to < today
        ]
        models.sort(key=lambda x: (x.due_to or today, x.index))
        return self.get_entities(models)

    def get_tasks_by_due_to(self, not_before: date, not_after: date, user_id: UUID) -> list[Task]:
        models = [
            m
            for m in self._tasks.values()
            if m.user_id == user_id and m.due_to is not None and not_before <= m.due_to <= not_after
        ]
        models.sort(key=lambda x: (x.due_to or not_before, x.index))
        return self.get_entities(models)

    def search(self, user_id: UUID, query: str) -> list[Task]:
        q = query.strip().lower()
        if not q:
            return []
        models = [
            m
            for m in self._tasks.values()
            if m.user_id == user_id and (q in m.title.lower() or (m.description or "").lower().find(q) != -1)
        ]
        models.sort(key=lambda x: (x.section_id, x.index))
        return self.get_entities(models)


class SQLAlchemySectionRepository:
    def __init__(self, task_repo: Optional[SQLAlchemyTaskRepository] = None):
        self._sections: Dict[UUID, SectionModel] = {}
        self._task_repo = task_repo

    def add(self, section: Section, index: NonNegativeInt) -> None:
        model = SectionModel.from_entity(section, index)
        self._sections[model.id] = model

    def update(self, section: Section, index: Optional[NonNegativeInt]) -> None:
        if section.id is None:
            raise ValueError("section.id is required")
        model = self._sections.get(section.id)
        if model is None:
            raise KeyError("section not found")
        if index is not None:
            if index < 0:
                raise ValueError("index must be non-negative")
            model.index = index
        model.title = section.title
        model.parent_id = section.parent_id
        model.has_tasks = section.has_tasks
        model.has_subsections = section.has_subsections

    def count_subsections(self, section_id: UUID) -> int:
        return sum(1 for s in self._sections.values() if s.parent_id == section_id)

    def get(self, section_id: UUID, with_direct_subsections: bool) -> Section:
        model = self._sections.get(section_id)
        if model is None:
            raise KeyError("section not found")
        tasks: list[Task] = []
        if self._task_repo is not None:
            task_models = [t for t in self._task_repo._tasks.values() if t.section_id == model.id]
            task_models.sort(key=lambda x: x.index)
            tasks = self._task_repo.get_entities(task_models)
        subsections: list[Section] = []
        if with_direct_subsections:
            child_models = [s for s in self._sections.values() if s.parent_id == model.id]
            child_models.sort(key=lambda x: x.index)
            subsections = [cm.to_entity(tasks=[], subsections=[]) for cm in child_models]
        return model.to_entity(tasks=tasks, subsections=subsections)

    def construct_sections_tree(self, section_models: list[SectionModel], return_flat: bool) -> list[Section]:
        models_by_id: Dict[UUID, SectionModel] = {m.id: m for m in section_models}
        children: Dict[Optional[UUID], list[SectionModel]] = {}
        for m in section_models:
            children.setdefault(m.parent_id, []).append(m)
        for lst in children.values():
            lst.sort(key=lambda x: x.index)

        def build(mid: UUID) -> Section:
            m = models_by_id[mid]
            subs = [build(ch.id) for ch in children.get(m.id, [])]
            return m.to_entity(tasks=[], subsections=subs)

        roots = [m for m in section_models if m.parent_id is None]
        roots.sort(key=lambda x: x.index)
        tree = [build(r.id) for r in roots]
        if return_flat:
            flat: list[Section] = []

            def walk(s: Section) -> None:
                flat.append(s)
                for ss in s.subsections:
                    walk(ss)

            for r in tree:
                walk(r)
            return flat
        return tree

    def get_all_without_tasks(self, user_id: UUID, leaves_only: bool, as_tree: bool) -> list[Section]:
        models = [m for m in self._sections.values() if m.user_id == user_id]
        if leaves_only:
            parent_ids = {m.parent_id for m in models if m.parent_id is not None}
            models = [m for m in models if m.id not in parent_ids]
        models.sort(key=lambda x: (x.parent_id is not None, x.parent_id or UUID(int=0), x.index))
        if as_tree:
            return self.construct_sections_tree(models, return_flat=False)
        return [m.to_entity(tasks=[], subsections=[]) for m in models]


class SQLAlchemyUserRepository:
    def __init__(self):
        self._users: Dict[UUID, UserModel] = {}
        self._verified: set[UUID] = set()

    def get_all_users(self) -> list[UserStats]:
        stats: list[UserStats] = []
        for um in self._users.values():
            stats.append(UserStats(user=um.to_entity(), sections_count=len(um.sections), tasks_count=len(um.tasks)))
        return stats

    def verify_user(self, user_id: UUID) -> None:
        if user_id not in self._users:
            raise KeyError("user not found")
        self._verified.add(user_id)


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
    def __init__(self, session_factory: Optional[async_sessionmaker] = None):
        self.session_factory: async_sessionmaker = session_factory or async_sessionmaker()
        self.session: AsyncSession = self.session_factory()
        self.task_repo = SQLAlchemyTaskRepository()
        self.section_repo = SQLAlchemySectionRepository(task_repo=self.task_repo)
        self.user_repo = SQLAlchemyUserRepository()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()