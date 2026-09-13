from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, TypeVar
from uuid import UUID, uuid4


NonNegativeInt = int


def _validate_non_negative_int(value: int, name: str) -> None:
    if not isinstance(value, int):
        raise TypeError(f"{name} must be int")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _insert_at_index(items: List[Any], item: Any, index: Optional[NonNegativeInt]) -> None:
    if index is None:
        items.append(item)
        return
    _validate_non_negative_int(index, "index")
    if index > len(items):
        raise IndexError("index out of range")
    items.insert(index, item)


def _remove_first(items: List[Any], predicate) -> Any:
    for i, x in enumerate(items):
        if predicate(x):
            return items.pop(i)
    raise ValueError("item not found")


T = TypeVar("T")


class Entity:
    model_config: Dict[str, Any] = {}


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
        if not isinstance(self.s3_file_key, str) or not self.s3_file_key:
            raise ValueError("s3_file_key must be non-empty str")
        if not isinstance(self.aes_key_b64, str) or not self.aes_key_b64:
            raise ValueError("aes_key_b64 must be non-empty str")
        if not isinstance(self.aes_iv_b64, str) or not self.aes_iv_b64:
            raise ValueError("aes_iv_b64 must be non-empty str")
        if self.id is not None and not isinstance(self.id, UUID):
            raise TypeError("id must be UUID or None")
        if self.added_at is not None and not isinstance(self.added_at, datetime):
            raise TypeError("added_at must be datetime or None")


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
        if not isinstance(self.user_id, UUID):
            raise TypeError("user_id must be UUID")
        if not isinstance(self.section_id, UUID):
            raise TypeError("section_id must be UUID")
        if not isinstance(self.title, str) or not self.title:
            raise ValueError("title must be non-empty str")
        if self.id is not None and not isinstance(self.id, UUID):
            raise TypeError("id must be UUID or None")
        if self.added_at is not None and not isinstance(self.added_at, datetime):
            raise TypeError("added_at must be datetime or None")
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
            raise ValueError("attachment not found")
        _remove_first(self.attachments, lambda a: a is attachment or (a.id is not None and a.id == attachment.id))

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
    has_subsections: bool = False
    has_tasks: bool = False
    subsections: List["Section"] = None
    tasks: List[Task] = None

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, UUID):
            raise TypeError("user_id must be UUID")
        if not isinstance(self.title, str) or not self.title:
            raise ValueError("title must be non-empty str")
        if self.id is not None and not isinstance(self.id, UUID):
            raise TypeError("id must be UUID or None")
        if self.parent_id is not None and not isinstance(self.parent_id, UUID):
            raise TypeError("parent_id must be UUID or None")
        if self.added_at is not None and not isinstance(self.added_at, datetime):
            raise TypeError("added_at must be datetime or None")
        if not isinstance(self.has_subsections, bool):
            raise TypeError("has_subsections must be bool")
        if not isinstance(self.has_tasks, bool):
            raise TypeError("has_tasks must be bool")
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

    @staticmethod
    def create_root_section(user_id: UUID) -> "Section":
        if not isinstance(user_id, UUID):
            raise TypeError("user_id must be UUID")
        return Section(user_id=user_id, title="Root", parent_id=None)

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
        _insert_at_index(self.subsections, subsection, index)
        self.check_flags()

    def remove_subsection(self, subsection: "Section") -> "Section":
        if not isinstance(subsection, Section):
            raise TypeError("subsection must be Section")
        removed = _remove_first(self.subsections, lambda s: s is subsection or (s.id is not None and s.id == subsection.id))
        self.check_flags()
        return removed

    def insert_task(self, task: Task, index: Optional[NonNegativeInt]) -> None:
        if not isinstance(task, Task):
            raise TypeError("task must be Task")
        if task.user_id != self.user_id:
            raise ValueError("task.user_id must match section.user_id")
        _insert_at_index(self.tasks, task, index)
        self.check_flags()

    def remove_task(self, task: Task) -> Task:
        if not isinstance(task, Task):
            raise TypeError("task must be Task")
        removed = _remove_first(self.tasks, lambda t: t is task or (t.id is not None and t.id == task.id))
        self.check_flags()
        return removed

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
        removed = section_from.remove_task(task_to_move)
        section_to.insert_task(removed, index)
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
            raise ValueError("user_id mismatch")
        removed = section_from.remove_subsection(section)
        section_to.insert_subsection(removed, index)
        section_from.check_flags()
        section_to.check_flags()


