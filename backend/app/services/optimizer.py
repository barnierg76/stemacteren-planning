"""
Scheduling Optimizer - OR-Tools integratie voor optimale planning

Gebruikt Google OR-Tools CP-SAT solver voor:
- Automatische planning generatie
- Constraint satisfaction
- What-if scenario analyses
"""

from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import (
    Workshop,
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
from app.models.schemas import RevenueReport, TargetReport


class SchedulingOptimizer:
    """
    Optimizer voor workshop scheduling.

    Gebruikt OR-Tools voor complexe optimalisatie problemen.
    Alle constraints komen uit de Settings tabel.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_available_slots(
        self,
        workshop_type_id: Optional[str],
        from_date: date,
        to_date: date,
        location_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Vind beschikbare slots voor een workshop.

        Retourneert slots gesorteerd op "score" (beste opties eerst).
        """
        suggestions = []

        # Get workshop type if specified
        workshop_type = None
        if workshop_type_id:
            query = select(WorkshopType).where(WorkshopType.id == workshop_type_id)
            result = await self.session.execute(query)
            workshop_type = result.scalar_one_or_none()

        # Get locations
        loc_query = select(Location).where(Location.is_active == True)
        if location_id:
            loc_query = loc_query.where(Location.id == location_id)

        loc_result = await self.session.execute(loc_query)
        locations = loc_result.scalars().all()

        # Filter by allowed locations if workshop type specified
        if workshop_type:
            allowed_query = select(WorkshopTypeLocation.location_id).where(
                WorkshopTypeLocation.workshop_type_id == workshop_type_id
            )
            allowed_result = await self.session.execute(allowed_query)
            allowed_ids = {r[0] for r in allowed_result.all()}
            locations = [loc for loc in locations if loc.id in allowed_ids]

        # Check each day in range
        current = from_date
        while current <= to_date:
            day_name = current.strftime("%A").lower()

            for location in locations:
                # Check if location is available on this day
                if day_name not in [d.lower() for d in location.available_days]:
                    continue

                # Check if no workshop already scheduled
                workshop_query = select(Workshop).where(
                    and_(
                        Workshop.location_id == location.id,
                        Workshop.start_date == current,
                        Workshop.status != "CANCELLED",
                    )
                )
                ws_result = await self.session.execute(workshop_query)
                if ws_result.scalar_one_or_none():
                    continue

                # Find available instructors
                available_instructors = await self._find_available_instructors(
                    current, workshop_type_id
                )

                if available_instructors:
                    # Calculate score based on various factors
                    score = await self._calculate_slot_score(
                        current, location, available_instructors, workshop_type
                    )

                    suggestions.append(
                        {
                            "date": current.isoformat(),
                            "day": day_name,
                            "location": {
                                "id": location.id,
                                "code": location.code,
                                "name": location.name,
                            },
                            "available_instructors": [
                                {"id": i.id, "name": i.name}
                                for i in available_instructors[:5]
                            ],
                            "score": score,
                        }
                    )

            current += timedelta(days=1)

        # Sort by score descending
        suggestions.sort(key=lambda x: x["score"], reverse=True)

        return suggestions[:20]  # Return top 20

    async def generate_optimal_schedule(
        self,
        from_date: date,
        to_date: date,
        target_revenue: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Genereer een optimale planning voor een periode.

        Gebruikt OR-Tools CP-SAT solver.
        """
        try:
            from ortools.sat.python import cp_model

            model = cp_model.CpModel()

            # Load data
            workshop_types = await self._get_active_workshop_types()
            locations = await self._get_active_locations()
            instructors = await self._get_active_instructors()

            # Generate possible dates
            dates = []
            current = from_date
            while current <= to_date:
                if current.weekday() < 5:  # Mon-Fri
                    dates.append(current)
                current += timedelta(days=1)

            # Decision variables: workshop[type][location][date]
            workshops = {}
            for wt in workshop_types:
                for loc in locations:
                    for d in dates:
                        key = (wt.id, loc.id, d.isoformat())
                        workshops[key] = model.NewBoolVar(f"ws_{wt.code}_{loc.code}_{d}")

            # Constraint: max 1 workshop per location per day
            for loc in locations:
                for d in dates:
                    model.Add(
                        sum(
                            workshops[(wt.id, loc.id, d.isoformat())]
                            for wt in workshop_types
                        )
                        <= 1
                    )

            # Constraint: respect location available days
            for loc in locations:
                for d in dates:
                    day_name = d.strftime("%A").lower()
                    if day_name not in [ld.lower() for ld in loc.available_days]:
                        for wt in workshop_types:
                            model.Add(workshops[(wt.id, loc.id, d.isoformat())] == 0)

            # Objective: maximize revenue (or hit target)
            revenue_terms = []
            for wt in workshop_types:
                for loc in locations:
                    for d in dates:
                        key = (wt.id, loc.id, d.isoformat())
                        # Estimated revenue = price * expected participants
                        expected = min(wt.max_participants, wt.min_participants + 3)
                        revenue_terms.append(
                            workshops[key] * int(float(wt.price) * expected)
                        )

            model.Maximize(sum(revenue_terms))

            # Solve
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 30
            status = solver.Solve(model)

            if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
                # Extract solution
                scheduled = []
                for wt in workshop_types:
                    for loc in locations:
                        for d in dates:
                            key = (wt.id, loc.id, d.isoformat())
                            if solver.Value(workshops[key]):
                                scheduled.append(
                                    {
                                        "workshop_type": {
                                            "id": wt.id,
                                            "code": wt.code,
                                            "name": wt.name,
                                        },
                                        "location": {
                                            "id": loc.id,
                                            "code": loc.code,
                                            "name": loc.name,
                                        },
                                        "date": d.isoformat(),
                                    }
                                )

                total_revenue = solver.ObjectiveValue()

                return {
                    "status": "success",
                    "optimal": status == cp_model.OPTIMAL,
                    "scheduled_workshops": scheduled,
                    "total_workshops": len(scheduled),
                    "estimated_revenue": total_revenue,
                }

            else:
                return {
                    "status": "no_solution",
                    "message": "Geen haalbare planning gevonden met de huidige constraints",
                }

        except ImportError:
            return {
                "status": "error",
                "message": "OR-Tools niet geïnstalleerd. Installeer met: pip install ortools",
            }

    async def analyze_scenario(self, scenario: Dict) -> Dict[str, Any]:
        """
        Analyseer een what-if scenario.

        scenario kan bevatten:
        - add_workshops: [{"type_code": "BWS", "location_code": "AMS", "date": "2025-01-15"}]
        - remove_workshop_ids: ["id1", "id2"]
        - modify_workshops: [{"id": "...", "new_date": "..."}]
        """
        current_revenue = await self._calculate_current_revenue()

        # Calculate impact of adding workshops
        added_revenue = Decimal(0)
        if "add_workshops" in scenario:
            for ws in scenario["add_workshops"]:
                wt_query = select(WorkshopType).where(
                    WorkshopType.code == ws["type_code"]
                )
                result = await self.session.execute(wt_query)
                wt = result.scalar_one_or_none()
                if wt:
                    # Assume average occupancy
                    avg_participants = (wt.min_participants + wt.max_participants) // 2
                    added_revenue += wt.price * avg_participants

        # Calculate impact of removing workshops
        removed_revenue = Decimal(0)
        if "remove_workshop_ids" in scenario:
            for ws_id in scenario["remove_workshop_ids"]:
                query = (
                    select(Workshop)
                    .options(selectinload(Workshop.type))
                    .where(Workshop.id == ws_id)
                )
                result = await self.session.execute(query)
                ws = result.scalar_one_or_none()
                if ws:
                    removed_revenue += ws.type.price * ws.current_participants

        new_revenue = current_revenue + added_revenue - removed_revenue

        return {
            "current_revenue": float(current_revenue),
            "scenario_revenue": float(new_revenue),
            "difference": float(new_revenue - current_revenue),
            "percentage_change": (
                float((new_revenue - current_revenue) / current_revenue * 100)
                if current_revenue > 0
                else 0
            ),
            "added_revenue": float(added_revenue),
            "removed_revenue": float(removed_revenue),
        }

    async def analyze_capacity(
        self, from_date: date, to_date: date
    ) -> List[Dict[str, Any]]:
        """Analyseer capaciteit per teamlid"""
        capacity = []

        # Get all active instructors
        query = select(Person).where(
            and_(
                Person.is_active == True,
                Person.type.in_(["INSTRUCTOR", "EXTERNAL_INSTRUCTOR"]),
            )
        )
        result = await self.session.execute(query)
        instructors = result.scalars().all()

        for instructor in instructors:
            # Count assignments in period
            assign_query = (
                select(func.count(Assignment.id))
                .join(Workshop)
                .where(
                    and_(
                        Assignment.person_id == instructor.id,
                        Workshop.start_date >= from_date,
                        Workshop.start_date <= to_date,
                        Workshop.status != "CANCELLED",
                    )
                )
            )
            assign_result = await self.session.execute(assign_query)
            current_assignments = assign_result.scalar() or 0

            # Calculate available days
            weeks = (to_date - from_date).days / 7
            max_days = (
                int(instructor.max_days_per_week * weeks)
                if instructor.max_days_per_week
                else int(5 * weeks)
            )

            capacity.append(
                {
                    "person": {
                        "id": instructor.id,
                        "name": instructor.name,
                        "type": instructor.type.value,
                    },
                    "current_assignments": current_assignments,
                    "max_capacity": max_days,
                    "remaining_capacity": max_days - current_assignments,
                    "utilization": (
                        current_assignments / max_days * 100 if max_days > 0 else 0
                    ),
                }
            )

        # Sort by utilization descending
        capacity.sort(key=lambda x: x["utilization"], reverse=True)

        return capacity

    async def calculate_revenue_forecast(
        self, from_date: date, to_date: date
    ) -> RevenueReport:
        """Bereken omzetprognose"""
        query = (
            select(Workshop)
            .options(selectinload(Workshop.type), selectinload(Workshop.location))
            .where(
                and_(
                    Workshop.start_date >= from_date,
                    Workshop.start_date <= to_date,
                    Workshop.status.in_(["DRAFT", "PUBLISHED", "CONFIRMED"]),
                )
            )
        )

        result = await self.session.execute(query)
        workshops = result.scalars().all()

        total = Decimal(0)
        by_type: Dict[str, Decimal] = {}
        by_location: Dict[str, Decimal] = {}
        total_participants = 0

        for ws in workshops:
            # Use current participants or estimate
            participants = ws.current_participants or ws.type.min_participants
            revenue = ws.type.price * participants

            total += revenue
            total_participants += participants

            # By type
            type_code = ws.type.code
            by_type[type_code] = by_type.get(type_code, Decimal(0)) + revenue

            # By location
            loc_code = ws.location.code
            by_location[loc_code] = by_location.get(loc_code, Decimal(0)) + revenue

        return RevenueReport(
            period=f"{from_date.isoformat()} - {to_date.isoformat()}",
            total_revenue=total,
            by_workshop_type={k: v for k, v in by_type.items()},
            by_location={k: v for k, v in by_location.items()},
            workshop_count=len(workshops),
            participant_count=total_participants,
        )

    async def get_target_progress(self, year: int) -> List[TargetReport]:
        """Vergelijk planning met jaarlijkse targets"""
        reports = []

        # Get targets from settings
        setting_query = select(Setting).where(Setting.key == "yearly_targets")
        setting_result = await self.session.execute(setting_query)
        setting = setting_result.scalar_one_or_none()

        targets = setting.value if setting else {}

        # Get all workshop types
        types_query = select(WorkshopType).where(WorkshopType.is_active == True)
        types_result = await self.session.execute(types_query)
        workshop_types = types_result.scalars().all()

        for wt in workshop_types:
            target = targets.get(wt.code, 0)

            # Count workshops for this year
            count_query = (
                select(func.count(Workshop.id))
                .where(
                    and_(
                        Workshop.type_id == wt.id,
                        func.extract("year", Workshop.start_date) == year,
                        Workshop.status != "CANCELLED",
                    )
                )
            )
            count_result = await self.session.execute(count_query)
            current = count_result.scalar() or 0

            reports.append(
                TargetReport(
                    workshop_type=wt.code,
                    yearly_target=target,
                    current_count=current,
                    gap=target - current,
                    on_track=current >= target * (date.today().month / 12),
                )
            )

        return reports

    # ============================================
    # HELPER METHODS
    # ============================================

    async def _find_available_instructors(
        self, check_date: date, workshop_type_id: Optional[str] = None
    ) -> List[Person]:
        """Find instructors available on a date"""
        query = select(Person).where(
            and_(
                Person.is_active == True,
                Person.type.in_(["INSTRUCTOR", "EXTERNAL_INSTRUCTOR"]),
            )
        )

        result = await self.session.execute(query)
        all_instructors = result.scalars().all()

        available = []
        for instructor in all_instructors:
            # Check if can teach this type
            if workshop_type_id:
                can_teach_query = select(PersonWorkshopType).where(
                    and_(
                        PersonWorkshopType.person_id == instructor.id,
                        PersonWorkshopType.workshop_type_id == workshop_type_id,
                    )
                )
                can_teach_result = await self.session.execute(can_teach_query)
                if not can_teach_result.scalar_one_or_none():
                    continue

            # Check unavailability
            unavail_query = select(Availability).where(
                and_(
                    Availability.person_id == instructor.id,
                    Availability.type == AvailabilityType.UNAVAILABLE,
                    Availability.start_date <= check_date,
                    Availability.end_date >= check_date,
                )
            )
            unavail_result = await self.session.execute(unavail_query)
            if unavail_result.scalar_one_or_none():
                continue

            # Check no existing assignment
            assign_query = (
                select(Assignment)
                .join(Workshop)
                .where(
                    and_(
                        Assignment.person_id == instructor.id,
                        Workshop.start_date == check_date,
                        Workshop.status != "CANCELLED",
                    )
                )
            )
            assign_result = await self.session.execute(assign_query)
            if assign_result.scalar_one_or_none():
                continue

            available.append(instructor)

        return available

    async def _calculate_slot_score(
        self,
        slot_date: date,
        location: Location,
        instructors: List[Person],
        workshop_type: Optional[WorkshopType],
    ) -> float:
        """Calculate a score for a slot (higher = better)"""
        score = 1.0

        # Prefer instructors with matching preferred location
        preferred_count = sum(
            1 for i in instructors if i.preferred_location_id == location.id
        )
        score += preferred_count * 0.1

        # Prefer dates further in the future (more prep time)
        days_ahead = (slot_date - date.today()).days
        if days_ahead > 56:  # 8 weeks
            score += 0.3
        elif days_ahead > 28:  # 4 weeks
            score += 0.2

        # More available instructors = more flexibility
        score += min(len(instructors), 5) * 0.05

        return round(score, 2)

    async def _get_active_workshop_types(self) -> List[WorkshopType]:
        query = select(WorkshopType).where(WorkshopType.is_active == True)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def _get_active_locations(self) -> List[Location]:
        query = select(Location).where(Location.is_active == True)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def _get_active_instructors(self) -> List[Person]:
        query = select(Person).where(
            and_(
                Person.is_active == True,
                Person.type.in_(["INSTRUCTOR", "EXTERNAL_INSTRUCTOR"]),
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def _calculate_current_revenue(self) -> Decimal:
        """Calculate total revenue from non-cancelled workshops"""
        query = (
            select(Workshop)
            .options(selectinload(Workshop.type))
            .where(Workshop.status != "CANCELLED")
        )
        result = await self.session.execute(query)
        workshops = result.scalars().all()

        return sum(
            ws.type.price * (ws.current_participants or ws.type.min_participants)
            for ws in workshops
        )
