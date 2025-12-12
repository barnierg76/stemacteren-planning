"""
Workshop CRUD endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import (
    get_async_session,
    Workshop,
    WorkshopSession,
    WorkshopType,
    Location,
    Assignment,
)
from app.models.schemas import (
    WorkshopCreate,
    WorkshopUpdate,
    WorkshopResponse,
    WorkshopListResponse,
    WorkshopSessionCreate,
    WorkshopSessionResponse,
    ValidationResult,
)
from app.services.constraint_engine import ConstraintEngine

router = APIRouter()


@router.get("", response_model=List[WorkshopListResponse])
async def list_workshops(
    status: Optional[str] = Query(None),
    location_id: Optional[str] = Query(None),
    type_id: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    session: AsyncSession = Depends(get_async_session),
):
    """Lijst alle workshops met filters"""
    query = (
        select(Workshop)
        .options(
            selectinload(Workshop.type),
            selectinload(Workshop.location),
        )
        .order_by(Workshop.start_date.desc())
        .limit(limit)
        .offset(offset)
    )

    if status:
        query = query.where(Workshop.status == status)
    if location_id:
        query = query.where(Workshop.location_id == location_id)
    if type_id:
        query = query.where(Workshop.type_id == type_id)

    result = await session.execute(query)
    workshops = result.scalars().all()

    return [
        WorkshopListResponse(
            id=w.id,
            display_id=w.display_id,
            display_code=w.display_code,
            start_date=w.start_date,
            end_date=w.end_date,
            status=w.status,
            current_participants=w.current_participants,
            type=w.type,
            location=w.location,
        )
        for w in workshops
    ]


@router.get("/{workshop_id}", response_model=WorkshopResponse)
async def get_workshop(
    workshop_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Haal een specifieke workshop op"""
    query = (
        select(Workshop)
        .options(
            selectinload(Workshop.type),
            selectinload(Workshop.location),
            selectinload(Workshop.sessions),
            selectinload(Workshop.assignments).selectinload(Assignment.person),
        )
        .where(Workshop.id == workshop_id)
    )

    result = await session.execute(query)
    workshop = result.scalar_one_or_none()

    if not workshop:
        raise HTTPException(status_code=404, detail="Workshop niet gevonden")

    return workshop


@router.post("", response_model=WorkshopResponse)
async def create_workshop(
    data: WorkshopCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Maak een nieuwe workshop aan"""
    # Valideer constraints
    engine = ConstraintEngine(session)
    validation = await engine.validate_workshop(data)

    if not validation.is_valid:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Workshop voldoet niet aan constraints",
                "errors": [e.model_dump() for e in validation.errors],
            },
        )

    # Maak workshop aan
    workshop = Workshop(
        type_id=data.type_id,
        location_id=data.location_id,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status,
        current_participants=data.current_participants,
        notes=data.notes,
    )
    session.add(workshop)
    await session.flush()  # Get the ID

    # Maak sessies aan
    for session_data in data.sessions:
        ws_session = WorkshopSession(
            workshop_id=workshop.id,
            session_number=session_data.session_number,
            date=session_data.date,
            start_time=session_data.start_time,
            end_time=session_data.end_time,
            requires_technician=session_data.requires_technician,
            notes=session_data.notes,
        )
        session.add(ws_session)

    await session.commit()

    # Reload with relations
    return await get_workshop(workshop.id, session)


@router.put("/{workshop_id}", response_model=WorkshopResponse)
async def update_workshop(
    workshop_id: str,
    data: WorkshopUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    """Update een workshop"""
    query = select(Workshop).where(Workshop.id == workshop_id)
    result = await session.execute(query)
    workshop = result.scalar_one_or_none()

    if not workshop:
        raise HTTPException(status_code=404, detail="Workshop niet gevonden")

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workshop, field, value)

    await session.commit()

    return await get_workshop(workshop_id, session)


@router.delete("/{workshop_id}")
async def delete_workshop(
    workshop_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Verwijder een workshop (of markeer als geannuleerd)"""
    query = select(Workshop).where(Workshop.id == workshop_id)
    result = await session.execute(query)
    workshop = result.scalar_one_or_none()

    if not workshop:
        raise HTTPException(status_code=404, detail="Workshop niet gevonden")

    # Soft delete: markeer als geannuleerd
    workshop.status = "CANCELLED"
    await session.commit()

    return {"message": "Workshop geannuleerd", "id": workshop_id}


@router.post("/validate", response_model=ValidationResult)
async def validate_workshop(
    data: WorkshopCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Valideer workshop zonder op te slaan"""
    engine = ConstraintEngine(session)
    return await engine.validate_workshop(data)


@router.get("/{workshop_id}/sessions", response_model=List[WorkshopSessionResponse])
async def get_workshop_sessions(
    workshop_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Haal alle sessies van een workshop op"""
    query = (
        select(WorkshopSession)
        .where(WorkshopSession.workshop_id == workshop_id)
        .order_by(WorkshopSession.session_number)
    )

    result = await session.execute(query)
    return result.scalars().all()