@dataclass
class User(Entity):
    email: str
    id: Optional[UUID] = None
    added_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not isinstance(self.email, str) or not self.email:
            raise ValueError("email must be non-empty str")
        if self.id is not None and not isinstance(self.id, UUID):
            raise TypeError("id must be UUID or None")
        if self.added_at is not None and not isinstance(self.added_at, datetime):
            raise TypeError("added_at must be datetime or None")


@dataclass
class UserStats(Entity):
    user_id: UUID
    email: str
    sections_count: int
    tasks_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, UUID):
            raise TypeError("user_id must be UUID")
        if not isinstance(self.email, str) or not self.email:
            raise ValueError("email must be non-empty str")
        if not isinstance(self.sections_count, int) or self.sections_count < 0:
            raise ValueError("sections_count must be non-negative int")
        if not isinstance(self.tasks_count, int) or self.tasks_count < 0:
            raise ValueError("tasks_count must be non-negative int")


class AccessTokenModel:
    def __init__(self) -> None:
        pass


class UserModel:
    def __init__(self, id: UUID, email: str, added_at: datetime) -> None:
        self.id: UUID = id
        self.email: str = email
        self.added_at: datetime = added_at
        self.sections: List[SectionModel] = []
        self.tasks: List[TaskModel] = []

    def to_entity(self) -> User:
        return User(id=self.id, email=self.email, added_at=self.added_at)


