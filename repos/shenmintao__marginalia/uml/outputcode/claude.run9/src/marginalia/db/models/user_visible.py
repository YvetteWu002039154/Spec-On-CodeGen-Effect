# ---------------------------------------------------------------------------

class File(IdMixin, TimestampMixin, Base):
    __tablename__ = "files"

    sha256: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    original_ext: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    kind: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ingest_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    ingested_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)


class FileEntry(IdMixin, TimestampMixin, Base):
    __tablename__ = "file_entries"

    file_id: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    folder_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    catalog_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lifecycle: Mapped[str] = mapped_column(String, nullable=False, default="active")
    purge_after: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)


class Folder(IdMixin, TimestampMixin, Base):
    __tablename__ = "folders"

    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)


# ---------------------------------------------------------------------------
