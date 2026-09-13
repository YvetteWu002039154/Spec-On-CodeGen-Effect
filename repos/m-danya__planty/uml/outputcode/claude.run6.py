from __future__ import annotations

import random
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Literal, Optional, Sequence
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, model_validator


# ---------------------------------------------------------------------------
# Domain layer
# ---------------------------------------------------------------------------

class Entity(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class RecurrenceInfo(Entity):
    type: Literal["days", "weeks", "months", "years"]
    period: int
    flexible_mode: bool = False


class Attachment(Entity):
    id: Optional[UUID] = None
    task_id: UUID
    s3_file_key: str
    aes_key_b64: str
    aes_iv_b64: str
    added_at: Optional[datetime] = None


class Task(Entity):
    id: Optional[UUID] = None
    section_id: UUID
    user_id: UUID
    title: str
    content: Optional[str] = None
    description: Optional[str] = None
    due_to: Optional[date] = None
    is_completed: bool = False
    is_archived: bool = False
    recurrence: Optional[RecurrenceInfo] = None
    attachments: Optional[list[Attachment]] = None
    added_at: Optional[datetime] = None

    @model_validator(mode="after")
    def check_recurrence_due_date(self) -> "Task":
        if self.recurrence is not None and self.due_to is None:
            raise ValueError("A task with recurrence must have a due_to date.")
        return self

    def add_attachment(self, attachment: Attachment) -> None:
        if self.attachments is None:
            self.attachments = []
        self.attachments.append(attachment)

    def remove_attachment(self, attachment: Attachment) -> None:
        if self.attachments is not None:
            self.attachments = [a for a in self.attachments if a.id != attachment.id]

    def mark_completed(self, auto_archive: bool = False) -> None:
        if self.recurrence is not None and self.due_to is not None:
            from datetime import timedelta
            period_map = {
                "days": timedelta(days=self.recurrence.period),
                "weeks": timedelta(weeks=self.recurrence.period),
            }
            if self.recurrence.type in ("days", "weeks"):
                delta = period_map[self.recurrence.type]
                if self.recurrence.flexible_mode:
                    self.due_to = date.today() + delta
                else:
                    self.due_to = self.due_to + delta
            elif self.recurrence.type == "months":
                month = self.due_to.month + self.recurrence.period
                year = self.due_to.year + (month - 1) // 12
                month = (month - 1) % 12 + 1
                self.due_to = self.due_to.replace(year=year, month=month)
            elif self.recurrence.type == "years":
                self.due_to = self.due_to.replace(
                    year=self.due_to.year + self.recurrence.period
                )
        else:
            self.is_completed = True
            if auto_archive:
                self.is_archived = True

    def toggle_completed(self, auto_archive: bool = False) -> None:
        if self.is_completed:
            self.is_completed = False
        else:
            self.mark_completed(auto_archive=auto_archive)

    def archive(self) -> None:
        self.is_archived = True

    def unarchive(self) -> None:
        self.is_archived = False

    def toggle_archived(self) -> None:
        self.is_archived = not self.is_archived


class Section(Entity):
    id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    user_id: UUID
    title: str
    tasks: list[Task] = []
    subsections: list["Section"] = []
    has_tasks: bool = False
    has_subsections: bool = False
    added_at: Optional[datetime] = None

    @model_validator(mode="after")
    def check_flags(self) -> "Section":
        self.has_tasks = len(self.tasks) > 0
        self.has_subsections = len(self.subsections) > 0
        return self

    @classmethod
    def create_root_section(cls, user_id: UUID) -> "Section":
        return cls(
            id=uuid4(),
            user_id=user_id,
            title="root",
            parent_id=None,
        )

    def is_root(self) -> bool:
        return self.parent_id is None

    def insert_task(self, task: Task, index: Optional[int] = None) -> None:
        if index is None:
            self.tasks.append(task)
        else:
            self.tasks.insert(index, task)
        self.has_tasks = True

    def remove_task(self, task: Task) -> Task:
        self.tasks = [t for t in self.tasks if t.id != task.id]
        self.has_tasks = len(self.tasks) > 0
        return task

    def insert_subsection(self, subsection: "Section", index: Optional[int] = None) -> None:
        if index is None:
            self.subsections.append(subsection)
        else:
            self.subsections.insert(index, subsection)
        self.has_subsections = True

    def remove_subsection(self, subsection: "Section") -> "Section":
        self.subsections = [s for s in self.subsections if s.id != subsection.id]
        self.has_subsections = len(self.subsections) > 0
        return subsection

    def shuffle_tasks(self) -> None:
        random.shuffle(self.tasks)

    @staticmethod
    def move_task(
        task_to_move: Task,
        section_from: "Section",
        section_to: "Section",
        index: int,
    ) -> None:
        section_from.remove_task(task_to_move)
        section_to.insert_task(task_to_move, index)

    @staticmethod
    def move_section(
        section: "Section",
        section_from: "Section",
        section_to: "Section",
        index: int,
    ) -> None:
        section_from.remove_subsection(section)
        section_to.insert_subsection(section, index)


class User(Entity):
    id: Optional[UUID] = None
    email: str
    added_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Infrastructure – models (ORM-like plain classes, no SQLAlchemy dependency)
# ---------------------------------------------------------------------------

class UserStats:
    def __init__(self, user_id: UUID, email: str, task_count: int = 0):
        self.user_id = user_id
        self.email = email
        self.task_count = task_count


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
    ):
        self.id = id
        self.task_id = task_id
        self.s3_file_key = s3_file_key
        self.aes_key_b64 = aes_key_b64
        self.aes_iv_b64 = aes_iv_b64
        self.added_at = added_at
        self.index = index
        self.task = None

    @classmethod
    def from_entity(cls, attachment: Attachment, index: int) -> "AttachmentModel":
        return cls(
            id=attachment.id or uuid4(),
            task_id=attachment.task_id,
            s3_file_key=attachment.s3_file_key,
            aes_key_b64=attachment.aes_key_b64,
            aes_iv_b64=attachment.aes_iv_b64,
            added_at=attachment.added_at or datetime.utcnow(),
            index=index,
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
        section_id: UUID,
        user_id: UUID,
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
    ):
        self.id = id
        self.section_id = section_id
        self.user_id = user_id
        self.title = title
        self.description = description
        self.due_to = due_to
        self.is_completed = is_completed
        self.is_archived = is_archived
        self.recurrence_type = recurrence_type
        self.recurrence_period = recurrence_period
        self.flexible_recurrence_mode = flexible_recurrence_mode
        self.added_at = added_at
        self.index = index
        self.attachments: list[AttachmentModel] = []
        self.section = None
        self.user = None

    @classmethod
    def from_entity(cls, task: Task, index: int) -> "TaskModel":
        recurrence_type = None
        recurrence_period = None
        flexible_recurrence_mode = None
        if task.recurrence is not None:
            recurrence_type = task.recurrence.type
            recurrence_period = task.recurrence.period
            flexible_recurrence_mode = task.recurrence.flexible_mode

        return cls(
            id=task.id or uuid4(),
            section_id=task.section_id,
            user_id=task.user_id,
            title=task.title,
            description=task.description,
            due_to=task.due_to,
            is_completed=task.is_completed,
            is_archived=task.is_archived,
            recurrence_type=recurrence_type,
            recurrence_period=recurrence_period,
            flexible_recurrence_mode=flexible_recurrence_mode,
            added_at=task.added_at or datetime.utcnow(),
            index=index,
        )

    def to_entity(self, attachments: list[Attachment]) -> Task:
        recurrence = None
        if self.recurrence_type is not None and self.recurrence_period is not None:
            recurrence = RecurrenceInfo(
                type=self.recurrence_type,
                period=self.recurrence_period,
                flexible_mode=self.flexible_recurrence_mode or False,
            )
        return Task(
            id=self.id,
            section_id=self.section_id,
            user_id=self.user_id,
            title=self.title,
            description=self.description,
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
        parent_id: Optional[UUID],
        has_tasks: bool,
        has_subsections: bool,
        added_at: datetime,
        index: int,
    ):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.parent_id = parent_id
        self.has_tasks = has_tasks
        self.has_subsections = has_subsections
        self.added_at = added_at
        self.index = index
        self.tasks: list[TaskModel] = []
        self.user = None

    @classmethod
    def from_entity(cls, section: Section, index: int) -> "SectionModel":
        return cls(
            id=section.id or uuid4(),
            user_id=section.user_id,
            title=section.title,
            parent_id=section.parent_id,
            has_tasks=section.has_tasks,
            has_subsections=section.has_subsections,
            added_at=section.added_at or datetime.utcnow(),
            index=index,
        )

    def to_entity(self, tasks: list[Task], subsections: list[Section]) -> Section:
        return Section(
            id=self.id,
            user_id=self.user_id,
            title=self.title,
            parent_id=self.parent_id,
            has_tasks=self.has_tasks,
            has_subsections=self.has_subsections,
            added_at=self.added_at,
            tasks=tasks,
            subsections=subsections,
        )


