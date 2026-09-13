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
        if self.attachments is None:
            return
        self.attachments = [a for a in self.attachments if a.id != attachment.id]

    def mark_completed(self, auto_archive: bool = False) -> None:
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
    user_id: UUID
    parent_id: Optional[UUID] = None
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
            parent_id=None,
            title="root",
            tasks=[],
            subsections=[],
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
        task_to_move.section_id = section_to.id  # type: ignore[assignment]
        section_to.insert_task(task_to_move, index)

    @staticmethod
    def move_section(
        section: "Section",
        section_from: "Section",
        section_to: "Section",
        index: int,
    ) -> None:
        section_from.remove_subsection(section)
        section.parent_id = section_to.id
        section_to.insert_subsection(section, index)


class User(Entity):
    id: Optional[UUID] = None
    email: str
    added_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Infrastructure – simple in-memory model stubs (no SQLAlchemy dependency)
# ---------------------------------------------------------------------------

NonNegativeInt = int  # type alias


class UserStats:
    def __init__(self, user_id: UUID, email: str, task_count: int = 0):
        self.user_id = user_id
        self.email = email
        self.task_count = task_count


# ---------------------------------------------------------------------------
# Infrastructure models (plain Python, no ORM)
# ---------------------------------------------------------------------------

class AccessTokenModel:
    pass


class UserModel:
    def __init__(
        self,
        id: UUID,
        email: str,
        added_at: datetime,
    ):
        self.id = id
        self.email = email
        self.added_at = added_at
        self.sections: list[SectionModel] = []
        self.tasks: list[TaskModel] = []

    def to_entity(self) -> User:
        return User(id=self.id, email=self.email, added_at=self.added_at)


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
        self.task: Optional[TaskModel] = None

    @classmethod
    def from_entity(cls, attachment: Attachment, index: NonNegativeInt) -> "AttachmentModel":
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
        self.section: Optional[SectionModel] = None
        self.user: Optional[UserModel] = None

    @classmethod
    def from_entity(cls, task: Task, index: NonNegativeInt) -> "TaskModel":
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
        if (
            self.recurrence_type is not None
            and self.recurrence_period is not None
        ):
            recurrence = RecurrenceInfo(
                type=self.recurrence_type,  # type: ignore[arg-type]
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
        parent_id: Optional[UUID],
        title: str,
        has_tasks: bool,
        has_subsections: bool,
        added_at: datetime,
        index: int,
    ):
        self.id = id
        self.user_id = user_id
        self.parent_id = parent_id
        self.title = title
        self.has_tasks = has_tasks
        self.has_subsections = has_subsections
        self.added_at = added_at
        self.index = index
        self.tasks: list[TaskModel] = []
        self.user: Optional[UserModel] = None

    @classmethod
    def from_entity(cls, section: Section, index: NonNegativeInt) -> "SectionModel":
        return cls(
            id=section.id or uuid4(),
            user_id=section.user_id,
            parent_id=section.parent_id,
            title=section.title,
            has_tasks=section.has_tasks,
            has_subsections=section.has_subsections,
            added_at=section.added_at or datetime.utcnow(),
            index=index,
        )

    def to_entity(self, tasks: list[Task], subsections: list[Section]) -> Section:
        return Section(
            id=self.id,
            user_id=self.user_id,
            parent_id=self.parent_id,
            title=self.title,
            tasks=tasks,
            subsections=subsections,
            has_tasks=self.has_tasks,
            has_subsections=self.has_subsections,
            added_at=self.added_at,
        )


# ---------------------------------------------------------------------------
# Infrastructure repositories (in-memory implementations)
# ---------------------------------------------------------------------------

class SQLAlchemyUserRepository:
    def __init__(self):
        self._users: dict[UUID, UserModel] = {}

    def get_all_users(self) -> list[UserStats]:
        result = []
        for user_model in self._users.values():
            task_count = len(user_model.tasks)
            result.append(UserStats(user_id=user_model.id, email=user_model.email, task_count=task_count))
        return result

    def verify_user(self, user_id: UUID) -> None:
        if user_id not in self._users:
            raise ValueError(f"User {user_id} not found.")


