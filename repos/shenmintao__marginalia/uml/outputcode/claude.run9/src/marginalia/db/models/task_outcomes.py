# ---------------------------------------------------------------------------

class TaskOutcome(IdMixin, Base):
    __tablename__ = "task_outcomes"

    task_kind: Mapped[str] = mapped_column(String, nullable=False)
    task_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    object_kind: Mapped[str] = mapped_column(String, nullable=False)
    object_id: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    detail: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