class UserModel:
    def __init__(self, id: UUID, email: str, added_at: datetime):
        self.id = id
        self.email = email
        self.added_at = added_at
        self.sections: list[SectionModel] = []
        self.tasks: list[TaskModel] = []

    def to_entity(self) -> User:
        return User(
            id=self.id,
            email=self.email,
            added_at=self.added_at,
        )


class AccessTokenModel:
    def __init__(self, token: str, user_id: UUID, expires_at: datetime):
        self.token = token
        self.user_id = user_id
        self.expires_at = expires_at


# ---------------------------------------------------------------------------
# Infrastructure – repositories
# ---------------------------------------------------------------------------

class SQLAlchemyTaskRepository:
    def __init__(self, session: Any):
        self._session = session
        self._task_store: dict[UUID, TaskModel] = {}
        self._attachment_store: dict[UUID, AttachmentModel] = {}

    def add(self, task: Task, index: int) -> None:
        model = TaskModel.from_entity(task, index)
        if task.attachments:
            for i, att in enumerate(task.attachments):
                att_model = AttachmentModel.from_entity(att, i)
                model.attachments.append(att_model)
                self._attachment_store[att_model.id] = att_model
        self._task_store[model.id] = model

    def get(self, task_id: UUID) -> Task:
        model = self._task_store[task_id]
        return self.get_entity(model)

    def get_entity(self, task_model: TaskModel) -> Task:
        attachments = [a.to_entity() for a in task_model.attachments]
        return task_model.to_entity(attachments)

    def get_entities(self, task_models: Sequence[TaskModel]) -> list[Task]:
        return [self.get_entity(m) for m in task_models]

    def remove(self, task: Task) -> None:
        if task.id in self._task_store:
            del self._task_store[task.id]

    def update_or_create(
        self,
        task: Task,
        index: Optional[int] = None,
        must_exist: bool = False,
    ) -> None:
        if task.id in self._task_store:
            existing = self._task_store[task.id]
            idx = index if index is not None else existing.index
            updated = TaskModel.from_entity(task, idx)
            updated.attachments = existing.attachments
            self._task_store[task.id] = updated
        else:
            if must_exist:
                raise KeyError(f"Task {task.id} does not exist.")
            self.add(task, index or 0)

    def update_or_create_bulk(self, section_tasks: list[Task]) -> None:
        for i, task in enumerate(section_tasks):
            self.update_or_create(task, index=i)

    def delete_attachment(self, attachment: Attachment) -> None:
        if attachment.id in self._attachment_store:
            del self._attachment_store[attachment.id]
        for model in self._task_store.values():
            model.attachments = [
                a for a in model.attachments if a.id != attachment.id
            ]

    def get_archived_tasks(self, user_id: UUID) -> list[Task]:
        return [
            self.get_entity(m)
            for m in self._task_store.values()
            if m.user_id == user_id and m.is_archived
        ]

    def get_overdue_tasks(self, user_id: UUID) -> list[Task]:
        today = date.today()
        return [
            self.get_entity(m)
            for m in self._task_store.values()
            if m.user_id == user_id
            and m.due_to is not None
            and m.due_to < today
            and not m.is_completed
            and not m.is_archived
        ]

    def get_tasks_by_due_to(
        self, not_before: date, not_after: date, user_id: UUID
    ) -> list[Task]:
        return [
            self.get_entity(m)
            for m in self._task_store.values()
            if m.user_id == user_id
            and m.due_to is not None
            and not_before <= m.due_to <= not_after
        ]

    def search(self, user_id: UUID, query: str) -> list[Task]:
        q = query.lower()
        return [
            self.get_entity(m)
            for m in self._task_store.values()
            if m.user_id == user_id and q in m.title.lower()
        ]


