"""
SQLAlchemy Database Models
Gespiegeld van Prisma schema - alles configureerbaar
"""

import enum
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Any
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    Date,
    Text,
    Numeric,
    ForeignKey,
    JSON,
    Enum,
    Index,
    UniqueConstraint,
    ARRAY,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.config import get_settings


class Base(DeclarativeBase):
    pass


# ============================================
# ENUMS
# ============================================


class PersonType(str, enum.Enum):
    INSTRUCTOR = "INSTRUCTOR"
    EXTERNAL_INSTRUCTOR = "EXTERNAL_INSTRUCTOR"
    TECHNICIAN = "TECHNICIAN"


class DurationType(str, enum.Enum):
    EVENING_SERIES = "EVENING_SERIES"
    MULTI_DAY = "MULTI_DAY"
    SINGLE_DAY = "SINGLE_DAY"
    HALF_DAY = "HALF_DAY"
    SINGLE_SESSION = "SINGLE_SESSION"


class WorkshopStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class AssignmentRole(str, enum.Enum):
    INSTRUCTOR = "INSTRUCTOR"
    CO_INSTRUCTOR = "CO_INSTRUCTOR"
    GUEST = "GUEST"
    TECHNICIAN = "TECHNICIAN"


class AssignmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    DECLINED = "DECLINED"


class AvailabilityType(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    PREFERRED = "PREFERRED"


class MessageRole(str, enum.Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"
    FUNCTION = "FUNCTION"


# ============================================
# CONFIGURATIE ENTITIES
# ============================================


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(255))
    available_days: Mapped[List[str]] = mapped_column(ARRAY(String))
    calendar_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    workshops: Mapped[List["Workshop"]] = relationship(back_populates="location")
    preferred_by: Mapped[List["Person"]] = relationship(back_populates="preferred_location")
    workshop_types: Mapped[List["WorkshopTypeLocation"]] = relationship(
        back_populates="location"
    )


class Person(Base):
    __tablename__ = "persons"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    type: Mapped[PersonType] = mapped_column(Enum(PersonType))
    max_days_per_week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preferred_location_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("locations.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    preferred_location: Mapped[Optional["Location"]] = relationship(
        back_populates="preferred_by"
    )
    can_teach: Mapped[List["PersonWorkshopType"]] = relationship(back_populates="person")
    assignments: Mapped[List["Assignment"]] = relationship(back_populates="person")
    availability: Mapped[List["Availability"]] = relationship(back_populates="person")


class WorkshopType(Base):
    __tablename__ = "workshop_types"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    duration_type: Mapped[DurationType] = mapped_column(Enum(DurationType))
    default_start_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    default_end_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    session_count: Mapped[int] = mapped_column(Integer, default=1)

    # Deelnemers
    max_participants: Mapped[int] = mapped_column(Integer)
    min_participants: Mapped[int] = mapped_column(Integer)

    # Financieel
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    # Vereisten
    requires_technician: Mapped[bool] = mapped_column(Boolean, default=False)

    # Zichtbaarheid
    visible_public: Mapped[bool] = mapped_column(Boolean, default=True)
    visible_students: Mapped[bool] = mapped_column(Boolean, default=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    allowed_locations: Mapped[List["WorkshopTypeLocation"]] = relationship(
        back_populates="workshop_type"
    )
    allowed_instructors: Mapped[List["PersonWorkshopType"]] = relationship(
        back_populates="workshop_type"
    )
    workshops: Mapped[List["Workshop"]] = relationship(back_populates="type")
    prerequisites: Mapped[List["WorkshopTypePrerequisite"]] = relationship(
        back_populates="workshop_type",
        foreign_keys="WorkshopTypePrerequisite.workshop_type_id",
    )
    prerequisite_for: Mapped[List["WorkshopTypePrerequisite"]] = relationship(
        back_populates="prerequisite_type",
        foreign_keys="WorkshopTypePrerequisite.prerequisite_type_id",
    )


class WorkshopTypeLocation(Base):
    __tablename__ = "workshop_type_locations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workshop_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workshop_types.id", ondelete="CASCADE")
    )
    location_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("locations.id", ondelete="CASCADE")
    )

    # Relationships
    workshop_type: Mapped["WorkshopType"] = relationship(
        back_populates="allowed_locations"
    )
    location: Mapped["Location"] = relationship(back_populates="workshop_types")

    __table_args__ = (
        UniqueConstraint("workshop_type_id", "location_id", name="uq_workshop_type_location"),
    )


