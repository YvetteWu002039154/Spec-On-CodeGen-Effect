from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Literal, Optional, Any, Sequence
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# ---------------------------------------------------------------------------
