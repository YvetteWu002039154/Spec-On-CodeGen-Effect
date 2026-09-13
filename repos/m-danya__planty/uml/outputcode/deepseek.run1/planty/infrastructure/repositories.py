# ---------------------------------------------------------------------------

from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

# Simple UserStats DTO
class UserStats:
    def __init__(self, user_id: UUID, email: str, task_count: int, section_count: int):
        self.user_id = user_id
        self.email = email
        self.task_count = task_count
        self.section_count = section_count


class SQLAlchemySectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, section: Section, index: int) -> None:
        model = SectionModel.from_entity(section, index)
        self.session.add(model)

    async def get(self, section_id: UUID, with_direct_subsections: bool = False) -> Section:
        stmt = select(SectionModel).where(SectionModel.id == section_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        # fetch tasks and subsections if needed
        task_models = []
        subsection_models = []
        if with_direct_subsections:
            subsection_models = (await self.session.execute(
                select(SectionModel).where(SectionModel.parent_id == section_id)
            )).scalars().all()
        # tasks are loaded via relationship, but we'll build entity from model
        tasks = [t.to_entity([]) for t in model.tasks]  # attachments not loaded
        subsections = [s.to_entity([], []) for s in subsection_models]
        return model.to_entity(tasks, subsections)

    async def get_all_without_tasks(self, user_id: UUID, leaves_only: bool = False, as_tree: bool = False) -> list[Section]:
        stmt = select(SectionModel).where(SectionModel.user_id == user_id)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        # simplified: just convert to entities without full nesting
        sections = [m.to_entity([], []) for m in models]
        if leaves_only:
            sections = [s for s in sections if s.has_tasks or s.has_subsections]
        return sections

    async def count_subsections(self, section_id: UUID) -> int:
        stmt = select(func.count(SectionModel.id)).where(SectionModel.parent_id == section_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def construct_sections_tree(self, section_models: list[SectionModel], return_flat: bool = False) -> list[Section]:
        # placeholder
        sections = [m.to_entity([], []) for m in section_models]
        if return_flat:
            return sections
        # simplified: no tree building; just return list
        return sections

    async def update(self, section: Section, index: Optional[int] = None) -> None:
        stmt = (
            update(SectionModel)
            .where(SectionModel.id == section.id)
            .values(
                title=section.title,
                has_subsections=section.has_subsections,
                has_tasks=section.has_tasks,
            )
        )
        if index is not None:
            stmt = stmt.values(index=index)
        await self.session.execute(stmt)


class SQLAlchemyTaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, task: Task, index: int) -> None:
        model = TaskModel.from_entity(task, index)
        self.session.add(model)

    async def get(self, task_id: UUID) -> Task:
        stmt = select(TaskModel).where(TaskModel.id == task_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        attachments = [a.to_entity() for a in model.attachments]
        return model.to_entity(attachments)

    async def get_entity(self, task_model: TaskModel) -> Task:
        attachments = [a.to_entity() for a in task_model.attachments]
        return task_model.to_entity(attachments)

    async def get_entities(self, task_models: Sequence[TaskModel]) -> list[Task]:
        return [await self.get_entity(m) for m in task_models]

    async def get_archived_tasks(self, user_id: UUID) -> list[Task]:
        stmt = select(TaskModel).where(and_(TaskModel.user_id == user_id, TaskModel.is_archived == True))
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return await self.get_entities(models)

    async def get_overdue_tasks(self, user_id: UUID) -> list[Task]:
        today = date.today()
        stmt = select(TaskModel).where(and_(
            TaskModel.user_id == user_id,
            TaskModel.due_to < today,
            TaskModel.is_completed == False,
        ))
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return await self.get_entities(models)

    async def get_tasks_by_due_to(self, not_before: date, not_after: date, user_id: UUID) -> list[Task]:
        stmt = select(TaskModel).where(and_(
            TaskModel.user_id == user_id,
            TaskModel.due_to >= not_before,
            TaskModel.due_to <= not_after,
        ))
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return await self.get_entities(models)

    async def search(self, user_id: UUID, query: str) -> list[Task]:
        pattern = f"%{query}%"
        stmt = select(TaskModel).where(and_(
            TaskModel.user_id == user_id,
            TaskModel.title.ilike(pattern),
        ))
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return await self.get_entities(models)

    async def remove(self, task: Task) -> None:
        stmt = delete(TaskModel).where(TaskModel.id == task.id)
        await self.session.execute(stmt)

    async def update_or_create(self, task: Task, index: Optional[int] = None, must_exist: bool = False) -> None:
        stmt = select(TaskModel).where(TaskModel.id == task.id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            # update
            values = {
                "title": task.title,
                "description": task.description,
                "due_to": task.due_to,
                "is_archived": task.is_archived,
                "is_completed": task.is_completed,
                "section_id": task.section_id,
            }
            if task.recurrence:
                values.update({
                    "flexible_recurrence_mode": task.recurrence.flexible_mode,
                    "recurrence_period": task.recurrence.period,
                    "recurrence_type": task.recurrence.type,
                })
            if index is not None:
                values["index"] = index
            stmt = update(TaskModel).where(TaskModel.id == task.id).values(**values)
            await self.session.execute(stmt)
        else:
            if must_exist:
                raise ValueError("Task does not exist")
            model = TaskModel.from_entity(task, index if index is not None else 0)
            self.session.add(model)

    async def update_or_create_bulk(self, section_tasks: list[Task]) -> None:
        for task in section_tasks:
            await self.update_or_create(task)

    async def delete_attachment(self, attachment: Attachment) -> None:
        stmt = delete(AttachmentModel).where(AttachmentModel.id == attachment.id)
        await self.session.execute(stmt)


class SQLAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def verify_user(self, user_id: UUID) -> None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        if not result.scalar_one_or_none():
            raise ValueError("User not found")

    async def get_all_users(self) -> list[UserStats]:
        stmt = select(UserModel)
        result = await self.session.execute(stmt)
        users = result.scalars().all()
        stats = []
        for u in users:
            task_count = len(u.tasks)
            section_count = len(u.sections)
            stats.append(UserStats(u.id, u.email, task_count, section_count))
        return stats
