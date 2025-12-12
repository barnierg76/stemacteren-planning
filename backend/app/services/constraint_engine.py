"""
Constraint Engine - Validatie van alle business rules

BELANGRIJK: Alle regels zijn configureerbaar via Settings tabel.
Geen hardcoded waarden in deze code.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import (
    Workshop,
    WorkshopSession,
    WorkshopType,
    Location,
    Person,
    Assignment,
    Availability,
    AvailabilityType,
    Setting,
    PersonWorkshopType,
    WorkshopTypeLocation,
)
from app.models.schemas import (
    WorkshopCreate,
    AssignmentCreate,
    ValidationResult,
    ValidationError,
)


class ConstraintEngine:
    """
    Valideert alle business rules voor planning.

    Alle regels worden geladen uit de Settings tabel,
    zodat ze via de admin interface aangepast kunnen worden.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._settings_cache: Dict[str, Any] = {}

    async def _get_setting(self, key: str, default: Any = None) -> Any:
        """Haal setting op uit cache of database"""
        if key not in self._settings_cache:
            query = select(Setting).where(Setting.key == key)
            result = await self.session.execute(query)
            setting = result.scalar_one_or_none()
            self._settings_cache[key] = setting.value if setting else default

        return self._settings_cache.get(key, default)

    async def validate_workshop(self, data: WorkshopCreate) -> ValidationResult:
        """
        Valideer een workshop tegen alle constraints.

        Returns ValidationResult met errors (blokkerend) en warnings (adviserend).
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # Load related data
        workshop_type = await self._get_workshop_type(data.type_id)
        location = await self._get_location(data.location_id)

        if not workshop_type:
            errors.append(
                ValidationError(
                    field="type_id",
                    message="Workshoptype niet gevonden",
                    severity="error",
                )
            )
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        if not location:
            errors.append(
                ValidationError(
                    field="location_id",
                    message="Locatie niet gevonden",
                    severity="error",
                )
            )
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Run all validations
        errors.extend(await self._validate_location_allowed(workshop_type, location))
        errors.extend(await self._validate_location_day(workshop_type, location, data.start_date))
        errors.extend(await self._validate_no_overlap(location, data.start_date, data.end_date, data.sessions))
        warnings.extend(await self._validate_publication_time(data.start_date))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    async def validate_assignment(self, data: AssignmentCreate) -> ValidationResult:
        """Valideer een docent/technicus toewijzing"""
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # Load related data
        person = await self._get_person(data.person_id)
        workshop = await self._get_workshop(data.workshop_id)

        if not person:
            errors.append(
                ValidationError(
                    field="person_id",
                    message="Persoon niet gevonden",
                    severity="error",
                )
            )
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        if not workshop:
            errors.append(
                ValidationError(
                    field="workshop_id",
                    message="Workshop niet gevonden",
                    severity="error",
                )
            )
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Validate person can teach this type (for instructors)
        if data.role in ["INSTRUCTOR", "CO_INSTRUCTOR"]:
            errors.extend(await self._validate_can_teach(person, workshop.type))

        # Validate no conflicts
        errors.extend(await self._validate_no_person_conflict(person, workshop))

        # Validate max days per week
        warnings.extend(await self._validate_max_days(person, workshop.start_date))

        # Validate availability
        errors.extend(await self._validate_person_available(person, workshop.start_date))

        # Check energy rules
        warnings.extend(await self._validate_energy_rules(person, workshop))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    async def validate_period(self, from_date: date, to_date: date) -> ValidationResult:
        """Valideer alle workshops in een periode"""
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # Get all workshops in period
        query = (
            select(Workshop)
            .options(
                selectinload(Workshop.type),
                selectinload(Workshop.location),
                selectinload(Workshop.sessions),
                selectinload(Workshop.assignments).selectinload(Assignment.person),
            )
            .where(
                and_(
                    Workshop.start_date >= from_date,
                    Workshop.start_date <= to_date,
                    Workshop.status != "CANCELLED",
                )
            )
        )

        result = await self.session.execute(query)
        workshops = result.scalars().all()

        for workshop in workshops:
            # Check for missing assignments
            if not workshop.assignments:
                warnings.append(
                    ValidationError(
                        field=f"workshop_{workshop.id}",
                        message=f"{workshop.display_code}: Geen docent toegewezen",
                        severity="warning",
                    )
                )

            # Check for technician if required
            if workshop.type.requires_technician:
                has_tech = any(a.role == "TECHNICIAN" for a in workshop.assignments)
                if not has_tech:
                    warnings.append(
                        ValidationError(
                            field=f"workshop_{workshop.id}",
                            message=f"{workshop.display_code}: Technicus vereist maar niet toegewezen",
                            severity="warning",
                        )
                    )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    async def find_conflicts(self, from_date: date, to_date: date) -> List[Dict]:
        """Vind alle conflicten in een periode"""
        conflicts = []

        # Location conflicts
        location_conflicts = await self._find_location_conflicts(from_date, to_date)
        conflicts.extend(location_conflicts)

        # Person conflicts (double bookings)
        person_conflicts = await self._find_person_conflicts(from_date, to_date)
        conflicts.extend(person_conflicts)

        return conflicts

    # ============================================
    # PRIVATE VALIDATION METHODS
    # ============================================

    async def _validate_location_allowed(
        self, workshop_type: WorkshopType, location: Location
    ) -> List[ValidationError]:
        """Check if workshop type is allowed at this location"""
        errors = []

        query = select(WorkshopTypeLocation).where(
            and_(
                WorkshopTypeLocation.workshop_type_id == workshop_type.id,
                WorkshopTypeLocation.location_id == location.id,
            )
        )
        result = await self.session.execute(query)

        if not result.scalar_one_or_none():
            errors.append(
                ValidationError(
                    field="location_id",
                    message=f"{workshop_type.code} is niet toegestaan in {location.name}",
                    severity="error",
                )
            )

        return errors

    async def _validate_location_day(
        self, workshop_type: WorkshopType, location: Location, start_date: date
    ) -> List[ValidationError]:
        """Check if the day is allowed for this location"""
        errors = []

        day_name = start_date.strftime("%A").lower()

        if day_name not in [d.lower() for d in location.available_days]:
            errors.append(
                ValidationError(
                    field="start_date",
                    message=f"{location.name} is niet beschikbaar op {day_name}",
                    severity="error",
                )
            )

        return errors

    async def _validate_no_overlap(
        self,
        location: Location,
        start_date: date,
        end_date: Optional[date],
        sessions: List,
    ) -> List[ValidationError]:
        """Check for overlapping workshops at the same location"""
        errors = []

        # Simple check: any workshop on the same date at same location
        query = select(Workshop).where(
            and_(
                Workshop.location_id == location.id,
                Workshop.start_date == start_date,
                Workshop.status != "CANCELLED",
            )
        )

        result = await self.session.execute(query)
        existing = result.scalars().all()

        if existing:
            errors.append(
                ValidationError(
                    field="start_date",
                    message=f"Er is al een workshop gepland in {location.name} op deze datum",
                    severity="error",
                )
            )

        return errors

    async def _validate_publication_time(self, start_date: date) -> List[ValidationError]:
        """Check if there's enough publication time"""
        warnings = []

        ideal_weeks = await self._get_setting("publication_lead_time_ideal_weeks", 8)
        min_weeks = await self._get_setting("publication_lead_time_minimum_weeks", 4)

        today = date.today()
        weeks_until = (start_date - today).days / 7

        if weeks_until < min_weeks:
            warnings.append(
                ValidationError(
                    field="start_date",
                    message=f"Minder dan {min_weeks} weken tot start (minimum publicatietijd)",
                    severity="warning",
                )
            )
        elif weeks_until < ideal_weeks:
            warnings.append(
                ValidationError(
                    field="start_date",
                    message=f"Minder dan {ideal_weeks} weken tot start (ideale publicatietijd)",
                    severity="warning",
                )
            )

        return warnings

    async def _validate_can_teach(
        self, person: Person, workshop_type: WorkshopType
    ) -> List[ValidationError]:
        """Check if person is allowed to teach this workshop type"""
        errors = []

        query = select(PersonWorkshopType).where(
            and_(
                PersonWorkshopType.person_id == person.id,
                PersonWorkshopType.workshop_type_id == workshop_type.id,
            )
        )
        result = await self.session.execute(query)

        if not result.scalar_one_or_none():
            errors.append(
                ValidationError(
                    field="person_id",
                    message=f"{person.name} mag geen {workshop_type.code} geven",
                    severity="error",
                )
            )

        return errors

    async def _validate_no_person_conflict(
        self, person: Person, workshop: Workshop
    ) -> List[ValidationError]:
        """Check if person has no conflicting assignments"""
        errors = []

        query = (
            select(Assignment)
            .join(Workshop)
            .where(
                and_(
                    Assignment.person_id == person.id,
                    Workshop.start_date == workshop.start_date,
                    Workshop.status != "CANCELLED",
                    Workshop.id != workshop.id,
                )
            )
        )

        result = await self.session.execute(query)
        conflicts = result.scalars().all()

        if conflicts:
            errors.append(
                ValidationError(
                    field="person_id",
                    message=f"{person.name} heeft al een toewijzing op deze datum",
                    severity="error",
                )
            )

        return errors

    async def _validate_max_days(
        self, person: Person, workshop_date: date
    ) -> List[ValidationError]:
        """Check if person doesn't exceed max days per week"""
        warnings = []

        if not person.max_days_per_week:
            return warnings

        # Get start and end of week
        week_start = workshop_date - timedelta(days=workshop_date.weekday())
        week_end = week_start + timedelta(days=6)

        # Count assignments this week
        query = (
            select(func.count(Assignment.id))
            .join(Workshop)
            .where(
                and_(
                    Assignment.person_id == person.id,
                    Workshop.start_date >= week_start,
                    Workshop.start_date <= week_end,
                    Workshop.status != "CANCELLED",
                )
            )
        )

        result = await self.session.execute(query)
        count = result.scalar() or 0

        if count >= person.max_days_per_week:
            warnings.append(
                ValidationError(
                    field="person_id",
                    message=f"{person.name} zit aan max ({person.max_days_per_week} dagen) deze week",
                    severity="warning",
                )
            )

        return warnings

    async def _validate_person_available(
        self, person: Person, check_date: date
    ) -> List[ValidationError]:
        """Check if person is available on this date"""
        errors = []

        query = select(Availability).where(
            and_(
                Availability.person_id == person.id,
                Availability.type == AvailabilityType.UNAVAILABLE,
                Availability.start_date <= check_date,
                Availability.end_date >= check_date,
            )
        )

        result = await self.session.execute(query)
        unavailable = result.scalar_one_or_none()

        if unavailable:
            reason = unavailable.reason or "Niet beschikbaar"
            errors.append(
                ValidationError(
                    field="person_id",
                    message=f"{person.name} is niet beschikbaar: {reason}",
                    severity="error",
                )
            )

        return errors

    async def _validate_energy_rules(
        self, person: Person, workshop: Workshop
    ) -> List[ValidationError]:
        """Check energy rules (e.g., full day bootcamp blocks evening)"""
        warnings = []

        energy_rules = await self._get_setting("energy_rules", {})

        if not energy_rules.get("full_day_bootcamp_blocks_evening", True):
            return warnings

        # Check if person has a bootcamp on the same day
        query = (
            select(Assignment)
            .join(Workshop)
            .join(WorkshopType)
            .where(
                and_(
                    Assignment.person_id == person.id,
                    Workshop.start_date == workshop.start_date,
                    WorkshopType.duration_type == "MULTI_DAY",
                    Workshop.status != "CANCELLED",
                )
            )
        )

        result = await self.session.execute(query)
        bootcamp_assignment = result.scalar_one_or_none()

        if bootcamp_assignment and workshop.type.duration_type == "EVENING_SERIES":
            warnings.append(
                ValidationError(
                    field="person_id",
                    message=f"{person.name} heeft een hele dag bootcamp, avondles wordt afgeraden",
                    severity="warning",
                )
            )

        return warnings

    # ============================================
    # HELPER METHODS
    # ============================================

    async def _get_workshop_type(self, type_id: str) -> Optional[WorkshopType]:
        query = select(WorkshopType).where(WorkshopType.id == type_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _get_location(self, location_id: str) -> Optional[Location]:
        query = select(Location).where(Location.id == location_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _get_person(self, person_id: str) -> Optional[Person]:
        query = select(Person).where(Person.id == person_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _get_workshop(self, workshop_id: str) -> Optional[Workshop]:
        query = (
            select(Workshop)
            .options(selectinload(Workshop.type))
            .where(Workshop.id == workshop_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _find_location_conflicts(
        self, from_date: date, to_date: date
    ) -> List[Dict]:
        """Find workshops at the same location on the same date"""
        conflicts = []

        # This is a simplified check - for production you'd want to check time overlap too
        query = (
            select(
                Workshop.location_id,
                Workshop.start_date,
                func.count(Workshop.id).label("count"),
            )
            .where(
                and_(
                    Workshop.start_date >= from_date,
                    Workshop.start_date <= to_date,
                    Workshop.status != "CANCELLED",
                )
            )
            .group_by(Workshop.location_id, Workshop.start_date)
            .having(func.count(Workshop.id) > 1)
        )

        result = await self.session.execute(query)
        rows = result.all()

        for row in rows:
            conflicts.append(
                {
                    "type": "location_conflict",
                    "location_id": row.location_id,
                    "date": row.start_date.isoformat(),
                    "count": row.count,
                    "message": f"Meerdere workshops ({row.count}) op dezelfde locatie/datum",
                }
            )

        return conflicts

    async def _find_person_conflicts(
        self, from_date: date, to_date: date
    ) -> List[Dict]:
        """Find persons assigned to multiple workshops on the same date"""
        conflicts = []

        query = (
            select(
                Assignment.person_id,
                Workshop.start_date,
                func.count(Assignment.id).label("count"),
            )
            .join(Workshop)
            .where(
                and_(
                    Workshop.start_date >= from_date,
                    Workshop.start_date <= to_date,
                    Workshop.status != "CANCELLED",
                )
            )
            .group_by(Assignment.person_id, Workshop.start_date)
            .having(func.count(Assignment.id) > 1)
        )

        result = await self.session.execute(query)
        rows = result.all()

        for row in rows:
            conflicts.append(
                {
                    "type": "person_conflict",
                    "person_id": row.person_id,
                    "date": row.start_date.isoformat(),
                    "count": row.count,
                    "message": f"Persoon toegewezen aan meerdere workshops ({row.count}) op dezelfde datum",
                }
            )

        return conflicts
