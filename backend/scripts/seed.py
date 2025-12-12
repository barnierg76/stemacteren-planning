"""
Seed script - Vul database met initiële configureerbare data

BELANGRIJK: Dit is VOORBEELDDATA gebaseerd op de briefing.
Alle gegevens zijn configureerbaar via de admin interface.

Run: python -m scripts.seed
"""

import asyncio
from decimal import Decimal
from datetime import date

from sqlalchemy import select
from app.models.database import (
    Base,
    engine,
    async_session_maker,
    Location,
    Person,
    PersonType,
    WorkshopType,
    DurationType,
    WorkshopTypeLocation,
    PersonWorkshopType,
    Setting,
)


async def seed_locations():
    """Seed locaties - configureerbaar"""
    async with async_session_maker() as session:
        # Check if already seeded
        result = await session.execute(select(Location))
        if result.scalars().first():
            print("Locaties al aanwezig, overslaan...")
            return

        locations = [
            Location(
                code="AMS",
                name="Amsterdam",
                address="Donauweg 10, 1043 AJ Amsterdam",
                available_days=["tuesday", "wednesday", "thursday"],
                is_active=True,
            ),
            Location(
                code="UTR",
                name="Utrecht",
                address="Ondiep-Zuidzijde 6, 3551 BW Utrecht",
                available_days=["tuesday", "wednesday", "thursday"],
                is_active=True,
            ),
            Location(
                code="LEI",
                name="Leiden",
                address="Middelstegracht 89u, 2312 TT Leiden",
                available_days=["tuesday", "thursday"],  # Geen woensdag!
                is_active=True,
            ),
        ]

        for loc in locations:
            session.add(loc)

        await session.commit()
        print(f"✓ {len(locations)} locaties toegevoegd")


async def seed_workshop_types():
    """Seed workshoptypes - configureerbaar"""
    async with async_session_maker() as session:
        result = await session.execute(select(WorkshopType))
        if result.scalars().first():
            print("Workshoptypes al aanwezig, overslaan...")
            return

        types = [
            WorkshopType(
                code="BWS",
                name="Basisworkshop",
                description="9 avondlessen voice-over basics",
                duration_type=DurationType.EVENING_SERIES,
                default_start_time="19:30",
                default_end_time="22:00",
                session_count=9,
                max_participants=10,
                min_participants=5,
                price=Decimal("1195.00"),
                requires_technician=False,  # Niet alle lessen
                visible_public=True,
                visible_students=True,
                sort_order=1,
            ),
            WorkshopType(
                code="BTC",
                name="Bootcamp",
                description="3 intensieve dagen + terugkomdag",
                duration_type=DurationType.MULTI_DAY,
                default_start_time="10:00",
                default_end_time="17:00",
                session_count=4,  # 3 dagen + terugkomdag
                max_participants=10,
                min_participants=5,
                price=Decimal("1195.00"),
                requires_technician=True,
                visible_public=True,
                visible_students=True,
                sort_order=2,
            ),
            WorkshopType(
                code="VWS",
                name="Vervolgworkshop",
                description="7 seminardagen voor gevorderden",
                duration_type=DurationType.MULTI_DAY,
                default_start_time="13:00",
                default_end_time="17:00",
                session_count=7,
                max_participants=10,
                min_participants=5,
                price=Decimal("4000.00"),
                requires_technician=False,  # Wisselend
                visible_public=True,  # Alleen op uitnodiging
                visible_students=True,
                sort_order=3,
            ),
            WorkshopType(
                code="IWS",
                name="Introductieworkshop",
                description="1 middag kennismaken met voice-over",
                duration_type=DurationType.HALF_DAY,
                default_start_time="12:30",
                default_end_time="16:00",
                session_count=1,
                max_participants=12,
                min_participants=4,
                price=Decimal("99.00"),  # Placeholder
                requires_technician=False,
                visible_public=True,
                visible_students=True,
                sort_order=4,
            ),
            WorkshopType(
                code="AWS",
                name="Animatieworkshop",
                description="2 dagen animatie voice-over",
                duration_type=DurationType.MULTI_DAY,
                default_start_time="10:00",
                default_end_time="17:00",
                session_count=2,
                max_participants=6,
                min_participants=3,
                price=Decimal("750.00"),
                requires_technician=True,  # Verplicht voor animatie
                visible_public=True,
                visible_students=True,
                sort_order=5,
            ),
            WorkshopType(
                code="LBWS",
                name="Luisterboekenworkshop",
                description="2 dagdelen luisterboeken",
                duration_type=DurationType.HALF_DAY,
                default_start_time="10:00",
                default_end_time="15:00",
                session_count=2,
                max_participants=6,
                min_participants=3,
                price=Decimal("500.00"),  # Placeholder
                requires_technician=True,
                visible_public=True,
                visible_students=True,
                sort_order=6,
            ),
        ]

        for wt in types:
            session.add(wt)

        await session.commit()
        print(f"✓ {len(types)} workshoptypes toegevoegd")