class PersonWorkshopType(Base):
    __tablename__ = "person_workshop_types"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    person_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("persons.id", ondelete="CASCADE")
    )
    workshop_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workshop_types.id", ondelete="CASCADE")
    )

    # Relationships
    person: Mapped["Person"] = relationship(back_populates="can_teach")
    workshop_type: Mapped["WorkshopType"] = relationship(
        back_populates="allowed_instructors"
    )

    __table_args__ = (
        UniqueConstraint("person_id", "workshop_type_id", name="uq_person_workshop_type"),
    )


class WorkshopTypePrerequisite(Base):
    __tablename__ = "workshop_type_prerequisites"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workshop_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workshop_types.id", ondelete="CASCADE")
    )
    prerequisite_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workshop_types.id", ondelete="CASCADE")
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    workshop_type: Mapped["WorkshopType"] = relationship(
        back_populates="prerequisites",
        foreign_keys=[workshop_type_id],
    )
    prerequisite_type: Mapped["WorkshopType"] = relationship(
        back_populates="prerequisite_for",
        foreign_keys=[prerequisite_type_id],
    )

    __table_args__ = (
        UniqueConstraint(
            "workshop_type_id", "prerequisite_type_id", name="uq_workshop_prerequisite"
        ),
    )


# ============================================
# OPERATIONELE ENTITIES
# ============================================


class Workshop(Base):
    __tablename__ = "workshops"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    display_id: Mapped[int] = mapped_column(Integer, autoincrement=True, unique=True)
    type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workshop_types.id")
    )
    location_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("locations.id")
    )

    # Timing
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Status
    status: Mapped[WorkshopStatus] = mapped_column(
        Enum(WorkshopStatus), default=WorkshopStatus.DRAFT
    )
    current_participants: Mapped[int] = mapped_column(Integer, default=0)

    # Calendar sync
    calendar_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sync_uid: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    type: Mapped["WorkshopType"] = relationship(back_populates="workshops")
    location: Mapped["Location"] = relationship(back_populates="workshops")
    sessions: Mapped[List["WorkshopSession"]] = relationship(
        back_populates="workshop", cascade="all, delete-orphan"
    )
    assignments: Mapped[List["Assignment"]] = relationship(
        back_populates="workshop", cascade="all, delete-orphan"
    )

    @property
    def display_code(self) -> str:
        """Genereer display code zoals IWS_192_U"""
        location_suffix = {
            "AMS": "A",
            "UTR": "U",
            "LEI": "L",
        }.get(self.location.code, self.location.code[0]) if self.location else "?"
        return f"{self.type.code}_{self.display_id}_{location_suffix}"


class WorkshopSession(Base):
    __tablename__ = "workshop_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workshop_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workshops.id", ondelete="CASCADE")
    )
    session_number: Mapped[int] = mapped_column(Integer)

    # Timing
    date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[str] = mapped_column(String(5))
    end_time: Mapped[str] = mapped_column(String(5))

    # Vereisten
    requires_technician: Mapped[bool] = mapped_column(Boolean, default=False)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    workshop: Mapped["Workshop"] = relationship(back_populates="sessions")
    assignments: Mapped[List["Assignment"]] = relationship(back_populates="session")

    __table_args__ = (
        UniqueConstraint("workshop_id", "session_number", name="uq_workshop_session"),
    )


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workshop_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workshops.id", ondelete="CASCADE")
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("workshop_sessions.id", ondelete="CASCADE"), nullable=True
    )
    person_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("persons.id")
    )
    role: Mapped[AssignmentRole] = mapped_column(Enum(AssignmentRole))
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus), default=AssignmentStatus.PENDING
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    workshop: Mapped["Workshop"] = relationship(back_populates="assignments")
    session: Mapped[Optional["WorkshopSession"]] = relationship(back_populates="assignments")
    person: Mapped["Person"] = relationship(back_populates="assignments")


# ============================================
# BESCHIKBAARHEID
# ============================================


class Availability(Base):
    __tablename__ = "availability"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    person_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("persons.id", ondelete="CASCADE")
    )
    type: Mapped[AvailabilityType] = mapped_column(Enum(AvailabilityType))

    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)

    recurring_pattern: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    person: Mapped["Person"] = relationship(back_populates="availability")


# ============================================
# SETTINGS
# ============================================


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[Any] = mapped_column(JSON)
    category: Mapped[str] = mapped_column(String(50))
    label: Mapped[str] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ============================================
# AI CHAT
# ============================================


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    messages: Mapped[List["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE")
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole))
    content: Mapped[str] = mapped_column(Text)

    function_call: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    function_result: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


# ============================================
# AUDIT LOG
# ============================================


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(20))
    changes: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)


# ============================================
# DATABASE SESSION
# ============================================

settings = get_settings()
engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
