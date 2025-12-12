"""
Team management endpoints (Persons, Assignments)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import (
    get_async_session,
    Person,
    PersonType,
    PersonWorkshopType,
    Assignment,
    WorkshopType,
)
from app.models.schemas import (
    PersonCreate,
    PersonUpdate,
    PersonResponse,
    AssignmentCreate,
    AssignmentUpdate,
    AssignmentResponse,
    ValidationResult,
)
from app.services.constraint_engine import ConstraintEngine

router = APIRouter()


# ============================================
# PERSONS
# ============================================


@router.get("", response_model=List[PersonResponse])
async def list_persons(
    type: Optional[PersonType] = Query(None),
    is_active: bool = Query(True),
    session: AsyncSession = Depends(get_async_session),
):
    """Lijst alle teamleden"""
    query = (
        select(Person)
        .options(
            selectinload(Person.preferred_location),
            selectinload(Person.can_teach).selectinload(PersonWorkshopType.workshop_type),
        )
        .where(Person.is_active == is_active)
        .order_by(Person.name)
    )

    if type:
        query = query.where(Person.type == type)

    result = await session.execute(query)
    persons = result.scalars().all()

    return [
        PersonResponse(
            id=p.id,
            name=p.name,
            email=p.email,
            phone=p.phone,
            type=p.type,
            max_days_per_week=p.max_days_per_week,
            preferred_location_id=p.preferred_location_id,
            is_active=p.is_active,
            notes=p.notes,
            created_at=p.created_at,
            updated_at=p.updated_at,
            preferred_location=p.preferred_location,
            can_teach=[pwt.workshop_type for pwt in p.can_teach],
        )
        for p in persons
    ]


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Haal een specifiek teamlid op"""
    query = (
        select(Person)
        .options(
            selectinload(Person.preferred_location),
            selectinload(Person.can_teach).selectinload(PersonWorkshopType.workshop_type),
        )
        .where(Person.id == person_id)
    )

    result = await session.execute(query)
    person = result.scalar_one_or_none()

    if not person:
        raise HTTPException(status_code=404, detail="Persoon niet gevonden")

    return PersonResponse(
        id=person.id,
        name=person.name,
        email=person.email,
        phone=person.phone,
        type=person.type,
        max_days_per_week=person.max_days_per_week,
        preferred_location_id=person.preferred_location_id,
        is_active=person.is_active,
        notes=person.notes,
        created_at=person.created_at,
        updated_at=person.updated_at,
        preferred_location=person.preferred_location,
        can_teach=[pwt.workshop_type for pwt in person.can_teach],
    )


@router.post("", response_model=PersonResponse)
async def create_person(
    data: PersonCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Maak een nieuw teamlid aan"""
    person = Person(
        name=data.name,
        email=data.email,
        phone=data.phone,
        type=data.type,
        max_days_per_week=data.max_days_per_week,
        preferred_location_id=data.preferred_location_id,
        is_active=data.is_active,
        notes=data.notes,
    )
    session.add(person)
    await session.flush()

    # Add workshop types they can teach
    for type_id in data.can_teach_type_ids:
        pwt = PersonWorkshopType(person_id=person.id, workshop_type_id=type_id)
        session.add(pwt)

    await session.commit()

    return await get_person(person.id, session)


@router.put("/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: str,
    data: PersonUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    """Update een teamlid"""
    query = select(Person).where(Person.id == person_id)
    result = await session.execute(query)
    person = result.scalar_one_or_none()

    if not person:
        raise HTTPException(status_code=404, detail="Persoon niet gevonden")

    # Update fields
    update_data = data.model_dump(exclude_unset=True, exclude={"can_teach_type_ids"})
    for field, value in update_data.items():
        setattr(person, field, value)

    # Update workshop types if provided
    if data.can_teach_type_ids is not None:
        # Remove existing
        delete_query = select(PersonWorkshopType).where(
            PersonWorkshopType.person_id == person_id
        )
        existing = await session.execute(delete_query)
        for pwt in existing.scalars().all():
            await session.delete(pwt)

        # Add new
        for type_id in data.can_teach_type_ids:
            pwt = PersonWorkshopType(person_id=person_id, workshop_type_id=type_id)
            session.add(pwt)

    await session.commit()

    return await get_person(person_id, session)


@router.delete("/{person_id}")
async def delete_person(
    person_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Deactiveer een teamlid (soft delete)"""
    query = select(Person).where(Person.id == person_id)
    result = await session.execute(query)
    person = result.scalar_one_or_none()

    if not person:
        raise HTTPException(status_code=404, detail="Persoon niet gevonden")

    person.is_active = False
    await session.commit()

    return {"message": "Persoon gedeactiveerd", "id": person_id}


# ============================================
# ASSIGNMENTS
# ============================================


@router.get("/{person_id}/assignments", response_model=List[AssignmentResponse])
async def get_person_assignments(
    person_id: str,
    status: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    """Haal alle toewijzingen van een persoon op"""
    query = (
        select(Assignment)
        .options(selectinload(Assignment.person))
        .where(Assignment.person_id == person_id)
        .order_by(Assignment.created_at.desc())
    )

    if status:
        query = query.where(Assignment.status == status)

    result = await session.execute(query)
    return result.scalars().all()


@router.post("/assignments", response_model=AssignmentResponse)
async def create_assignment(
    data: AssignmentCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Maak een nieuwe toewijzing aan"""
    # Valideer de toewijzing
    engine = ConstraintEngine(session)
    validation = await engine.validate_assignment(data)

    if not validation.is_valid:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Toewijzing voldoet niet aan constraints",
                "errors": [e.model_dump() for e in validation.errors],
            },
        )

    assignment = Assignment(
        workshop_id=data.workshop_id,
        session_id=data.session_id,
        person_id=data.person_id,
        role=data.role,
        notes=data.notes,
    )
    session.add(assignment)
    await session.commit()

    # Reload with person
    query = (
        select(Assignment)
        .options(selectinload(Assignment.person))
        .where(Assignment.id == assignment.id)
    )
    result = await session.execute(query)
    return result.scalar_one()


@router.put("/assignments/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: str,
    data: AssignmentUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    """Update een toewijzing (bijv. bevestigen/afwijzen)"""
    query = (
        select(Assignment)
        .options(selectinload(Assignment.person))
        .where(Assignment.id == assignment_id)
    )
    result = await session.execute(query)
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="Toewijzing niet gevonden")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(assignment, field, value)

    # Set confirmed_at when status changes to CONFIRMED
    if data.status == "CONFIRMED":
        from datetime import datetime

        assignment.confirmed_at = datetime.utcnow()

    await session.commit()

    return assignment


@router.delete("/assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Verwijder een toewijzing"""
    query = select(Assignment).where(Assignment.id == assignment_id)
    result = await session.execute(query)
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="Toewijzing niet gevonden")

    await session.delete(assignment)
    await session.commit()

    return {"message": "Toewijzing verwijderd", "id": assignment_id}
