from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, Generic, Iterable, List, Literal, Optional, Sequence, Tuple, TypeVar, Union
from uuid import UUID, uuid4
from abc import ABC, abstractmethod
import random


NonNegativeInt = int


def _ensure_non_negative_int(value: int, name: str) -> None:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative int")


def _ensure_uuid(value: Any, name: str) -> None:
    if not isinstance(value, UUID):
        raise ValueError(f"{name} must be a UUID")


def _ensure_optional_uuid(value: Any, name: str) -> None:
    if value is not None and not isinstance(value, UUID):
        raise ValueError(f"{name} must be a UUID or None")


def _ensure_optional_date(value: Any, name: str) -> None:
    if value is not None and not isinstance(value, date):
        raise ValueError(f"{name} must be a date or None")


def _ensure_optional_datetime(value: Any, name: str) -> None:
    if value is not None and not isinstance(value, datetime):
        raise ValueError(f"{name} must be a datetime or None")


def _ensure_str(value: Any, name: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a str")


def _ensure_optional_str(value: Any, name: str) -> None:
    if value is not None and not isinstance(value, str):
        raise ValueError(f"{name} must be a str or None")


@dataclass
class Entity:
    model_config: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)


RecurrenceType = Literal["daily", "weekly", "monthly", "yearly"]


@dataclass
class RecurrenceInfo(Entity):
    flexible_mode: bool
    period: int
    type: RecurrenceType

    def __post_init__(self) -> None:
        if not isinstance(self.flexible_mode, bool):
            raise ValueError("flexible_mode must be bool")
        if not isinstance(self.period, int) or self.period <= 0:
            raise ValueError("period must be a positive int")
        if self.type not in ("daily", "weekly", "monthly", "yearly"):
            raise ValueError("type must be one of: daily, weekly, monthly, yearly")


@dataclass
class Attachment(Entity):
    added_at: Optional[datetime]
    aes_iv_b64: str
    aes_key_b64: str
    id: Optional[UUID]
    s3_file_key: str
    task_id: UUID

    def __post_init__(self) -> None:
        _ensure_optional_datetime(self.added_at, "added_at")
        _ensure_str(self.aes_iv_b64, "aes_iv_b64")
        _ensure_str(self.aes_key_b64, "aes_key_b64")
        _ensure_optional_uuid(self.id, "id")
        _ensure_str(self.s3_file_key, "s3_file_key")
        _ensure_uuid(self.task_id, "task_id")


@dataclass
class Task(Entity):
    added_at: Optional[datetime]
    attachments: Optional[List[Attachment]]
    content: Optional[str]
    description: Optional[str]
    due_to: Optional[date]
    id: Optional[UUID]
    is_archived: bool
    is_completed: bool
    recurrence: Optional[RecurrenceInfo]
    section_id: UUID
    title: str
    user_id: UUID

    def __post_init__(self) -> None:
        _ensure_optional_datetime(self.added_at, "added_at")
        if self.attachments is not None:
            if not isinstance(self.attachments, list) or any(not isinstance(a, Attachment) for a in self.attachments):
                raise ValueError("attachments must be a list[Attachment] or None")
        _ensure_optional_str(self.content, "content")
        _ensure_optional_str(self.description, "description")
        _ensure_optional_date(self.due_to, "due_to")
        _ensure_optional_uuid(self.id, "id")
        if not isinstance(self.is_archived, bool):
            raise ValueError("is_archived must be bool")
        if not isinstance(self.is_completed, bool):
            raise ValueError("is_completed must be bool")
        if self.recurrence is not None and not isinstance(self.recurrence, RecurrenceInfo):
            raise ValueError("recurrence must be RecurrenceInfo or None")
        _ensure_uuid(self.section_id, "section_id")
        _ensure_str(self.title, "title")
        _ensure_uuid(self.user_id, "user_id")
        self.check_recurrence_due_date(None)

    def check_recurrence_due_date(self, values: Any) -> Any:
        if self.recurrence is not None and self.due_to is None:
            raise ValueError("due_to must be set when recurrence is set")
        return values

    def add_attachment(self, attachment: Attachment) -> None:
        if not isinstance(attachment, Attachment):
            raise ValueError("attachment must be Attachment")
        if attachment.task_id != (self.id if self.id is not None else attachment.task_id):
            if self.id is not None and attachment.task_id != self.id:
                raise ValueError("attachment.task_id must match task.id")
        if self.attachments is None:
            self.attachments = []
        self.attachments.append(attachment)

    def remove_attachment(self, attachment: Attachment) -> None:
        if self.attachments is None:
            return
        self.attachments = [a for a in self.attachments if a is not attachment and a.id != attachment.id]

    def archive(self) -> None:
        self.is_archived = True

    def unarchive(self) -> None:
        self.is_archived = False

    def toggle_archived(self) -> None:
        self.is_archived = not self.is_archived

    def mark_completed(self, auto_archive: bool) -> None:
        if not isinstance(auto_archive, bool):
            raise ValueError("auto_archive must be bool")
        self.is_completed = True
        if auto_archive:
            self.is_archived = True

    def toggle_completed(self, auto_archive: bool) -> None:
        if not isinstance(auto_archive, bool):
            raise ValueError("auto_archive must be bool")
        self.is_completed = not self.is_completed
        if self.is_completed and auto_archive:
            self.is_archived = True


