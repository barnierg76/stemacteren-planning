"""
Pydantic Schemas voor API Request/Response validation
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum


# ============================================
# ENUMS (gespiegeld van database)
# ============================================


class PersonType(str, Enum):
    INSTRUCTOR = "INSTRUCTOR"
    EXTERNAL_INSTRUCTOR = "EXTERNAL_INSTRUCTOR"
    TECHNICIAN = "TECHNICIAN"


class DurationType(str, Enum):
    EVENING_SERIES = "EVENING_SERIES"
    MULTI_DAY = "MULTI_DAY"
    SINGLE_DAY = "SINGLE_DAY"
    HALF_DAY = "HALF_DAY"
    SINGLE_SESSION = "SINGLE_SESSION"


class WorkshopStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class AssignmentRole(str, Enum):
    INSTRUCTOR = "INSTRUCTOR"
    CO_INSTRUCTOR = "CO_INSTRUCTOR"
    GUEST = "GUEST"
    TECHNICIAN = "TECHNICIAN"


class AssignmentStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    DECLINED = "DECLINED"


class AvailabilityType(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    PREFERRED = "PREFERRED"


# ============================================
# BASE SCHEMAS
# ============================================


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ============================================
# LOCATION SCHEMAS
# ============================================


class LocationBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1, max_length=100)
    address: str = Field(..., min_length=1, max_length=255)
    available_days: List[str] = Field(default_factory=list)
    calendar_id: Optional[str] = None
    is_active: bool = True


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=10)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    address: Optional[str] = Field(None, min_length=1, max_length=255)
    available_days: Optional[List[str]] = None
    calendar_id: Optional[str] = None
    is_active: Optional[bool] = None


class LocationResponse(LocationBase, BaseSchema):
    id: str
    created_at: datetime
    updated_at: datetime


# ============================================
# PERSON SCHEMAS
# ============================================


class PersonBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    type: PersonType
    max_days_per_week: Optional[int] = Field(None, ge=1, le=7)
    preferred_location_id: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None


class PersonCreate(PersonBase):
    can_teach_type_ids: List[str] = Field(default_factory=list)


class PersonUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    type: Optional[PersonType] = None
    max_days_per_week: Optional[int] = Field(None, ge=1, le=7)
    preferred_location_id: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None
    can_teach_type_ids: Optional[List[str]] = None


class PersonResponse(PersonBase, BaseSchema):
    id: str
    created_at: datetime
    updated_at: datetime
    preferred_location: Optional[LocationResponse] = None
    can_teach: List["WorkshopTypeSimple"] = Field(default_factory=list)


# ============================================
# WORKSHOP TYPE SCHEMAS
# ============================================


class WorkshopTypeBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    duration_type: DurationType
    default_start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    default_end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    session_count: int = Field(1, ge=1)
    max_participants: int = Field(..., ge=1)
    min_participants: int = Field(..., ge=1)
    price: Decimal = Field(..., ge=0)
    requires_technician: bool = False
    visible_public: bool = True
    visible_students: bool = True
    is_active: bool = True
    sort_order: int = 0


class WorkshopTypeCreate(WorkshopTypeBase):
    allowed_location_ids: List[str] = Field(default_factory=list)
    allowed_instructor_ids: List[str] = Field(default_factory=list)
    prerequisite_type_ids: List[str] = Field(default_factory=list)


class WorkshopTypeUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    duration_type: Optional[DurationType] = None
    default_start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    default_end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    session_count: Optional[int] = Field(None, ge=1)
    max_participants: Optional[int] = Field(None, ge=1)
    min_participants: Optional[int] = Field(None, ge=1)
    price: Optional[Decimal] = Field(None, ge=0)
    requires_technician: Optional[bool] = None
    visible_public: Optional[bool] = None
    visible_students: Optional[bool] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    allowed_location_ids: Optional[List[str]] = None
    allowed_instructor_ids: Optional[List[str]] = None
    prerequisite_type_ids: Optional[List[str]] = None


class WorkshopTypeSimple(BaseSchema):
    """Simplified version for nested responses"""

    id: str
    code: str
    name: str


class WorkshopTypeResponse(WorkshopTypeBase, BaseSchema):
    id: str
    created_at: datetime
    updated_at: datetime
    allowed_locations: List[LocationResponse] = Field(default_factory=list)


# ============================================
# WORKSHOP SCHEMAS
# ============================================


class WorkshopSessionBase(BaseModel):
    session_number: int = Field(..., ge=1)
    date: date
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    requires_technician: bool = False
    notes: Optional[str] = None


class WorkshopSessionCreate(WorkshopSessionBase):
    pass


class WorkshopSessionResponse(WorkshopSessionBase, BaseSchema):
    id: str
    workshop_id: str
    created_at: datetime
    updated_at: datetime


class WorkshopBase(BaseModel):
    type_id: str
    location_id: str
    start_date: date
    end_date: Optional[date] = None
    status: WorkshopStatus = WorkshopStatus.DRAFT
    current_participants: int = Field(0, ge=0)
    notes: Optional[str] = None


class WorkshopCreate(WorkshopBase):
    sessions: List[WorkshopSessionCreate] = Field(default_factory=list)


class WorkshopUpdate(BaseModel):
    type_id: Optional[str] = None
    location_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[WorkshopStatus] = None
    current_participants: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class WorkshopResponse(WorkshopBase, BaseSchema):
    id: str
    display_id: int
    display_code: str
    calendar_event_id: Optional[str] = None
    sync_uid: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    type: WorkshopTypeSimple
    location: LocationResponse
    sessions: List[WorkshopSessionResponse] = Field(default_factory=list)
    assignments: List["AssignmentResponse"] = Field(default_factory=list)


class WorkshopListResponse(BaseSchema):
    """Lighter version for list views"""

    id: str
    display_id: int
    display_code: str
    start_date: date
    end_date: Optional[date]
    status: WorkshopStatus
    current_participants: int
    type: WorkshopTypeSimple
    location: LocationResponse


# ============================================
# ASSIGNMENT SCHEMAS
# ============================================


class AssignmentBase(BaseModel):
    workshop_id: str
    session_id: Optional[str] = None
    person_id: str
    role: AssignmentRole
    notes: Optional[str] = None


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentUpdate(BaseModel):
    session_id: Optional[str] = None
    person_id: Optional[str] = None
    role: Optional[AssignmentRole] = None
    status: Optional[AssignmentStatus] = None
    notes: Optional[str] = None


class AssignmentResponse(AssignmentBase, BaseSchema):
    id: str
    status: AssignmentStatus
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    person: "PersonSimple"


class PersonSimple(BaseSchema):
    """Simplified person for nested responses"""

    id: str
    name: str
    type: PersonType


# ============================================
# AVAILABILITY SCHEMAS
# ============================================


class AvailabilityBase(BaseModel):
    person_id: str
    type: AvailabilityType
    start_date: date
    end_date: date
    recurring_pattern: Optional[str] = None
    reason: Optional[str] = None


class AvailabilityCreate(AvailabilityBase):
    pass


class AvailabilityUpdate(BaseModel):
    type: Optional[AvailabilityType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    recurring_pattern: Optional[str] = None
    reason: Optional[str] = None


class AvailabilityResponse(AvailabilityBase, BaseSchema):
    id: str
    created_at: datetime
    updated_at: datetime


# ============================================
# SETTINGS SCHEMAS
# ============================================


class SettingBase(BaseModel):
    key: str
    value: Any
    category: str
    label: str


class SettingCreate(SettingBase):
    pass


class SettingUpdate(BaseModel):
    value: Any
    label: Optional[str] = None


class SettingResponse(SettingBase, BaseSchema):
    id: str
    updated_at: datetime


# ============================================
# VALIDATION SCHEMAS
# ============================================


class ValidationError(BaseModel):
    field: str
    message: str
    severity: str = "error"  # "error" or "warning"


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationError] = Field(default_factory=list)


# ============================================
# CHAT SCHEMAS
# ============================================


class ChatMessageInput(BaseModel):
    content: str = Field(..., min_length=1)
    session_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    function_call: Optional[Any] = None
    created_at: datetime


class ChatResponse(BaseModel):
    session_id: str
    message: ChatMessageResponse
    requires_confirmation: bool = False
    pending_action: Optional[dict] = None


# ============================================
# REPORT SCHEMAS
# ============================================


class RevenueReport(BaseModel):
    period: str
    total_revenue: Decimal
    by_workshop_type: dict[str, Decimal]
    by_location: dict[str, Decimal]
    workshop_count: int
    participant_count: int


class OccupancyReport(BaseModel):
    workshop_id: str
    display_code: str
    max_participants: int
    current_participants: int
    occupancy_rate: float
    status: WorkshopStatus


class TargetReport(BaseModel):
    workshop_type: str
    yearly_target: int
    current_count: int
    gap: int
    on_track: bool


# Update forward references
PersonResponse.model_rebuild()
WorkshopResponse.model_rebuild()
AssignmentResponse.model_rebuild()