class SQLAlchemyTaskRepository:
    def __init__(self):
        self._tasks: dict[UUID, TaskModel] = {}
        self._attachments: dict[UUID, AttachmentModel] = {}

    def _next_index_for_section(self, section_id: UUID) -> int:
        indices = [
            t.index for t in self._tasks.values() if t.section_id == section_id
        ]
        return max(indices, default=-1) + 1

    def add(self, task: Task, index: NonNegativeInt) -> None:
        model = TaskModel.from_entity(task, index)
        self._tasks[model.id] = model
        if task.attachments:
            for i, att in enumerate(task.attachments):
                att_model = AttachmentModel.from_entity(att, i)
                att_model.task = model
                self._attachments[att_model.id] = att_model
                model.attachments.append(att_model)

    def get(self, task_id: UUID) -> Task:
        model = self._tasks.get(task_id)
        if model is None:
            raise ValueError(f"Task {task_id} not found.")
        return self.get_entity(model)

    def get_entity(self, task_model: TaskModel) -> Task:
        attachments = [a.to_entity() for a in task_model.attachments]
        return task_model.to_entity(attachments)

    def get_entities(self, task_models: Sequence[TaskModel]) -> list[Task]:
        return [self.get_entity(m) for m in task_models]

    def remove(self, task: Task) -> None:
        if task.id in self._tasks:
            model = self._tasks.pop(task.id)
            for att in list(model.attachments):
                self._attachments.pop(att.id, None)

    def delete_attachment(self, attachment: Attachment) -> None:
        self._attachments.pop(attachment.id, None)
        for task_model in self._tasks.values():
            task_model.attachments = [
                a for a in task_model.attachments if a.id != attachment.id
            ]

    def update_or_create(
        self,
        task: Task,
        index: Optional[NonNegativeInt],
        must_exist: bool = False,
    ) -> None:
        if task.id is not None and task.id in self._tasks:
            existing = self._tasks[task.id]
            idx = index if index is not None else existing.index
            new_model = TaskModel.from_entity(task, idx)
            new_model.attachments = existing.attachments
            self._tasks[task.id] = new_model
        else:
            if must_exist:
                raise ValueError(f"Task {task.id} must exist but was not found.")
            idx = index if index is not None else self._next_index_for_section(task.section_id)
            self.add(task, idx)

    def update_or_create_bulk(self, section_tasks: list[Task]) -> None:
        for i, task in enumerate(section_tasks):
            self.update_or_create(task, i)

    def get_archived_tasks(self, user_id: UUID) -> list[Task]:
        models = [
            m for m in self._tasks.values()
            if m.user_id == user_id and m.is_archived
        ]
        return self.get_entities(models)

    def get_overdue_tasks(self, user_id: UUID) -> list[Task]:
        today = date.today()
        models = [
            m for m in self._tasks.values()
            if m.user_id == user_id
            and m.due_to is not None
            and m.due_to < today
            and not m.is_completed
            and not m.is_archived
        ]
        return self.get_entities(models)

    def get_tasks_by_due_to(
        self, not_before: date, not_after: date, user_id: UUID
    ) -> list[Task]:
        models = [
            m for m in self._tasks.values()
            if m.user_id == user_id
            and m.due_to is not None
            and not_before <= m.due_to <= not_after
        ]
        return self.get_entities(models)

    def search(self, user_id: UUID, query: str) -> list[Task]:
        q = query.lower()
        models = [
            m for m in self._tasks.values()
            if m.user_id == user_id
            and (q in m.title.lower() or (m.description and q in m.description.lower()))
        ]
        return self.get_entities(models)


