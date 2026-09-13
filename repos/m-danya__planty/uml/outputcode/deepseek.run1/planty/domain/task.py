# ---------------------------------------------------------------------------

class Entity(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Attachment(Entity):
    added_at: Optional[datetime] = None
    aes_iv_b64: str
    aes_key_b64: str
    id: Optional[UUID] = None
    s3_file_key: str
    task_id: UUID


class RecurrenceInfo(Entity):
    flexible_mode: bool = False
    period: int
    type: Literal["daily", "weekly", "monthly", "yearly"]


class User(Entity):
    added_at: Optional[datetime] = None
    email: str
    id: Optional[UUID] = None


class Task(Entity):
    added_at: Optional[datetime] = None
    attachments: list[Attachment] = []
    content: Optional[str] = None
    description: Optional[str] = None
    due_to: Optional[date] = None
    id: Optional[UUID] = None
    is_archived: bool = False
    is_completed: bool = False
    recurrence: Optional[RecurrenceInfo] = None
    section_id: UUID
    title: str
    user_id: UUID

    def add_attachment(self, attachment: Attachment) -> None:
        self.attachments.append(attachment)

    def remove_attachment(self, attachment: Attachment) -> None:
        self.attachments = [a for a in self.attachments if a.id != attachment.id]

    def archive(self) -> None:
        self.is_archived = True

    def unarchive(self) -> None:
        self.is_archived = False

    def toggle_archived(self) -> None:
        self.is_archived = not self.is_archived

    def mark_completed(self, auto_archive: bool = False) -> None:
        self.is_completed = True
        if auto_archive:
            self.archive()

    def toggle_completed(self, auto_archive: bool = False) -> None:
        if self.is_completed:
            self.is_completed = False
            if auto_archive:
                self.unarchive()
        else:
            self.mark_completed(auto_archive)

    def check_recurrence_due_date(self, values: Any) -> Any:
        # placeholder – actual logic could compute next due date based on recurrence
        return values


class Section(Entity):
    added_at: Optional[datetime] = None
    has_subsections: bool = False
    has_tasks: bool = False
    id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    subsections: list[Section] = []
    tasks: list[Task] = []
    title: str
    user_id: UUID

    @classmethod
    def create_root_section(cls, user_id: UUID) -> Section:
        return cls(
            id=uuid4(),
            user_id=user_id,
            title="Root",
            parent_id=None,
        )

    def check_flags(self) -> Section:
        self.has_subsections = len(self.subsections) > 0
        self.has_tasks = len(self.tasks) > 0
        return self

    def is_root(self) -> bool:
        return self.parent_id is None

    def insert_subsection(self, subsection: Section, index: Optional[int] = None) -> None:
        if index is None:
            self.subsections.append(subsection)
        else:
            self.subsections.insert(index, subsection)
        subsection.parent_id = self.id
        self.check_flags()

    def remove_subsection(self, subsection: Section) -> Section:
        self.subsections = [s for s in self.subsections if s.id != subsection.id]
        subsection.parent_id = None
        self.check_flags()
        return subsection

    def insert_task(self, task: Task, index: Optional[int] = None) -> None:
        if index is None:
            self.tasks.append(task)
        else:
            self.tasks.insert(index, task)
        task.section_id = self.id
        self.check_flags()

    def remove_task(self, task: Task) -> Task:
        self.tasks = [t for t in self.tasks if t.id != task.id]
        task.section_id = None  # caller should reassign
        self.check_flags()
        return task

    def move_section(self, section: Section, section_from: Section, section_to: Section, index: int) -> None:
        section_from.remove_subsection(section)
        section_to.insert_subsection(section, index)

    def move_task(self, task_to_move: Task, section_from: Section, section_to: Section, index: int) -> None:
        section_from.remove_task(task_to_move)
        section_to.insert_task(task_to_move, index)

    def shuffle_tasks(self) -> None:
        import random
        random.shuffle(self.tasks)


# ---------------------------------------------------------------------------
