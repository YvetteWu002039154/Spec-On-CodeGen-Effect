from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, Generic, Iterable, List, Literal, Optional, Sequence, Tuple, TypeVar, Union
from uuid import UUID, uuid4
from abc import ABC, abstractmethod


T = TypeVar("T")


class NonNegativeInt(int):
    def __new__(cls, value: int) -> "NonNegativeInt":
        if not isinstance(value, int):
            raise TypeError("NonNegativeInt must be an int")
        if value < 0:
            raise ValueError("NonNegativeInt must be >= 0")
        return int.__new__(cls, value)


class Entity:
    model_config: Dict[str, Any] = {}


@dataclass
class User(Entity):
    email: str
    id: Optional[UUID] = None
    added_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not isinstance(self.email, str) or not self.email.strip():
            raise ValueError("email must be a non-empty string")


@dataclass
class RecurrenceInfo(Entity):
    type: Literal["daily", "weekly", "monthly", "yearly"]
    period: int
    flexible_mode: bool

    def __post_init__(self) -> None:
        if self.type not in ("daily", "weekly", "monthly", "yearly"):
            raise ValueError("Invalid recurrence type")
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
        for name, val in (
            ("s3_file_key", self.s3_file_key),
            ("aes_key_b64", self.aes_key_b64),
            ("aes_iv_b64", self.aes_iv_b64),
        ):
            if not isinstance(val, str) or not val.strip():
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
    attachments: Optional[List[Attachment]] = None

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, UUID):
            raise TypeError("user_id must be UUID")
        if not isinstance(self.section_id, UUID):
            raise TypeError("section_id must be UUID")
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
                    raise TypeError("attachments must contain Attachment")
                if a.task_id != (self.id if self.id is not None else a.task_id):
                    pass
        self.check_recurrence_due_date(self)

    def check_recurrence_due_date(self, values: Any) -> Any:
        rec = getattr(values, "recurrence", None)
        due = getattr(values, "due_to", None)
        if rec is not None and due is None:
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
            raise ValueError("No attachments to remove")
        try:
            self.attachments.remove(attachment)
        except ValueError as e:
            raise ValueError("Attachment not found") from e

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
    subsections: List["Section"] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)
    has_subsections: bool = False
    has_tasks: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, UUID):
            raise TypeError("user_id must be UUID")
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("title must be a non-empty string")
        if self.parent_id is not None and not isinstance(self.parent_id, UUID):
            raise TypeError("parent_id must be UUID or None")
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

    def check_flags(self) -> "Section":
        self.has_subsections = len(self.subsections) > 0
        self.has_tasks = len(self.tasks) > 0
        return self

    @staticmethod
    def create_root_section(user_id: UUID) -> "Section":
        if not isinstance(user_id, UUID):
            raise TypeError("user_id must be UUID")
        return Section(user_id=user_id, title="Root", parent_id=None)

    def is_root(self) -> bool:
        return self.parent_id is None

    def insert_subsection(self, subsection: "Section", index: Optional[NonNegativeInt]) -> None:
        if not isinstance(subsection, Section):
            raise TypeError("subsection must be Section")
        if subsection.user_id != self.user_id:
            raise ValueError("subsection.user_id must match section.user_id")
        if index is None:
            self.subsections.append(subsection)
        else:
            idx = int(index)
            if idx > len(self.subsections):
                raise ValueError("index out of range")
            self.subsections.insert(idx, subsection)
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
        if index is None:
            self.tasks.append(task)
        else:
            idx = int(index)
            if idx > len(self.tasks):
                raise ValueError("index out of range")
            self.tasks.insert(idx, task)
        self.check_flags()

    def remove_task(self, task: Task) -> Task:
        try:
            self.tasks.remove(task)
        except ValueError as e:
            raise ValueError("task not found") from e
        self.check_flags()
        return task

    def shuffle_tasks(self) -> None:
        self.tasks = sorted(self.tasks, key=lambda t: (t.due_to is None, t.due_to or date.max, t.added_at or datetime.min))
        self.check_flags()

    @staticmethod
    def move_task(task_to_move: Task, section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if not isinstance(task_to_move, Task):
            raise TypeError("task_to_move must be Task")
        if not isinstance(section_from, Section) or not isinstance(section_to, Section):
            raise TypeError("section_from/section_to must be Section")
        if section_from.user_id != section_to.user_id or task_to_move.user_id != section_to.user_id:
            raise ValueError("user_id mismatch")
        section_from.remove_task(task_to_move)
        if section_to.id is not None:
            task_to_move.section_id = section_to.id
        section_to.insert_task(task_to_move, index)

    @staticmethod
    def move_section(section: "Section", section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if not isinstance(section, Section):
            raise TypeError("section must be Section")
        if not isinstance(section_from, Section) or not isinstance(section_to, Section):
            raise TypeError("section_from/section_to must be Section")
        if section_from.user_id != section_to.user_id or section.user_id != section_to.user_id:
            raise ValueError("user_id mismatch")
        section_from.remove_subsection(section)
        section.parent_id = section_to.id
        section_to.insert_subsection(section, index)


class AccessTokenModel:
    def __init__(self) -> None:
        pass


class UserStats:
    def __init__(self, user: User, sections_count: int = 0, tasks_count: int = 0) -> None:
        self.user = user
        self.sections_count = sections_count
        self.tasks_count = tasks_count


class UserModel:
    def __init__(self, id: UUID, email: str, added_at: datetime) -> None:
        self.id: UUID = id
        self.email: str = email
        self.added_at: datetime = added_at
        self.sections: List["SectionModel"] = []
        self.tasks: List["TaskModel"] = []

    def to_entity(self) -> User:
        return User(id=self.id, email=self.email, added_at=self.added_at)


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
        self.task: Optional["TaskModel"] = None

    @staticmethod
    def from_entity(attachment: Attachment, index: NonNegativeInt) -> "AttachmentModel":
        if attachment.id is None:
            att_id = uuid4()
        else:
            att_id = attachment.id
        added = attachment.added_at or datetime.utcnow()
        return AttachmentModel(
            id=att_id,
            task_id=attachment.task_id,
            index=int(index),
            s3_file_key=attachment.s3_file_key,
            aes_key_b64=attachment.aes_key_b64,
            aes_iv_b64=attachment.aes_iv_b64,
            added_at=added,
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
        index: int,
        title: str,
        description: Optional[str],
        due_to: Optional[date],
        is_archived: bool,
        is_completed: bool,
        recurrence_type: Optional[str],
        recurrence_period: Optional[int],
        flexible_recurrence_mode: Optional[bool],
        added_at: datetime,
    ) -> None:
        self.id: UUID = id
        self.user_id: UUID = user_id
        self.section_id: UUID = section_id
        self.index: int = index
        self.title: str = title
        self.description: Optional[str] = description
        self.due_to: Optional[date] = due_to
        self.is_archived: bool = is_archived
        self.is_completed: bool = is_completed
        self.recurrence_type: Optional[str] = recurrence_type
        self.recurrence_period: Optional[int] = recurrence_period
        self.flexible_recurrence_mode: Optional[bool] = flexible_recurrence_mode
        self.added_at: datetime = added_at
        self.section: Optional["SectionModel"] = None
        self.user: Optional[UserModel] = None
        self.attachments: List[AttachmentModel] = []

    @staticmethod
    def from_entity(task: Task, index: NonNegativeInt) -> "TaskModel":
        if task.id is None:
            task_id = uuid4()
        else:
            task_id = task.id
        added = task.added_at or datetime.utcnow()
        rec_type: Optional[str] = None
        rec_period: Optional[int] = None
        flex: Optional[bool] = None
        if task.recurrence is not None:
            rec_type = str(task.recurrence.type)
            rec_period = int(task.recurrence.period)
            flex = bool(task.recurrence.flexible_mode)
        return TaskModel(
            id=task_id,
            user_id=task.user_id,
            section_id=task.section_id,
            index=int(index),
            title=task.title,
            description=task.description,
            due_to=task.due_to,
            is_archived=task.is_archived,
            is_completed=task.is_completed,
            recurrence_type=rec_type,
            recurrence_period=rec_period,
            flexible_recurrence_mode=flex,
            added_at=added,
        )

    def to_entity(self, attachments: List[Attachment]) -> Task:
        rec: Optional[RecurrenceInfo] = None
        if self.recurrence_type is not None or self.recurrence_period is not None or self.flexible_recurrence_mode is not None:
            if self.recurrence_type is None or self.recurrence_period is None or self.flexible_recurrence_mode is None:
                raise ValueError("Incomplete recurrence fields")
            rec = RecurrenceInfo(
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
            due_to=self.due_to,
            is_archived=self.is_archived,
            is_completed=self.is_completed,
            recurrence=rec,
            attachments=attachments,
            added_at=self.added_at,
        )


class SectionModel:
    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        index: int,
        title: str,
        parent_id: Optional[UUID],
        has_subsections: bool,
        has_tasks: bool,
        added_at: datetime,
    ) -> None:
        self.id: UUID = id
        self.user_id: UUID = user_id
        self.index: int = index
        self.title: str = title
        self.parent_id: Optional[UUID] = parent_id
        self.has_subsections: bool = has_subsections
        self.has_tasks: bool = has_tasks
        self.added_at: datetime = added_at
        self.tasks: List[TaskModel] = []
        self.user: Optional[UserModel] = None

    @staticmethod
    def from_entity(section: Section, index: NonNegativeInt) -> "SectionModel":
        if section.id is None:
            sec_id = uuid4()
        else:
            sec_id = section.id
        added = section.added_at or datetime.utcnow()
        section.check_flags()
        return SectionModel(
            id=sec_id,
            user_id=section.user_id,
            index=int(index),
            title=section.title,
            parent_id=section.parent_id,
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
            added_at=added,
        )

    def to_entity(self, tasks: List[Task], subsections: List[Section]) -> Section:
        sec = Section(
            id=self.id,
            user_id=self.user_id,
            title=self.title,
            parent_id=self.parent_id,
            tasks=tasks,
            subsections=subsections,
            has_subsections=self.has_subsections,
            has_tasks=self.has_tasks,
            added_at=self.added_at,
        )
        sec.check_flags()
        return sec


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
    def __init__(self, factory: Any = None) -> None:
        self._factory = factory or AsyncSession

    def __call__(self) -> AsyncSession:
        return self._factory()


class SQLAlchemyTaskRepository:
    def __init__(self) -> None:
        self._tasks: Dict[UUID, Tuple[TaskModel, UUID, int]] = {}
        self._attachments: Dict[UUID, AttachmentModel] = {}

    def add(self, task: Task, index: NonNegativeInt) -> None:
        model = TaskModel.from_entity(task, index)
        task.id = model.id
        task.added_at = model.added_at
        self._tasks[model.id] = (model, model.section_id, model.index)
        if task.attachments:
            for i, att in enumerate(task.attachments):
                if att.id is None:
                    att.id = uuid4()
                if att.added_at is None:
                    att.added_at = datetime.utcnow()
                att.task_id = model.id
                am = AttachmentModel.from_entity(att, NonNegativeInt(i))
                self._attachments[am.id] = am
                model.attachments.append(am)

    def get(self, task_id: UUID) -> Task:
        if task_id not in self._tasks:
            raise KeyError("Task not found")
        model, _, _ = self._tasks[task_id]
        return self.get_entity(model)

    def get_entity(self, task_model: TaskModel) -> Task:
        atts = [am.to_entity() for am in sorted(task_model.attachments, key=lambda x: x.index)]
        return task_model.to_entity(atts)

    def get_entities(self, task_models: Sequence[TaskModel]) -> List[Task]:
        return [self.get_entity(m) for m in task_models]

    def remove(self, task: Task) -> None:
        if task.id is None or task.id not in self._tasks:
            raise KeyError("Task not found")
        model, _, _ = self._tasks.pop(task.id)
        for am in list(model.attachments):
            self._attachments.pop(am.id, None)

    def delete_attachment(self, attachment: Attachment) -> None:
        if attachment.id is None:
            raise ValueError("attachment.id is required")
        am = self._attachments.get(attachment.id)
        if am is None:
            raise KeyError("Attachment not found")
        self._attachments.pop(attachment.id, None)
        if am.task_id in self._tasks:
            model, _, _ = self._tasks[am.task_id]
            model.attachments = [x for x in model.attachments if x.id != attachment.id]

    def update_or_create(self, task: Task, index: Optional[NonNegativeInt], must_exist: bool) -> None:
        if task.id is None:
            if must_exist:
                raise KeyError("Task must exist")
            idx = index if index is not None else NonNegativeInt(0)
            self.add(task, idx)
            return

        if task.id not in self._tasks:
            if must_exist:
                raise KeyError("Task not found")
            idx = index if index is not None else NonNegativeInt(0)
            self.add(task, idx)
            return

        model, _, _ = self._tasks[task.id]
        if index is not None:
            model.index = int(index)
        model.user_id = task.user_id
        model.section_id = task.section_id
        model.title = task.title
        model.description = task.description
        model.due_to = task.due_to
        model.is_archived = task.is_archived
        model.is_completed = task.is_completed
        if task.recurrence is None:
            model.recurrence_type = None
            model.recurrence_period = None
            model.flexible_recurrence_mode = None
        else:
            model.recurrence_type = str(task.recurrence.type)
            model.recurrence_period = int(task.recurrence.period)
            model.flexible_recurrence_mode = bool(task.recurrence.flexible_mode)

        if task.attachments is None:
            task.attachments = []
        existing_ids = {am.id for am in model.attachments}
        desired_ids = {a.id for a in task.attachments if a.id is not None}
        for am in list(model.attachments):
            if am.id not in desired_ids:
                self._attachments.pop(am.id, None)
        model.attachments = [am for am in model.attachments if am.id in desired_ids]

        for i, att in enumerate(task.attachments):
            if att.id is None:
                att.id = uuid4()
            if att.added_at is None:
                att.added_at = datetime.utcnow()
            att.task_id = model.id
            if att.id in existing_ids:
                am = self._attachments.get(att.id)
                if am is None:
                    am = AttachmentModel.from_entity(att, NonNegativeInt(i))
                    self._attachments[am.id] = am
                    model.attachments.append(am)
                else:
                    am.index = i
                    am.s3_file_key = att.s3_file_key
                    am.aes_key_b64 = att.aes_key_b64
                    am.aes_iv_b64 = att.aes_iv_b64
            else:
                am = AttachmentModel.from_entity(att, NonNegativeInt(i))
                self._attachments[am.id] = am
                model.attachments.append(am)

        model.attachments.sort(key=lambda x: x.index)
        self._tasks[model.id] = (model, model.section_id, model.index)

    def update_or_create_bulk(self, section_tasks: List[Task]) -> None:
        for i, t in enumerate(section_tasks):
            if t.id is None:
                self.add(t, NonNegativeInt(i))
            else:
                self.update_or_create(t, NonNegativeInt(i), must_exist=False)

    def get_archived_tasks(self, user_id: UUID) -> List[Task]:
        models = [m for (m, _, _) in self._tasks.values() if m.user_id == user_id and m.is_archived]
        models.sort(key=lambda x: (x.added_at, x.index))
        return self.get_entities(models)

    def get_overdue_tasks(self, user_id: UUID) -> List[Task]:
        today = date.today()
        models = [
            m
            for (m, _, _) in self._tasks.values()
            if m.user_id == user_id and not m.is_archived and not m.is_completed and m.due_to is not None and m.due_to < today
        ]
        models.sort(key=lambda x: (x.due_to or date.max, x.index))
        return self.get_entities(models)

    def get_tasks_by_due_to(self, not_before: date, not_after: date, user_id: UUID) -> List[Task]:
        models = [
            m
            for (m, _, _) in self._tasks.values()
            if m.user_id == user_id and m.due_to is not None and not_before <= m.due_to <= not_after
        ]
        models.sort(key=lambda x: (x.due_to or date.max, x.index))
        return self.get_entities(models)

    def search(self, user_id: UUID, query: str) -> List[Task]:
        q = (query or "").strip().lower()
        if not q:
            return []
        models = []
        for (m, _, _) in self._tasks.values():
            if m.user_id != user_id:
                continue
            hay = " ".join([m.title or "", m.description or ""]).lower()
            if q in hay:
                models.append(m)
        models.sort(key=lambda x: (x.added_at, x.index))
        return self.get_entities(models)


class SQLAlchemySectionRepository:
    def __init__(self, task_repo: SQLAlchemyTaskRepository) -> None:
        self._sections: Dict[UUID, Tuple[SectionModel, Optional[UUID], int]] = {}
        self._task_repo = task_repo

    def add(self, section: Section, index: NonNegativeInt) -> None:
        model = SectionModel.from_entity(section, index)
        section.id = model.id
        section.added_at = model.added_at
        self._sections[model.id] = (model, model.parent_id, model.index)

    def update(self, section: Section, index: Optional[NonNegativeInt]) -> None:
        if section.id is None or section.id not in self._sections:
            raise KeyError("Section not found")
        model, _, _ = self._sections[section.id]
        if index is not None:
            model.index = int(index)
        model.user_id = section.user_id
        model.title = section.title
        model.parent_id = section.parent_id
        section.check_flags()
        model.has_subsections = section.has_subsections
        model.has_tasks = section.has_tasks
        self._sections[model.id] = (model, model.parent_id, model.index)

    def count_subsections(self, section_id: UUID) -> int:
        return sum(1 for (_, parent_id, _) in self._sections.values() if parent_id == section_id)

    def get(self, section_id: UUID, with_direct_subsections: bool) -> Section:
        if section_id not in self._sections:
            raise KeyError("Section not found")
        model, _, _ = self._sections[section_id]
        tasks_models = [m for (m, _, _) in self._task_repo._tasks.values() if m.section_id == section_id]
        tasks_models.sort(key=lambda x: x.index)
        tasks = self._task_repo.get_entities(tasks_models)
        subsections: List[Section] = []
        if with_direct_subsections:
            child_models = [sm for (sm, parent_id, _) in self._sections.values() if parent_id == section_id]
            child_models.sort(key=lambda x: x.index)
            for cm in child_models:
                subsections.append(cm.to_entity(tasks=[], subsections=[]))
        return model.to_entity(tasks=tasks, subsections=subsections)

    def construct_sections_tree(self, section_models: List[SectionModel], return_flat: bool) -> List[Section]:
        models_by_id: Dict[UUID, SectionModel] = {m.id: m for m in section_models}
        children: Dict[Optional[UUID], List[SectionModel]] = {}
        for m in section_models:
            children.setdefault(m.parent_id, []).append(m)
        for lst in children.values():
            lst.sort(key=lambda x: x.index)

        def build(m: SectionModel) -> Section:
            task_models = [tm for (tm, _, _) in self._task_repo._tasks.values() if tm.section_id == m.id]
            task_models.sort(key=lambda x: x.index)
            tasks = self._task_repo.get_entities(task_models)
            subs = [build(ch) for ch in children.get(m.id, [])]
            return m.to_entity(tasks=tasks if not return_flat else [], subsections=subs if not return_flat else [])

        roots = children.get(None, [])
        built = [build(r) for r in roots]
        if return_flat:
            flat: List[Section] = []

            def walk(s: Section) -> None:
                flat.append(s)
                for ch in s.subsections:
                    walk(ch)

            for r in built:
                walk(r)
            return flat
        return built

    def get_all_without_tasks(self, user_id: UUID, leaves_only: bool, as_tree: bool) -> List[Section]:
        models = [m for (m, _, _) in self._sections.values() if m.user_id == user_id]
        if leaves_only:
            models = [m for m in models if self.count_subsections(m.id) == 0]
        models.sort(key=lambda x: (x.parent_id is not None, x.parent_id or UUID(int=0), x.index))
        if as_tree:
            return self.construct_sections_tree(models, return_flat=False)
        return [m.to_entity(tasks=[], subsections=[]) for m in models]


class SQLAlchemyUserRepository:
    def __init__(self) -> None:
        self._users: Dict[UUID, UserModel] = {}

    def add_user(self, user: User) -> None:
        if user.id is None:
            user.id = uuid4()
        if user.added_at is None:
            user.added_at = datetime.utcnow()
        self._users[user.id] = UserModel(id=user.id, email=user.email, added_at=user.added_at)

    def verify_user(self, user_id: UUID) -> None:
        if user_id not in self._users:
            raise KeyError("User not found")

    def get_all_users(self) -> List[UserStats]:
        return [UserStats(user=um.to_entity(), sections_count=0, tasks_count=0) for um in self._users.values()]


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
        self.user_repo = SQLAlchemyUserRepository()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()