from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Generic, List, Literal, Optional, Sequence, TypeVar
from uuid import UUID, uuid4
from abc import ABC, abstractmethod


NonNegativeInt = int


def _ensure_non_negative_int(value: int, name: str) -> int:
    if not isinstance(value, int):
        raise TypeError(f"{name} must be int")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _insert_at_index(lst: list, item: Any, index: Optional[NonNegativeInt]) -> None:
    if index is None:
        lst.append(item)
        return
    _ensure_non_negative_int(index, "index")
    if index > len(lst):
        raise IndexError("index out of range")
    lst.insert(index, item)


def _remove_first_identity(lst: list, item: Any) -> None:
    for i, x in enumerate(lst):
        if x is item:
            del lst[i]
            return
    raise ValueError("item not found")


def _move_between_lists(
    item: Any,
    src: list,
    dst: list,
    index: NonNegativeInt,
) -> None:
    _ensure_non_negative_int(index, "index")
    if index > len(dst):
        raise IndexError("index out of range")
    _remove_first_identity(src, item)
    dst.insert(index, item)


class Entity:
    model_config: Dict[str, Any] = {"arbitrary_types_allowed": True}


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
            raise ValueError("Invalid recurrence type")
        if not isinstance(self.period, int) or self.period <= 0:
            raise ValueError("period must be a positive integer")
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
        if not isinstance(self.title, str) or not self.title:
            raise ValueError("title must be a non-empty string")
        if self.attachments is None:
            self.attachments = []
        if self.recurrence is not None:
            self.check_recurrence_due_date(None)

    def check_recurrence_due_date(self, values: Any) -> Any:
        if self.recurrence is not None and self.due_to is None:
            raise ValueError("due_to must be set when recurrence is set")
        return values

    def add_attachment(self, attachment: Attachment) -> None:
        if attachment.task_id != (self.id if self.id is not None else self.section_id):
            if self.id is not None and attachment.task_id != self.id:
                raise ValueError("attachment.task_id must match task.id")
        if self.attachments is None:
            self.attachments = []
        self.attachments.append(attachment)

    def remove_attachment(self, attachment: Attachment) -> None:
        if self.attachments is None:
            raise ValueError("No attachments")
        _remove_first_identity(self.attachments, attachment)

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


