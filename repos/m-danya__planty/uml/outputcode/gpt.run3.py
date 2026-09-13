from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Sequence, TypeVar, Union
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


T = TypeVar("T")


class Mapped(Generic := TypeVar("Generic")):  # minimal placeholder for SQLAlchemy typing
    pass


GUID = UUID


class Entity:
    model_config: Dict[str, Any] = {"arbitrary_types_allowed": True}


@dataclass
class RecurrenceInfo(Entity):
    flexible_mode: bool
    period: int
    type: Literal["daily", "weekly", "monthly", "yearly"]

    def __post_init__(self) -> None:
        if not isinstance(self.flexible_mode, bool):
            raise TypeError("flexible_mode must be bool")
        if not isinstance(self.period, int):
            raise TypeError("period must be int")
        if self.period <= 0:
            raise ValueError("period must be positive")
        if self.type not in ("daily", "weekly", "monthly", "yearly"):
            raise ValueError("type must be one of: daily, weekly, monthly, yearly")


@dataclass
class User(Entity):
    email: str
    id: Optional[UUID] = None
    added_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not isinstance(self.email, str) or not self.email.strip():
            raise ValueError("email must be a non-empty string")


@dataclass
class Attachment(Entity):
    task_id: UUID
    s3_file_key: str
    aes_key_b64: str
    aes_iv_b64: str
    id: Optional[UUID] = None
    added_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, UUID):
            raise TypeError("task_id must be UUID")
        for name, val in (
            ("s3_file_key", self.s3_file_key),
            ("aes_key_b64", self.aes_key_b64),
            ("aes_iv_b64", self.aes_iv_b64),
        ):
            if not isinstance(val, str) or not val:
                raise ValueError(f"{name} must be a non-empty string")


