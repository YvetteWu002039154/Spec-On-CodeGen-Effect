# ---------------------------------------------------------------------------

class File(IdMixin, Base):
    __tablename__ = "files"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ingest_status: Mapped[str] = mapped_column(String, nullable=False)
    ingested_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    kind: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    original_ext: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sha256: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class FileEntry(IdMixin, Base):
    __tablename__ = "file_entries"

    catalog_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_id: Mapped[str] = mapped_column(String, nullable=False)
    folder_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lifecycle: Mapped[str] = mapped_column(String, nullable=False)
    purge_after: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)


class Folder(IdMixin, Base):
    __tablename__ = "folders"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)


# ---------------------------------------------------------------------------