async def seed_workshop_type_locations():
    """Koppel workshoptypes aan locaties"""
    async with async_session_maker() as session:
        result = await session.execute(select(WorkshopTypeLocation))
        if result.scalars().first():
            print("Workshop-locatie koppelingen al aanwezig, overslaan...")
            return

        # Get IDs
        locs = await session.execute(select(Location))
        locations = {loc.code: loc.id for loc in locs.scalars().all()}

        types = await session.execute(select(WorkshopType))
        workshop_types = {wt.code: wt.id for wt in types.scalars().all()}

        # BWS, BTC, IWS: alle locaties
        for code in ["BWS", "BTC", "IWS"]:
            for loc_code in ["AMS", "UTR", "LEI"]:
                session.add(
                    WorkshopTypeLocation(
                        workshop_type_id=workshop_types[code],
                        location_id=locations[loc_code],
                    )
                )

        # VWS: alleen AMS en UTR
        for loc_code in ["AMS", "UTR"]:
            session.add(
                WorkshopTypeLocation(
                    workshop_type_id=workshop_types["VWS"],
                    location_id=locations[loc_code],
                )
            )

        # AWS: AMS en UTR
        for loc_code in ["AMS", "UTR"]:
            session.add(
                WorkshopTypeLocation(
                    workshop_type_id=workshop_types["AWS"],
                    location_id=locations[loc_code],
                )
            )

        # LBWS: alleen AMS
        session.add(
            WorkshopTypeLocation(
                workshop_type_id=workshop_types["LBWS"],
                location_id=locations["AMS"],
            )
        )

        await session.commit()
        print("✓ Workshop-locatie koppelingen toegevoegd")


async def seed_team():
    """Seed teamleden - configureerbaar"""
    async with async_session_maker() as session:
        result = await session.execute(select(Person))
        if result.scalars().first():
            print("Teamleden al aanwezig, overslaan...")
            return

        # Get location IDs
        locs = await session.execute(select(Location))
        locations = {loc.code: loc.id for loc in locs.scalars().all()}

        team = [
            # Interne docenten
            Person(
                name="Lune van der Meulen",
                type=PersonType.INSTRUCTOR,
                max_days_per_week=2,
                preferred_location_id=locations["UTR"],
                notes="Kan BWS, BTC, VWS, IWS geven",
            ),
            Person(
                name="Malou Oosterhof",
                type=PersonType.INSTRUCTOR,
                max_days_per_week=3,
                preferred_location_id=locations["LEI"],
                notes="Junior docent, nog in ontwikkeling. Kan BWS, BTC, soms IWS",
            ),
            Person(
                name="Nienke Cusell",
                type=PersonType.INSTRUCTOR,
                max_days_per_week=2,
                notes="Medior/senior. Kan BWS, BTC, VWS, IWS geven",
            ),
            Person(
                name="Camila Alfieri",
                type=PersonType.INSTRUCTOR,
                max_days_per_week=3,
                notes="Medior/senior. Kan BWS, BTC, VWS, IWS geven",
            ),
            Person(
                name="Thyrza van Dieijen",
                type=PersonType.INSTRUCTOR,
                max_days_per_week=1,
                notes="Educatiemanager - alleen in noodgevallen lesgeven",
            ),
            Person(
                name="Barnier Geerling",
                type=PersonType.INSTRUCTOR,
                max_days_per_week=2,
                notes="Directeur. Afsluitende les BWS (les 9), 1 seminardag VWS. Max 2/week.",
            ),
            # Externe docenten
            Person(
                name="Jürgen Theuns",
                type=PersonType.EXTERNAL_INSTRUCTOR,
                notes="Animatie specialist - AWS, VAWS",
            ),
            Person(
                name="Sander de Heer",
                type=PersonType.EXTERNAL_INSTRUCTOR,
                notes="Luisterboeken/Storytelling - LBWS, VLBWS",
            ),
            Person(
                name="Louis van Beek",
                type=PersonType.EXTERNAL_INSTRUCTOR,
                notes="Luisterboeken - VLBWS",
            ),
            Person(
                name="Beatrijs Sluijter",
                type=PersonType.EXTERNAL_INSTRUCTOR,
                notes="Animatie - gastles in AWS",
            ),
            Person(
                name="Alex Boon",
                type=PersonType.EXTERNAL_INSTRUCTOR,
                notes="Stem en Spraak - gastlessen",
            ),
            # Technici
            Person(
                name="Rinus van Diemen",
                type=PersonType.TECHNICIAN,
                max_days_per_week=4,
                preferred_location_id=locations["LEI"],
                notes="32u/week, voorkeur Leiden",
            ),
            Person(
                name="Jan Farha",
                type=PersonType.TECHNICIAN,
                max_days_per_week=4,
                notes="32u/week, alle locaties",
            ),
            Person(
                name="Jasper Hartsuijker",
                type=PersonType.TECHNICIAN,
                max_days_per_week=1,
                notes="MT-lid, alleen noodgevallen",
            ),
        ]

        for person in team:
            session.add(person)

        await session.commit()
        print(f"✓ {len(team)} teamleden toegevoegd")


