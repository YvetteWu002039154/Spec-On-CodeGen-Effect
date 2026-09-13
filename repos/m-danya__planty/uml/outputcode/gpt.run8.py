from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, ClassVar, Dict, Literal, Optional, Sequence, TypeVar, Generic, List
from uuid import UUID, uuid4


NonNegativeInt = int


def _ensure_non_negative_int(value: int, name: str) -> int:
    if not isinstance(value, int):
        raise TypeError(f"{name} must be int")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _insert_at(lst: list[Any], item: Any, index: Optional[NonNegativeInt]) -> None:
    if index is None:
        lst.append(item)
        return
    _ensure_non_negative_int(index, "index")
    if index > len(lst):
        raise IndexError("index out of range")
    lst.insert(index, item)


def _remove_first(lst: list[Any], item: Any) -> None:
    for i, x in enumerate(lst):
        if x is item or x == item:
            del lst[i]
            return
    raise ValueError("item not found")


class Entity:
    model_config: ClassVar[Dict[str, Any]] = {"arbitrary_types_allowed": True}


@dataclass
class User(Entity):
    email: str
    id: Optional[UUID] = None
    added_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not isinstance(self.email, str) or not self.email:
            raise ValueError("email must be a non-empty string")


@dataclass
class RecurrenceInfo(Entity):
    type: Literal["daily", "weekly", "monthly", "yearly"]
    period: int
    flexible_mode: bool

    def __post_init__(self) -> None:
        if self.type not in ("daily", "weekly", "monthly", "yearly"):
            raise ValueError("type must be one of: daily, weekly, monthly, yearly")
        if not isinstance(self.period, int) or self.period <= 0:
            raise ValueError("period must be a positive int")
        if not isinstance(self.flexible_mode, bool):
            raise TypeError("flexible_mode must be bool")


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
        for name in ("s3_file_key", "aes_key_b64", "aes_iv_b64"):
            v = getattr(self, name)
            if not isinstance(v, str) or not v:
                raise ValueError(f"{name} must be a non-empty string")


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
    attachments: Optional[list[Attachment]] = None

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, UUID):
            raise TypeError("user_id must be UUID")
        if not isinstance(self.section_id, UUID):
            raise TypeError("section_id must be UUID")
        if not isinstance(self.title, str) or not self.title:
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
                    raise TypeError("attachments must contain Attachment")
                if a.task_id != (self.id if self.id is not None else a.task_id):
                    pass
        self.check_recurrence_due_date(None)

    def check_recurrence_due_date(self, values: Any) -> Any:
        if self.recurrence is not None and self.due_to is None:
            raise ValueError("due_to must be set when recurrence is set")
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
            raise ValueError("no attachments")
        _remove_first(self.attachments, attachment)
        if len(self.attachments) == 0:
            self.attachments = []

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
    added_at: Optional[datetime] = None
    parent_id: Optional[UUID] = None
    subsections: list["Section"] = None  # type: ignore[assignment]
    tasks: list[Task] = None  # type: ignore[assignment]
    has_subsections: bool = False
    has_tasks: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, UUID):
            raise TypeError("user_id must be UUID")
        if not isinstance(self.title, str) or not self.title:
            raise ValueError("title must be a non-empty string")
        if self.parent_id is not None and not isinstance(self.parent_id, UUID):
            raise TypeError("parent_id must be UUID or None")
        if self.subsections is None:
            self.subsections = []
        if self.tasks is None:
            self.tasks = []
        if not isinstance(self.subsections, list):
            raise TypeError("subsections must be list")
        if not isinstance(self.tasks, list):
            raise TypeError("tasks must be list")
        for s in self.subsections:
            if not isinstance(s, Section):
                raise TypeError("subsections must contain Section")
        for t in self.tasks:
            if not isinstance(t, Task):
                raise TypeError("tasks must contain Task")
        self.check_flags()

    @classmethod
    def create_root_section(cls, user_id: UUID) -> "Section":
        if not isinstance(user_id, UUID):
            raise TypeError("user_id must be UUID")
        return cls(user_id=user_id, title="Root", parent_id=None)

    def is_root(self) -> bool:
        return self.parent_id is None

    def check_flags(self) -> "Section":
        self.has_subsections = len(self.subsections) > 0
        self.has_tasks = len(self.tasks) > 0
        return self

    def insert_subsection(self, subsection: "Section", index: Optional[NonNegativeInt]) -> None:
        if not isinstance(subsection, Section):
            raise TypeError("subsection must be Section")
        if subsection.user_id != self.user_id:
            raise ValueError("subsection.user_id must match section.user_id")
        _insert_at(self.subsections, subsection, index)
        self.check_flags()

    def remove_subsection(self, subsection: "Section") -> "Section":
        _remove_first(self.subsections, subsection)
        self.check_flags()
        return subsection

    def insert_task(self, task: Task, index: Optional[NonNegativeInt]) -> None:
        if not isinstance(task, Task):
            raise TypeError("task must be Task")
        if task.user_id != self.user_id:
            raise ValueError("task.user_id must match section.user_id")
        if self.id is not None and task.section_id != self.id:
            raise ValueError("task.section_id must match section.id")
        _insert_at(self.tasks, task, index)
        self.check_flags()

    def remove_task(self, task: Task) -> Task:
        _remove_first(self.tasks, task)
        self.check_flags()
        return task

    def shuffle_tasks(self) -> None:
        self.tasks = [t for t in self.tasks]
        self.check_flags()

    @staticmethod
    def move_task(task_to_move: Task, section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if not isinstance(task_to_move, Task):
            raise TypeError("task_to_move must be Task")
        if not isinstance(section_from, Section) or not isinstance(section_to, Section):
            raise TypeError("section_from and section_to must be Section")
        _ensure_non_negative_int(index, "index")
        if section_from.user_id != section_to.user_id or task_to_move.user_id != section_to.user_id:
            raise ValueError("user_id mismatch")
        section_from.remove_task(task_to_move)
        _insert_at(section_to.tasks, task_to_move, index)
        section_to.check_flags()
        section_from.check_flags()

    @staticmethod
    def move_section(section: "Section", section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if not isinstance(section, Section):
            raise TypeError("section must be Section")
        if not isinstance(section_from, Section) or not isinstance(section_to, Section):
            raise TypeError("section_from and section_to must be Section")
        _ensure_non_negative_int(index, "index")
        if section_from.user_id != section_to.user_id or section.user_id != section_to.user_id:
            raise ValueError("user_id mismatch")
        section_from.remove_subsection(section)
        _insert_at(section_to.subsections, section, index)
        section_to.check_flags()
        section_from.check_flags()


T = TypeVar("T")


class Mapped(Generic[T]):
    pass


class GUID(UUID):
    pass


class AccessTokenModel:
    def __init__(self) -> None:
        pass


class AttachmentModel:
    def __init__(
        self,
        id: UUID,
        task_id: UUID,
        s3_file_key: str,
        aes_key_b64: str,
        aes_iv_b64: str,
        index: int,
        added_at: datetime,
    ) -> None:
        self.id: UUID = id
        self.task_id: UUID = task_id
        self.s3_file_key: str = s3_file_key
        self.aes_key_b64: str = aes_key_b64
        self.aes_iv_b64: str = aes_iv_b64
        self.index: int = index
        self.added_at: datetime = added_at
        self.task: Optional["TaskModel"] = None

    @staticmethod
    def from_entity(attachment: Attachment, index: NonNegativeInt) -> "AttachmentModel":
        _ensure_non_negative_int(index, "index")
        if attachment.id is None:
            att_id = uuid4()
        else:
            att_id = attachment.id
        added_at = attachment.added_at or datetime.utcnow()
        return AttachmentModel(
            id=att_id,
            task_id=attachment.task_id,
            s3_file_key=attachment.s3_file_key,
            aes_key_b64=attachment.aes_key_b64,
            aes_iv_b64=attachment.aes_iv_b64,
            index=index,
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


class TaskModel:
    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        section_id: UUID,
        title: str,
        index: int,
        added_at: datetime,
        description: Optional[str],
        due_to: Optional[date],
        is_archived: bool,
        is_completed: bool,
        recurrence_type: Optional[str],
        recurrence_period: Optional[int],
        flexible_recurrence_mode: Optional[bool],
    ) -> None:
        self.id: UUID = id
        self.user_id: UUID = user_id
        self.section_id: UUID = section_id
        self.title: str = title
        self.index: int = index
        self.added_at: datetime = added_at
        self.description: Optional[str] = description
        self.due_to: Optional[date] = due_to
        self.is_archived: bool = is_archived
        self.is_completed: bool = is_completed
        self.recurrence_type: Optional[str] = recurrence_type
        self.recurrence_period: Optional[int] = recurrence_period
        self.flexible_recurrence_mode: Optional[bool] = flexible_recurrence_mode
        self.attachments: list[AttachmentModel] = []
        self.section: Optional["SectionModel"] = None
        self.user: Optional["UserModel"] = None

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
        model = TaskModel(
            id=task_id,
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
        if task.attachments:
            model.attachments = [AttachmentModel.from_entity(a, i) for i, a in enumerate(task.attachments)]
        return model

    def to_entity(self, attachments: list[Attachment]) -> Task:
        recurrence: Optional[RecurrenceInfo] = None
        if self.recurrence_type is not None or self.recurrence_period is not None or self.flexible_recurrence_mode is not None:
            if self.recurrence_type is None or self.recurrence_period is None or self.flexible_recurrence_mode is None:
                raise ValueError("Incomplete recurrence fields")
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
            added_at=self.added_at,
            description=self.description,
            due_to=self.due_to,
            is_archived=self.is_archived,
            is_completed=self.is_completed,
            recurrence=recurrence,
            attachments=attachments,
        )


class SectionModel:
    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        title: str,
        index: int,
        added_at: datetime,
        parent_id: Optional[GUID],
        has_subsections: bool,
        has_tasks: bool,
    ) -> None:
        self.id: UUID = id
        self.user_id: UUID = user_id
        self.title: str = title
        self.index: int = index
        self.added_at: datetime = added_at
        self.parent_id: Optional[GUID] = parent_id
        self.has_subsections: bool = has_subsections
        self.has_tasks: bool = has_tasks
        self.tasks: list[TaskModel] = []
        self.user: Optional["UserModel"] = None

    @staticmethod
    def from_entity(section: Section, index: NonNegativeInt) -> "SectionModel":
        _ensure_non_negative_int(index, "index")
        sec_id = section.id or uuid4()
        added_at = section.added_at or datetime.utcnow()
        parent_id: Optional[GUID] = None
        if section.parent_id is not None:
            parent_id = GUID(bytes=section.parent_id.bytes)
        model = SectionModel(
            id=sec_id,
            user_id=section.user_id,
            title=section.title,
            index=index,
            added_at=added_at,
            parent_id=parent_id,
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
        )
        return model

    def to_entity(self, tasks: list[Task], subsections: list[Section]) -> Section:
        parent_uuid: Optional[UUID] = None
        if self.parent_id is not None:
            parent_uuid = UUID(bytes=self.parent_id.bytes)
        sec = Section(
            id=self.id,
            user_id=self.user_id,
            title=self.title,
            added_at=self.added_at,
            parent_id=parent_uuid,
            tasks=tasks,
            subsections=subsections,
            has_subsections=self.has_subsections,
            has_tasks=self.has_tasks,
        )
        sec.check_flags()
        return sec


class UserModel:
    def __init__(self, id: UUID, email: str, added_at: datetime) -> None:
        self.id: UUID = id
        self.email: str = email
        self.added_at: datetime = added_at
        self.sections: list[SectionModel] = []
        self.tasks: list[TaskModel] = []

    def to_entity(self) -> User:
        return User(id=self.id, email=self.email, added_at=self.added_at)


@dataclass
class UserStats(Entity):
    user_id: UUID
    email: str
    added_at: Optional[datetime] = None


class AsyncSession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class async_sessionmaker:
    def __init__(self, session_cls: type[AsyncSession] = AsyncSession) -> None:
        self._session_cls = session_cls

    def __call__(self) -> AsyncSession:
        return self._session_cls()


class SQLAlchemyTaskRepository:
    def __init__(self) -> None:
        self._tasks: Dict[UUID, Task] = {}
        self._section_index: Dict[UUID, list[UUID]] = {}

    def add(self, task: Task, index: NonNegativeInt) -> None:
        _ensure_non_negative_int(index, "index")
        if task.id is None:
            task.id = uuid4()
        if task.added_at is None:
            task.added_at = datetime.utcnow()
        if task.id in self._tasks:
            raise ValueError("task already exists")
        self._tasks[task.id] = task
        ids = self._section_index.setdefault(task.section_id, [])
        if index > len(ids):
            raise IndexError("index out of range")
        ids.insert(index, task.id)

    def get(self, task_id: UUID) -> Task:
        if task_id not in self._tasks:
            raise KeyError("task not found")
        return self._tasks[task_id]

    def remove(self, task: Task) -> None:
        if task.id is None or task.id not in self._tasks:
            raise KeyError("task not found")
        del self._tasks[task.id]
        ids = self._section_index.get(task.section_id, [])
        if task.id in ids:
            ids.remove(task.id)

    def delete_attachment(self, attachment: Attachment) -> None:
        task = None
        if attachment.task_id in self._tasks:
            task = self._tasks[attachment.task_id]
        else:
            for t in self._tasks.values():
                if t.id == attachment.task_id:
                    task = t
                    break
        if task is None:
            raise KeyError("task not found for attachment")
        task.remove_attachment(attachment)

    def update_or_create(self, task: Task, index: Optional[NonNegativeInt], must_exist: bool) -> None:
        if task.id is None:
            if must_exist:
                raise KeyError("task must exist")
            if index is None:
                index = len(self._section_index.get(task.section_id, []))
            self.add(task, index)
            return

        if task.id in self._tasks:
            existing = self._tasks[task.id]
            old_section_id = existing.section_id
            self._tasks[task.id] = task
            if old_section_id != task.section_id:
                old_ids = self._section_index.get(old_section_id, [])
                if task.id in old_ids:
                    old_ids.remove(task.id)
                new_ids = self._section_index.setdefault(task.section_id, [])
                if index is None:
                    new_ids.append(task.id)
                else:
                    _ensure_non_negative_int(index, "index")
                    if index > len(new_ids):
                        raise IndexError("index out of range")
                    new_ids.insert(index, task.id)
            else:
                if index is not None:
                    _ensure_non_negative_int(index, "index")
                    ids = self._section_index.setdefault(task.section_id, [])
                    if task.id in ids:
                        ids.remove(task.id)
                    if index > len(ids):
                        raise IndexError("index out of range")
                    ids.insert(index, task.id)
            return

        if must_exist:
            raise KeyError("task not found")
        if index is None:
            index = len(self._section_index.get(task.section_id, []))
        self.add(task, index)

    def update_or_create_bulk(self, section_tasks: list[Task]) -> None:
        if not isinstance(section_tasks, list):
            raise TypeError("section_tasks must be list")
        for i, t in enumerate(section_tasks):
            self.update_or_create(t, index=i, must_exist=False)

    def get_entity(self, task_model: TaskModel) -> Task:
        attachments = [am.to_entity() for am in task_model.attachments]
        return task_model.to_entity(attachments=attachments)

    def get_entities(self, task_models: Sequence[TaskModel]) -> list[Task]:
        return [self.get_entity(tm) for tm in task_models]

    def get_archived_tasks(self, user_id: UUID) -> list[Task]:
        return [t for t in self._tasks.values() if t.user_id == user_id and t.is_archived]

    def get_overdue_tasks(self, user_id: UUID) -> list[Task]:
        today = date.today()
        return [
            t
            for t in self._tasks.values()
            if t.user_id == user_id and not t.is_archived and not t.is_completed and t.due_to is not None and t.due_to < today
        ]

    def get_tasks_by_due_to(self, not_before: date, not_after: date, user_id: UUID) -> list[Task]:
        if not isinstance(not_before, date) or not isinstance(not_after, date):
            raise TypeError("not_before and not_after must be date")
        return [
            t
            for t in self._tasks.values()
            if t.user_id == user_id and t.due_to is not None and not_before <= t.due_to <= not_after
        ]

    def search(self, user_id: UUID, query: str) -> list[Task]:
        if not isinstance(query, str):
            raise TypeError("query must be str")
        q = query.strip().lower()
        if not q:
            return []
        res: list[Task] = []
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


class SQLAlchemySectionRepository:
    def __init__(self) -> None:
        self._sections: Dict[UUID, Section] = {}
        self._children_index: Dict[Optional[UUID], list[UUID]] = {}

    def add(self, section: Section, index: NonNegativeInt) -> None:
        _ensure_non_negative_int(index, "index")
        if section.id is None:
            section.id = uuid4()
        if section.added_at is None:
            section.added_at = datetime.utcnow()
        if section.id in self._sections:
            raise ValueError("section already exists")
        self._sections[section.id] = section
        ids = self._children_index.setdefault(section.parent_id, [])
        if index > len(ids):
            raise IndexError("index out of range")
        ids.insert(index, section.id)

    def update(self, section: Section, index: Optional[NonNegativeInt]) -> None:
        if section.id is None or section.id not in self._sections:
            raise KeyError("section not found")
        existing = self._sections[section.id]
        old_parent = existing.parent_id
        self._sections[section.id] = section
        if old_parent != section.parent_id:
            old_ids = self._children_index.get(old_parent, [])
            if section.id in old_ids:
                old_ids.remove(section.id)
            new_ids = self._children_index.setdefault(section.parent_id, [])
            if index is None:
                new_ids.append(section.id)
            else:
                _ensure_non_negative_int(index, "index")
                if index > len(new_ids):
                    raise IndexError("index out of range")
                new_ids.insert(index, section.id)
        else:
            if index is not None:
                _ensure_non_negative_int(index, "index")
                ids = self._children_index.setdefault(section.parent_id, [])
                if section.id in ids:
                    ids.remove(section.id)
                if index > len(ids):
                    raise IndexError("index out of range")
                ids.insert(index, section.id)

    def count_subsections(self, section_id: UUID) -> int:
        return len(self._children_index.get(section_id, []))

    def get(self, section_id: UUID, with_direct_subsections: bool) -> Section:
        if section_id not in self._sections:
            raise KeyError("section not found")
        base = self._sections[section_id]
        if not with_direct_subsections:
            return Section(
                id=base.id,
                user_id=base.user_id,
                title=base.title,
                added_at=base.added_at,
                parent_id=base.parent_id,
                subsections=[],
                tasks=list(base.tasks),
                has_subsections=base.has_subsections,
                has_tasks=base.has_tasks,
            ).check_flags()
        child_ids = self._children_index.get(section_id, [])
        children = [self._sections[cid] for cid in child_ids if cid in self._sections]
        return Section(
            id=base.id,
            user_id=base.user_id,
            title=base.title,
            added_at=base.added_at,
            parent_id=base.parent_id,
            subsections=[Section(
                id=c.id,
                user_id=c.user_id,
                title=c.title,
                added_at=c.added_at,
                parent_id=c.parent_id,
                subsections=[],
                tasks=list(c.tasks),
                has_subsections=c.has_subsections,
                has_tasks=c.has_tasks,
            ).check_flags() for c in children],
            tasks=list(base.tasks),
            has_subsections=base.has_subsections,
            has_tasks=base.has_tasks,
        ).check_flags()

    def construct_sections_tree(self, section_models: list[SectionModel], return_flat: bool) -> list[Section]:
        if not isinstance(section_models, list):
            raise TypeError("section_models must be list")
        entities: Dict[UUID, Section] = {}
        for sm in section_models:
            tasks: list[Task] = []
            subsections: list[Section] = []
            entities[sm.id] = sm.to_entity(tasks=tasks, subsections=subsections)

        children_map: Dict[Optional[UUID], list[UUID]] = {}
        for sm in section_models:
            parent_uuid: Optional[UUID] = None
            if sm.parent_id is not None:
                parent_uuid = UUID(bytes=sm.parent_id.bytes)
            children_map.setdefault(parent_uuid, []).append(sm.id)

        for sm in section_models:
            sec = entities[sm.id]
            child_ids = children_map.get(sec.id, [])
            sec.subsections = [entities[cid] for cid in child_ids if cid in entities]
            sec.check_flags()

        roots = [entities[sid] for sid in children_map.get(None, []) if sid in entities]
        if return_flat:
            return list(entities.values())
        return roots

    def get_all_without_tasks(self, user_id: UUID, leaves_only: bool, as_tree: bool) -> list[Section]:
        secs = [s for s in self._sections.values() if s.user_id == user_id]
        if leaves_only:
            secs = [s for s in secs if len(self._children_index.get(s.id, [])) == 0]
        if not as_tree:
            return [
                Section(
                    id=s.id,
                    user_id=s.user_id,
                    title=s.title,
                    added_at=s.added_at,
                    parent_id=s.parent_id,
                    subsections=[],
                    tasks=[],
                    has_subsections=len(self._children_index.get(s.id, [])) > 0,
                    has_tasks=False,
                ).check_flags()
                for s in secs
            ]
        models: list[SectionModel] = []
        for s in secs:
            parent_id: Optional[GUID] = None
            if s.parent_id is not None:
                parent_id = GUID(bytes=s.parent_id.bytes)
            sm = SectionModel(
                id=s.id or uuid4(),
                user_id=s.user_id,
                title=s.title,
                index=0,
                added_at=s.added_at or datetime.utcnow(),
                parent_id=parent_id,
                has_subsections=len(self._children_index.get(s.id, [])) > 0,
                has_tasks=False,
            )
            models.append(sm)
        return self.construct_sections_tree(models, return_flat=False)


class SQLAlchemyUserRepository:
    def __init__(self) -> None:
        self._users: Dict[UUID, User] = {}

    def add(self, user: User) -> None:
        if user.id is None:
            user.id = uuid4()
        if user.added_at is None:
            user.added_at = datetime.utcnow()
        if user.id in self._users:
            raise ValueError("user already exists")
        self._users[user.id] = user

    def verify_user(self, user_id: UUID) -> None:
        if user_id not in self._users:
            raise KeyError("user not found")

    def get_all_users(self) -> list[UserStats]:
        return [UserStats(user_id=u.id or uuid4(), email=u.email, added_at=u.added_at) for u in self._users.values()]


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
        self.session_factory: async_sessionmaker = session_factory
        self.session: AsyncSession = session_factory()
        self.section_repo: SQLAlchemySectionRepository = SQLAlchemySectionRepository()
        self.task_repo: SQLAlchemyTaskRepository = SQLAlchemyTaskRepository()
        self.user_repo: SQLAlchemyUserRepository = SQLAlchemyUserRepository()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()