@dataclass
class Section(Entity):
    added_at: Optional[datetime]
    has_subsections: bool
    has_tasks: bool
    id: Optional[UUID]
    parent_id: Optional[UUID]
    subsections: List["Section"]
    tasks: List[Task]
    title: str
    user_id: UUID

    def __post_init__(self) -> None:
        _ensure_optional_datetime(self.added_at, "added_at")
        if not isinstance(self.has_subsections, bool):
            raise ValueError("has_subsections must be bool")
        if not isinstance(self.has_tasks, bool):
            raise ValueError("has_tasks must be bool")
        _ensure_optional_uuid(self.id, "id")
        _ensure_optional_uuid(self.parent_id, "parent_id")
        if not isinstance(self.subsections, list) or any(not isinstance(s, Section) for s in self.subsections):
            raise ValueError("subsections must be list[Section]")
        if not isinstance(self.tasks, list) or any(not isinstance(t, Task) for t in self.tasks):
            raise ValueError("tasks must be list[Task]")
        _ensure_str(self.title, "title")
        _ensure_uuid(self.user_id, "user_id")
        self.check_flags()

    def check_flags(self) -> "Section":
        self.has_subsections = len(self.subsections) > 0
        self.has_tasks = len(self.tasks) > 0
        return self

    @staticmethod
    def create_root_section(user_id: UUID) -> "Section":
        _ensure_uuid(user_id, "user_id")
        return Section(
            added_at=datetime.utcnow(),
            has_subsections=False,
            has_tasks=False,
            id=None,
            parent_id=None,
            subsections=[],
            tasks=[],
            title="Root",
            user_id=user_id,
        )

    def is_root(self) -> bool:
        return self.parent_id is None

    def insert_subsection(self, subsection: "Section", index: Optional[NonNegativeInt]) -> None:
        if not isinstance(subsection, Section):
            raise ValueError("subsection must be Section")
        if subsection.user_id != self.user_id:
            raise ValueError("subsection.user_id must match section.user_id")
        if index is not None:
            _ensure_non_negative_int(index, "index")
            if index > len(self.subsections):
                index = len(self.subsections)
            self.subsections.insert(index, subsection)
        else:
            self.subsections.append(subsection)
        self.check_flags()

    def remove_subsection(self, subsection: "Section") -> "Section":
        self.subsections = [s for s in self.subsections if s is not subsection and s.id != subsection.id]
        self.check_flags()
        return subsection

    def insert_task(self, task: Task, index: Optional[NonNegativeInt]) -> None:
        if not isinstance(task, Task):
            raise ValueError("task must be Task")
        if task.user_id != self.user_id:
            raise ValueError("task.user_id must match section.user_id")
        if self.id is not None and task.section_id != self.id:
            raise ValueError("task.section_id must match section.id")
        if index is not None:
            _ensure_non_negative_int(index, "index")
            if index > len(self.tasks):
                index = len(self.tasks)
            self.tasks.insert(index, task)
        else:
            self.tasks.append(task)
        self.check_flags()

    def remove_task(self, task: Task) -> Task:
        self.tasks = [t for t in self.tasks if t is not task and t.id != task.id]
        self.check_flags()
        return task

    def shuffle_tasks(self) -> None:
        random.shuffle(self.tasks)
        self.check_flags()

    @staticmethod
    def move_task(task_to_move: Task, section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if not isinstance(task_to_move, Task):
            raise ValueError("task_to_move must be Task")
        if not isinstance(section_from, Section) or not isinstance(section_to, Section):
            raise ValueError("section_from and section_to must be Section")
        _ensure_non_negative_int(index, "index")
        if section_from.user_id != section_to.user_id or task_to_move.user_id != section_to.user_id:
            raise ValueError("user_id mismatch")
        section_from.remove_task(task_to_move)
        if section_to.id is not None:
            task_to_move.section_id = section_to.id
        section_to.insert_task(task_to_move, index)

    @staticmethod
    def move_section(section: "Section", section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if not isinstance(section, Section):
            raise ValueError("section must be Section")
        if not isinstance(section_from, Section) or not isinstance(section_to, Section):
            raise ValueError("section_from and section_to must be Section")
        _ensure_non_negative_int(index, "index")
        if section_from.user_id != section_to.user_id or section.user_id != section_to.user_id:
            raise ValueError("user_id mismatch")
        section_from.remove_subsection(section)
        section.parent_id = section_to.id
        section_to.insert_subsection(section, index)


@dataclass
class User(Entity):
    added_at: Optional[datetime]
    email: str
    id: Optional[UUID]
 
    def __post_init__(self) -> None:
        _ensure_optional_datetime(self.added_at, "added_at")
        _ensure_str(self.email, "email")
        _ensure_optional_uuid(self.id, "id")


@dataclass
class UserStats(Entity):
    user: User
    sections_count: int
    tasks_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.user, User):
            raise ValueError("user must be User")
        if not isinstance(self.sections_count, int) or self.sections_count < 0:
            raise ValueError("sections_count must be non-negative int")
        if not isinstance(self.tasks_count, int) or self.tasks_count < 0:
            raise ValueError("tasks_count must be non-negative int")


T = TypeVar("T")


class Mapped(Generic[T]):
    def __init__(self, value: Optional[T] = None):
        self.value = value

    def __repr__(self) -> str:
        return f"Mapped({self.value!r})"


class AccessTokenModel:
    pass


@dataclass
class AttachmentModel:
    added_at: Mapped[datetime]
    aes_iv_b64: Mapped[str]
    aes_key_b64: Mapped[str]
    id: Mapped[UUID]
    index: Mapped[int]
    s3_file_key: Mapped[str]
    task: Any = None
    task_id: Mapped[UUID] = field(default_factory=lambda: Mapped(uuid4()))

    @staticmethod
    def from_entity(attachment: Attachment, index: NonNegativeInt) -> "AttachmentModel":
        if not isinstance(attachment, Attachment):
            raise ValueError("attachment must be Attachment")
        _ensure_non_negative_int(index, "index")
        att_id = attachment.id or uuid4()
        added_at = attachment.added_at or datetime.utcnow()
        return AttachmentModel(
            added_at=Mapped(added_at),
            aes_iv_b64=Mapped(attachment.aes_iv_b64),
            aes_key_b64=Mapped(attachment.aes_key_b64),
            id=Mapped(att_id),
            index=Mapped(index),
            s3_file_key=Mapped(attachment.s3_file_key),
            task=None,
            task_id=Mapped(attachment.task_id),
        )

    def to_entity(self) -> Attachment:
        return Attachment(
            added_at=self.added_at.value,
            aes_iv_b64=self.aes_iv_b64.value,
            aes_key_b64=self.aes_key_b64.value,
            id=self.id.value,
            s3_file_key=self.s3_file_key.value,
            task_id=self.task_id.value,
        )


@dataclass
class TaskModel:
    added_at: Mapped[datetime]
    attachments: Any = None
    description: Mapped[Optional[str]] = field(default_factory=lambda: Mapped(None))
    due_to: Mapped[Optional[date]] = field(default_factory=lambda: Mapped(None))
    flexible_recurrence_mode: Mapped[Optional[bool]] = field(default_factory=lambda: Mapped(None))
    id: Mapped[UUID] = field(default_factory=lambda: Mapped(uuid4()))
    index: Mapped[int] = field(default_factory=lambda: Mapped(0))
    is_archived: Mapped[bool] = field(default_factory=lambda: Mapped(False))
    is_completed: Mapped[bool] = field(default_factory=lambda: Mapped(False))
    recurrence_period: Mapped[Optional[int]] = field(default_factory=lambda: Mapped(None))
    recurrence_type: Mapped[Optional[str]] = field(default_factory=lambda: Mapped(None))
    section: Any = None
    section_id: Mapped[UUID] = field(default_factory=lambda: Mapped(uuid4()))
    title: Mapped[str] = field(default_factory=lambda: Mapped(""))
    user: Any = None
    user_id: Mapped[UUID] = field(default_factory=lambda: Mapped(uuid4()))

    @staticmethod
    def from_entity(task: Task, index: NonNegativeInt) -> "TaskModel":
        if not isinstance(task, Task):
            raise ValueError("task must be Task")
        _ensure_non_negative_int(index, "index")
        task_id = task.id or uuid4()
        added_at = task.added_at or datetime.utcnow()
        rec_type: Optional[str] = None
        rec_period: Optional[int] = None
        flex: Optional[bool] = None
        if task.recurrence is not None:
            rec_type = task.recurrence.type
            rec_period = task.recurrence.period
            flex = task.recurrence.flexible_mode
        return TaskModel(
            added_at=Mapped(added_at),
            attachments=None,
            description=Mapped(task.description),
            due_to=Mapped(task.due_to),
            flexible_recurrence_mode=Mapped(flex),
            id=Mapped(task_id),
            index=Mapped(index),
            is_archived=Mapped(task.is_archived),
            is_completed=Mapped(task.is_completed),
            recurrence_period=Mapped(rec_period),
            recurrence_type=Mapped(rec_type),
            section=None,
            section_id=Mapped(task.section_id),
            title=Mapped(task.title),
            user=None,
            user_id=Mapped(task.user_id),
        )

    def to_entity(self, attachments: List[Attachment]) -> Task:
        rec: Optional[RecurrenceInfo] = None
        if self.recurrence_type.value is not None or self.recurrence_period.value is not None or self.flexible_recurrence_mode.value is not None:
            if self.recurrence_type.value is None or self.recurrence_period.value is None or self.flexible_recurrence_mode.value is None:
                raise ValueError("Incomplete recurrence fields in TaskModel")
            rec = RecurrenceInfo(
                flexible_mode=bool(self.flexible_recurrence_mode.value),
                period=int(self.recurrence_period.value),
                type=self.recurrence_type.value,  # type: ignore[arg-type]
            )
        return Task(
            added_at=self.added_at.value,
            attachments=list(attachments),
            content=None,
            description=self.description.value,
            due_to=self.due_to.value,
            id=self.id.value,
            is_archived=bool(self.is_archived.value),
            is_completed=bool(self.is_completed.value),
            recurrence=rec,
            section_id=self.section_id.value,
            title=self.title.value,
            user_id=self.user_id.value,
        )


@dataclass
class SectionModel:
    added_at: Mapped[datetime]
    has_subsections: Mapped[bool]
    has_tasks: Mapped[bool]
    id: Mapped[UUID]
    index: Mapped[int]
    parent_id: Mapped[Optional[UUID]]
    tasks: Mapped[List[TaskModel]]
    title: Mapped[str]
    user: Any = None
    user_id: Mapped[UUID] = field(default_factory=lambda: Mapped(uuid4()))

    @staticmethod
    def from_entity(section: Section, index: NonNegativeInt) -> "SectionModel":
        if not isinstance(section, Section):
            raise ValueError("section must be Section")
        _ensure_non_negative_int(index, "index")
        sec_id = section.id or uuid4()
        added_at = section.added_at or datetime.utcnow()
        return SectionModel(
            added_at=Mapped(added_at),
            has_subsections=Mapped(bool(section.has_subsections)),
            has_tasks=Mapped(bool(section.has_tasks)),
            id=Mapped(sec_id),
            index=Mapped(index),
            parent_id=Mapped(section.parent_id),
            tasks=Mapped([]),
            title=Mapped(section.title),
            user=None,
            user_id=Mapped(section.user_id),
        )

    def to_entity(self, tasks: List[Task], subsections: List[Section]) -> Section:
        return Section(
            added_at=self.added_at.value,
            has_subsections=bool(self.has_subsections.value),
            has_tasks=bool(self.has_tasks.value),
            id=self.id.value,
            parent_id=self.parent_id.value,
            subsections=list(subsections),
            tasks=list(tasks),
            title=self.title.value,
            user_id=self.user_id.value,
        )


@dataclass
class UserModel:
    added_at: Mapped[datetime]
    sections: Any = None
    tasks: Any = None
    id: Mapped[UUID] = field(default_factory=lambda: Mapped(uuid4()))
    email: Mapped[str] = field(default_factory=lambda: Mapped(""))

    def to_entity(self) -> User:
        return User(
            added_at=self.added_at.value,
            email=self.email.value,
            id=self.id.value,
        )


class AsyncSession:
    def __init__(self) -> None:
        self._pending: List[Tuple[str, Any]] = []
        self._committed: bool = False
        self._rolled_back: bool = False

    async def commit(self) -> None:
        self._committed = True
        self._pending.clear()

    async def rollback(self) -> None:
        self._rolled_back = True
        self._pending.clear()


class async_sessionmaker:
    def __init__(self, factory: Optional[Any] = None):
        self._factory = factory or AsyncSession

    def __call__(self) -> AsyncSession:
        return self._factory()


class SQLAlchemyTaskRepository:
    def __init__(self) -> None:
        self._tasks_by_id: Dict[UUID, Task] = {}
        self._tasks_by_section: Dict[UUID, List[UUID]] = {}
        self._attachments_by_id: Dict[UUID, Attachment] = {}
        self._attachments_by_task: Dict[UUID, List[UUID]] = {}

    def add(self, task: Task, index: NonNegativeInt) -> None:
        if not isinstance(task, Task):
            raise ValueError("task must be Task")
        _ensure_non_negative_int(index, "index")
        if task.id is None:
            task.id = uuid4()
        if task.added_at is None:
            task.added_at = datetime.utcnow()
        self._tasks_by_id[task.id] = task
        lst = self._tasks_by_section.setdefault(task.section_id, [])
        if index > len(lst):
            index = len(lst)
        if task.id in lst:
            lst.remove(task.id)
        lst.insert(index, task.id)

        if task.attachments:
            for a in task.attachments:
                if a.id is None:
                    a.id = uuid4()
                if a.added_at is None:
                    a.added_at = datetime.utcnow()
                self._attachments_by_id[a.id] = a
                alst = self._attachments_by_task.setdefault(task.id, [])
                if a.id not in alst:
                    alst.append(a.id)

    def get(self, task_id: UUID) -> Task:
        _ensure_uuid(task_id, "task_id")
        if task_id not in self._tasks_by_id:
            raise KeyError("Task not found")
        task = self._tasks_by_id[task_id]
        att_ids = self._attachments_by_task.get(task_id, [])
        attachments = [self._attachments_by_id[aid] for aid in att_ids if aid in self._attachments_by_id]
        task.attachments = attachments
        return task

    def remove(self, task: Task) -> None:
        if not isinstance(task, Task):
            raise ValueError("task must be Task")
        if task.id is None:
            return
        tid = task.id
        self._tasks_by_id.pop(tid, None)
        if task.section_id in self._tasks_by_section:
            self._tasks_by_section[task.section_id] = [x for x in self._tasks_by_section[task.section_id] if x != tid]
        for aid in list(self._attachments_by_task.get(tid, [])):
            self._attachments_by_id.pop(aid, None)
        self._attachments_by_task.pop(tid, None)

    def delete_attachment(self, attachment: Attachment) -> None:
        if not isinstance(attachment, Attachment):
            raise ValueError("attachment must be Attachment")
        if attachment.id is None:
            return
        aid = attachment.id
        self._attachments_by_id.pop(aid, None)
        if attachment.task_id in self._attachments_by_task:
            self._attachments_by_task[attachment.task_id] = [x for x in self._attachments_by_task[attachment.task_id] if x != aid]

    def update_or_create(self, task: Task, index: Optional[NonNegativeInt], must_exist: bool) -> None:
        if not isinstance(task, Task):
            raise ValueError("task must be Task")
        if index is not None:
            _ensure_non_negative_int(index, "index")
        if task.id is None:
            if must_exist:
                raise KeyError("Task must exist")
            self.add(task, index or 0)
            return
        exists = task.id in self._tasks_by_id
        if must_exist and not exists:
            raise KeyError("Task must exist")
        if not exists:
            self.add(task, index or 0)
            return
        self._tasks_by_id[task.id] = task
        if index is not None:
            lst = self._tasks_by_section.setdefault(task.section_id, [])
            if task.id in lst:
                lst.remove(task.id)
            if index > len(lst):
                index = len(lst)
            lst.insert(index, task.id)

    def update_or_create_bulk(self, section_tasks: List[Task]) -> None:
        if not isinstance(section_tasks, list) or any(not isinstance(t, Task) for t in section_tasks):
            raise ValueError("section_tasks must be list[Task]")
        for idx, task in enumerate(section_tasks):
            self.update_or_create(task, idx, must_exist=False)

    def get_archived_tasks(self, user_id: UUID) -> List[Task]:
        _ensure_uuid(user_id, "user_id")
        return [t for t in self._tasks_by_id.values() if t.user_id == user_id and t.is_archived]

    def get_overdue_tasks(self, user_id: UUID) -> List[Task]:
        _ensure_uuid(user_id, "user_id")
        today = date.today()
        return [
            t
            for t in self._tasks_by_id.values()
            if t.user_id == user_id and not t.is_completed and not t.is_archived and t.due_to is not None and t.due_to < today
        ]

    def get_tasks_by_due_to(self, not_before: date, not_after: date, user_id: UUID) -> List[Task]:
        if not isinstance(not_before, date) or not isinstance(not_after, date):
            raise ValueError("not_before and not_after must be date")
        _ensure_uuid(user_id, "user_id")
        return [
            t
            for t in self._tasks_by_id.values()
            if t.user_id == user_id and t.due_to is not None and not_before <= t.due_to <= not_after
        ]

    def search(self, user_id: UUID, query: str) -> List[Task]:
        _ensure_uuid(user_id, "user_id")
        _ensure_str(query, "query")
        q = query.lower()
        res: List[Task] = []
        for t in self._tasks_by_id.values():
            if t.user_id != user_id:
                continue
            hay = " ".join([t.title or "", t.description or "", t.content or ""]).lower()
            if q in hay:
                res.append(t)
        return res

    def get_entity(self, task_model: TaskModel) -> Task:
        if not isinstance(task_model, TaskModel):
            raise ValueError("task_model must be TaskModel")
        tid = task_model.id.value
        att_ids = self._attachments_by_task.get(tid, [])
        attachments = [self._attachments_by_id[aid] for aid in att_ids if aid in self._attachments_by_id]
        return task_model.to_entity(attachments=attachments)

    def get_entities(self, task_models: Sequence[TaskModel]) -> List[Task]:
        if any(not isinstance(tm, TaskModel) for tm in task_models):
            raise ValueError("task_models must be Sequence[TaskModel]")
        return [self.get_entity(tm) for tm in task_models]


class SQLAlchemySectionRepository:
    def __init__(self, task_repo: Optional[SQLAlchemyTaskRepository] = None) -> None:
        self._sections_by_id: Dict[UUID, Section] = {}
        self._sections_by_parent: Dict[Optional[UUID], List[UUID]] = {}
        self._task_repo = task_repo

    def add(self, section: Section, index: NonNegativeInt) -> None:
        if not isinstance(section, Section):
            raise ValueError("section must be Section")
        _ensure_non_negative_int(index, "index")
        if section.id is None:
            section.id = uuid4()
        if section.added_at is None:
            section.added_at = datetime.utcnow()
        self._sections_by_id[section.id] = section
        lst = self._sections_by_parent.setdefault(section.parent_id, [])
        if index > len(lst):
            index = len(lst)
        if section.id in lst:
            lst.remove(section.id)
        lst.insert(index, section.id)

    def update(self, section: Section, index: Optional[NonNegativeInt]) -> None:
        if not isinstance(section, Section):
            raise ValueError("section must be Section")
        if section.id is None or section.id not in self._sections_by_id:
            raise KeyError("Section not found")
        if index is not None:
            _ensure_non_negative_int(index, "index")
        self._sections_by_id[section.id] = section
        if index is not None:
            lst = self._sections_by_parent.setdefault(section.parent_id, [])
            if section.id in lst:
                lst.remove(section.id)
            if index > len(lst):
                index = len(lst)
            lst.insert(index, section.id)

    def count_subsections(self, section_id: UUID) -> int:
        _ensure_uuid(section_id, "section_id")
        return len(self._sections_by_parent.get(section_id, []))

    def get(self, section_id: UUID, with_direct_subsections: bool) -> Section:
        _ensure_uuid(section_id, "section_id")
        if section_id not in self._sections_by_id:
            raise KeyError("Section not found")
        sec = self._sections_by_id[section_id]
        if with_direct_subsections:
            child_ids = self._sections_by_parent.get(section_id, [])
            sec.subsections = [self._sections_by_id[cid] for cid in child_ids if cid in self._sections_by_id]
        sec.check_flags()
        return sec

    def construct_sections_tree(self, section_models: List[SectionModel], return_flat: bool) -> List[Section]:
        if not isinstance(section_models, list) or any(not isinstance(sm, SectionModel) for sm in section_models):
            raise ValueError("section_models must be list[SectionModel]")
        entities: Dict[UUID, Section] = {}
        for sm in section_models:
            sec = sm.to_entity(tasks=[], subsections=[])
            entities[sec.id] = sec  # type: ignore[index]
        roots: List[Section] = []
        for sec in entities.values():
            pid = sec.parent_id
            if pid is None or pid not in entities:
                roots.append(sec)
            else:
                entities[pid].subsections.append(sec)
        for sec in entities.values():
            sec.check_flags()
        if return_flat:
            return list(entities.values())
        return roots

    def get_all_without_tasks(self, user_id: UUID, leaves_only: bool, as_tree: bool) -> List[Section]:
        _ensure_uuid(user_id, "user_id")
        secs = [s for s in self._sections_by_id.values() if s.user_id == user_id]
        if leaves_only:
            secs = [s for s in secs if len(self._sections_by_parent.get(s.id, [])) == 0]
        if as_tree:
            id_to_copy: Dict[UUID, Section] = {}
            for s in secs:
                id_to_copy[s.id] = Section(
                    added_at=s.added_at,
                    has_subsections=s.has_subsections,
                    has_tasks=False,
                    id=s.id,
                    parent_id=s.parent_id,
                    subsections=[],
                    tasks=[],
                    title=s.title,
                    user_id=s.user_id,
                )
            roots: List[Section] = []
            for s in id_to_copy.values():
                if s.parent_id is None or s.parent_id not in id_to_copy:
                    roots.append(s)
                else:
                    id_to_copy[s.parent_id].subsections.append(s)
            for s in id_to_copy.values():
                s.check_flags()
            return roots
        for s in secs:
            s.tasks = []
            s.check_flags()
        return secs


class SQLAlchemyUserRepository:
    def __init__(self, section_repo: Optional[SQLAlchemySectionRepository] = None, task_repo: Optional[SQLAlchemyTaskRepository] = None) -> None:
        self._users_by_id: Dict[UUID, User] = {}
        self._section_repo = section_repo
        self._task_repo = task_repo

    def verify_user(self, user_id: UUID) -> None:
        _ensure_uuid(user_id, "user_id")
        if user_id not in self._users_by_id:
            raise KeyError("User not found")

    def get_all_users(self) -> List[UserStats]:
        stats: List[UserStats] = []
        for u in self._users_by_id.values():
            sections_count = 0
            tasks_count = 0
            if self._section_repo is not None:
                sections_count = len([s for s in self._section_repo._sections_by_id.values() if s.user_id == u.id])
            if self._task_repo is not None:
                tasks_count = len([t for t in self._task_repo._tasks_by_id.values() if t.user_id == u.id])
            stats.append(UserStats(user=u, sections_count=sections_count, tasks_count=tasks_count))
        return stats

    def _add_user(self, user: User) -> None:
        if user.id is None:
            user.id = uuid4()
        if user.added_at is None:
            user.added_at = datetime.utcnow()
        self._users_by_id[user.id] = user


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
    def __init__(self, session_factory: Optional[async_sessionmaker] = None) -> None:
        self.session_factory: async_sessionmaker = session_factory or async_sessionmaker()
        self.session: AsyncSession = self.session_factory()
        self.task_repo = SQLAlchemyTaskRepository()
        self.section_repo = SQLAlchemySectionRepository(task_repo=self.task_repo)
        self.user_repo = SQLAlchemyUserRepository(section_repo=self.section_repo, task_repo=self.task_repo)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()