@dataclass
class Task(Entity):
    section_id: UUID
    title: str
    user_id: UUID
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
        if not isinstance(self.section_id, UUID):
            raise TypeError("section_id must be UUID")
        if not isinstance(self.user_id, UUID):
            raise TypeError("user_id must be UUID")
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("title must be a non-empty string")
        if self.description is not None and not isinstance(self.description, str):
            raise TypeError("description must be str or None")
        if self.content is not None and not isinstance(self.content, str):
            raise TypeError("content must be str or None")
        if self.due_to is not None and not isinstance(self.due_to, date):
            raise TypeError("due_to must be date or None")
        if not isinstance(self.is_archived, bool):
            raise TypeError("is_archived must be bool")
        if not isinstance(self.is_completed, bool):
            raise TypeError("is_completed must be bool")
        if self.recurrence is not None and not isinstance(self.recurrence, RecurrenceInfo):
            raise TypeError("recurrence must be RecurrenceInfo or None")
        if self.attachments is not None:
            if not isinstance(self.attachments, list):
                raise TypeError("attachments must be list or None")
            for a in self.attachments:
                if not isinstance(a, Attachment):
                    raise TypeError("attachments must contain Attachment instances")
        self.check_recurrence_due_date(None)

    def check_recurrence_due_date(self, values: Any) -> Any:
        if self.recurrence is not None and self.due_to is None:
            raise ValueError("due_to must be set when recurrence is set")
        return values

    def add_attachment(self, attachment: Attachment) -> None:
        if not isinstance(attachment, Attachment):
            raise TypeError("attachment must be Attachment")
        if attachment.task_id != (self.id if self.id is not None else attachment.task_id):
            if self.id is not None and attachment.task_id != self.id:
                raise ValueError("attachment.task_id must match task.id")
        if self.attachments is None:
            self.attachments = []
        self.attachments.append(attachment)

    def remove_attachment(self, attachment: Attachment) -> None:
        if self.attachments is None:
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
    title: str
    user_id: UUID
    id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    added_at: Optional[datetime] = None
    has_subsections: bool = False
    has_tasks: bool = False
    subsections: List["Section"] = None  # type: ignore[assignment]
    tasks: List[Task] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("title must be a non-empty string")
        if not isinstance(self.user_id, UUID):
            raise TypeError("user_id must be UUID")
        if self.parent_id is not None and not isinstance(self.parent_id, UUID):
            raise TypeError("parent_id must be UUID or None")
        if not isinstance(self.has_subsections, bool):
            raise TypeError("has_subsections must be bool")
        if not isinstance(self.has_tasks, bool):
            raise TypeError("has_tasks must be bool")
        if self.subsections is None:
            self.subsections = []
        if self.tasks is None:
            self.tasks = []
        self.check_flags()

    @staticmethod
    def create_root_section(user_id: UUID) -> "Section":
        if not isinstance(user_id, UUID):
            raise TypeError("user_id must be UUID")
        return Section(title="Root", user_id=user_id, parent_id=None)

    def is_root(self) -> bool:
        return self.parent_id is None

    def check_flags(self) -> "Section":
        self.has_subsections = len(self.subsections) > 0
        self.has_tasks = len(self.tasks) > 0
        return self

    def insert_subsection(self, subsection: "Section", index: Optional[NonNegativeInt]) -> None:
        if not isinstance(subsection, Section):
            raise TypeError("subsection must be Section")
        _validate_optional_non_negative_int(index, "index")
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
        if not isinstance(subsection, Section):
            raise TypeError("subsection must be Section")
        try:
            self.subsections.remove(subsection)
        except ValueError as e:
            raise ValueError("subsection not found") from e
        self.check_flags()
        return subsection

    def insert_task(self, task: Task, index: Optional[NonNegativeInt]) -> None:
        if not isinstance(task, Task):
            raise TypeError("task must be Task")
        _validate_optional_non_negative_int(index, "index")
        if task.user_id != self.user_id:
            raise ValueError("task.user_id must match section.user_id")
        if self.id is not None:
            task.section_id = self.id
        if index is None or index >= len(self.tasks):
            self.tasks.append(task)
        else:
            self.tasks.insert(index, task)
        self.check_flags()

    def remove_task(self, task: Task) -> Task:
        if not isinstance(task, Task):
            raise TypeError("task must be Task")
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
            raise ValueError("user_id mismatch")
        section_from.remove_task(task_to_move)
        section_to.insert_task(task_to_move, index)

    @staticmethod
    def move_section(section: "Section", section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if not isinstance(section, Section):
            raise TypeError("section must be Section")
        if not isinstance(section_from, Section) or not isinstance(section_to, Section):
            raise TypeError("section_from and section_to must be Section")
        _validate_non_negative_int(index, "index")
        if section_from.user_id != section_to.user_id or section.user_id != section_to.user_id:
            raise ValueError("user_id mismatch")
        section_from.remove_subsection(section)
        section_to.insert_subsection(section, index)


class AccessTokenModel:
    def __init__(self) -> None:
        pass


class UserModel:
    added_at: Mapped[datetime]
    sections: Any
    tasks: Any

    def __init__(self, id: UUID, email: str, added_at: Optional[datetime] = None) -> None:
        self.id: UUID = id
        self.email: str = email
        self.added_at_value: datetime = added_at or datetime.utcnow()

    def to_entity(self) -> User:
        return User(id=self.id, email=self.email, added_at=self.added_at_value)


class SectionModel:
    added_at: Mapped[datetime]
    has_subsections: Mapped[bool]
    has_tasks: Mapped[bool]
    id: Mapped[UUID]
    index: Mapped[int]
    parent_id: Mapped[Optional[GUID]]
    tasks: Mapped[List["TaskModel"]]
    title: Mapped[str]
    user: Any
    user_id: Mapped[UUID]

    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        title: str,
        index: int,
        parent_id: Optional[UUID] = None,
        added_at: Optional[datetime] = None,
        has_subsections: bool = False,
        has_tasks: bool = False,
    ) -> None:
        self.id_value = id
        self.user_id_value = user_id
        self.title_value = title
        self.index_value = index
        self.parent_id_value = parent_id
        self.added_at_value = added_at or datetime.utcnow()
        self.has_subsections_value = has_subsections
        self.has_tasks_value = has_tasks
        self.tasks_value: List[TaskModel] = []

    @staticmethod
    def from_entity(section: Section, index: NonNegativeInt) -> "SectionModel":
        _validate_non_negative_int(index, "index")
        sid = section.id or uuid4()
        added_at = section.added_at or datetime.utcnow()
        model = SectionModel(
            id=sid,
            user_id=section.user_id,
            title=section.title,
            index=index,
            parent_id=section.parent_id,
            added_at=added_at,
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
        )
        return model

    def to_entity(self, tasks: List[Task], subsections: List[Section]) -> Section:
        sec = Section(
            id=self.id_value,
            user_id=self.user_id_value,
            title=self.title_value,
            parent_id=self.parent_id_value,
            added_at=self.added_at_value,
            has_subsections=self.has_subsections_value,
            has_tasks=self.has_tasks_value,
            subsections=list(subsections),
            tasks=list(tasks),
        )
        sec.check_flags()
        return sec