class SQLAlchemySectionRepository:
    def __init__(self):
        self._sections: dict[UUID, SectionModel] = {}
        self._task_repo: Optional[SQLAlchemyTaskRepository] = None

    def _set_task_repo(self, task_repo: SQLAlchemyTaskRepository) -> None:
        self._task_repo = task_repo

    def _next_index_for_parent(self, parent_id: Optional[UUID]) -> int:
        indices = [
            s.index for s in self._sections.values() if s.parent_id == parent_id
        ]
        return max(indices, default=-1) + 1

    def add(self, section: Section, index: NonNegativeInt) -> None:
        model = SectionModel.from_entity(section, index)
        self._sections[model.id] = model

    def get(self, section_id: UUID, with_direct_subsections: bool = False) -> Section:
        model = self._sections.get(section_id)
        if model is None:
            raise ValueError(f"Section {section_id} not found.")
        tasks: list[Task] = []
        if self._task_repo:
            tasks = self._task_repo.get_entities(model.tasks)
        subsections: list[Section] = []
        if with_direct_subsections:
            child_models = [
                s for s in self._sections.values() if s.parent_id == section_id
            ]
            subsections = [
                m.to_entity([], []) for m in sorted(child_models, key=lambda x: x.index)
            ]
        return model.to_entity(tasks, subsections)

    def count_subsections(self, section_id: UUID) -> int:
        return sum(1 for s in self._sections.values() if s.parent_id == section_id)

    def construct_sections_tree(
        self,
        section_models: list[SectionModel],
        return_flat: bool = False,
    ) -> list[Section]:
        id_to_model = {m.id: m for m in section_models}
        id_to_entity: dict[UUID, Section] = {}

        for model in sorted(section_models, key=lambda x: x.index):
            tasks: list[Task] = []
            if self._task_repo:
                tasks = self._task_repo.get_entities(model.tasks)
            entity = model.to_entity(tasks, [])
            id_to_entity[model.id] = entity

        roots: list[Section] = []
        for model in sorted(section_models, key=lambda x: x.index):
            entity = id_to_entity[model.id]
            if model.parent_id is None or model.parent_id not in id_to_entity:
                roots.append(entity)
            else:
                parent_entity = id_to_entity[model.parent_id]
                parent_entity.subsections.append(entity)
                parent_entity.has_subsections = True

        if return_flat:
            return list(id_to_entity.values())
        return roots

    def get_all_without_tasks(
        self,
        user_id: UUID,
        leaves_only: bool = False,
        as_tree: bool = False,
    ) -> list[Section]:
        models = [m for m in self._sections.values() if m.user_id == user_id]
        if leaves_only:
            parent_ids = {m.parent_id for m in models if m.parent_id is not None}
            models = [m for m in models if m.id not in parent_ids]

        if as_tree:
            return self.construct_sections_tree(models, return_flat=False)

        result = []
        for model in sorted(models, key=lambda x: x.index):
            result.append(model.to_entity([], []))
        return result

    def update(self, section: Section, index: Optional[NonNegativeInt] = None) -> None:
        if section.id is None or section.id not in self._sections:
            raise ValueError(f"Section {section.id} not found.")
        existing = self._sections[section.id]
        idx = index if index is not None else existing.index
        new_model = SectionModel.from_entity(section, idx)
        new_model.tasks = existing.tasks
        self._sections[section.id] = new_model


# ---------------------------------------------------------------------------
# Unit of Work
# ---------------------------------------------------------------------------

class IUnitOfWork(ABC):
    section_repo: SQLAlchemySectionRepository
    task_repo: SQLAlchemyTaskRepository
    user_repo: SQLAlchemyUserRepository

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self, session_factory: Any = None):
        self.session_factory = session_factory
        self.session: Any = None
        self.task_repo = SQLAlchemyTaskRepository()
        self.section_repo = SQLAlchemySectionRepository()
        self.section_repo._set_task_repo(self.task_repo)
        self.user_repo = SQLAlchemyUserRepository()

    def commit(self) -> None:
        if self.session is not None:
            try:
                self.session.commit()
            except Exception:
                pass

    def rollback(self) -> None:
        if self.session is not None:
            try:
                self.session.rollback()
            except Exception:
                pass