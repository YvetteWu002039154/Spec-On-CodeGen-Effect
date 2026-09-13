from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, ClassVar, Dict, Iterable, List, Literal, Optional, Sequence, Tuple, TypeVar
from uuid import UUID, uuid4
from abc import ABC, abstractmethod


NonNegativeInt = int


def _validate_non_negative_int(value: int, name: str) -> int:
    if not isinstance(value, int):
        raise TypeError(f"{name} must be int")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _validate_optional_non_negative_int(value: Optional[int], name: str) -> Optional[int]:
    if value is None:
        return None
    return _validate_non_negative_int(value, name)


def _validate_uuid(value: UUID, name: str) -> UUID:
    if not isinstance(value, UUID):
        raise TypeError(f"{name} must be UUID")
    return value


def _validate_optional_uuid(value: Optional[UUID], name: str) -> Optional[UUID]:
    if value is None:
        return None
    return _validate_uuid(value, name)


def _now_utc_naive() -> datetime:
    return datetime.utcnow()


@dataclass
class Entity:
    model_config: ClassVar[dict] = {"arbitrary_types_allowed": True}


@dataclass
class RecurrenceInfo(Entity):
    type: Literal["daily", "weekly", "monthly", "yearly"]
    period: int
    flexible_mode: bool

    def __post_init__(self) -> None:
        if self.type not in ("daily", "weekly", "monthly", "yearly"):
            raise ValueError("RecurrenceInfo.type must be one of: daily, weekly, monthly, yearly")
        if not isinstance(self.period, int):
            raise TypeError("RecurrenceInfo.period must be int")
        if self.period <= 0:
            raise ValueError("RecurrenceInfo.period must be positive")
        if not isinstance(self.flexible_mode, bool):
            raise TypeError("RecurrenceInfo.flexible_mode must be bool")


@dataclass
class Attachment(Entity):
    task_id: UUID
    s3_file_key: str
    aes_key_b64: str
    aes_iv_b64: str
    id: Optional[UUID] = None
    added_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        _validate_uuid(self.task_id, "Attachment.task_id")
        if not isinstance(self.s3_file_key, str) or not self.s3_file_key:
            raise ValueError("Attachment.s3_file_key must be a non-empty str")
        if not isinstance(self.aes_key_b64, str) or not self.aes_key_b64:
            raise ValueError("Attachment.aes_key_b64 must be a non-empty str")
        if not isinstance(self.aes_iv_b64, str) or not self.aes_iv_b64:
            raise ValueError("Attachment.aes_iv_b64 must be a non-empty str")
        _validate_optional_uuid(self.id, "Attachment.id")
        if self.added_at is not None and not isinstance(self.added_at, datetime):
            raise TypeError("Attachment.added_at must be datetime or None")