class TaskModel:
    added_at: Mapped[datetime]
    attachments: Any
    description: Mapped[Optional[str]]
    due_to: Mapped[Optional[date]]
    flexible_recurrence_mode: Mapped[Optional[bool]]
    id: Mapped[UUID]
    index: Mapped[int]
    is_archived: Mapped[bool]
    is_completed: Mapped[bool]
    recurrence_period: Mapped[Optional[int]]
    recurrence_type: Mapped[Optional[str]]
    section: Any
    section_id: Mapped[UUID]
    title: Mapped[str]
    user: Any
    user_id: Mapped[UUID]

    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        section_id: UUID,
        title: str,
        index: int,
        added_at: Optional[datetime] = None,
        description: Optional[str] = None,
        due_to: Optional[date] = None,
        is_archived: bool = False,
        is_completed: bool = False,
        recurrence_type: Optional[str] = None,
        recurrence_period: Optional[int] = None,
        flexible_recurrence_mode: Optional[bool] = None,
    ) -> None:
        self.id_value = id
        self.user_id_value = user_id
        self.section_id_value = section_id
        self.title_value = title
        self.index_value = index
        self.added_at_value = added_at or datetime.utcnow()
        self.description_value = description
        self.due_to_value = due_to
        self.is_archived_value = is_archived
        self.is_completed_value = is_completed
        self.recurrence_type_value = recurrence_type
        self.recurrence_period_value = recurrence_period
        self.flexible_recurrence_mode_value = flexible_recurrence_mode
        self.attachments_value: List[AttachmentModel] = []

    @staticmethod
    def from_entity(task: Task, index: NonNegativeInt) -> "TaskModel":
        _validate_non_negative_int(index, "index")
        tid = task.id or uuid4()
        added_at = task.added_at or datetime.utcnow()
        recurrence_type: Optional[str] = None
        recurrence_period: Optional[int] = None
        flexible_mode: Optional[bool] = None
        if task.recurrence is not None:
            recurrence_type = str(task.recurrence.type)
            recurrence_period = int(task.recurrence.period)
            flexible_mode = bool(task.recurrence.flexible_mode)
        model = TaskModel(
            id=tid,
            user_id=task.user_id,
            section_id=task.section_id,
            title=task.title,
            index=index,
            added_at=added_at,
            description=task.description,
            due_to=task.due_to,
            is_archived=task.is_archived,
            is_completed=task.is_completed,
            recurrence_type=recurrence_type,
            recurrence_period=recurrence_period,
            flexible_recurrence_mode=flexible_mode,
        )
        return model

    def to_entity(self, attachments: List[Attachment]) -> Task:
        recurrence: Optional[RecurrenceInfo] = None
        if self.recurrence_type_value is not None or self.recurrence_period_value is not None or self.flexible_recurrence_mode_value is not None:
            if self.recurrence_type_value is None or self.recurrence_period_value is None or self.flexible_recurrence_mode_value is None:
                raise ValueError("Incomplete recurrence fields in TaskModel")
            recurrence = RecurrenceInfo(
                type=self.recurrence_type_value,  # type: ignore[arg-type]
                period=self.recurrence_period_value,
                flexible_mode=self.flexible_recurrence_mode_value,
            )
        task = Task(
            id=self.id_value,
            user_id=self.user_id_value,
            section_id=self.section_id_value,
            title=self.title_value,
            added_at=self.added_at_value,
            description=self.description_value,
            due_to=self.due_to_value,
            is_archived=self.is_archived_value,
            is_completed=self.is_completed_value,
            recurrence=recurrence,
            attachments=list(attachments),
        )
        return task


