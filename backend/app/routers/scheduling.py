"""
Scheduling & Optimization endpoints
"""

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_async_session
from app.models.schemas import ValidationResult, RevenueReport, TargetReport
from app.services.constraint_engine import ConstraintEngine
from app.services.optimizer import SchedulingOptimizer

router = APIRouter()


@router.post("/validate")
async def validate_planning(
    from_date: date,
    to_date: date,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Valideer de volledige planning voor een periode.

    Controleert:
    - Locatie conflicten
    - Docent dubbele boekingen
    - Technicus beschikbaarheid
    - Business rules (energie-regel, etc.)
    """
    engine = ConstraintEngine(session)
    result = await engine.validate_period(from_date, to_date)

    return result


@router.get("/suggestions")
async def get_suggestions(
    workshop_type_id: Optional[str] = Query(None),
    from_date: date = Query(...),
    to_date: date = Query(...),
    location_id: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Krijg suggesties voor beschikbare slots.

    Retourneert:
    - Beschikbare datums/locaties voor een workshoptype
    - Beschikbare docenten per slot
    - Score per optie (gebaseerd op voorkeuren, spreiding, etc.)
    """
    optimizer = SchedulingOptimizer(session)
    suggestions = await optimizer.find_available_slots(
        workshop_type_id=workshop_type_id,
        from_date=from_date,
        to_date=to_date,
        location_id=location_id,
    )

    return suggestions


@router.post("/optimize")
async def optimize_schedule(
    from_date: date,
    to_date: date,
    target_revenue: Optional[float] = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Genereer een optimale planning voor een periode.

    Gebruikt OR-Tools om de beste combinatie te vinden van:
    - Workshoptypes
    - Locaties
    - Docenten

    Optimaliseert voor:
    - Omzet target (indien opgegeven)
    - Docent voorkeuren
    - Spreiding over locaties
    - Minimale reistijd docenten
    """
    optimizer = SchedulingOptimizer(session)
    result = await optimizer.generate_optimal_schedule(
        from_date=from_date,
        to_date=to_date,
        target_revenue=target_revenue,
    )

    return result


@router.post("/scenario")
async def run_scenario(
    scenario: dict,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Voer een what-if scenario analyse uit.

    Scenario kan bevatten:
    - add_workshops: Workshops om toe te voegen
    - remove_workshops: Workshops om te verwijderen
    - change_location: Locatie wijzigingen

    Retourneert impact op:
    - Totale omzet
    - Bezetting docenten
    - Constraint violations
    """
    optimizer = SchedulingOptimizer(session)
    result = await optimizer.analyze_scenario(scenario)

    return result


@router.get("/conflicts")
async def get_conflicts(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Vind alle conflicten in een periode.

    Retourneert:
    - Dubbele boekingen (locatie of persoon)
    - Ontbrekende toewijzingen
    - Business rule violations
    """
    engine = ConstraintEngine(session)
    conflicts = await engine.find_conflicts(from_date, to_date)

    return conflicts


@router.get("/capacity")
async def get_capacity(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Analyseer capaciteit voor een periode.

    Retourneert per docent/technicus:
    - Huidige bezetting
    - Resterende capaciteit
    - Dagen per locatie
    """
    optimizer = SchedulingOptimizer(session)
    capacity = await optimizer.analyze_capacity(from_date, to_date)

    return capacity


@router.get("/revenue-forecast", response_model=RevenueReport)
async def get_revenue_forecast(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Bereken omzetprognose voor een periode.

    Gebaseerd op:
    - Geplande workshops
    - Huidige deelnemersaantallen
    - Verwachte conversie (BWS/BTC → VWS)
    """
    optimizer = SchedulingOptimizer(session)
    forecast = await optimizer.calculate_revenue_forecast(from_date, to_date)

    return forecast


@router.get("/targets", response_model=List[TargetReport])
async def get_target_progress(
    year: int = Query(...),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Vergelijk huidige planning met jaarlijkse targets.
    """
    optimizer = SchedulingOptimizer(session)
    progress = await optimizer.get_target_progress(year)

    return progress
