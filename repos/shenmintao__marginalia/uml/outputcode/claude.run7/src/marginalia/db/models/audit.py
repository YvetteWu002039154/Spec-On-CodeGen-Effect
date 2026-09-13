# ---------------------------------------------------------------------------

class AuditEvent(IdMixin, Base):
    __tablename__ = "audit_events"

    conversation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    payload: Mapped[Any] = mapped_column(JSON, nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    task_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Conversation(IdMixin, Base):
    __tablename__ = "conversations"

    agent_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    llm_calls: Mapped[Any] = mapped_column(JSON, nullable=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    tool_calls: Mapped[Any] = mapped_column(JSON, nullable=True)
    total_cache_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8), nullable=False, default=Decimal("0")
    )
    total_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_llm_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)


class Session(IdMixin, Base):
    __tablename__ = "sessions"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    end_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    initiating_user_message: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    total_cache_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8), nullable=False, default=Decimal("0")
    )
    total_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_llm_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# ---------------------------------------------------------------------------