class SectionModel:
    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        title: str,
        index: int,
        added_at: datetime,
        parent_id: Optional[UUID],
        has_subsections: bool,
        has_tasks: bool,
    ) -> None:
        self.id: UUID = id
        self.user_id: UUID = user_id
        self.title: str = title
        self.index: int = index
        self.added_at: datetime = added_at
        self.parent_id: Optional[UUID] = parent_id
        self.has_subsections: bool = has_subsections
        self.has_tasks: bool = has_tasks
        self.tasks: List[TaskModel] = []
        self.user: Optional[UserModel] = None

    @staticmethod
    def from_entity(section: Section, index: NonNegativeInt) -> "SectionModel":
        _validate_non_negative_int(index, "index")
        sid = section.id or uuid4()
        added_at = section.added_at or datetime.utcnow()
        return SectionModel(
            id=sid,
            user_id=section.user_id,
            title=section.title,
            index=index,
            added_at=added_at,
            parent_id=section.parent_id,
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
        )

    def to_entity(self, tasks: List[Task], subsections: List[Section]) -> Section:
        return Section(
            id=self.id,
            user_id=self.user_id,
            title=self.title,
            parent_id=self.parent_id,
            added_at=self.added_at,
            has_subsections=self.has_subsections,
            has_tasks=self.has_tasks,
            tasks=tasks,
            subsections=subsections,
        ).check_flags()


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
        self.attachments: List[AttachmentModel] = []
        self.section: Optional[SectionModel] = None
        self.user: Optional[UserModel] = None

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
        return TaskModel(
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

    def to_entity(self, attachments: List[Attachment]) -> Task:
        recurrence: Optional[RecurrenceInfo] = None
        if self.recurrence_type is not None or self.recurrence_period is not None or self.flexible_recurrence_mode is not None:
            if self.recurrence_type is None or self.recurrence_period is None or self.flexible_recurrence_mode is None:
                raise ValueError("recurrence fields must be all set or all None")
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


class AttachmentModel:
    def __init__(
        self,
        id: UUID,
        task_id: UUID,
        index: int,
        s3_file_key: str,
        aes_key_b64: str,
        aes_iv_b64: str,
        added_at: datetime,
    ) -> None:
        self.id: UUID = id
        self.task_id: UUID = task_id
        self.index: int = index
        self.s3_file_key: str = s3_file_key
        self.aes_key_b64: str = aes_key_b64
        self.aes_iv_b64: str = aes_iv_b64
        self.added_at: datetime = added_at
        self.task: Optional[TaskModel] = None

    @staticmethod
    def from_entity(attachment: Attachment, index: NonNegativeInt) -> "AttachmentModel":
        _validate_non_negative_int(index, "index")
        aid = attachment.id or uuid4()
        added_at = attachment.added_at or datetime.utcnow()
        return AttachmentModel(
            id=aid,
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


class AsyncSession:
    def __init__(self) -> None:
        self._pending: List[Tuple[str, Any]] = []

    async def commit(self) -> None:
        self._pending.clear()

    async def rollback(self) -> None:
        self._pending.clear()


class async_sessionmaker:
    def __init__(self) -> None:
        self._session = AsyncSession()

    def __call__(self) -> AsyncSession:
        return AsyncSession()


class SQLAlchemyTaskRepository:
    def __init__(self) -> None:
        self._tasks: Dict[UUID, TaskModel] = {}
        self._attachments: Dict[UUID, AttachmentModel] = {}
        self._task_attachments: Dict[UUID, List[UUID]] = {}
        self._section_tasks: Dict[UUID, List[UUID]] = {}

    def add(self, task: Task, index: NonNegativeInt) -> None:
        _validate_non_negative_int(index, "index")
        model = TaskModel.from_entity(task, index)
        self._tasks[model.id] = model
        if model.section_id not in self._section_tasks:
            self._section_tasks[model.section_id] = []
        if index > len(self._section_tasks[model.section_id]):
            raise IndexError("index out of range")
        self._section_tasks[model.section_id].insert(index, model.id)
        if task.attachments:
            for i, att in enumerate(task.attachments):
                att_model = AttachmentModel.from_entity(att, i)
                att_model.task_id = model.id
                self._attachments[att_model.id] = att_model
                self._task_attachments.setdefault(model.id, []).append(att_model.id)

    def remove(self, task: Task) -> None:
        if task.id is None:
            raise ValueError("task.id is required")
        tid = task.id
        model = self._tasks.pop(tid, None)
        if model is None:
            raise ValueError("task not found")
        ids = self._task_attachments.pop(tid, [])
        for aid in ids:
            self._attachments.pop(aid, None)
        if model.section_id in self._section_tasks:
            self._section_tasks[model.section_id] = [x for x in self._section_tasks[model.section_id] if x != tid]

    def get(self, task_id: UUID) -> Task:
        model = self._tasks.get(task_id)
        if model is None:
            raise ValueError("task not found")
        return self.get_entity(model)

    def get_entity(self, task_model: TaskModel) -> Task:
        att_ids = self._task_attachments.get(task_model.id, [])
        atts = [self._attachments[aid].to_entity() for aid in sorted(att_ids, key=lambda x: self._attachments[x].index)]
        return task_model.to_entity(attachments=atts)

    def get_entities(self, task_models: Sequence[TaskModel]) -> List[Task]:
        return [self.get_entity(m) for m in task_models]

    def update_or_create(self, task: Task, index: Optional[NonNegativeInt], must_exist: bool) -> None:
        if task.id is None:
            if must_exist:
                raise ValueError("task must exist")
            idx = 0 if index is None else index
            self.add(task, idx)
            return

        existing = self._tasks.get(task.id)
        if existing is None:
            if must_exist:
                raise ValueError("task not found")
            idx = 0 if index is None else index
            self.add(task, idx)
            return

        if index is not None:
            _validate_non_negative_int(index, "index")
            sec_list = self._section_tasks.get(existing.section_id, [])
            if task.id in sec_list:
                sec_list.remove(task.id)
            if index > len(sec_list):
                raise IndexError("index out of range")
            sec_list.insert(index, task.id)
            self._section_tasks[existing.section_id] = sec_list
            existing.index = index

        existing.title = task.title
        existing.description = task.description
        existing.due_to = task.due_to
        existing.is_archived = task.is_archived
        existing.is_completed = task.is_completed
        existing.section_id = task.section_id
        existing.user_id = task.user_id

        if task.recurrence is None:
            existing.recurrence_type = None
            existing.recurrence_period = None
            existing.flexible_recurrence_mode = None
        else:
            existing.recurrence_type = str(task.recurrence.type)
            existing.recurrence_period = int(task.recurrence.period)
            existing.flexible_recurrence_mode = bool(task.recurrence.flexible_mode)

    def update_or_create_bulk(self, section_tasks: List[Task]) -> None:
        for i, t in enumerate(section_tasks):
            self.update_or_create(t, index=i, must_exist=False)

    def delete_attachment(self, attachment: Attachment) -> None:
        if attachment.id is None:
            raise ValueError("attachment.id is required")
        model = self._attachments.pop(attachment.id, None)
        if model is None:
            raise ValueError("attachment not found")
        if model.task_id in self._task_attachments:
            self._task_attachments[model.task_id] = [x for x in self._task_attachments[model.task_id] if x != model.id]

    def get_archived_tasks(self, user_id: UUID) -> List[Task]:
        models = [m for m in self._tasks.values() if m.user_id == user_id and m.is_archived]
        models.sort(key=lambda m: (m.added_at, m.index))
        return self.get_entities(models)

    def get_overdue_tasks(self, user_id: UUID) -> List[Task]:
        today = date.today()
        models = [
            m
            for m in self._tasks.values()
            if m.user_id == user_id and (m.due_to is not None and m.due_to < today) and not m.is_completed
        ]
        models.sort(key=lambda m: (m.due_to or today, m.index))
        return self.get_entities(models)

    def get_tasks_by_due_to(self, not_before: date, not_after: date, user_id: UUID) -> List[Task]:
        if not isinstance(not_before, date) or not isinstance(not_after, date):
            raise TypeError("not_before and not_after must be date")
        models = [
            m
            for m in self._tasks.values()
            if m.user_id == user_id and m.due_to is not None and not_before <= m.due_to <= not_after
        ]
        models.sort(key=lambda m: (m.due_to or not_before, m.index))
        return self.get_entities(models)

    def search(self, user_id: UUID, query: str) -> List[Task]:
        if not isinstance(query, str):
            raise TypeError("query must be str")
        q = query.strip().lower()
        models = [m for m in self._tasks.values() if m.user_id == user_id]
        if q:
            models = [
                m
                for m in models
                if q in m.title.lower() or (m.description or "").lower().find(q) != -1
            ]
        models.sort(key=lambda m: (m.added_at, m.index))
        return self.get_entities(models)


class SQLAlchemySectionRepository:
    def __init__(self, task_repo: SQLAlchemyTaskRepository) -> None:
        self._sections: Dict[UUID, SectionModel] = {}
        self._user_sections: Dict[UUID, List[UUID]] = {}
        self._children: Dict[Optional[UUID], List[UUID]] = {}
        self._task_repo = task_repo

    def add(self, section: Section, index: NonNegativeInt) -> None:
        _validate_non_negative_int(index, "index")
        model = SectionModel.from_entity(section, index)
        self._sections[model.id] = model
        self._user_sections.setdefault(model.user_id, [])
        if index > len(self._user_sections[model.user_id]):
            raise IndexError("index out of range")
        self._user_sections[model.user_id].insert(index, model.id)
        self._children.setdefault(model.parent_id, [])
        self._children[model.parent_id].append(model.id)

    def update(self, section: Section, index: Optional[NonNegativeInt]) -> None:
        if section.id is None:
            raise ValueError("section.id is required")
        model = self._sections.get(section.id)
        if model is None:
            raise ValueError("section not found")
        if index is not None:
            _validate_non_negative_int(index, "index")
            lst = self._user_sections.get(model.user_id, [])
            if model.id in lst:
                lst.remove(model.id)
            if index > len(lst):
                raise IndexError("index out of range")
            lst.insert(index, model.id)
            self._user_sections[model.user_id] = lst
            model.index = index
        model.title = section.title
        model.has_subsections = section.has_subsections
        model.has_tasks = section.has_tasks
        if model.parent_id != section.parent_id:
            if model.parent_id in self._children:
                self._children[model.parent_id] = [x for x in self._children[model.parent_id] if x != model.id]
            model.parent_id = section.parent_id
            self._children.setdefault(model.parent_id, []).append(model.id)

    def count_subsections(self, section_id: UUID) -> int:
        return len(self._children.get(section_id, []))

    def get(self, section_id: UUID, with_direct_subsections: bool) -> Section:
        model = self._sections.get(section_id)
        if model is None:
            raise ValueError("section not found")
        tasks = self._get_tasks_for_section(section_id)
        subsections: List[Section] = []
        if with_direct_subsections:
            child_ids = self._children.get(section_id, [])
            child_models = [self._sections[cid] for cid in child_ids]
            child_models.sort(key=lambda m: m.index)
            for cm in child_models:
                subsections.append(cm.to_entity(tasks=self._get_tasks_for_section(cm.id), subsections=[]))
        return model.to_entity(tasks=tasks, subsections=subsections)

    def _get_tasks_for_section(self, section_id: UUID) -> List[Task]:
        ids = self._task_repo._section_tasks.get(section_id, [])
        models = [self._task_repo._tasks[tid] for tid in ids if tid in self._task_repo._tasks]
        models.sort(key=lambda m: m.index)
        return self._task_repo.get_entities(models)

    def construct_sections_tree(self, section_models: List[SectionModel], return_flat: bool) -> List[Section]:
        by_id: Dict[UUID, SectionModel] = {m.id: m for m in section_models}
        children: Dict[Optional[UUID], List[SectionModel]] = {}
        for m in section_models:
            children.setdefault(m.parent_id, []).append(m)
        for k in children:
            children[k].sort(key=lambda m: m.index)

        def build(mid: UUID) -> Section:
            m = by_id[mid]
            subs = [build(ch.id) for ch in children.get(m.id, [])]
            tasks = self._get_tasks_for_section(m.id)
            return m.to_entity(tasks=tasks, subsections=subs)

        roots = children.get(None, [])
        entities = [build(r.id) for r in roots]
        if return_flat:
            flat: List[Section] = []

            def walk(s: Section) -> None:
                flat.append(s)
                for ss in s.subsections:
                    walk(ss)

            for r in entities:
                walk(r)
            return flat
        return entities

    def get_all_without_tasks(self, user_id: UUID, leaves_only: bool, as_tree: bool) -> List[Section]:
        models = [m for m in self._sections.values() if m.user_id == user_id]
        if leaves_only:
            models = [m for m in models if len(self._children.get(m.id, [])) == 0]
        models.sort(key=lambda m: (m.parent_id is not None, m.index))
        if as_tree:
            return self.construct_sections_tree(models, return_flat=False)
        return [m.to_entity(tasks=[], subsections=[]) for m in models]


class SQLAlchemyUserRepository:
    def __init__(self, section_repo: SQLAlchemySectionRepository, task_repo: SQLAlchemyTaskRepository) -> None:
        self._users: Dict[UUID, UserModel] = {}
        self._section_repo = section_repo
        self._task_repo = task_repo

    def verify_user(self, user_id: UUID) -> None:
        if user_id not in self._users:
            raise ValueError("user not found")

    def get_all_users(self) -> List[UserStats]:
        stats: List[UserStats] = []
        for uid, um in self._users.items():
            sections_count = len([s for s in self._section_repo._sections.values() if s.user_id == uid])
            tasks_count = len([t for t in self._task_repo._tasks.values() if t.user_id == uid])
            stats.append(UserStats(user_id=uid, email=um.email, sections_count=sections_count, tasks_count=tasks_count))
        stats.sort(key=lambda s: s.email.lower())
        return stats

    def _add_user(self, user: User) -> User:
        uid = user.id or uuid4()
        added_at = user.added_at or datetime.utcnow()
        model = UserModel(id=uid, email=user.email, added_at=added_at)
        self._users[uid] = model
        return model.to_entity()


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
        self.session: AsyncSession = self.session_factory()
        self.task_repo = SQLAlchemyTaskRepository()
        self.section_repo = SQLAlchemySectionRepository(task_repo=self.task_repo)
        self.user_repo = SQLAlchemyUserRepository(section_repo=self.section_repo, task_repo=self.task_repo)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()