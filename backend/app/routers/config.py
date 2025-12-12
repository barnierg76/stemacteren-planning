"""
Configuration endpoints (WorkshopTypes, Locations, Settings)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import (
    get_async_session,
    Location,
    WorkshopType,
    WorkshopTypeLocation,
    PersonWorkshopType,
    Setting,
)
from app.models.schemas import (
    LocationCreate,
    LocationUpdate,
    LocationResponse,
    WorkshopTypeCreate,
    WorkshopTypeUpdate,
    WorkshopTypeResponse,
    SettingCreate,
    SettingUpdate,
    SettingResponse,
)

router = APIRouter()


# ============================================
# LOCATIONS
# ============================================


@router.get("/locations", response_model=List[LocationResponse])
async def list_locations(
    is_active: bool = Query(True),
    session: AsyncSession = Depends(get_async_session),
):
    """Lijst alle locaties"""
    query = (
        select(Location)
        .where(Location.is_active == is_active)
        .order_by(Location.name)
    )

    result = await session.execute(query)
    return result.scalars().all()


@router.get("/locations/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Haal een specifieke locatie op"""
    query = select(Location).where(Location.id == location_id)
    result = await session.execute(query)
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(status_code=404, detail="Locatie niet gevonden")

    return location


@router.post("/locations", response_model=LocationResponse)
async def create_location(
    data: LocationCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Maak een nieuwe locatie aan"""
    # Check for duplicate code
    existing_query = select(Location).where(Location.code == data.code)
    existing = await session.execute(existing_query)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Locatie code bestaat al")

    location = Location(**data.model_dump())
    session.add(location)
    await session.commit()
    await session.refresh(location)

    return location


@router.put("/locations/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: str,
    data: LocationUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    """Update een locatie"""
    query = select(Location).where(Location.id == location_id)
    result = await session.execute(query)
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(status_code=404, detail="Locatie niet gevonden")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)

    await session.commit()

    return location


@router.delete("/locations/{location_id}")
async def delete_location(
    location_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Deactiveer een locatie (soft delete)"""
    query = select(Location).where(Location.id == location_id)
    result = await session.execute(query)
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(status_code=404, detail="Locatie niet gevonden")

    location.is_active = False
    await session.commit()

    return {"message": "Locatie gedeactiveerd", "id": location_id}


# ============================================
# WORKSHOP TYPES
# ============================================


@router.get("/workshop-types", response_model=List[WorkshopTypeResponse])
async def list_workshop_types(
    is_active: bool = Query(True),
    session: AsyncSession = Depends(get_async_session),
):
    """Lijst alle workshoptypes"""
    query = (
        select(WorkshopType)
        .options(
            selectinload(WorkshopType.allowed_locations).selectinload(
                WorkshopTypeLocation.location
            )
        )
        .where(WorkshopType.is_active == is_active)
        .order_by(WorkshopType.sort_order, WorkshopType.code)
    )

    result = await session.execute(query)
    types = result.scalars().all()

    return [
        WorkshopTypeResponse(
            id=t.id,
            code=t.code,
            name=t.name,
            description=t.description,
            duration_type=t.duration_type,
            default_start_time=t.default_start_time,
            default_end_time=t.default_end_time,
            session_count=t.session_count,
            max_participants=t.max_participants,
            min_participants=t.min_participants,
            price=t.price,
            requires_technician=t.requires_technician,
            visible_public=t.visible_public,
            visible_students=t.visible_students,
            is_active=t.is_active,
            sort_order=t.sort_order,
            created_at=t.created_at,
            updated_at=t.updated_at,
            allowed_locations=[wtl.location for wtl in t.allowed_locations],
        )
        for t in types
    ]


@router.get("/workshop-types/{type_id}", response_model=WorkshopTypeResponse)
async def get_workshop_type(
    type_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Haal een specifiek workshoptype op"""
    query = (
        select(WorkshopType)
        .options(
            selectinload(WorkshopType.allowed_locations).selectinload(
                WorkshopTypeLocation.location
            )
        )
        .where(WorkshopType.id == type_id)
    )

    result = await session.execute(query)
    wt = result.scalar_one_or_none()

    if not wt:
        raise HTTPException(status_code=404, detail="Workshoptype niet gevonden")

    return WorkshopTypeResponse(
        id=wt.id,
        code=wt.code,
        name=wt.name,
        description=wt.description,
        duration_type=wt.duration_type,
        default_start_time=wt.default_start_time,
        default_end_time=wt.default_end_time,
        session_count=wt.session_count,
        max_participants=wt.max_participants,
        min_participants=wt.min_participants,
        price=wt.price,
        requires_technician=wt.requires_technician,
        visible_public=wt.visible_public,
        visible_students=wt.visible_students,
        is_active=wt.is_active,
        sort_order=wt.sort_order,
        created_at=wt.created_at,
        updated_at=wt.updated_at,
        allowed_locations=[wtl.location for wtl in wt.allowed_locations],
    )


@router.post("/workshop-types", response_model=WorkshopTypeResponse)
async def create_workshop_type(
    data: WorkshopTypeCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Maak een nieuw workshoptype aan"""
    # Check for duplicate code
    existing_query = select(WorkshopType).where(WorkshopType.code == data.code)
    existing = await session.execute(existing_query)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Workshop code bestaat al")

    wt = WorkshopType(
        code=data.code,
        name=data.name,
        description=data.description,
        duration_type=data.duration_type,
        default_start_time=data.default_start_time,
        default_end_time=data.default_end_time,
        session_count=data.session_count,
        max_participants=data.max_participants,
        min_participants=data.min_participants,
        price=data.price,
        requires_technician=data.requires_technician,
        visible_public=data.visible_public,
        visible_students=data.visible_students,
        is_active=data.is_active,
        sort_order=data.sort_order,
    )
    session.add(wt)
    await session.flush()

    # Add allowed locations
    for loc_id in data.allowed_location_ids:
        wtl = WorkshopTypeLocation(workshop_type_id=wt.id, location_id=loc_id)
        session.add(wtl)

    # Add allowed instructors
    for instructor_id in data.allowed_instructor_ids:
        pwt = PersonWorkshopType(person_id=instructor_id, workshop_type_id=wt.id)
        session.add(pwt)

    await session.commit()

    return await get_workshop_type(wt.id, session)


@router.put("/workshop-types/{type_id}", response_model=WorkshopTypeResponse)
async def update_workshop_type(
    type_id: str,
    data: WorkshopTypeUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    """Update een workshoptype"""
    query = select(WorkshopType).where(WorkshopType.id == type_id)
    result = await session.execute(query)
    wt = result.scalar_one_or_none()

    if not wt:
        raise HTTPException(status_code=404, detail="Workshoptype niet gevonden")

    # Update basic fields
    update_data = data.model_dump(
        exclude_unset=True,
        exclude={"allowed_location_ids", "allowed_instructor_ids", "prerequisite_type_ids"},
    )
    for field, value in update_data.items():
        setattr(wt, field, value)

    # Update locations if provided
    if data.allowed_location_ids is not None:
        # Remove existing
        delete_query = select(WorkshopTypeLocation).where(
            WorkshopTypeLocation.workshop_type_id == type_id
        )
        existing = await session.execute(delete_query)
        for wtl in existing.scalars().all():
            await session.delete(wtl)

        # Add new
        for loc_id in data.allowed_location_ids:
            wtl = WorkshopTypeLocation(workshop_type_id=type_id, location_id=loc_id)
            session.add(wtl)

    await session.commit()

    return await get_workshop_type(type_id, session)


@router.delete("/workshop-types/{type_id}")
async def delete_workshop_type(
    type_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Deactiveer een workshoptype (soft delete)"""
    query = select(WorkshopType).where(WorkshopType.id == type_id)
    result = await session.execute(query)
    wt = result.scalar_one_or_none()

    if not wt:
        raise HTTPException(status_code=404, detail="Workshoptype niet gevonden")

    wt.is_active = False
    await session.commit()

    return {"message": "Workshoptype gedeactiveerd", "id": type_id}


# ============================================
# SETTINGS
# ============================================


@router.get("/settings", response_model=List[SettingResponse])
async def list_settings(
    category: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    """Lijst alle configureerbare settings"""
    query = select(Setting).order_by(Setting.category, Setting.key)

    if category:
        query = query.where(Setting.category == category)

    result = await session.execute(query)
    return result.scalars().all()


@router.get("/settings/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Haal een specifieke setting op"""
    query = select(Setting).where(Setting.key == key)
    result = await session.execute(query)
    setting = result.scalar_one_or_none()

    if not setting:
        raise HTTPException(status_code=404, detail="Setting niet gevonden")

    return setting


@router.put("/settings/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    data: SettingUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    """Update een setting"""
    query = select(Setting).where(Setting.key == key)
    result = await session.execute(query)
    setting = result.scalar_one_or_none()

    if not setting:
        raise HTTPException(status_code=404, detail="Setting niet gevonden")

    setting.value = data.value
    if data.label:
        setting.label = data.label

    await session.commit()

    return setting


@router.post("/settings", response_model=SettingResponse)
async def create_setting(
    data: SettingCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Maak een nieuwe setting aan"""
    # Check for duplicate key
    existing_query = select(Setting).where(Setting.key == data.key)
    existing = await session.execute(existing_query)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Setting key bestaat al")

    setting = Setting(**data.model_dump())
    session.add(setting)
    await session.commit()
    await session.refresh(setting)

    return setting
