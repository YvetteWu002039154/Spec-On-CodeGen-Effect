# ---------------------------------------------------------------------------

class Task(IdMixin, Base):
    __tablename__ = "tasks"

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    dedup_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    locked_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    payload: Mapped[Any] = mapped_column(JSON, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scheduled_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)


# ---------------------------------------------------------------------------