class AttachmentModel:
    added_at: Mapped[datetime]
    aes_iv_b64: Mapped[str]
    aes_key_b64: Mapped[str]
    id: Mapped[UUID]
    index: Mapped[int]
    s3_file_key: Mapped[str]
    task: Any
    task_id: Mapped[UUID]

    def __init__(
        self,
        id: UUID,
        task_id: UUID,
        s3_file_key: str,
        aes_key_b64: str,
        aes_iv_b64: str,
        index: int,
        added_at: Optional[datetime] = None,
    ) -> None:
        self.id_value = id
        self.task_id_value = task_id
        self.s3_file_key_value = s3_file_key
        self.aes_key_b64_value = aes_key_b64
        self.aes_iv_b64_value = aes_iv_b64
        self.index_value = index
        self.added_at_value = added_at or datetime.utcnow()

    @staticmethod
    def from_entity(attachment: Attachment, index: NonNegativeInt) -> "AttachmentModel":
        _validate_non_negative_int(index, "index")
        aid = attachment.id or uuid4()
        added_at = attachment.added_at or datetime.utcnow()
        return AttachmentModel(
            id=aid,
            task_id=attachment.task_id,
            s3_file_key=attachment.s3_file_key,
            aes_key_b64=attachment.aes_key_b64,
            aes_iv_b64=attachment.aes_iv_b64,
            index=index,
            added_at=added_at,
        )

    def to_entity(self) -> Attachment:
        return Attachment(
            id=self.id_value,
            task_id=self.task_id_value,
            s3_file_key=self.s3_file_key_value,
            aes_key_b64=self.aes_key_b64_value,
            aes_iv_b64=self.aes_iv_b64_value,
            added_at=self.added_at_value,
        )


@dataclass
class UserStats(Entity):
    user_id: UUID
    email: str
    sections_count: int
    tasks_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, UUID):
            raise TypeError("user_id must be UUID")
        if not isinstance(self.email, str) or not self.email.strip():
            raise ValueError("email must be non-empty")
        if not isinstance(self.sections_count, int) or self.sections_count < 0:
            raise ValueError("sections_count must be non-negative int")
        if not isinstance(self.tasks_count, int) or self.tasks_count < 0:
            raise ValueError("tasks_count must be non-negative int")


class AsyncSession:
    def __init__(self) -> None:
        self._pending: List[Any] = []

    async def commit(self) -> None:
        self._pending.clear()

    async def rollback(self) -> None:
        self._pending.clear()


class async_sessionmaker:
    def __init__(self) -> None:
        pass

    def __call__(self) -> AsyncSession:
        return AsyncSession()


