from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Sequence, TypeVar, Generic
from uuid import UUID, uuid4
from abc import ABC, abstractmethod
import random

try:
    from pydantic import BaseModel, ConfigDict, Field, model_validator
except Exception:  # pragma: no cover
    BaseModel = object  # type: ignore
    ConfigDict = dict  # type: ignore

    def Field(*args: Any, **kwargs: Any) -> Any:  # type: ignore
        return None

    def model_validator(*args: Any, **kwargs: Any) -> Any:  # type: ignore
        def deco(fn: Any) -> Any:
            return fn

        return deco


NonNegativeInt = int


class Entity(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RecurrenceInfo(Entity):
    type: Literal["daily", "weekly", "monthly", "yearly"]
    period: int
    flexible_mode: bool = False

    @model_validator(mode="after")
    def _validate_period(self) -> "RecurrenceInfo":
        if self.period <= 0:
            raise ValueError("period must be > 0")
        return self


class Attachment(Entity):
    id: Optional[UUID] = None
    task_id: UUID
    s3_file_key: str
    aes_key_b64: str
    aes_iv_b64: str
    added_at: Optional[datetime] = None

    @model_validator(mode="after")
    def _validate_fields(self) -> "Attachment":
        if not self.s3_file_key:
            raise ValueError("s3_file_key must be non-empty")
        if not self.aes_key_b64:
            raise ValueError("aes_key_b64 must be non-empty")
        if not self.aes_iv_b64:
            raise ValueError("aes_iv_b64 must be non-empty")
        return self


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
    attachments: Optional[List[Attachment]] = None
    added_at: Optional[datetime] = None

    @model_validator(mode="after")
    def check_recurrence_due_date(self) -> "Task":
        if self.recurrence is not None and self.due_to is None:
            raise ValueError("due_to must be set when recurrence is set")
        return self

    def add_attachment(self, attachment: Attachment) -> None:
        if attachment.task_id != (self.id if self.id is not None else attachment.task_id):
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
    tasks: List[Task] = Field(default_factory=list)
    subsections: List["Section"] = Field(default_factory=list)
    has_tasks: bool = False
    has_subsections: bool = False
    added_at: Optional[datetime] = None

    def is_root(self) -> bool:
        return self.parent_id is None

    @classmethod
    def create_root_section(cls, user_id: UUID) -> "Section":
        return cls(id=None, user_id=user_id, title="Root", parent_id=None, tasks=[], subsections=[], has_tasks=False, has_subsections=False)

    def check_flags(self) -> "Section":
        self.has_tasks = bool(self.tasks)
        self.has_subsections = bool(self.subsections)
        return self

    def insert_task(self, task: Task, index: Optional[NonNegativeInt]) -> None:
        if index is not None and index < 0:
            raise ValueError("index must be non-negative")
        if task.section_id != (self.id if self.id is not None else task.section_id):
            if self.id is not None and task.section_id != self.id:
                raise ValueError("task.section_id must match section.id")
        if index is None or index >= len(self.tasks):
            self.tasks.append(task)
        else:
            self.tasks.insert(index, task)
        self.check_flags()

    def remove_task(self, task: Task) -> Task:
        try:
            self.tasks.remove(task)
        except ValueError as e:
            raise ValueError("task not found in section") from e
        self.check_flags()
        return task

    def insert_subsection(self, subsection: "Section", index: Optional[NonNegativeInt]) -> None:
        if index is not None and index < 0:
            raise ValueError("index must be non-negative")
        if subsection.user_id != self.user_id:
            raise ValueError("subsection.user_id must match section.user_id")
        if self.id is not None:
            subsection.parent_id = self.id
        if index is None or index >= len(self.subsections):
            self.subsections.append(subsection)
        else:
            self.subsections.insert(index, subsection)
        self.check_flags()

    def remove_subsection(self, subsection: "Section") -> "Section":
        try:
            self.subsections.remove(subsection)
        except ValueError as e:
            raise ValueError("subsection not found in section") from e
        self.check_flags()
        return subsection

    @staticmethod
    def move_task(task_to_move: Task, section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if index < 0:
            raise ValueError("index must be non-negative")
        removed = section_from.remove_task(task_to_move)
        if section_to.id is not None:
            removed.section_id = section_to.id
        section_to.insert_task(removed, index)
        section_from.check_flags()
        section_to.check_flags()

    @staticmethod
    def move_section(section: "Section", section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if index < 0:
            raise ValueError("index must be non-negative")
        removed = section_from.remove_subsection(section)
        if section_to.id is not None:
            removed.parent_id = section_to.id
        else:
            removed.parent_id = None
        section_to.insert_subsection(removed, index)
        section_from.check_flags()
        section_to.check_flags()

    def shuffle_tasks(self) -> None:
        random.shuffle(self.tasks)
        self.check_flags()


class User(Entity):
    id: Optional[UUID] = None
    email: str
    added_at: Optional[datetime] = None

    @model_validator(mode="after")
    def _validate_email(self) -> "User":
        if not self.email or "@" not in self.email:
            raise ValueError("email must be a valid email-like string")
        return self


T = TypeVar("T")


class Mapped(Generic[T]):
    pass


class GUID(UUID):
    pass


class AccessTokenModel:
    def __init__(self) -> None:
        pass


class AttachmentModel:
    id: Mapped[UUID]
    task_id: Mapped[UUID]
    s3_file_key: Mapped[str]
    aes_key_b64: Mapped[str]
    aes_iv_b64: Mapped[str]
    added_at: Mapped[datetime]
    index: Mapped[int]
    task: Any

    def __init__(
        self,
        *,
        id: UUID,
        task_id: UUID,
        s3_file_key: str,
        aes_key_b64: str,
        aes_iv_b64: str,
        added_at: datetime,
        index: int,
    ) -> None:
        self.id = id  # type: ignore[assignment]
        self.task_id = task_id  # type: ignore[assignment]
        self.s3_file_key = s3_file_key  # type: ignore[assignment]
        self.aes_key_b64 = aes_key_b64  # type: ignore[assignment]
        self.aes_iv_b64 = aes_iv_b64  # type: ignore[assignment]
        self.added_at = added_at  # type: ignore[assignment]
        self.index = index  # type: ignore[assignment]
        self.task = None

    @staticmethod
    def from_entity(attachment: Attachment, index: NonNegativeInt) -> "AttachmentModel":
        if index < 0:
            raise ValueError("index must be non-negative")
        att_id = attachment.id or uuid4()
        added_at = attachment.added_at or datetime.utcnow()
        return AttachmentModel(
            id=att_id,
            task_id=attachment.task_id,
            s3_file_key=attachment.s3_file_key,
            aes_key_b64=attachment.aes_key_b64,
            aes_iv_b64=attachment.aes_iv_b64,
            added_at=added_at,
            index=index,
        )

    def to_entity(self) -> Attachment:
        return Attachment(
            id=self.id,  # type: ignore[arg-type]
            task_id=self.task_id,  # type: ignore[arg-type]
            s3_file_key=self.s3_file_key,  # type: ignore[arg-type]
            aes_key_b64=self.aes_key_b64,  # type: ignore[arg-type]
            aes_iv_b64=self.aes_iv_b64,  # type: ignore[arg-type]
            added_at=self.added_at,  # type: ignore[arg-type]
        )


class TaskModel:
    id: Mapped[UUID]
    user_id: Mapped[UUID]
    section_id: Mapped[UUID]
    title: Mapped[str]
    description: Mapped[Optional[str]]
    due_to: Mapped[Optional[date]]
    is_completed: Mapped[bool]
    is_archived: Mapped[bool]
    recurrence_type: Mapped[Optional[str]]
    recurrence_period: Mapped[Optional[int]]
    flexible_recurrence_mode: Mapped[Optional[bool]]
    added_at: Mapped[datetime]
    index: Mapped[int]
    section: Any
    user: Any
    attachments: Any

    def __init__(
        self,
        *,
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
    ) -> None:
        self.id = id  # type: ignore[assignment]
        self.user_id = user_id  # type: ignore[assignment]
        self.section_id = section_id  # type: ignore[assignment]
        self.title = title  # type: ignore[assignment]
        self.description = description  # type: ignore[assignment]
        self.due_to = due_to  # type: ignore[assignment]
        self.is_completed = is_completed  # type: ignore[assignment]
        self.is_archived = is_archived  # type: ignore[assignment]
        self.recurrence_type = recurrence_type  # type: ignore[assignment]
        self.recurrence_period = recurrence_period  # type: ignore[assignment]
        self.flexible_recurrence_mode = flexible_recurrence_mode  # type: ignore[assignment]
        self.added_at = added_at  # type: ignore[assignment]
        self.index = index  # type: ignore[assignment]
        self.section = None
        self.user = None
        self.attachments = []

    @staticmethod
    def from_entity(task: Task, index: NonNegativeInt) -> "TaskModel":
        if index < 0:
            raise ValueError("index must be non-negative")
        task_id = task.id or uuid4()
        added_at = task.added_at or datetime.utcnow()
        recurrence_type: Optional[str] = None
        recurrence_period: Optional[int] = None
        flexible: Optional[bool] = None
        if task.recurrence is not None:
            recurrence_type = str(task.recurrence.type)
            recurrence_period = int(task.recurrence.period)
            flexible = bool(task.recurrence.flexible_mode)
        return TaskModel(
            id=task_id,
            user_id=task.user_id,
            section_id=task.section_id,
            title=task.title,
            description=task.description,
            due_to=task.due_to,
            is_completed=task.is_completed,
            is_archived=task.is_archived,
            recurrence_type=recurrence_type,
            recurrence_period=recurrence_period,
            flexible_recurrence_mode=flexible,
            added_at=added_at,
            index=index,
        )

    def to_entity(self, attachments: List[Attachment]) -> Task:
        recurrence: Optional[RecurrenceInfo] = None
        if self.recurrence_type is not None and self.recurrence_period is not None:
            recurrence = RecurrenceInfo(
                type=self.recurrence_type,  # type: ignore[arg-type]
                period=int(self.recurrence_period),  # type: ignore[arg-type]
                flexible_mode=bool(self.flexible_recurrence_mode) if self.flexible_recurrence_mode is not None else False,
            )
        return Task(
            id=self.id,  # type: ignore[arg-type]
            user_id=self.user_id,  # type: ignore[arg-type]
            section_id=self.section_id,  # type: ignore[arg-type]
            title=self.title,  # type: ignore[arg-type]
            description=self.description,  # type: ignore[arg-type]
            content=None,
            due_to=self.due_to,  # type: ignore[arg-type]
            is_completed=bool(self.is_completed),  # type: ignore[arg-type]
            is_archived=bool(self.is_archived),  # type: ignore[arg-type]
            recurrence=recurrence,
            attachments=attachments,
            added_at=self.added_at,  # type: ignore[arg-type]
        )


class SectionModel:
    id: Mapped[UUID]
    user_id: Mapped[UUID]
    title: Mapped[str]
    parent_id: Mapped[Optional[GUID]]
    has_tasks: Mapped[bool]
    has_subsections: Mapped[bool]
    added_at: Mapped[datetime]
    index: Mapped[int]
    tasks: Mapped[List[TaskModel]]
    user: Any

    def __init__(
        self,
        *,
        id: UUID,
        user_id: UUID,
        title: str,
        parent_id: Optional[UUID],
        has_tasks: bool,
        has_subsections: bool,
        added_at: datetime,
        index: int,
        tasks: Optional[List[TaskModel]] = None,
    ) -> None:
        self.id = id  # type: ignore[assignment]
        self.user_id = user_id  # type: ignore[assignment]
        self.title = title  # type: ignore[assignment]
        self.parent_id = parent_id  # type: ignore[assignment]
        self.has_tasks = has_tasks  # type: ignore[assignment]
        self.has_subsections = has_subsections  # type: ignore[assignment]
        self.added_at = added_at  # type: ignore[assignment]
        self.index = index  # type: ignore[assignment]
        self.tasks = (tasks or [])  # type: ignore[assignment]
        self.user = None

    @staticmethod
    def from_entity(section: Section, index: NonNegativeInt) -> "SectionModel":
        if index < 0:
            raise ValueError("index must be non-negative")
        sec_id = section.id or uuid4()
        added_at = section.added_at or datetime.utcnow()
        section.check_flags()
        return SectionModel(
            id=sec_id,
            user_id=section.user_id,
            title=section.title,
            parent_id=section.parent_id,
            has_tasks=section.has_tasks,
            has_subsections=section.has_subsections,
            added_at=added_at,
            index=index,
            tasks=[],
        )

    def to_entity(self, tasks: List[Task], subsections: List[Section]) -> Section:
        sec = Section(
            id=self.id,  # type: ignore[arg-type]
            user_id=self.user_id,  # type: ignore[arg-type]
            title=self.title,  # type: ignore[arg-type]
            parent_id=self.parent_id,  # type: ignore[arg-type]
            tasks=tasks,
            subsections=subsections,
            has_tasks=bool(self.has_tasks),  # type: ignore[arg-type]
            has_subsections=bool(self.has_subsections),  # type: ignore[arg-type]
            added_at=self.added_at,  # type: ignore[arg-type]
        )
        sec.check_flags()
        return sec


class UserModel:
    added_at: Mapped[datetime]
    sections: Any
    tasks: Any

    def __init__(self, *, id: UUID, email: str, added_at: datetime) -> None:
        self.id = id
        self.email = email
        self.added_at = added_at  # type: ignore[assignment]
        self.sections = []
        self.tasks = []

    def to_entity(self) -> User:
        return User(id=self.id, email=self.email, added_at=self.added_at)  # type: ignore[arg-type]


@dataclass(frozen=True)
class UserStats:
    user_id: UUID
    email: str
    sections_count: int
    tasks_count: int


class SQLAlchemyTaskRepository:
    def __init__(self) -> None:
        self._tasks: Dict[UUID, Task] = {}
        self._section_index: Dict[UUID, List[UUID]] = {}

    def add(self, task: Task, index: NonNegativeInt) -> None:
        if index < 0:
            raise ValueError("index must be non-negative")
        if task.id is None:
            task.id = uuid4()
        if task.added_at is None:
            task.added_at = datetime.utcnow()
        self._tasks[task.id] = task
        lst = self._section_index.setdefault(task.section_id, [])
        if index >= len(lst):
            lst.append(task.id)
        else:
            lst.insert(index, task.id)

    def get(self, task_id: UUID) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError as e:
            raise ValueError("task not found") from e

    def remove(self, task: Task) -> None:
        if task.id is None or task.id not in self._tasks:
            raise ValueError("task not found")
        del self._tasks[task.id]
        lst = self._section_index.get(task.section_id, [])
        if task.id in lst:
            lst.remove(task.id)

    def delete_attachment(self, attachment: Attachment) -> None:
        task = self.get(attachment.task_id)
        task.remove_attachment(attachment)

    def update_or_create(self, task: Task, index: Optional[NonNegativeInt], must_exist: bool) -> None:
        if task.id is None:
            if must_exist:
                raise ValueError("task must exist")
            self.add(task, index if index is not None else 0)
            return
        exists = task.id in self._tasks
        if must_exist and not exists:
            raise ValueError("task must exist")
        if not exists:
            self.add(task, index if index is not None else 0)
            return
        self._tasks[task.id] = task
        if index is not None:
            if index < 0:
                raise ValueError("index must be non-negative")
            lst = self._section_index.setdefault(task.section_id, [])
            if task.id in lst:
                lst.remove(task.id)
            if index >= len(lst):
                lst.append(task.id)
            else:
                lst.insert(index, task.id)

    def update_or_create_bulk(self, section_tasks: List[Task]) -> None:
        for t in section_tasks:
            self.update_or_create(t, index=None, must_exist=False)

    def get_entities(self, task_models: Sequence[TaskModel]) -> List[Task]:
        entities: List[Task] = []
        for tm in task_models:
            attachments: List[Attachment] = []
            if getattr(tm, "attachments", None):
                for am in tm.attachments:
                    if isinstance(am, AttachmentModel):
                        attachments.append(am.to_entity())
            entities.append(tm.to_entity(attachments=attachments))
        return entities

    def get_entity(self, task_model: TaskModel) -> Task:
        return self.get_entities([task_model])[0]

    def get_archived_tasks(self, user_id: UUID) -> List[Task]:
        return [t for t in self._tasks.values() if t.user_id == user_id and t.is_archived]

    def get_overdue_tasks(self, user_id: UUID) -> List[Task]:
        today = date.today()
        return [
            t
            for t in self._tasks.values()
            if t.user_id == user_id and not t.is_archived and not t.is_completed and t.due_to is not None and t.due_to < today
        ]

    def get_tasks_by_due_to(self, not_before: date, not_after: date, user_id: UUID) -> List[Task]:
        return [
            t
            for t in self._tasks.values()
            if t.user_id == user_id and t.due_to is not None and not_before <= t.due_to <= not_after
        ]

    def search(self, user_id: UUID, query: str) -> List[Task]:
        q = query.lower()
        res: List[Task] = []
        for t in self._tasks.values():
            if t.user_id != user_id:
                continue
            hay = " ".join([t.title or "", t.description or "", t.content or ""]).lower()
            if q in hay:
                res.append(t)
        return res


class SQLAlchemySectionRepository:
    def __init__(self, task_repo: SQLAlchemyTaskRepository) -> None:
        self._sections: Dict[UUID, Section] = {}
        self._children: Dict[Optional[UUID], List[UUID]] = {}
        self._task_repo = task_repo

    def add(self, section: Section, index: NonNegativeInt) -> None:
        if index < 0:
            raise ValueError("index must be non-negative")
        if section.id is None:
            section.id = uuid4()
        if section.added_at is None:
            section.added_at = datetime.utcnow()
        section.check_flags()
        self._sections[section.id] = section
        lst = self._children.setdefault(section.parent_id, [])
        if index >= len(lst):
            lst.append(section.id)
        else:
            lst.insert(index, section.id)

    def get(self, section_id: UUID, with_direct_subsections: bool) -> Section:
        if section_id not in self._sections:
            raise ValueError("section not found")
        sec = self._sections[section_id]
        if not with_direct_subsections:
            return sec
        child_ids = self._children.get(section_id, [])
        subsections = [self._sections[cid] for cid in child_ids]
        sec.subsections = subsections
        sec.check_flags()
        return sec

    def update(self, section: Section, index: Optional[NonNegativeInt]) -> None:
        if section.id is None or section.id not in self._sections:
            raise ValueError("section not found")
        section.check_flags()
        self._sections[section.id] = section
        if index is not None:
            if index < 0:
                raise ValueError("index must be non-negative")
            parent = section.parent_id
            lst = self._children.setdefault(parent, [])
            if section.id in lst:
                lst.remove(section.id)
            if index >= len(lst):
                lst.append(section.id)
            else:
                lst.insert(index, section.id)

    def count_subsections(self, section_id: UUID) -> int:
        return len(self._children.get(section_id, []))

    def construct_sections_tree(self, section_models: List[SectionModel], return_flat: bool) -> List[Section]:
        sections = [sm.to_entity(tasks=[], subsections=[]) for sm in section_models]
        if return_flat:
            return sections
        by_id: Dict[UUID, Section] = {s.id: s for s in sections if s.id is not None}  # type: ignore[arg-type]
        roots: List[Section] = []
        for s in sections:
            if s.parent_id is None:
                roots.append(s)
            else:
                parent = by_id.get(s.parent_id)
                if parent is not None:
                    parent.subsections.append(s)
        for s in sections:
            s.check_flags()
        return roots

    def get_all_without_tasks(self, user_id: UUID, leaves_only: bool, as_tree: bool) -> List[Section]:
        secs = [s for s in self._sections.values() if s.user_id == user_id]
        if leaves_only:
            secs = [s for s in secs if not self._children.get(s.id, [])]
        if not as_tree:
            return secs
        by_id: Dict[UUID, Section] = {s.id: s for s in secs if s.id is not None}  # type: ignore[arg-type]
        for s in secs:
            s.subsections = []
        roots: List[Section] = []
        for s in secs:
            if s.parent_id is None:
                roots.append(s)
            else:
                p = by_id.get(s.parent_id)
                if p is not None:
                    p.subsections.append(s)
        for s in secs:
            s.check_flags()
        return roots


class SQLAlchemyUserRepository:
    def __init__(self) -> None:
        self._users: Dict[UUID, User] = {}
        self._verified: set[UUID] = set()
        self._sections_count: Dict[UUID, int] = {}
        self._tasks_count: Dict[UUID, int] = {}

    def add_user(self, user: User) -> None:
        if user.id is None:
            user.id = uuid4()
        if user.added_at is None:
            user.added_at = datetime.utcnow()
        self._users[user.id] = user
        self._sections_count.setdefault(user.id, 0)
        self._tasks_count.setdefault(user.id, 0)

    def bump_sections(self, user_id: UUID, delta: int) -> None:
        self._sections_count[user_id] = self._sections_count.get(user_id, 0) + delta

    def bump_tasks(self, user_id: UUID, delta: int) -> None:
        self._tasks_count[user_id] = self._tasks_count.get(user_id, 0) + delta

    def verify_user(self, user_id: UUID) -> None:
        if user_id not in self._users:
            raise ValueError("user not found")
        self._verified.add(user_id)

    def get_all_users(self) -> List[UserStats]:
        res: List[UserStats] = []
        for uid, u in self._users.items():
            res.append(
                UserStats(
                    user_id=uid,
                    email=u.email,
                    sections_count=self._sections_count.get(uid, 0),
                    tasks_count=self._tasks_count.get(uid, 0),
                )
            )
        return res


class AsyncSession:
    def __init__(self) -> None:
        self._in_transaction = True

    async def commit(self) -> None:
        self._in_transaction = False

    async def rollback(self) -> None:
        self._in_transaction = False

    async def close(self) -> None:
        self._in_transaction = False


class async_sessionmaker:
    def __init__(self) -> None:
        pass

    async def __call__(self) -> AsyncSession:
        return AsyncSession()


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
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory
        self.session: Optional[AsyncSession] = None
        self.task_repo = SQLAlchemyTaskRepository()
        self.section_repo = SQLAlchemySectionRepository(task_repo=self.task_repo)
        self.user_repo = SQLAlchemyUserRepository()

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = await self.session_factory()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.session is None:
            return
        if exc is not None:
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()

    async def commit(self) -> None:
        if self.session is None:
            return
        await self.session.commit()

    async def rollback(self) -> None:
        if self.session is None:
            return
        await self.session.rollback()