@dataclass
class Section(Entity):
    title: str
    user_id: UUID
    id: Optional[UUID] = None
    added_at: Optional[datetime] = None
    parent_id: Optional[UUID] = None
    subsections: List["Section"] = None  # type: ignore[assignment]
    tasks: List[Task] = None  # type: ignore[assignment]
    has_subsections: bool = False
    has_tasks: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, UUID):
            raise TypeError("user_id must be UUID")
        if not isinstance(self.title, str) or not self.title:
            raise ValueError("title must be a non-empty string")
        if self.subsections is None:
            self.subsections = []
        if self.tasks is None:
            self.tasks = []
        self.check_flags()

    def check_flags(self) -> "Section":
        self.has_subsections = len(self.subsections) > 0
        self.has_tasks = len(self.tasks) > 0
        return self

    @classmethod
    def create_root_section(cls, user_id: UUID) -> "Section":
        return cls(title="Root", user_id=user_id, parent_id=None)

    def is_root(self) -> bool:
        return self.parent_id is None

    def insert_subsection(self, subsection: "Section", index: Optional[NonNegativeInt]) -> None:
        if subsection.user_id != self.user_id:
            raise ValueError("subsection.user_id must match section.user_id")
        subsection.parent_id = self.id
        _insert_at_index(self.subsections, subsection, index)
        self.check_flags()

    def remove_subsection(self, subsection: "Section") -> "Section":
        _remove_first_identity(self.subsections, subsection)
        self.check_flags()
        return subsection

    def insert_task(self, task: Task, index: Optional[NonNegativeInt]) -> None:
        if task.user_id != self.user_id:
            raise ValueError("task.user_id must match section.user_id")
        task.section_id = self.id if self.id is not None else task.section_id
        _insert_at_index(self.tasks, task, index)
        self.check_flags()

    def remove_task(self, task: Task) -> Task:
        _remove_first_identity(self.tasks, task)
        self.check_flags()
        return task

    def shuffle_tasks(self) -> None:
        self.tasks = [t for t in self.tasks if not t.is_archived] + [t for t in self.tasks if t.is_archived]
        self.check_flags()

    @staticmethod
    def move_task(task_to_move: Task, section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if section_from.user_id != section_to.user_id or task_to_move.user_id != section_to.user_id:
            raise ValueError("user_id mismatch")
        _move_between_lists(task_to_move, section_from.tasks, section_to.tasks, index)
        task_to_move.section_id = section_to.id if section_to.id is not None else task_to_move.section_id
        section_from.check_flags()
        section_to.check_flags()

    @staticmethod
    def move_section(section: "Section", section_from: "Section", section_to: "Section", index: NonNegativeInt) -> None:
        if section_from.user_id != section_to.user_id or section.user_id != section_to.user_id:
            raise ValueError("user_id mismatch")
        _move_between_lists(section, section_from.subsections, section_to.subsections, index)
        section.parent_id = section_to.id
        section_from.check_flags()
        section_to.check_flags()


T = TypeVar("T")


class Mapped(Generic[T]):
    def __init__(self, default: Optional[T] = None) -> None:
        self.default = default


class AccessTokenModel:
    pass


@dataclass
class UserStats:
    user_id: UUID
    email: str
    sections_count: int
    tasks_count: int


class UserModel:
    added_at: Mapped[datetime]
    sections: Any
    tasks: Any

    def __init__(self, id: UUID, email: str, added_at: Optional[datetime] = None) -> None:
        self.id: UUID = id
        self.email: str = email
        self.added_at = Mapped(added_at or datetime.utcnow())
        self.sections = []
        self.tasks = []

    def to_entity(self) -> User:
        return User(id=self.id, email=self.email, added_at=self.added_at.default)


class SectionModel:
    added_at: Mapped[datetime]
    has_subsections: Mapped[bool]
    has_tasks: Mapped[bool]
    id: Mapped[UUID]
    index: Mapped[int]
    parent_id: Mapped[Optional["GUID"]]
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
        parent_id: Optional[UUID],
        added_at: Optional[datetime] = None,
        has_subsections: bool = False,
        has_tasks: bool = False,
    ) -> None:
        self.id = Mapped(id)
        self.user_id = Mapped(user_id)
        self.title = Mapped(title)
        self.index = Mapped(index)
        self.parent_id = Mapped(parent_id)
        self.added_at = Mapped(added_at or datetime.utcnow())
        self.has_subsections = Mapped(has_subsections)
        self.has_tasks = Mapped(has_tasks)
        self.tasks = Mapped([])
        self.user = None

    @staticmethod
    def from_entity(section: Section, index: NonNegativeInt) -> "SectionModel":
        _ensure_non_negative_int(index, "index")
        sid = section.id or uuid4()
        return SectionModel(
            id=sid,
            user_id=section.user_id,
            title=section.title,
            index=index,
            parent_id=section.parent_id,
            added_at=section.added_at or datetime.utcnow(),
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
        )

    def to_entity(self, tasks: List[Task], subsections: List[Section]) -> Section:
        return Section(
            id=self.id.default,
            user_id=self.user_id.default,
            title=self.title.default,
            parent_id=self.parent_id.default,
            added_at=self.added_at.default,
            tasks=tasks,
            subsections=subsections,
            has_tasks=self.has_tasks.default,
            has_subsections=self.has_subsections.default,
        ).check_flags()


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
        self.id = Mapped(id)
        self.user_id = Mapped(user_id)
        self.section_id = Mapped(section_id)
        self.title = Mapped(title)
        self.index = Mapped(index)
        self.added_at = Mapped(added_at or datetime.utcnow())
        self.description = Mapped(description)
        self.due_to = Mapped(due_to)
        self.is_archived = Mapped(is_archived)
        self.is_completed = Mapped(is_completed)
        self.recurrence_type = Mapped(recurrence_type)
        self.recurrence_period = Mapped(recurrence_period)
        self.flexible_recurrence_mode = Mapped(flexible_recurrence_mode)
        self.attachments = []
        self.section = None
        self.user = None

    @staticmethod
    def from_entity(task: Task, index: NonNegativeInt) -> "TaskModel":
        _ensure_non_negative_int(index, "index")
        tid = task.id or uuid4()
        recurrence_type = task.recurrence.type if task.recurrence else None
        recurrence_period = task.recurrence.period if task.recurrence else None
        flexible_mode = task.recurrence.flexible_mode if task.recurrence else None
        return TaskModel(
            id=tid,
            user_id=task.user_id,
            section_id=task.section_id,
            title=task.title,
            index=index,
            added_at=task.added_at or datetime.utcnow(),
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
        if self.recurrence_type.default is not None:
            if self.recurrence_period.default is None or self.flexible_recurrence_mode.default is None:
                raise ValueError("Incomplete recurrence fields")
            recurrence = RecurrenceInfo(
                type=self.recurrence_type.default,  # type: ignore[arg-type]
                period=self.recurrence_period.default,
                flexible_mode=self.flexible_recurrence_mode.default,
            )
        return Task(
            id=self.id.default,
            user_id=self.user_id.default,
            section_id=self.section_id.default,
            title=self.title.default,
            added_at=self.added_at.default,
            description=self.description.default,
            due_to=self.due_to.default,
            is_archived=self.is_archived.default,
            is_completed=self.is_completed.default,
            recurrence=recurrence,
            attachments=attachments,
        )


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
        self.id = Mapped(id)
        self.task_id = Mapped(task_id)
        self.s3_file_key = Mapped(s3_file_key)
        self.aes_key_b64 = Mapped(aes_key_b64)
        self.aes_iv_b64 = Mapped(aes_iv_b64)
        self.index = Mapped(index)
        self.added_at = Mapped(added_at or datetime.utcnow())
        self.task = None

    @staticmethod
    def from_entity(attachment: Attachment, index: NonNegativeInt) -> "AttachmentModel":
        _ensure_non_negative_int(index, "index")
        aid = attachment.id or uuid4()
        return AttachmentModel(
            id=aid,
            task_id=attachment.task_id,
            s3_file_key=attachment.s3_file_key,
            aes_key_b64=attachment.aes_key_b64,
            aes_iv_b64=attachment.aes_iv_b64,
            index=index,
            added_at=attachment.added_at or datetime.utcnow(),
        )

    def to_entity(self) -> Attachment:
        return Attachment(
            id=self.id.default,
            task_id=self.task_id.default,
            s3_file_key=self.s3_file_key.default,
            aes_key_b64=self.aes_key_b64.default,
            aes_iv_b64=self.aes_iv_b64.default,
            added_at=self.added_at.default,
        )


GUID = UUID


class AsyncSession:
    def __init__(self) -> None:
        self._committed = False
        self._rolled_back = False

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        self._rolled_back = True


class async_sessionmaker:
    def __init__(self, factory: Optional[Any] = None) -> None:
        self._factory = factory or (lambda: AsyncSession())

    def __call__(self) -> AsyncSession:
        return self._factory()


class SQLAlchemySectionRepository:
    def __init__(self) -> None:
        self._sections_by_user: Dict[UUID, List[Section]] = {}
        self._sections_by_id: Dict[UUID, Section] = {}

    def add(self, section: Section, index: NonNegativeInt) -> None:
        _ensure_non_negative_int(index, "index")
        if section.id is None:
            section.id = uuid4()
        if section.added_at is None:
            section.added_at = datetime.utcnow()
        user_sections = self._sections_by_user.setdefault(section.user_id, [])
        if index > len(user_sections):
            raise IndexError("index out of range")
        user_sections.insert(index, section)
        self._sections_by_id[section.id] = section

    def update(self, section: Section, index: Optional[NonNegativeInt]) -> None:
        if section.id is None or section.id not in self._sections_by_id:
            raise KeyError("section not found")
        existing = self._sections_by_id[section.id]
        existing.title = section.title
        existing.parent_id = section.parent_id
        existing.subsections = section.subsections
        existing.tasks = section.tasks
        existing.check_flags()
        if index is not None:
            _ensure_non_negative_int(index, "index")
            user_sections = self._sections_by_user.get(existing.user_id, [])
            for i, s in enumerate(user_sections):
                if s.id == existing.id:
                    del user_sections[i]
                    break
            else:
                raise KeyError("section not found in user list")
            if index > len(user_sections):
                raise IndexError("index out of range")
            user_sections.insert(index, existing)

    def get(self, section_id: UUID, with_direct_subsections: bool) -> Section:
        if section_id not in self._sections_by_id:
            raise KeyError("section not found")
        section = self._sections_by_id[section_id]
        if with_direct_subsections:
            return section
        return Section(
            id=section.id,
            user_id=section.user_id,
            title=section.title,
            parent_id=section.parent_id,
            added_at=section.added_at,
            subsections=[],
            tasks=section.tasks,
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
        ).check_flags()

    def count_subsections(self, section_id: UUID) -> int:
        section = self.get(section_id, with_direct_subsections=True)
        return len(section.subsections)

    def construct_sections_tree(self, section_models: List[SectionModel], return_flat: bool) -> List[Section]:
        sections: List[Section] = []
        for sm in section_models:
            sections.append(sm.to_entity(tasks=[], subsections=[]))
        if return_flat:
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
        for r in roots:
            r.check_flags()
        return roots

    def get_all_without_tasks(self, user_id: UUID, leaves_only: bool, as_tree: bool) -> List[Section]:
        sections = list(self._sections_by_user.get(user_id, []))
        if leaves_only:
            sections = [s for s in sections if len(s.subsections) == 0]
        if not as_tree:
            return [Section(id=s.id, user_id=s.user_id, title=s.title, parent_id=s.parent_id, added_at=s.added_at, subsections=[], tasks=[], has_subsections=s.has_subsections, has_tasks=False).check_flags() for s in sections]
        models = [SectionModel.from_entity(s, i) for i, s in enumerate(sections)]
        return self.construct_sections_tree(models, return_flat=False)


class SQLAlchemyTaskRepository:
    def __init__(self) -> None:
        self._tasks_by_user: Dict[UUID, List[Task]] = {}
        self._tasks_by_id: Dict[UUID, Task] = {}

    def add(self, task: Task, index: NonNegativeInt) -> None:
        _ensure_non_negative_int(index, "index")
        if task.id is None:
            task.id = uuid4()
        if task.added_at is None:
            task.added_at = datetime.utcnow()
        user_tasks = self._tasks_by_user.setdefault(task.user_id, [])
        if index > len(user_tasks):
            raise IndexError("index out of range")
        user_tasks.insert(index, task)
        self._tasks_by_id[task.id] = task

    def remove(self, task: Task) -> None:
        if task.id is None or task.id not in self._tasks_by_id:
            raise KeyError("task not found")
        existing = self._tasks_by_id.pop(task.id)
        user_tasks = self._tasks_by_user.get(existing.user_id, [])
        for i, t in enumerate(user_tasks):
            if t.id == existing.id:
                del user_tasks[i]
                break

    def get(self, task_id: UUID) -> Task:
        if task_id not in self._tasks_by_id:
            raise KeyError("task not found")
        return self._tasks_by_id[task_id]

    def update_or_create(self, task: Task, index: Optional[NonNegativeInt], must_exist: bool) -> None:
        if task.id is None:
            if must_exist:
                raise KeyError("task must exist")
            self.add(task, index if index is not None else len(self._tasks_by_user.get(task.user_id, [])))
            return
        if task.id not in self._tasks_by_id:
            if must_exist:
                raise KeyError("task not found")
            self.add(task, index if index is not None else len(self._tasks_by_user.get(task.user_id, [])))
            return
        existing = self._tasks_by_id[task.id]
        existing.title = task.title
        existing.description = task.description
        existing.content = task.content
        existing.due_to = task.due_to
        existing.is_archived = task.is_archived
        existing.is_completed = task.is_completed
        existing.recurrence = task.recurrence
        existing.section_id = task.section_id
        existing.attachments = task.attachments
        if index is not None:
            _ensure_non_negative_int(index, "index")
            user_tasks = self._tasks_by_user.get(existing.user_id, [])
            for i, t in enumerate(user_tasks):
                if t.id == existing.id:
                    del user_tasks[i]
                    break
            if index > len(user_tasks):
                raise IndexError("index out of range")
            user_tasks.insert(index, existing)

    def update_or_create_bulk(self, section_tasks: List[Task]) -> None:
        for i, t in enumerate(section_tasks):
            self.update_or_create(t, index=i, must_exist=False)

    def get_entity(self, task_model: TaskModel) -> Task:
        attachments: List[Attachment] = []
        if isinstance(task_model.attachments, list):
            for am in task_model.attachments:
                if isinstance(am, AttachmentModel):
                    attachments.append(am.to_entity())
        return task_model.to_entity(attachments=attachments)

    def get_entities(self, task_models: Sequence[TaskModel]) -> List[Task]:
        return [self.get_entity(tm) for tm in task_models]

    def delete_attachment(self, attachment: Attachment) -> None:
        if attachment.task_id not in self._tasks_by_id:
            raise KeyError("task not found")
        task = self._tasks_by_id[attachment.task_id]
        if task.attachments is None:
            return
        for i, a in enumerate(task.attachments):
            if a is attachment or (a.id is not None and attachment.id is not None and a.id == attachment.id):
                del task.attachments[i]
                return

    def get_archived_tasks(self, user_id: UUID) -> List[Task]:
        return [t for t in self._tasks_by_user.get(user_id, []) if t.is_archived]

    def get_overdue_tasks(self, user_id: UUID) -> List[Task]:
        today = date.today()
        return [
            t
            for t in self._tasks_by_user.get(user_id, [])
            if (t.due_to is not None and t.due_to < today and not t.is_completed and not t.is_archived)
        ]

    def get_tasks_by_due_to(self, not_before: date, not_after: date, user_id: UUID) -> List[Task]:
        return [
            t
            for t in self._tasks_by_user.get(user_id, [])
            if t.due_to is not None and not_before <= t.due_to <= not_after
        ]

    def search(self, user_id: UUID, query: str) -> List[Task]:
        q = (query or "").strip().lower()
        if not q:
            return []
        res: List[Task] = []
        for t in self._tasks_by_user.get(user_id, []):
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


class SQLAlchemyUserRepository:
    def __init__(self) -> None:
        self._users: Dict[UUID, User] = {}
        self._sections_repo: Optional[SQLAlchemySectionRepository] = None
        self._tasks_repo: Optional[SQLAlchemyTaskRepository] = None

    def bind_repos(self, sections_repo: SQLAlchemySectionRepository, tasks_repo: SQLAlchemyTaskRepository) -> None:
        self._sections_repo = sections_repo
        self._tasks_repo = tasks_repo

    def add(self, user: User) -> None:
        if user.id is None:
            user.id = uuid4()
        if user.added_at is None:
            user.added_at = datetime.utcnow()
        self._users[user.id] = user

    def verify_user(self, user_id: UUID) -> None:
        if user_id not in self._users:
            raise KeyError("user not found")

    def get_all_users(self) -> List[UserStats]:
        stats: List[UserStats] = []
        for uid, u in self._users.items():
            sections_count = 0
            tasks_count = 0
            if self._sections_repo is not None:
                sections_count = len(self._sections_repo._sections_by_user.get(uid, []))
            if self._tasks_repo is not None:
                tasks_count = len(self._tasks_repo._tasks_by_user.get(uid, []))
            stats.append(UserStats(user_id=uid, email=u.email, sections_count=sections_count, tasks_count=tasks_count))
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