class SQLAlchemyTaskRepository:
    def __init__(self) -> None:
        self._tasks: Dict[UUID, Task] = {}
        self._attachments: Dict[UUID, Attachment] = {}
        self._section_task_order: Dict[UUID, List[UUID]] = {}

    def add(self, task: Task, index: NonNegativeInt) -> None:
        _validate_non_negative_int(index, "index")
        if task.id is None:
            task.id = uuid4()
        if task.added_at is None:
            task.added_at = datetime.utcnow()
        if task.attachments:
            for a in task.attachments:
                if a.id is None:
                    a.id = uuid4()
                if a.added_at is None:
                    a.added_at = datetime.utcnow()
                self._attachments[a.id] = a
        self._tasks[task.id] = task
        order = self._section_task_order.setdefault(task.section_id, [])
        if task.id in order:
            order.remove(task.id)
        if index >= len(order):
            order.append(task.id)
        else:
            order.insert(index, task.id)

    def get(self, task_id: UUID) -> Task:
        if task_id not in self._tasks:
            raise KeyError("Task not found")
        return self._tasks[task_id]

    def remove(self, task: Task) -> None:
        if task.id is None or task.id not in self._tasks:
            raise KeyError("Task not found")
        del self._tasks[task.id]
        order = self._section_task_order.get(task.section_id)
        if order and task.id in order:
            order.remove(task.id)
        if task.attachments:
            for a in list(task.attachments):
                if a.id is not None and a.id in self._attachments:
                    del self._attachments[a.id]

    def delete_attachment(self, attachment: Attachment) -> None:
        if attachment.id is None or attachment.id not in self._attachments:
            raise KeyError("Attachment not found")
        del self._attachments[attachment.id]
        if attachment.task_id in self._tasks:
            t = self._tasks[attachment.task_id]
            if t.attachments is not None:
                t.attachments = [a for a in t.attachments if a.id != attachment.id]

    def update_or_create(self, task: Task, index: Optional[NonNegativeInt], must_exist: bool) -> None:
        _validate_optional_non_negative_int(index, "index")
        if task.id is None:
            if must_exist:
                raise KeyError("Task must exist")
            task.id = uuid4()
        exists = task.id in self._tasks
        if must_exist and not exists:
            raise KeyError("Task not found")
        if task.added_at is None:
            task.added_at = datetime.utcnow()
        self._tasks[task.id] = task
        if index is not None:
            order = self._section_task_order.setdefault(task.section_id, [])
            if task.id in order:
                order.remove(task.id)
            if index >= len(order):
                order.append(task.id)
            else:
                order.insert(index, task.id)

    def update_or_create_bulk(self, section_tasks: List[Task]) -> None:
        for i, t in enumerate(section_tasks):
            self.update_or_create(t, index=i, must_exist=False)

    def get_archived_tasks(self, user_id: UUID) -> List[Task]:
        return [t for t in self._tasks.values() if t.user_id == user_id and t.is_archived]

    def get_overdue_tasks(self, user_id: UUID) -> List[Task]:
        today = date.today()
        return [
            t
            for t in self._tasks.values()
            if t.user_id == user_id and not t.is_completed and t.due_to is not None and t.due_to < today
        ]

    def get_tasks_by_due_to(self, not_before: date, not_after: date, user_id: UUID) -> List[Task]:
        if not isinstance(not_before, date) or not isinstance(not_after, date):
            raise TypeError("not_before and not_after must be date")
        if not_before > not_after:
            raise ValueError("not_before must be <= not_after")
        return [
            t
            for t in self._tasks.values()
            if t.user_id == user_id and t.due_to is not None and not_before <= t.due_to <= not_after
        ]

    def search(self, user_id: UUID, query: str) -> List[Task]:
        if not isinstance(query, str):
            raise TypeError("query must be str")
        q = query.strip().lower()
        if not q:
            return []
        res: List[Task] = []
        for t in self._tasks.values():
            if t.user_id != user_id:
                continue
            hay = " ".join(
                [
                    t.title or "",
                    t.description or "",
                    t.content or "",
                ]
            ).lower()
            if q in hay:
                res.append(t)
        return res

    def get_entity(self, task_model: TaskModel) -> Task:
        attachments: List[Attachment] = []
        for am in getattr(task_model, "attachments_value", []):
            if isinstance(am, AttachmentModel):
                attachments.append(am.to_entity())
        return task_model.to_entity(attachments=attachments)

    def get_entities(self, task_models: Sequence[TaskModel]) -> List[Task]:
        return [self.get_entity(tm) for tm in task_models]