async def seed_person_workshop_types():
    """Koppel docenten aan workshoptypes die ze mogen geven"""
    async with async_session_maker() as session:
        result = await session.execute(select(PersonWorkshopType))
        if result.scalars().first():
            print("Docent-workshop koppelingen al aanwezig, overslaan...")
            return

        # Get IDs
        persons = await session.execute(select(Person))
        people = {p.name: p.id for p in persons.scalars().all()}

        types = await session.execute(select(WorkshopType))
        workshop_types = {wt.code: wt.id for wt in types.scalars().all()}

        # Mapping: wie mag wat geven
        mappings = {
            "Lune van der Meulen": ["BWS", "BTC", "VWS", "IWS"],
            "Malou Oosterhof": ["BWS", "BTC", "IWS"],
            "Nienke Cusell": ["BWS", "BTC", "VWS", "IWS"],
            "Camila Alfieri": ["BWS", "BTC", "VWS", "IWS"],
            "Thyrza van Dieijen": ["BWS", "BTC", "VWS"],
            "Barnier Geerling": ["BWS", "VWS"],
            "Jürgen Theuns": ["AWS"],
            "Sander de Heer": ["LBWS"],
        }

        for person_name, type_codes in mappings.items():
            if person_name not in people:
                continue
            for code in type_codes:
                if code not in workshop_types:
                    continue
                session.add(
                    PersonWorkshopType(
                        person_id=people[person_name],
                        workshop_type_id=workshop_types[code],
                    )
                )

        await session.commit()
        print("✓ Docent-workshop koppelingen toegevoegd")


async def seed_settings():
    """Seed configureerbare settings"""
    async with async_session_maker() as session:
        result = await session.execute(select(Setting))
        if result.scalars().first():
            print("Settings al aanwezig, overslaan...")
            return

        settings = [
            # Publicatie
            Setting(
                key="publication_lead_time_ideal_weeks",
                value=8,
                category="publication",
                label="Ideale publicatietijd (weken voor start)",
            ),
            Setting(
                key="publication_lead_time_minimum_weeks",
                value=4,
                category="publication",
                label="Minimum publicatietijd (weken voor start)",
            ),
            Setting(
                key="workshop_full_weeks_before_start",
                value=4,
                category="publication",
                label="Workshop moet X weken voor start vol zijn",
            ),
            # Targets
            Setting(
                key="yearly_targets",
                value={"BWS": 32, "BTC": 19, "VWS": 15, "AWS": 10, "LBWS": 6},
                category="targets",
                label="Jaarlijkse targets per workshoptype",
            ),
            # Conversie
            Setting(
                key="conversion_rates",
                value={"BWS_to_VWS": 0.30, "BTC_to_VWS": 0.30},
                category="funnel",
                label="Conversiepercentages doorstroom",
            ),
            # Energie regels
            Setting(
                key="energy_rules",
                value={
                    "full_day_bootcamp_blocks_evening": True,
                    "max_stemtests_per_instructor_per_day": 2,
                },
                category="constraints",
                label="Energie en belasting regels",
            ),
            # Calendar
            Setting(
                key="calendar_event_format",
                value={
                    "title": "{CODE}_{ID}_{LOC} - {NAME} ({LOCATION})",
                    "sync_tag": "[SYNC-ICS-LESSON]<!-- UID={UID}@stemacteren.nl-->",
                },
                category="calendar",
                label="Google Calendar event format",
            ),
        ]

        for setting in settings:
            session.add(setting)

        await session.commit()
        print(f"✓ {len(settings)} settings toegevoegd")


async def main():
    """Run all seed functions"""
    print("\n🌱 Database seeding starten...\n")

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Database tabellen aangemaakt\n")

    # Seed in order (dependencies)
    await seed_locations()
    await seed_workshop_types()
    await seed_workshop_type_locations()
    await seed_team()
    await seed_person_workshop_types()
    await seed_settings()

    print("\n✅ Database seeding voltooid!\n")
    print("Je kunt nu de applicatie starten met:")
    print("  docker-compose up")
    print("  of")
    print("  cd backend && uvicorn app.main:app --reload")


if __name__ == "__main__":
    asyncio.run(main())
