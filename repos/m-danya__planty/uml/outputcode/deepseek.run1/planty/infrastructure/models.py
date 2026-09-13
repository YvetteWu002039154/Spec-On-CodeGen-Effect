# ---------------------------------------------------------------------------
# Minimal base for SQLAlchemy models
class Base(DeclarativeBase):
    pass


class AccessTokenModel(Base):
    __tablename__ = "access_tokens"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False)
    token: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)


class UserModel(Base):
    __tablename__ = "users"
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    email: Mapped[str] = mapped_column(unique=True)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sections: Mapped[list[SectionModel]] = relationship(back_populates="user")
    tasks: Mapped[list[TaskModel]] = relationship(back_populates="user")

    def to_entity(self) -> User:
        return User(
            added_at=self.added_at,
            email=self.email,
            id=self.id,
        )


class SectionModel(Base):
    __tablename__ = "sections"
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    has_subsections: Mapped[bool] = mapped_column(default=False)
    has_tasks: Mapped[bool] = mapped_column(default=False)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    index: Mapped[int] = mapped_column()
    parent_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID, nullable=True)
    title: Mapped[str] = mapped_column()
    user_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False)
    user: Mapped[UserModel] = relationship(back_populates="sections")
    tasks: Mapped[list[TaskModel]] = relationship(back_populates="section")

    @classmethod
    def from_entity(cls, section: Section, index: int) -> SectionModel:
        return cls(
            added_at=section.added_at or datetime.utcnow(),
            has_subsections=section.has_subsections,
            has_tasks=section.has_tasks,
            id=section.id or uuid4(),
            index=index,
            parent_id=section.parent_id,
            title=section.title,
            user_id=section.user_id,
        )

    def to_entity(self, tasks: list[Task], subsections: list[Section]) -> Section:
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
        )


class TaskModel(Base):
    __tablename__ = "tasks"
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    description: Mapped[Optional[str]] = mapped_column()
    due_to: Mapped[Optional[date]] = mapped_column()
    flexible_recurrence_mode: Mapped[Optional[bool]] = mapped_column()
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    index: Mapped[int] = mapped_column()
    is_archived: Mapped[bool] = mapped_column(default=False)
    is_completed: Mapped[bool] = mapped_column(default=False)
    recurrence_period: Mapped[Optional[int]] = mapped_column()
    recurrence_type: Mapped[Optional[str]] = mapped_column()
    section_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False)
    title: Mapped[str] = mapped_column()
    user_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False)
    section: Mapped[SectionModel] = relationship(back_populates="tasks")
    user: Mapped[UserModel] = relationship(back_populates="tasks")
    attachments: Mapped[list[AttachmentModel]] = relationship(back_populates="task")

    @classmethod
    def from_entity(cls, task: Task, index: int) -> TaskModel:
        return cls(
            added_at=task.added_at or datetime.utcnow(),
            description=task.description,
            due_to=task.due_to,
            flexible_recurrence_mode=task.recurrence.flexible_mode if task.recurrence else None,
            id=task.id or uuid4(),
            index=index,
            is_archived=task.is_archived,
            is_completed=task.is_completed,
            recurrence_period=task.recurrence.period if task.recurrence else None,
            recurrence_type=task.recurrence.type if task.recurrence else None,
            section_id=task.section_id,
            title=task.title,
            user_id=task.user_id,
        )

    def to_entity(self, attachments: list[Attachment]) -> Task:
        recurrence = None
        if self.recurrence_type:
            recurrence = RecurrenceInfo(
                flexible_mode=self.flexible_recurrence_mode or False,
                period=self.recurrence_period or 0,
                type=self.recurrence_type,  # type: ignore
            )
        return Task(
            added_at=self.added_at,
            attachments=attachments,
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


class AttachmentModel(Base):
    __tablename__ = "attachments"
    added_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    aes_iv_b64: Mapped[str] = mapped_column()
    aes_key_b64: Mapped[str] = mapped_column()
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    index: Mapped[int] = mapped_column()
    s3_file_key: Mapped[str] = mapped_column()
    task_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False)
    task: Mapped[TaskModel] = relationship(back_populates="attachments")

    @classmethod
    def from_entity(cls, attachment: Attachment, index: int) -> AttachmentModel:
        return cls(
            added_at=attachment.added_at or datetime.utcnow(),
            aes_iv_b64=attachment.aes_iv_b64,
            aes_key_b64=attachment.aes_key_b64,
            id=attachment.id or uuid4(),
            index=index,
            s3_file_key=attachment.s3_file_key,
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


# ---------------------------------------------------------------------------