class SQLAlchemySectionRepository:
    def __init__(self) -> None:
        self._sections: Dict[UUID, Section] = {}
        self._user_section_order: Dict[UUID, List[UUID]] = {}
        self._children_order: Dict[UUID, List[UUID]] = {}

    def add(self, section: Section, index: NonNegativeInt) -> None:
        _validate_non_negative_int(index, "index")
        if section.id is None:
            section.id = uuid4()
        if section.added_at is None:
            section.added_at = datetime.utcnow()
        self._sections[section.id] = section
        if section.parent_id is None:
            order = self._user_section_order.setdefault(section.user_id, [])
        else:
            order = self._children_order.setdefault(section.parent_id, [])
        if section.id in order:
            order.remove(section.id)
        if index >= len(order):
            order.append(section.id)
        else:
            order.insert(index, section.id)

    def update(self, section: Section, index: Optional[NonNegativeInt]) -> None:
        _validate_optional_non_negative_int(index, "index")
        if section.id is None or section.id not in self._sections:
            raise KeyError("Section not found")
        self._sections[section.id] = section
        if index is not None:
            if section.parent_id is None:
                order = self._user_section_order.setdefault(section.user_id, [])
            else:
                order = self._children_order.setdefault(section.parent_id, [])
            if section.id in order:
                order.remove(section.id)
            if index >= len(order):
                order.append(section.id)
            else:
                order.insert(index, section.id)

    def get(self, section_id: UUID, with_direct_subsections: bool) -> Section:
        if section_id not in self._sections:
            raise KeyError("Section not found")
        sec = self._sections[section_id]
        if not with_direct_subsections:
            return Section(
                id=sec.id,
                user_id=sec.user_id,
                title=sec.title,
                parent_id=sec.parent_id,
                added_at=sec.added_at,
                has_subsections=sec.has_subsections,
                has_tasks=sec.has_tasks,
                subsections=[],
                tasks=list(sec.tasks),
            ).check_flags()
        child_ids = self._children_order.get(section_id, [])
        subsections = [self._sections[cid] for cid in child_ids if cid in self._sections]
        return Section(
            id=sec.id,
            user_id=sec.user_id,
            title=sec.title,
            parent_id=sec.parent_id,
            added_at=sec.added_at,
            has_subsections=sec.has_subsections,
            has_tasks=sec.has_tasks,
            subsections=list(subsections),
            tasks=list(sec.tasks),
        ).check_flags()

    def count_subsections(self, section_id: UUID) -> int:
        return len(self._children_order.get(section_id, []))

    def construct_sections_tree(self, section_models: List[SectionModel], return_flat: bool) -> List[Section]:
        sections: List[Section] = []
        for sm in section_models:
            if not isinstance(sm, SectionModel):
                raise TypeError("section_models must contain SectionModel")
            sections.append(
                Section(
                    id=sm.id_value,
                    user_id=sm.user_id_value,
                    title=sm.title_value,
                    parent_id=sm.parent_id_value,
                    added_at=sm.added_at_value,
                    has_subsections=sm.has_subsections_value,
                    has_tasks=sm.has_tasks_value,
                    subsections=[],
                    tasks=[],
                )
            )
        if return_flat:
            for s in sections:
                s.check_flags()
            return sections

        by_id: Dict[UUID, Section] = {s.id: s for s in sections if s.id is not None}
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
            secs = [s for s in secs if len(self._children_order.get(s.id or UUID(int=0), [])) == 0]
        if not as_tree:
            return [Section(id=s.id, user_id=s.user_id, title=s.title, parent_id=s.parent_id, added_at=s.added_at, subsections=[], tasks=[]).check_flags() for s in secs]
        models = [SectionModel.from_entity(s, index=0) for s in secs]
        return self.construct_sections_tree(models, return_flat=False)


class SQLAlchemyUserRepository:
    def __init__(self) -> None:
        self._users: Dict[UUID, User] = {}
        self._verified: set[UUID] = set()
        self._sections_repo: Optional[SQLAlchemySectionRepository] = None
        self._tasks_repo: Optional[SQLAlchemyTaskRepository] = None

    def bind_repos(self, sections_repo: SQLAlchemySectionRepository, tasks_repo: SQLAlchemyTaskRepository) -> None:
        self._sections_repo = sections_repo
        self._tasks_repo = tasks_repo

    def verify_user(self, user_id: UUID) -> None:
        if user_id not in self._users:
            raise KeyError("User not found")
        self._verified.add(user_id)

    def get_all_users(self) -> List[UserStats]:
        stats: List[UserStats] = []
        for u in self._users.values():
            sections_count = 0
            tasks_count = 0
            if self._sections_repo is not None:
                sections_count = len([s for s in self._sections_repo._sections.values() if s.user_id == u.id])
            if self._tasks_repo is not None:
                tasks_count = len([t for t in self._tasks_repo._tasks.values() if t.user_id == u.id])
            stats.append(UserStats(user_id=u.id or UUID(int=0), email=u.email, sections_count=sections_count, tasks_count=tasks_count))
        return stats

    def _add_user(self, user: User) -> None:
        if user.id is None:
            user.id = uuid4()
        if user.added_at is None:
            user.added_at = datetime.utcnow()
        self._users[user.id] = user


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
        self.section_repo = SQLAlchemySectionRepository()
        self.task_repo = SQLAlchemyTaskRepository()
        self.user_repo = SQLAlchemyUserRepository()
        self.user_repo.bind_repos(self.section_repo, self.task_repo)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()