class SQLAlchemySectionRepository:
    def __init__(self, session: Any):
        self._session = session
        self._section_store: dict[UUID, SectionModel] = {}

    def add(self, section: Section, index: int) -> None:
        model = SectionModel.from_entity(section, index)
        self._section_store[model.id] = model

    def get(self, section_id: UUID, with_direct_subsections: bool = False) -> Section:
        model = self._section_store[section_id]
        subsections: list[Section] = []
        if with_direct_subsections:
            subsections = [
                self._section_store[sid].to_entity([], [])
                for sid, m in self._section_store.items()
                if m.parent_id == section_id
            ]
        return model.to_entity([], subsections)

    def count_subsections(self, section_id: UUID) -> int:
        return sum(
            1 for m in self._section_store.values() if m.parent_id == section_id
        )

    def update(self, section: Section, index: Optional[int] = None) -> None:
        if section.id not in self._section_store:
            raise KeyError(f"Section {section.id} does not exist.")
        existing = self._section_store[section.id]
        idx = index if index is not None else existing.index
        updated = SectionModel.from_entity(section, idx)
        updated.tasks = existing.tasks
        self._section_store[section.id] = updated

    def construct_sections_tree(
        self, section_models: list[SectionModel], return_flat: bool
    ) -> list[Section]:
        id_to_section: dict[UUID, Section] = {}
        for m in section_models:
            id_to_section[m.id] = m.to_entity([], [])

        roots: list[Section] = []
        for m in section_models:
            section = id_to_section[m.id]
            if m.parent_id is None or m.parent_id not in id_to_section:
                roots.append(section)
            else:
                parent = id_to_section[m.parent_id]
                parent.subsections.append(section)
                parent.has_subsections = True

        if return_flat:
            return list(id_to_section.values())
        return roots

    def get_all_without_tasks(
        self, user_id: UUID, leaves_only: bool = False, as_tree: bool = False
    ) -> list[Section]:
        models = [m for m in self._section_store.values() if m.user_id == user_id]
        if leaves_only:
            parent_ids = {m.parent_id for m in models if m.parent_id is not None}
            models = [m for m in models if m.id not in parent_ids]
        return self.construct_sections_tree(models, return_flat=not as_tree)