@dataclass
class Task(Entity):
    user_id: UUID
    section_id: UUID
    title: str
    id: Optional[UUID] = None
    added_at: Optional[datetime] = None
    description: Optional[str] = None
    content: Optional[str] = None
    due_to: Optional[date] = None
    is_archived: bool = False
    is_completed: bool = False
    recurrence: Optional[RecurrenceInfo] = None
    attachments: Optional[List[Attachment]] = None

    def __post_init__(self) -> None:
        _validate_uuid(self.user_id, "Task.user_id")
        _validate_uuid(self.section_id, "Task.section_id")
        if not isinstance(self.title, str) or not self.title:
            raise ValueError("Task.title must be a non-empty str")
        _validate_optional_uuid(self.id, "Task.id")
        if self.added_at is not None and not isinstance(self.added_at, datetime):
            raise TypeError("Task.added_at must be datetime or None")
        if self.description is not None and not isinstance(self.description, str):
            raise TypeError("Task.description must be str or None")
        if self.content is not None and not isinstance(self.content, str):
            raise TypeError("Task.content must be str or None")
        if self.due_to is not None and not isinstance(self.due_to, date):
            raise TypeError("Task.due_to must be date or None")
        if not isinstance(self.is_archived, bool):
            raise TypeError("Task.is_archived must be bool")
        if not isinstance(self.is_completed, bool):
            raise TypeError("Task.is_completed must be bool")
        if self.recurrence is not None and not isinstance(self.recurrence, RecurrenceInfo):
            raise TypeError("Task.recurrence must be RecurrenceInfo or None")
        if self.attachments is not None:
            if not isinstance(self.attachments, list):
                raise TypeError("Task.attachments must be list[Attachment] or None")
            for a in self.attachments:
                if not isinstance(a, Attachment):
                    raise TypeError("Task.attachments must contain Attachment")
                if a.task_id != (self.id if self.id is not None else a.task_id):
                    pass
        self.check_recurrence_due_date(None)

    def check_recurrence_due_date(self, values: Any) -> Any:
        if self.recurrence is not None and self.due_to is None:
            raise ValueError("Task.due_to must be set when recurrence is set")
        return values

    def add_attachment(self, attachment: Attachment) -> None:
        if not isinstance(attachment, Attachment):
            raise TypeError("attachment must be Attachment")
        if self.id is not None and attachment.task_id != self.id:
            raise ValueError("attachment.task_id must match task.id")
        if self.attachments is None:
            self.attachments = []
        self.attachments.append(attachment)

    def remove_attachment(self, attachment: Attachment) -> None:
        if self.attachments is None:
            raise ValueError("No attachments to remove from")
        try:
            self.attachments.remove(attachment)
        except ValueError as e:
            raise ValueError("Attachment not found in task") from e

    def archive(self) -> None:
        self.is_archived = True

    def unarchive(self) -> None:
        self.is_archived = False

    def toggle_archived(self) -> None:
        self.is_archived = not self.is_archived

    def mark_completed(self, auto_archive: bool) -> None:
        if not isinstance(auto_archive, bool):
            raise TypeError("auto_archive must be bool")
        self.is_completed = True
        if auto_archive:
            self.is_archived = True

    def toggle_completed(self, auto_archive: bool) -> None:
        if not isinstance(auto_archive, bool):
            raise TypeError("auto_archive must be bool")
        self.is_completed = not self.is_completed
        if self.is_completed and auto_archive:
            self.is_archived = True


