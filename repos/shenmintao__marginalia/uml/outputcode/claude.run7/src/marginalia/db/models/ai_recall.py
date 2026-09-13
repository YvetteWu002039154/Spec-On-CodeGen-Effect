# ---------------------------------------------------------------------------

class EntryRelation(IdMixin, Base):
    __tablename__ = "entry_relations"

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    entry_a_id: Mapped[str] = mapped_column(String, nullable=False)
    entry_b_id: Mapped[str] = mapped_column(String, nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    vetted: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    vetted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    vetted_observation_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vetted_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Journal(IdMixin, Base):
    __tablename__ = "journals"

    conversation_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    entry_ids: Mapped[Any] = mapped_column(JSON, nullable=True)
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    invalidated_by_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    invalidated_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    summarized_journal_ids: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    superseded_by_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tags: Mapped[Any] = mapped_column(JSON, nullable=True)


# ---------------------------------------------------------------------------
