from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, ClassVar, Dict, Iterable, List, Literal, Optional, Sequence, Tuple, TypeVar
from uuid import UUID, uuid4
from abc import ABC, abstractmethod


NonNegativeInt = int


def _ensure_non_negative_int(value: Optional[int], name: str) -> Optional[int]:
    if value is None:
        return None
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative int")
    return value


def _ensure_uuid(value: Optional[UUID], name: str) -> Optional[UUID]:
    if value is None:
        return None
    if not isinstance(value, UUID):
        raise ValueError(f"{name} must be a UUID")
    return value


def _ensure_required_uuid(value: UUID, name: str) -> UUID:
    if not isinstance(value, UUID):
        raise ValueError(f"{name} must be a UUID")
    return value


def _ensure_str(value: str, name: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{name} must be a non-empty str")
    return value


def _ensure_optional_str(value: Optional[str], name: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a str or None")
    return value


def _ensure_optional_date(value: Optional[date], name: str) -> Optional[date]:
    if value is None:
        return None
    if not isinstance(value, date):
        raise ValueError(f"{name} must be a date or None")
    return value


def _ensure_optional_datetime(value: Optional[datetime], name: str) -> Optional[datetime]:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise ValueError(f"{name} must be a datetime or None")
    return value


@dataclass
class Entity:
    model_config: ClassVar[Dict[str, Any]] = {}


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
        self.added_at = _ensure_optional_datetime(self.added_at, "added_at")
        self.aes_iv_b64 = _ensure_str(self.aes_iv_b64, "aes_iv_b64")
        self.aes_key_b64 = _ensure_str(self.aes_key_b64, "aes_key_b64")
        self.id = _ensure_uuid(self.id, "id")
        self.s3_file_key = _ensure_str(self.s3_file_key, "s3_file_key")
        self.task_id = _ensure_required_uuid(self.task_id, "task_id")


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
        self.added_at = _ensure_optional_datetime(self.added_at, "added_at")
        self.content = _ensure_optional_str(self.content, "content")
        self.description = _ensure_optional_str(self.description, "description")
        self.due_to = _ensure_optional_date(self.due_to, "due_to")
        self.id = _ensure_uuid(self.id, "id")
        if not isinstance(self.is_archived, bool):
            raise ValueError("is_archived must be bool")
        if not isinstance(self.is_completed, bool):
            raise ValueError("is_completed must be bool")
        if self.recurrence is not None and not isinstance(self.recurrence, RecurrenceInfo):
            raise ValueError("recurrence must be RecurrenceInfo or None")
        self.section_id = _ensure_required_uuid(self.section_id, "section_id")
        self.title = _ensure_str(self.title, "title")
        self.user_id = _ensure_required_uuid(self.user_id, "user_id")
        if self.attachments is not None:
            if not isinstance(self.attachments, list) or any(not isinstance(a, Attachment) for a in self.attachments):
                raise ValueError("attachments must be a list[Attachment] or None")
            for a in self.attachments:
                if a.task_id != self.id and self.id is not None:
                    raise ValueError("attachment.task_id must match task.id")
        self.check_recurrence_due_date(None)

    def check_recurrence_due_date(self, values: Any) -> Any:
        if self.recurrence is None:
            return values
        if self.due_to is None:
            raise ValueError("due_to must be set when recurrence is set")
        return values

    def add_attachment(self, attachment: Attachment) -> None:
        if not isinstance(attachment, Attachment):
            raise ValueError("attachment must be Attachment")
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
        self.added_at = _ensure_optional_datetime(self.added_at, "added_at")
        if not isinstance(self.has_subsections, bool):
            raise ValueError("has_subsections must be bool")
        if not isinstance(self.has_tasks, bool):
            raise ValueError("has_tasks must be bool")
        self.id = _ensure_uuid(self.id, "id")
        self.parent_id = _ensure_uuid(self.parent_id, "parent_id")
        if not isinstance(self.subsections, list) or any(not isinstance(s, Section) for s in self.subsections):
            raise ValueError("subsections must be list[Section]")
        if not isinstance(self.tasks, list) or any(not isinstance(t, Task) for t in self.tasks):
            raise ValueError("tasks must be list[Task]")
        self.title = _ensure_str(self.title, "title")
        self.user_id = _ensure_required_uuid(self.user_id, "user_id")
        self.check_flags()

    def check_flags(self) -> "Section":
        self.has_subsections = len(self.subsections) > 0
        self.has_tasks = len(self.tasks) > 0
        return self

    @classmethod
    def create_root_section(cls, user_id: UUID) -> "Section":
        _ensure_required_uuid(user_id, "user_id")
        return cls(
            added_at=datetime.utcnow(),
            has_subsections=False,
            has_tasks=False,
            id=uuid4(),
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
        index = _ensure_non_negative_int(index, "index")
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
            raise ValueError("task must be Task")
        index = _ensure_non_negative_int(index, "index")
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
        self.tasks = [t for t in self.tasks if not t.is_archived] + [t for t in self.tasks if t.is_archived]
        self.check_flags()

    @staticmethod
    def move_task(task_to_move: Task, section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if not isinstance(task_to_move, Task):
            raise ValueError("task_to_move must be Task")
        if not isinstance(section_from, Section) or not isinstance(section_to, Section):
            raise ValueError("section_from and section_to must be Section")
        index = _ensure_non_negative_int(index, "index")
        removed = section_from.remove_task(task_to_move)
        section_to.insert_task(removed, index)

    @staticmethod
    def move_section(section: "Section", section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if not isinstance(section, Section):
            raise ValueError("section must be Section")
        if not isinstance(section_from, Section) or not isinstance(section_to, Section):
            raise ValueError("section_from and section_to must be Section")
        index = _ensure_non_negative_int(index, "index")
        removed = section_from.remove_subsection(section)
        section_to.insert_subsection(removed, index)


@dataclass
class User(Entity):
    added_at: Optional[datetime]
    email: str
    id: Optional[UUID]

    def __post_init__(self) -> None:
        self.added_at = _ensure_optional_datetime(self.added_at, "added_at")
        self.email = _ensure_str(self.email, "email")
        self.id = _ensure_uuid(self.id, "id")


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


class Mapped(Generic := T):  # type: ignore[misc]
    pass


class GUID(UUID):
    pass


@dataclass
class AccessTokenModel:
    pass


@dataclass
class AttachmentModel:
    added_at: datetime
    aes_iv_b64: str
    aes_key_b64: str
    id: UUID
    index: int
    s3_file_key: str
    task: Optional["TaskModel"]
    task_id: UUID

    @staticmethod
    def from_entity(attachment: Attachment, index: NonNegativeInt) -> "AttachmentModel":
        _ensure_non_negative_int(index, "index")
        if attachment.id is None:
            attachment_id = uuid4()
        else:
            attachment_id = attachment.id
        added_at = attachment.added_at or datetime.utcnow()
        return AttachmentModel(
            added_at=added_at,
            aes_iv_b64=attachment.aes_iv_b64,
            aes_key_b64=attachment.aes_key_b64,
            id=attachment_id,
            index=index,
            s3_file_key=attachment.s3_file_key,
            task=None,
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


@dataclass
class TaskModel:
    added_at: datetime
    attachments: List[AttachmentModel]
    description: Optional[str]
    due_to: Optional[date]
    flexible_recurrence_mode: Optional[bool]
    id: UUID
    index: int
    is_archived: bool
    is_completed: bool
    recurrence_period: Optional[int]
    recurrence_type: Optional[str]
    section: Optional["SectionModel"]
    section_id: UUID
    title: str
    user: Optional["UserModel"]
    user_id: UUID

    @staticmethod
    def from_entity(task: Task, index: NonNegativeInt) -> "TaskModel":
        _ensure_non_negative_int(index, "index")
        task_id = task.id or uuid4()
        added_at = task.added_at or datetime.utcnow()

        recurrence_type: Optional[str] = None
        recurrence_period: Optional[int] = None
        flexible_mode: Optional[bool] = None
        if task.recurrence is not None:
            recurrence_type = str(task.recurrence.type)
            recurrence_period = int(task.recurrence.period)
            flexible_mode = bool(task.recurrence.flexible_mode)

        attachments_models: List[AttachmentModel] = []
        if task.attachments:
            for i, a in enumerate(task.attachments):
                if a.task_id != task_id:
                    a = Attachment(
                        added_at=a.added_at,
                        aes_iv_b64=a.aes_iv_b64,
                        aes_key_b64=a.aes_key_b64,
                        id=a.id,
                        s3_file_key=a.s3_file_key,
                        task_id=task_id,
                    )
                attachments_models.append(AttachmentModel.from_entity(a, i))

        return TaskModel(
            added_at=added_at,
            attachments=attachments_models,
            description=task.description,
            due_to=task.due_to,
            flexible_recurrence_mode=flexible_mode,
            id=task_id,
            index=index,
            is_archived=task.is_archived,
            is_completed=task.is_completed,
            recurrence_period=recurrence_period,
            recurrence_type=recurrence_type,
            section=None,
            section_id=task.section_id,
            title=task.title,
            user=None,
            user_id=task.user_id,
        )

    def to_entity(self, attachments: List[Attachment]) -> Task:
        recurrence: Optional[RecurrenceInfo] = None
        if self.recurrence_type is not None or self.recurrence_period is not None or self.flexible_recurrence_mode is not None:
            if self.recurrence_type is None or self.recurrence_period is None or self.flexible_recurrence_mode is None:
                raise ValueError("recurrence fields must be all set or all None")
            recurrence = RecurrenceInfo(
                flexible_mode=bool(self.flexible_recurrence_mode),
                period=int(self.recurrence_period),
                type=self.recurrence_type,  # type: ignore[arg-type]
            )
        return Task(
            added_at=self.added_at,
            attachments=attachments,
            content=None,
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


@dataclass
class SectionModel:
    added_at: datetime
    has_subsections: bool
    has_tasks: bool
    id: UUID
    index: int
    parent_id: Optional[UUID]
    tasks: List[TaskModel]
    title: str
    user: Optional["UserModel"]
    user_id: UUID

    @staticmethod
    def from_entity(section: Section, index: NonNegativeInt) -> "SectionModel":
        _ensure_non_negative_int(index, "index")
        section_id = section.id or uuid4()
        added_at = section.added_at or datetime.utcnow()
        task_models: List[TaskModel] = []
        for i, t in enumerate(section.tasks):
            if t.section_id != section_id:
                t = Task(
                    added_at=t.added_at,
                    attachments=t.attachments,
                    content=t.content,
                    description=t.description,
                    due_to=t.due_to,
                    id=t.id,
                    is_archived=t.is_archived,
                    is_completed=t.is_completed,
                    recurrence=t.recurrence,
                    section_id=section_id,
                    title=t.title,
                    user_id=t.user_id,
                )
            task_models.append(TaskModel.from_entity(t, i))
        return SectionModel(
            added_at=added_at,
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
            id=section_id,
            index=index,
            parent_id=section.parent_id,
            tasks=task_models,
            title=section.title,
            user=None,
            user_id=section.user_id,
        )

    def to_entity(self, tasks: List[Task], subsections: List[Section]) -> Section:
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
        ).check_flags()


@dataclass
class UserModel:
    added_at: datetime
    sections: List[SectionModel]
    tasks: List[TaskModel]
    id: UUID
    email: str

    def to_entity(self) -> User:
        return User(added_at=self.added_at, email=self.email, id=self.id)


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
    def __init__(self, factory: Any = AsyncSession) -> None:
        self._factory = factory

    def __call__(self) -> AsyncSession:
        return self._factory()


class SQLAlchemyTaskRepository:
    def __init__(self, store: "InMemoryStore") -> None:
        self._store = store

    def add(self, task: Task, index: NonNegativeInt) -> None:
        _ensure_non_negative_int(index, "index")
        if task.id is None:
            task.id = uuid4()
        if task.added_at is None:
            task.added_at = datetime.utcnow()
        if task.id in self._store.tasks:
            raise ValueError("task already exists")
        self._store.tasks[task.id] = task
        self._store.task_index[task.id] = index

    def get(self, task_id: UUID) -> Task:
        _ensure_required_uuid(task_id, "task_id")
        try:
            return self._store.tasks[task_id]
        except KeyError as e:
            raise ValueError("task not found") from e

    def remove(self, task: Task) -> None:
        if task.id is None:
            raise ValueError("task.id is required")
        if task.id not in self._store.tasks:
            raise ValueError("task not found")
        del self._store.tasks[task.id]
        self._store.task_index.pop(task.id, None)
        self._store.attachments_by_task.pop(task.id, None)

    def delete_attachment(self, attachment: Attachment) -> None:
        if attachment.task_id not in self._store.attachments_by_task:
            raise ValueError("attachment not found")
        lst = self._store.attachments_by_task[attachment.task_id]
        for i, a in enumerate(lst):
            if a.id == attachment.id and a.s3_file_key == attachment.s3_file_key:
                lst.pop(i)
                return
        raise ValueError("attachment not found")

    def get_entity(self, task_model: TaskModel) -> Task:
        attachments = [am.to_entity() for am in sorted(task_model.attachments, key=lambda x: x.index)]
        return task_model.to_entity(attachments=attachments)

    def get_entities(self, task_models: Sequence[TaskModel]) -> List[Task]:
        return [self.get_entity(tm) for tm in task_models]

    def update_or_create(self, task: Task, index: Optional[NonNegativeInt], must_exist: bool) -> None:
        index = _ensure_non_negative_int(index, "index")
        if task.id is None:
            if must_exist:
                raise ValueError("task must exist")
            task.id = uuid4()
        if task.added_at is None:
            task.added_at = datetime.utcnow()

        exists = task.id in self._store.tasks
        if must_exist and not exists:
            raise ValueError("task not found")
        self._store.tasks[task.id] = task
        if index is not None:
            self._store.task_index[task.id] = index

    def update_or_create_bulk(self, section_tasks: List[Task]) -> None:
        if not isinstance(section_tasks, list) or any(not isinstance(t, Task) for t in section_tasks):
            raise ValueError("section_tasks must be list[Task]")
        for i, t in enumerate(section_tasks):
            self.update_or_create(t, index=i, must_exist=False)

    def get_archived_tasks(self, user_id: UUID) -> List[Task]:
        _ensure_required_uuid(user_id, "user_id")
        return [t for t in self._store.tasks.values() if t.user_id == user_id and t.is_archived]

    def get_overdue_tasks(self, user_id: UUID) -> List[Task]:
        _ensure_required_uuid(user_id, "user_id")
        today = date.today()
        return [
            t
            for t in self._store.tasks.values()
            if t.user_id == user_id and (t.due_to is not None and t.due_to < today) and not t.is_completed
        ]

    def get_tasks_by_due_to(self, not_before: date, not_after: date, user_id: UUID) -> List[Task]:
        if not isinstance(not_before, date) or not isinstance(not_after, date):
            raise ValueError("not_before and not_after must be date")
        _ensure_required_uuid(user_id, "user_id")
        if not_before > not_after:
            raise ValueError("not_before must be <= not_after")
        return [
            t
            for t in self._store.tasks.values()
            if t.user_id == user_id and t.due_to is not None and not_before <= t.due_to <= not_after
        ]

    def search(self, user_id: UUID, query: str) -> List[Task]:
        _ensure_required_uuid(user_id, "user_id")
        if not isinstance(query, str):
            raise ValueError("query must be str")
        q = query.strip().lower()
        if q == "":
            return []
        res: List[Task] = []
        for t in self._store.tasks.values():
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


class SQLAlchemySectionRepository:
    def __init__(self, store: "InMemoryStore") -> None:
        self._store = store

    def add(self, section: Section, index: NonNegativeInt) -> None:
        _ensure_non_negative_int(index, "index")
        if section.id is None:
            section.id = uuid4()
        if section.added_at is None:
            section.added_at = datetime.utcnow()
        if section.id in self._store.sections:
            raise ValueError("section already exists")
        self._store.sections[section.id] = section
        self._store.section_index[section.id] = index

    def update(self, section: Section, index: Optional[NonNegativeInt]) -> None:
        index = _ensure_non_negative_int(index, "index")
        if section.id is None:
            raise ValueError("section.id is required")
        if section.id not in self._store.sections:
            raise ValueError("section not found")
        section.check_flags()
        self._store.sections[section.id] = section
        if index is not None:
            self._store.section_index[section.id] = index

    def get(self, section_id: UUID, with_direct_subsections: bool) -> Section:
        _ensure_required_uuid(section_id, "section_id")
        if section_id not in self._store.sections:
            raise ValueError("section not found")
        section = self._store.sections[section_id]
        if not with_direct_subsections:
            return Section(
                added_at=section.added_at,
                has_subsections=section.has_subsections,
                has_tasks=section.has_tasks,
                id=section.id,
                parent_id=section.parent_id,
                subsections=[],
                tasks=list(section.tasks),
                title=section.title,
                user_id=section.user_id,
            ).check_flags()
        direct_subs = [s for s in self._store.sections.values() if s.parent_id == section_id]
        direct_subs_sorted = sorted(direct_subs, key=lambda s: self._store.section_index.get(s.id or UUID(int=0), 0))
        return Section(
            added_at=section.added_at,
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
            id=section.id,
            parent_id=section.parent_id,
            subsections=[self.get(s.id, with_direct_subsections=False) for s in direct_subs_sorted if s.id is not None],
            tasks=list(section.tasks),
            title=section.title,
            user_id=section.user_id,
        ).check_flags()

    def count_subsections(self, section_id: UUID) -> int:
        _ensure_required_uuid(section_id, "section_id")
        return sum(1 for s in self._store.sections.values() if s.parent_id == section_id)

    def construct_sections_tree(self, section_models: List[SectionModel], return_flat: bool) -> List[Section]:
        if not isinstance(section_models, list) or any(not isinstance(sm, SectionModel) for sm in section_models):
            raise ValueError("section_models must be list[SectionModel]")
        entities_by_id: Dict[UUID, Section] = {}
        children_by_parent: Dict[Optional[UUID], List[SectionModel]] = {}
        for sm in section_models:
            children_by_parent.setdefault(sm.parent_id, []).append(sm)
        for parent, lst in children_by_parent.items():
            lst.sort(key=lambda x: x.index)

        def build(sm: SectionModel) -> Section:
            tasks = [self._store.tasks[t.id] for t in sorted(sm.tasks, key=lambda tm: tm.index) if t.id in self._store.tasks]
            subs_models = children_by_parent.get(sm.id, [])
            subs = [build(child) for child in subs_models]
            sec = sm.to_entity(tasks=tasks, subsections=subs)
            entities_by_id[sm.id] = sec
            return sec

        roots = children_by_parent.get(None, [])
        tree = [build(sm) for sm in roots]
        if return_flat:
            flat: List[Section] = []

            def walk(s: Section) -> None:
                flat.append(s)
                for c in s.subsections:
                    walk(c)

            for r in tree:
                walk(r)
            return flat
        return tree

    def get_all_without_tasks(self, user_id: UUID, leaves_only: bool, as_tree: bool) -> List[Section]:
        _ensure_required_uuid(user_id, "user_id")
        sections = [s for s in self._store.sections.values() if s.user_id == user_id]
        if leaves_only:
            parent_ids = {s.parent_id for s in sections if s.parent_id is not None}
            leaves = [s for s in sections if s.id not in parent_ids]
            sections = leaves
        if not as_tree:
            return [Section(
                added_at=s.added_at,
                has_subsections=s.has_subsections,
                has_tasks=False,
                id=s.id,
                parent_id=s.parent_id,
                subsections=[],
                tasks=[],
                title=s.title,
                user_id=s.user_id,
            ).check_flags() for s in sections]
        models: List[SectionModel] = []
        for s in sections:
            if s.id is None:
                continue
            models.append(
                SectionModel(
                    added_at=s.added_at or datetime.utcnow(),
                    has_subsections=s.has_subsections,
                    has_tasks=False,
                    id=s.id,
                    index=self._store.section_index.get(s.id, 0),
                    parent_id=s.parent_id,
                    tasks=[],
                    title=s.title,
                    user=None,
                    user_id=s.user_id,
                )
            )
        return self.construct_sections_tree(models, return_flat=False)


class SQLAlchemyUserRepository:
    def __init__(self, store: "InMemoryStore") -> None:
        self._store = store

    def verify_user(self, user_id: UUID) -> None:
        _ensure_required_uuid(user_id, "user_id")
        if user_id not in self._store.users:
            raise ValueError("user not found")

    def get_all_users(self) -> List[UserStats]:
        stats: List[UserStats] = []
        for u in self._store.users.values():
            sections_count = sum(1 for s in self._store.sections.values() if s.user_id == u.id)
            tasks_count = sum(1 for t in self._store.tasks.values() if t.user_id == u.id)
            stats.append(UserStats(user=u, sections_count=sections_count, tasks_count=tasks_count))
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


@dataclass
class InMemoryStore:
    users: Dict[UUID, User] = field(default_factory=dict)
    sections: Dict[UUID, Section] = field(default_factory=dict)
    tasks: Dict[UUID, Task] = field(default_factory=dict)
    attachments_by_task: Dict[UUID, List[Attachment]] = field(default_factory=dict)
    section_index: Dict[UUID, int] = field(default_factory=dict)
    task_index: Dict[UUID, int] = field(default_factory=dict)


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker, store: Optional[InMemoryStore] = None) -> None:
        self.session_factory = session_factory
        self.session: AsyncSession = self.session_factory()
        self._store = store or InMemoryStore()
        self.section_repo = SQLAlchemySectionRepository(self._store)
        self.task_repo = SQLAlchemyTaskRepository(self._store)
        self.user_repo = SQLAlchemyUserRepository(self._store)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()