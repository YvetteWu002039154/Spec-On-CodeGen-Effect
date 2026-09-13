# ---------------------------------------------------------------------------

class Catalog(IdMixin, Base):
    __tablename__ = "catalogs"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)


class EntryTag(IdMixin, Base):
    __tablename__ = "entry_tags"

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    entry_id: Mapped[str] = mapped_column(String, nullable=False)
    last_reaffirmed_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    reaffirm_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String, nullable=False)
    tag_id: Mapped[str] = mapped_column(String, nullable=False)


class Tag(IdMixin, Base):
    __tablename__ = "tags"

    alias_of: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    doc_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    facet: Mapped[str] = mapped_column(String, nullable=False)
    last_reaffirmed_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    reaffirm_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TagAlias(IdMixin, Base):
    __tablename__ = "tag_aliases"

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    from_name: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    to_tag_id: Mapped[str] = mapped_column(String, nullable=False)


class View(IdMixin, Base):
    __tablename__ = "views"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    filter_spec: Mapped[Any] = mapped_column(JSON, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)


# ---------------------------------------------------------------------------