@dataclass
class Section(Entity):
    user_id: UUID
    title: str
    id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    added_at: Optional[datetime] = None
    subsections: List["Section"] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)
    has_subsections: bool = False
    has_tasks: bool = False

    def __post_init__(self) -> None:
        _validate_uuid(self.user_id, "Section.user_id")
        if not isinstance(self.title, str) or not self.title:
            raise ValueError("Section.title must be a non-empty str")
        _validate_optional_uuid(self.id, "Section.id")
        _validate_optional_uuid(self.parent_id, "Section.parent_id")
        if self.added_at is not None and not isinstance(self.added_at, datetime):
            raise TypeError("Section.added_at must be datetime or None")
        if not isinstance(self.subsections, list):
            raise TypeError("Section.subsections must be list[Section]")
        if not isinstance(self.tasks, list):
            raise TypeError("Section.tasks must be list[Task]")
        for s in self.subsections:
            if not isinstance(s, Section):
                raise TypeError("Section.subsections must contain Section")
        for t in self.tasks:
            if not isinstance(t, Task):
                raise TypeError("Section.tasks must contain Task")
        self.check_flags()

    def check_flags(self) -> "Section":
        self.has_subsections = len(self.subsections) > 0
        self.has_tasks = len(self.tasks) > 0
        return self

    @classmethod
    def create_root_section(cls, user_id: UUID) -> "Section":
        _validate_uuid(user_id, "user_id")
        return cls(user_id=user_id, title="Root", parent_id=None)

    def is_root(self) -> bool:
        return self.parent_id is None

    def insert_subsection(self, subsection: "Section", index: Optional[NonNegativeInt]) -> None:
        if not isinstance(subsection, Section):
            raise TypeError("subsection must be Section")
        if subsection.user_id != self.user_id:
            raise ValueError("subsection.user_id must match section.user_id")
        _validate_optional_non_negative_int(index, "index")
        if index is None or index >= len(self.subsections):
            self.subsections.append(subsection)
        else:
            self.subsections.insert(index, subsection)
        self.check_flags()

    def remove_subsection(self, subsection: "Section") -> "Section":
        try:
            self.subsections.remove(subsection)
        except ValueError as e:
            raise ValueError("subsection not found") from e
        self.check_flags()
        return subsection

    def insert_task(self, task: Task, index: Optional[NonNegativeInt]) -> None:
        if not isinstance(task, Task):
            raise TypeError("task must be Task")
        if task.user_id != self.user_id:
            raise ValueError("task.user_id must match section.user_id")
        if self.id is not None and task.section_id != self.id:
            raise ValueError("task.section_id must match section.id")
        _validate_optional_non_negative_int(index, "index")
        if index is None or index >= len(self.tasks):
            self.tasks.append(task)
        else:
            self.tasks.insert(index, task)
        self.check_flags()

    def remove_task(self, task: Task) -> Task:
        try:
            self.tasks.remove(task)
        except ValueError as e:
            raise ValueError("task not found") from e
        self.check_flags()
        return task

    def shuffle_tasks(self) -> None:
        self.tasks = list(reversed(self.tasks))
        self.check_flags()

    @staticmethod
    def move_task(task_to_move: Task, section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if not isinstance(task_to_move, Task):
            raise TypeError("task_to_move must be Task")
        if not isinstance(section_from, Section) or not isinstance(section_to, Section):
            raise TypeError("section_from and section_to must be Section")
        _validate_non_negative_int(index, "index")
        if section_from.user_id != section_to.user_id or task_to_move.user_id != section_to.user_id:
            raise ValueError("user_id mismatch between task/sections")
        section_from.remove_task(task_to_move)
        if section_to.id is not None:
            task_to_move.section_id = section_to.id
        section_to.insert_task(task_to_move, index)
        section_from.check_flags()
        section_to.check_flags()

    @staticmethod
    def move_section(section: "Section", section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if not isinstance(section, Section):
            raise TypeError("section must be Section")
        if not isinstance(section_from, Section) or not isinstance(section_to, Section):
            raise TypeError("section_from and section_to must be Section")
        _validate_non_negative_int(index, "index")
        if section_from.user_id != section_to.user_id or section.user_id != section_to.user_id:
            raise ValueError("user_id mismatch between sections")
        section_from.remove_subsection(section)
        if section_to.id is not None:
            section.parent_id = section_to.id
        else:
            section.parent_id = None
        section_to.insert_subsection(section, index)
        section_from.check_flags()
        section_to.check_flags()


@dataclass
class User(Entity):
    email: str
    id: Optional[UUID] = None
    added_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not isinstance(self.email, str) or not self.email:
            raise ValueError("User.email must be a non-empty str")
        _validate_optional_uuid(self.id, "User.id")
        if self.added_at is not None and not isinstance(self.added_at, datetime):
            raise TypeError("User.added_at must be datetime or None")


T = TypeVar("T")


class Mapped(Generic[T]):  # type: ignore[misc]
    def __init__(self, value: Optional[T] = None):
        self.value = value

    def __repr__(self) -> str:
        return f"Mapped({self.value!r})"


GUID = UUID


@dataclass
class AttachmentModel:
    id: UUID
    task_id: UUID
    index: int
    s3_file_key: str
    aes_key_b64: str
    aes_iv_b64: str
    added_at: datetime
    task: Optional["TaskModel"] = None

    @staticmethod
    def from_entity(attachment: Attachment, index: NonNegativeInt) -> "AttachmentModel":
        _validate_non_negative_int(index, "index")
        if attachment.id is None:
            attachment_id = uuid4()
        else:
            attachment_id = attachment.id
        added_at = attachment.added_at or _now_utc_naive()
        return AttachmentModel(
            id=attachment_id,
            task_id=attachment.task_id,
            index=index,
            s3_file_key=attachment.s3_file_key,
            aes_key_b64=attachment.aes_key_b64,
            aes_iv_b64=attachment.aes_iv_b64,
            added_at=added_at,
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


@dataclass
class TaskModel:
    id: UUID
    user_id: UUID
    section_id: UUID
    index: int
    title: str
    description: Optional[str]
    due_to: Optional[date]
    is_archived: bool
    is_completed: bool
    recurrence_type: Optional[str]
    recurrence_period: Optional[int]
    flexible_recurrence_mode: Optional[bool]
    added_at: datetime
    attachments: List[AttachmentModel] = field(default_factory=list)
    section: Optional["SectionModel"] = None
    user: Optional["UserModel"] = None

    @staticmethod
    def from_entity(task: Task, index: NonNegativeInt) -> "TaskModel":
        _validate_non_negative_int(index, "index")
        if task.id is None:
            task_id = uuid4()
        else:
            task_id = task.id
        added_at = task.added_at or _now_utc_naive()
        recurrence_type: Optional[str] = None
        recurrence_period: Optional[int] = None
        flexible_mode: Optional[bool] = None
        if task.recurrence is not None:
            recurrence_type = str(task.recurrence.type)
            recurrence_period = int(task.recurrence.period)
            flexible_mode = bool(task.recurrence.flexible_mode)
        model = TaskModel(
            id=task_id,
            user_id=task.user_id,
            section_id=task.section_id,
            index=index,
            title=task.title,
            description=task.description,
            due_to=task.due_to,
            is_archived=task.is_archived,
            is_completed=task.is_completed,
            recurrence_type=recurrence_type,
            recurrence_period=recurrence_period,
            flexible_recurrence_mode=flexible_mode,
            added_at=added_at,
            attachments=[],
        )
        if task.attachments:
            model.attachments = [
                AttachmentModel.from_entity(a, i) for i, a in enumerate(task.attachments)
            ]
            for am in model.attachments:
                am.task = model
        return model

    def to_entity(self, attachments: List[Attachment]) -> Task:
        recurrence: Optional[RecurrenceInfo] = None
        if self.recurrence_type is not None or self.recurrence_period is not None or self.flexible_recurrence_mode is not None:
            if self.recurrence_type is None or self.recurrence_period is None or self.flexible_recurrence_mode is None:
                raise ValueError("Incomplete recurrence fields on TaskModel")
            recurrence = RecurrenceInfo(
                type=self.recurrence_type, period=self.recurrence_period, flexible_mode=self.flexible_recurrence_mode
            )
        return Task(
            id=self.id,
            user_id=self.user_id,
            section_id=self.section_id,
            title=self.title,
            description=self.description,
            due_to=self.due_to,
            is_archived=self.is_archived,
            is_completed=self.is_completed,
            recurrence=recurrence,
            attachments=attachments,
            added_at=self.added_at,
        )


@dataclass
class SectionModel:
    id: UUID
    user_id: UUID
    index: int
    title: str
    parent_id: Optional[GUID]
    has_subsections: bool
    has_tasks: bool
    added_at: datetime
    tasks: List[TaskModel] = field(default_factory=list)
    user: Optional["UserModel"] = None

    @staticmethod
    def from_entity(section: Section, index: NonNegativeInt) -> "SectionModel":
        _validate_non_negative_int(index, "index")
        if section.id is None:
            section_id = uuid4()
        else:
            section_id = section.id
        added_at = section.added_at or _now_utc_naive()
        model = SectionModel(
            id=section_id,
            user_id=section.user_id,
            index=index,
            title=section.title,
            parent_id=section.parent_id,
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
            added_at=added_at,
            tasks=[],
        )
        if section.tasks:
            model.tasks = [TaskModel.from_entity(t, i) for i, t in enumerate(section.tasks)]
            for tm in model.tasks:
                tm.section = model
        return model

    def to_entity(self, tasks: List[Task], subsections: List[Section]) -> Section:
        return Section(
            id=self.id,
            user_id=self.user_id,
            title=self.title,
            parent_id=self.parent_id,
            added_at=self.added_at,
            tasks=tasks,
            subsections=subsections,
            has_tasks=self.has_tasks,
            has_subsections=self.has_subsections,
        )


@dataclass
class UserModel:
    id: UUID
    email: str
    added_at: datetime
    sections: List[SectionModel] = field(default_factory=list)
    tasks: List[TaskModel] = field(default_factory=list)

    def to_entity(self) -> User:
        return User(id=self.id, email=self.email, added_at=self.added_at)


@dataclass
class AccessTokenModel:
    pass


@dataclass
class UserStats:
    user_id: UUID
    email: str
    tasks_total: int
    tasks_archived: int
    tasks_completed: int
    sections_total: int


class AsyncSession:
    def __init__(self) -> None:
        self._closed = False

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def close(self) -> None:
        self._closed = True


class async_sessionmaker:
    def __init__(self, factory):
        self._factory = factory

    def __call__(self) -> AsyncSession:
        return self._factory()


class SQLAlchemyTaskRepository:
    def __init__(self, store: "_InMemoryStore") -> None:
        self._store = store

    def add(self, task: Task, index: NonNegativeInt) -> None:
        _validate_non_negative_int(index, "index")
        if task.id is None:
            task.id = uuid4()
        if task.added_at is None:
            task.added_at = _now_utc_naive()
        self._store.add_task(task, index=index)

    def get(self, task_id: UUID) -> Task:
        _validate_uuid(task_id, "task_id")
        task = self._store.tasks.get(task_id)
        if task is None:
            raise KeyError("Task not found")
        return self._store.clone_task(task)

    def remove(self, task: Task) -> None:
        if task.id is None:
            raise ValueError("Task.id is required to remove")
        self._store.remove_task(task.id)

    def delete_attachment(self, attachment: Attachment) -> None:
        if attachment.id is None:
            raise ValueError("Attachment.id is required to delete")
        self._store.delete_attachment(attachment.id)

    def update_or_create(self, task: Task, index: Optional[NonNegativeInt], must_exist: bool) -> None:
        _validate_optional_non_negative_int(index, "index")
        if task.id is None:
            if must_exist:
                raise KeyError("Task must exist but has no id")
            task.id = uuid4()
        if task.added_at is None:
            task.added_at = _now_utc_naive()
        exists = task.id in self._store.tasks
        if must_exist and not exists:
            raise KeyError("Task not found")
        if exists:
            self._store.update_task(task, index=index)
        else:
            self._store.add_task(task, index=index if index is not None else 0)

    def update_or_create_bulk(self, section_tasks: List[Task]) -> None:
        if not isinstance(section_tasks, list):
            raise TypeError("section_tasks must be list[Task]")
        for i, t in enumerate(section_tasks):
            if not isinstance(t, Task):
                raise TypeError("section_tasks must contain Task")
            self.update_or_create(t, index=i, must_exist=False)

    def get_entities(self, task_models: Sequence[TaskModel]) -> List[Task]:
        return [self.get_entity(tm) for tm in task_models]

    def get_entity(self, task_model: TaskModel) -> Task:
        if not isinstance(task_model, TaskModel):
            raise TypeError("task_model must be TaskModel")
        attachments = [am.to_entity() for am in sorted(task_model.attachments, key=lambda x: x.index)]
        return task_model.to_entity(attachments=attachments)

    def get_archived_tasks(self, user_id: UUID) -> List[Task]:
        _validate_uuid(user_id, "user_id")
        tasks = [t for t in self._store.tasks.values() if t.user_id == user_id and t.is_archived]
        return [self._store.clone_task(t) for t in tasks]

    def get_overdue_tasks(self, user_id: UUID) -> List[Task]:
        _validate_uuid(user_id, "user_id")
        today = date.today()
        tasks = [
            t
            for t in self._store.tasks.values()
            if t.user_id == user_id and not t.is_archived and not t.is_completed and t.due_to is not None and t.due_to < today
        ]
        return [self._store.clone_task(t) for t in tasks]

    def get_tasks_by_due_to(self, not_before: date, not_after: date, user_id: UUID) -> List[Task]:
        if not isinstance(not_before, date) or not isinstance(not_after, date):
            raise TypeError("not_before and not_after must be date")
        _validate_uuid(user_id, "user_id")
        tasks = [
            t
            for t in self._store.tasks.values()
            if t.user_id == user_id and t.due_to is not None and not_before <= t.due_to <= not_after
        ]
        return [self._store.clone_task(t) for t in tasks]

    def search(self, user_id: UUID, query: str) -> List[Task]:
        _validate_uuid(user_id, "user_id")
        if not isinstance(query, str):
            raise TypeError("query must be str")
        q = query.strip().lower()
        if not q:
            return []
        def _hay(t: Task) -> str:
            parts = [t.title, t.description or "", t.content or ""]
            return " ".join(parts).lower()
        tasks = [t for t in self._store.tasks.values() if t.user_id == user_id and q in _hay(t)]
        return [self._store.clone_task(t) for t in tasks]


class SQLAlchemySectionRepository:
    def __init__(self, store: "_InMemoryStore") -> None:
        self._store = store

    def add(self, section: Section, index: NonNegativeInt) -> None:
        _validate_non_negative_int(index, "index")
        if section.id is None:
            section.id = uuid4()
        if section.added_at is None:
            section.added_at = _now_utc_naive()
        self._store.add_section(section, index=index)

    def update(self, section: Section, index: Optional[NonNegativeInt]) -> None:
        _validate_optional_non_negative_int(index, "index")
        if section.id is None:
            raise ValueError("Section.id is required to update")
        self._store.update_section(section, index=index)

    def get(self, section_id: UUID, with_direct_subsections: bool) -> Section:
        _validate_uuid(section_id, "section_id")
        section = self._store.sections.get(section_id)
        if section is None:
            raise KeyError("Section not found")
        sec = self._store.clone_section(section, include_tasks=True)
        if with_direct_subsections:
            subs = self._store.get_direct_subsections(section_id)
            sec.subsections = [self._store.clone_section(s, include_tasks=False) for s in subs]
        else:
            sec.subsections = []
        sec.check_flags()
        return sec

    def count_subsections(self, section_id: UUID) -> int:
        _validate_uuid(section_id, "section_id")
        return len(self._store.get_direct_subsections(section_id))

    def get_all_without_tasks(self, user_id: UUID, leaves_only: bool, as_tree: bool) -> List[Section]:
        _validate_uuid(user_id, "user_id")
        sections = [s for s in self._store.sections.values() if s.user_id == user_id]
        clones = [self._store.clone_section(s, include_tasks=False) for s in sections]
        if leaves_only:
            child_map: Dict[UUID, int] = {}
            for s in clones:
                if s.parent_id is not None:
                    child_map[s.parent_id] = child_map.get(s.parent_id, 0) + 1
            clones = [s for s in clones if child_map.get(s.id or UUID(int=0), 0) == 0]
        if as_tree:
            return self.construct_sections_tree(
                [SectionModel.from_entity(s, index=0) for s in clones], return_flat=False
            )
        return clones

    def construct_sections_tree(self, section_models: List[SectionModel], return_flat: bool) -> List[Section]:
        if not isinstance(section_models, list):
            raise TypeError("section_models must be list[SectionModel]")
        sections = [sm.to_entity(tasks=[], subsections=[]) for sm in section_models]
        by_id: Dict[UUID, Section] = {s.id: s for s in sections if s.id is not None}
        roots: List[Section] = []
        for s in sections:
            if s.parent_id is None:
                roots.append(s)
            else:
                parent = by_id.get(s.parent_id)
                if parent is None:
                    roots.append(s)
                else:
                    parent.subsections.append(s)
        for s in sections:
            s.check_flags()
        if return_flat:
            return sections
        return roots


class SQLAlchemyUserRepository:
    def __init__(self, store: "_InMemoryStore") -> None:
        self._store = store

    def verify_user(self, user_id: UUID) -> None:
        _validate_uuid(user_id, "user_id")
        if user_id not in self._store.users:
            raise KeyError("User not found")

    def get_all_users(self) -> List[UserStats]:
        stats: List[UserStats] = []
        for u in self._store.users.values():
            tasks = [t for t in self._store.tasks.values() if t.user_id == u.id]
            sections = [s for s in self._store.sections.values() if s.user_id == u.id]
            stats.append(
                UserStats(
                    user_id=u.id,
                    email=u.email,
                    tasks_total=len(tasks),
                    tasks_archived=sum(1 for t in tasks if t.is_archived),
                    tasks_completed=sum(1 for t in tasks if t.is_completed),
                    sections_total=len(sections),
                )
            )
        return stats


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


class _InMemoryStore:
    def __init__(self) -> None:
        self.users: Dict[UUID, User] = {}
        self.sections: Dict[UUID, Section] = {}
        self.tasks: Dict[UUID, Task] = {}
        self.attachments: Dict[UUID, Attachment] = {}
        self.section_order: Dict[UUID, List[UUID]] = {}
        self.task_order: Dict[UUID, List[UUID]] = {}

    def clone_attachment(self, a: Attachment) -> Attachment:
        return Attachment(
            id=a.id,
            task_id=a.task_id,
            s3_file_key=a.s3_file_key,
            aes_key_b64=a.aes_key_b64,
            aes_iv_b64=a.aes_iv_b64,
            added_at=a.added_at,
        )

    def clone_task(self, t: Task) -> Task:
        attachments = None
        if t.attachments is not None:
            attachments = [self.clone_attachment(a) for a in t.attachments]
        return Task(
            id=t.id,
            user_id=t.user_id,
            section_id=t.section_id,
            title=t.title,
            description=t.description,
            content=t.content,
            due_to=t.due_to,
            is_archived=t.is_archived,
            is_completed=t.is_completed,
            recurrence=t.recurrence,
            attachments=attachments,
            added_at=t.added_at,
        )

    def clone_section(self, s: Section, include_tasks: bool) -> Section:
        tasks: List[Task] = []
        if include_tasks:
            ordered = self.task_order.get(s.id, [])
            for tid in ordered:
                t = self.tasks.get(tid)
                if t is not None:
                    tasks.append(self.clone_task(t))
        return Section(
            id=s.id,
            user_id=s.user_id,
            title=s.title,
            parent_id=s.parent_id,
            added_at=s.added_at,
            subsections=[],
            tasks=tasks,
            has_subsections=s.has_subsections,
            has_tasks=s.has_tasks,
        )

    def add_section(self, section: Section, index: int) -> None:
        if section.id is None:
            raise ValueError("Section.id required")
        self.sections[section.id] = self.clone_section(section, include_tasks=False)
        parent_key = section.parent_id or UUID(int=0)
        order = self.section_order.setdefault(parent_key, [])
        if section.id in order:
            order.remove(section.id)
        if index >= len(order):
            order.append(section.id)
        else:
            order.insert(index, section.id)

    def update_section(self, section: Section, index: Optional[int]) -> None:
        if section.id is None:
            raise ValueError("Section.id required")
        if section.id not in self.sections:
            raise KeyError("Section not found")
        self.sections[section.id] = self.clone_section(section, include_tasks=False)
        if index is not None:
            parent_key = section.parent_id or UUID(int=0)
            order = self.section_order.setdefault(parent_key, [])
            if section.id in order:
                order.remove(section.id)
            if index >= len(order):
                order.append(section.id)
            else:
                order.insert(index, section.id)

    def get_direct_subsections(self, parent_id: UUID) -> List[Section]:
        order = self.section_order.get(parent_id, [])
        subs: List[Section] = []
        for sid in order:
            s = self.sections.get(sid)
            if s is not None and s.parent_id == parent_id:
                subs.append(s)
        return subs

    def add_task(self, task: Task, index: int) -> None:
        if task.id is None:
            raise ValueError("Task.id required")
        self.tasks[task.id] = self.clone_task(task)
        order = self.task_order.setdefault(task.section_id, [])
        if task.id in order:
            order.remove(task.id)
        if index >= len(order):
            order.append(task.id)
        else:
            order.insert(index, task.id)
        if task.attachments:
            for a in task.attachments:
                if a.id is None:
                    a.id = uuid4()
                if a.added_at is None:
                    a.added_at = _now_utc_naive()
                self.attachments[a.id] = self.clone_attachment(a)

    def update_task(self, task: Task, index: Optional[int]) -> None:
        if task.id is None:
            raise ValueError("Task.id required")
        if task.id not in self.tasks:
            raise KeyError("Task not found")
        old = self.tasks[task.id]
        if old.section_id != task.section_id:
            old_order = self.task_order.get(old.section_id, [])
            if task.id in old_order:
                old_order.remove(task.id)
        self.tasks[task.id] = self.clone_task(task)
        if index is not None:
            order = self.task_order.setdefault(task.section_id, [])
            if task.id in order:
                order.remove(task.id)
            if index >= len(order):
                order.append(task.id)
            else:
                order.insert(index, task.id)
        if task.attachments is not None:
            for a in list(self.attachments.values()):
                if a.task_id == task.id:
                    self.attachments.pop(a.id, None)
            for a in task.attachments:
                if a.id is None:
                    a.id = uuid4()
                if a.added_at is None:
                    a.added_at = _now_utc_naive()
                self.attachments[a.id] = self.clone_attachment(a)

    def remove_task(self, task_id: UUID) -> None:
        t = self.tasks.pop(task_id, None)
        if t is None:
            raise KeyError("Task not found")
        order = self.task_order.get(t.section_id, [])
        if task_id in order:
            order.remove(task_id)
        for aid, a in list(self.attachments.items()):
            if a.task_id == task_id:
                self.attachments.pop(aid, None)

    def delete_attachment(self, attachment_id: UUID) -> None:
        if attachment_id not in self.attachments:
            raise KeyError("Attachment not found")
        self.attachments.pop(attachment_id, None)
        for t in self.tasks.values():
            if t.attachments:
                t.attachments = [a for a in t.attachments if a.id != attachment_id]


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session_factory: Optional[async_sessionmaker] = None) -> None:
        self._store = _InMemoryStore()
        self.session_factory = session_factory or async_sessionmaker(lambda: AsyncSession())
        self.session: AsyncSession = self.session_factory()
        self.section_repo = SQLAlchemySectionRepository(self._store)
        self.task_repo = SQLAlchemyTaskRepository(self._store)
        self.user_repo = SQLAlchemyUserRepository(self._store)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()