class SQLAlchemyUserRepository:
    def __init__(self, session: Any):
        self._session = session
        self._user_store: dict[UUID, UserModel] = {}
        self._verified: set[UUID] = set()

    def get_all_users(self) -> list[UserStats]:
        return [
            UserStats(user_id=m.id, email=m.email)
            for m in self._user_store.values()
        ]

    def verify_user(self, user_id: UUID) -> None:
        if user_id not in self._user_store:
            raise KeyError(f"User {user_id} does not exist.")
        self._verified.add(user_id)


# ---------------------------------------------------------------------------
# Application – Unit of Work
# ---------------------------------------------------------------------------

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
    def __init__(self, session_factory: Any):
        self.session_factory = session_factory
        self.session: Any = None
        self.task_repo: SQLAlchemyTaskRepository = None  # type: ignore[assignment]
        self.section_repo: SQLAlchemySectionRepository = None  # type: ignore[assignment]
        self.user_repo: SQLAlchemyUserRepository = None  # type: ignore[assignment]

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        if callable(self.session_factory):
            self.session = self.session_factory()
        else:
            self.session = self.session_factory
        self.task_repo = SQLAlchemyTaskRepository(self.session)
        self.section_repo = SQLAlchemySectionRepository(self.session)
        self.user_repo = SQLAlchemyUserRepository(self.session)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            await self.rollback()
        self.session = None

    async def commit(self) -> None:
        if self.session is not None and hasattr(self.session, "commit"):
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session is not None and hasattr(self.session, "rollback"):
            await self.session.rollback()