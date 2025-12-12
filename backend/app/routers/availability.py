"""
Availability management endpoints
"""

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_async_session, Availability, Person
from app.models.schemas import (
    AvailabilityCreate,
    AvailabilityUpdate,
    AvailabilityResponse,
    AvailabilityType,
)

router = APIRouter()


@router.get("", response_model=List[AvailabilityResponse])
async def list_availability(
    person_id: Optional[str] = Query(None),
    type: Optional[AvailabilityType] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    """Lijst beschikbaarheid met filters"""
    query = select(Availability).order_by(Availability.start_date)

    if person_id:
        query = query.where(Availability.person_id == person_id)
    if type:
        query = query.where(Availability.type == type)
    if from_date:
        query = query.where(Availability.end_date >= from_date)
    if to_date:
        query = query.where(Availability.start_date <= to_date)

    result = await session.execute(query)
    return result.scalars().all()


@router.get("/person/{person_id}", response_model=List[AvailabilityResponse])
async def get_person_availability(
    person_id: str,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    """Haal beschikbaarheid op voor een specifiek persoon"""
    query = (
        select(Availability)
        .where(Availability.person_id == person_id)
        .order_by(Availability.start_date)
    )

    if from_date:
        query = query.where(Availability.end_date >= from_date)
    if to_date:
        query = query.where(Availability.start_date <= to_date)

    result = await session.execute(query)
    return result.scalars().all()


@router.post("", response_model=AvailabilityResponse)
async def create_availability(
    data: AvailabilityCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Maak nieuwe beschikbaarheid entry aan"""
    # Verify person exists
    person_query = select(Person).where(Person.id == data.person_id)
    person_result = await session.execute(person_query)
    if not person_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Persoon niet gevonden")

    # Validate date range
    if data.end_date < data.start_date:
        raise HTTPException(
            status_code=400, detail="Einddatum moet na startdatum liggen"
        )

    availability = Availability(
        person_id=data.person_id,
        type=data.type,
        start_date=data.start_date,
        end_date=data.end_date,
        recurring_pattern=data.recurring_pattern,
        reason=data.reason,
    )
    session.add(availability)
    await session.commit()
    await session.refresh(availability)

    return availability


@router.put("/{availability_id}", response_model=AvailabilityResponse)
async def update_availability(
    availability_id: str,
    data: AvailabilityUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    """Update beschikbaarheid entry"""
    query = select(Availability).where(Availability.id == availability_id)
    result = await session.execute(query)
    availability = result.scalar_one_or_none()

    if not availability:
        raise HTTPException(status_code=404, detail="Beschikbaarheid niet gevonden")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(availability, field, value)

    await session.commit()

    return availability


@router.delete("/{availability_id}")
async def delete_availability(
    availability_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Verwijder beschikbaarheid entry"""
    query = select(Availability).where(Availability.id == availability_id)
    result = await session.execute(query)
    availability = result.scalar_one_or_none()

    if not availability:
        raise HTTPException(status_code=404, detail="Beschikbaarheid niet gevonden")

    await session.delete(availability)
    await session.commit()

    return {"message": "Beschikbaarheid verwijderd", "id": availability_id}


@router.get("/check")
async def check_availability(
    person_id: str = Query(...),
    check_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Check of een persoon beschikbaar is op een specifieke datum"""
    # Find any unavailability entries that overlap with the date
    query = select(Availability).where(
        and_(
            Availability.person_id == person_id,
            Availability.type == AvailabilityType.UNAVAILABLE,
            Availability.start_date <= check_date,
            Availability.end_date >= check_date,
        )
    )

    result = await session.execute(query)
    unavailable_entries = result.scalars().all()

    if unavailable_entries:
        return {
            "available": False,
            "reason": unavailable_entries[0].reason or "Niet beschikbaar",
            "entries": [
                {
                    "id": e.id,
                    "start_date": e.start_date,
                    "end_date": e.end_date,
                    "reason": e.reason,
                }
                for e in unavailable_entries
            ],
        }

    return {"available": True, "reason": None, "entries": []}
