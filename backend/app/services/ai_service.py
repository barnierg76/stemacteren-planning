"""
AI Service - Claude API integration voor conversational interface

Dit is een KERNFEATURE van het systeem.
Thyrza moet kunnen "praten" met het systeem in natuurlijke taal.
"""

from typing import List, Dict, Any, Optional
import json
from datetime import date, datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.database import (
    ChatSession,
    ChatMessage,
    MessageRole,
    Workshop,
    WorkshopType,
    Location,
    Person,
    Assignment,
    Setting,
)

settings = get_settings()


# Tool definitions for Claude function calling
TOOLS = [
    {
        "name": "get_workshops",
        "description": "Haal workshops op met optionele filters. Gebruik dit om te zien welke workshops gepland zijn.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["DRAFT", "PUBLISHED", "CONFIRMED", "CANCELLED", "COMPLETED"],
                    "description": "Filter op status",
                },
                "location_code": {
                    "type": "string",
                    "description": "Filter op locatie code (bijv. AMS, UTR, LEI)",
                },
                "type_code": {
                    "type": "string",
                    "description": "Filter op workshoptype (bijv. BWS, BTC, VWS)",
                },
                "from_date": {
                    "type": "string",
                    "description": "Startdatum filter (YYYY-MM-DD)",
                },
                "to_date": {
                    "type": "string",
                    "description": "Einddatum filter (YYYY-MM-DD)",
                },
            },
        },
    },
    {
        "name": "get_team_availability",
        "description": "Check beschikbaarheid van teamleden op een specifieke datum of periode.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Datum om te checken (YYYY-MM-DD)",
                },
                "person_name": {
                    "type": "string",
                    "description": "Naam van de persoon (optioneel, als leeg worden alle beschikbare mensen getoond)",
                },
            },
            "required": ["date"],
        },
    },
    {
        "name": "calculate_revenue",
        "description": "Bereken omzet voor een periode gebaseerd op geplande workshops.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_date": {
                    "type": "string",
                    "description": "Startdatum (YYYY-MM-DD)",
                },
                "to_date": {
                    "type": "string",
                    "description": "Einddatum (YYYY-MM-DD)",
                },
            },
            "required": ["from_date", "to_date"],
        },
    },
    {
        "name": "create_workshop",
        "description": "Plan een nieuwe workshop in. Vraag ALTIJD bevestiging voordat je dit uitvoert.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type_code": {
                    "type": "string",
                    "description": "Workshoptype code (BWS, BTC, VWS, etc.)",
                },
                "location_code": {
                    "type": "string",
                    "description": "Locatie code (AMS, UTR, LEI)",
                },
                "start_date": {
                    "type": "string",
                    "description": "Startdatum (YYYY-MM-DD)",
                },
                "instructor_name": {
                    "type": "string",
                    "description": "Naam van de docent (optioneel)",
                },
            },
            "required": ["type_code", "location_code", "start_date"],
        },
    },
    {
        "name": "cancel_workshop",
        "description": "Annuleer een geplande workshop. Dit vereist ALTIJD bevestiging van de gebruiker.",
        "input_schema": {
            "type": "object",
            "properties": {
                "workshop_id": {
                    "type": "string",
                    "description": "ID van de workshop om te annuleren",
                },
                "reason": {
                    "type": "string",
                    "description": "Reden voor annulering",
                },
            },
            "required": ["workshop_id"],
        },
    },
    {
        "name": "assign_instructor",
        "description": "Wijs een docent of technicus toe aan een workshop.",
        "input_schema": {
            "type": "object",
            "properties": {
                "workshop_id": {
                    "type": "string",
                    "description": "ID van de workshop",
                },
                "person_name": {
                    "type": "string",
                    "description": "Naam van de docent/technicus",
                },
                "role": {
                    "type": "string",
                    "enum": ["INSTRUCTOR", "CO_INSTRUCTOR", "GUEST", "TECHNICIAN"],
                    "description": "Rol in de workshop",
                },
            },
            "required": ["workshop_id", "person_name", "role"],
        },
    },
    {
        "name": "run_scenario",
        "description": "Voer een what-if scenario uit om de impact van wijzigingen te zien.",
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario_type": {
                    "type": "string",
                    "enum": ["add_workshops", "remove_workshop", "change_instructor"],
                    "description": "Type scenario",
                },
                "details": {
                    "type": "object",
                    "description": "Details van het scenario",
                },
            },
            "required": ["scenario_type", "details"],
        },
    },
    {
        "name": "get_workshop_suggestions",
        "description": "Krijg suggesties voor beschikbare slots om een workshop in te plannen.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type_code": {
                    "type": "string",
                    "description": "Workshoptype code",
                },
                "month": {
                    "type": "string",
                    "description": "Maand om te zoeken (YYYY-MM)",
                },
                "preferred_location": {
                    "type": "string",
                    "description": "Voorkeur locatie (optioneel)",
                },
            },
            "required": ["type_code", "month"],
        },
    },
]


class AIService:
    """
    AI Service voor conversational interface.

    Gebruikt Claude API met function calling om:
    - Vragen te beantwoorden over planning
    - Acties uit te voeren (workshops aanmaken, wijzigen)
    - Scenario's te analyseren
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._pending_actions: Dict[str, Dict] = {}

    async def create_session(self) -> ChatSession:
        """Maak een nieuwe chat sessie aan"""
        chat_session = ChatSession()
        self.session.add(chat_session)
        await self.session.flush()
        return chat_session

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Haal een chat sessie op"""
        query = select(ChatSession).where(ChatSession.id == session_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_history(self, session_id: str, limit: int = 50) -> List[ChatMessage]:
        """Haal chat geschiedenis op"""
        query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        messages = result.scalars().all()
        return list(reversed(messages))

    async def delete_session(self, session_id: str) -> None:
        """Verwijder een chat sessie"""
        query = select(ChatSession).where(ChatSession.id == session_id)
        result = await self.session.execute(query)
        session = result.scalar_one_or_none()
        if session:
            await self.session.delete(session)
            await self.session.commit()

    async def process_message(
        self, chat_session: ChatSession, user_message: str
    ) -> Dict[str, Any]:
        """
        Verwerk een gebruikersbericht en genereer een response.

        Dit is het hart van de conversational interface.
        """
        # Build conversation history
        history = await self.get_history(chat_session.id, limit=20)
        messages = self._build_messages(history, user_message)

        # Get system context
        system_prompt = await self._build_system_prompt()

        try:
            # Call Claude API
            import anthropic

            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

            response = client.messages.create(
                model=settings.claude_model,
                max_tokens=4096,
                system=system_prompt,
                tools=TOOLS,
                messages=messages,
            )

            # Process response
            return await self._process_response(response, chat_session)

        except Exception as e:
            # Fallback for when API is not configured
            return {
                "content": f"AI service niet geconfigureerd. Fout: {str(e)}. "
                "Stel de ANTHROPIC_API_KEY in om de chat functie te gebruiken.",
                "function_call": None,
                "requires_confirmation": False,
            }

    async def execute_pending_action(
        self, session_id: str, action_id: str
    ) -> Dict[str, Any]:
        """Voer een pending actie uit na bevestiging"""
        action_key = f"{session_id}:{action_id}"
        action = self._pending_actions.get(action_key)

        if not action:
            return {"error": "Actie niet gevonden of verlopen"}

        # Execute the action
        result = await self._execute_tool(action["tool"], action["input"])

        # Remove from pending
        del self._pending_actions[action_key]

        return result

    async def cancel_pending_action(self, session_id: str, action_id: str) -> None:
        """Annuleer een pending actie"""
        action_key = f"{session_id}:{action_id}"
        if action_key in self._pending_actions:
            del self._pending_actions[action_key]

    # ============================================
    # PRIVATE METHODS
    # ============================================

    def _build_messages(
        self, history: List[ChatMessage], user_message: str
    ) -> List[Dict]:
        """Bouw berichten array voor Claude API"""
        messages = []

        for msg in history:
            role = "user" if msg.role == MessageRole.USER else "assistant"
            messages.append({"role": role, "content": msg.content})

        messages.append({"role": "user", "content": user_message})

        return messages

    async def _build_system_prompt(self) -> str:
        """Bouw system prompt met actuele context"""
        # Get current stats
        workshop_count = await self._get_workshop_count()
        team_count = await self._get_team_count()

        return f"""Je bent de AI-assistent voor het Stemacteren.nl Workshop Planning Systeem.

Je helpt Thyrza (de planner) met:
- Workshops inplannen en beheren
- Team beschikbaarheid checken
- Omzet berekenen en prognoses maken
- Vragen beantwoorden over de planning

BELANGRIJK:
- Antwoord ALTIJD in het Nederlands
- Wees beknopt maar informatief
- Bij acties die data wijzigen (aanmaken, verwijderen), vraag ALTIJD eerst bevestiging
- Gebruik de tools om actuele data op te halen, maak geen aannames

HUIDIGE STATUS:
- Aantal geplande workshops: {workshop_count}
- Aantal teamleden: {team_count}

WORKSHOPTYPES (configureerbaar):
- BWS: Basisworkshop (9 avonden)
- BTC: Bootcamp (3 dagen + terugkomdag)
- VWS: Vervolgworkshop (7 seminardagen)
- IWS: Introductieworkshop (1 middag)
- AWS: Animatieworkshop (2 dagen)
- LBWS: Luisterboekenworkshop (2 dagdelen)

LOCATIES (configureerbaar):
- AMS: Amsterdam (di, wo, do)
- UTR: Utrecht (di, wo, do)
- LEI: Leiden (di, do - GEEN woensdag!)

Als je niet zeker bent, vraag dan om verduidelijking.
"""

    async def _process_response(
        self, response: Any, chat_session: ChatSession
    ) -> Dict[str, Any]:
        """Verwerk Claude API response"""
        result = {
            "content": "",
            "function_call": None,
            "function_result": None,
            "requires_confirmation": False,
            "pending_action": None,
        }

        for block in response.content:
            if block.type == "text":
                result["content"] = block.text

            elif block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input

                # Check if this is a destructive action
                destructive_actions = ["cancel_workshop", "create_workshop"]

                if tool_name in destructive_actions:
                    # Store pending action for confirmation
                    import uuid

                    action_id = str(uuid.uuid4())[:8]
                    action_key = f"{chat_session.id}:{action_id}"

                    self._pending_actions[action_key] = {
                        "tool": tool_name,
                        "input": tool_input,
                    }

                    result["requires_confirmation"] = True
                    result["pending_action"] = {
                        "action_id": action_id,
                        "tool": tool_name,
                        "description": self._describe_action(tool_name, tool_input),
                    }
                    result["content"] = self._describe_action(tool_name, tool_input)

                else:
                    # Execute non-destructive action directly
                    tool_result = await self._execute_tool(tool_name, tool_input)
                    result["function_call"] = {"name": tool_name, "input": tool_input}
                    result["function_result"] = tool_result

                    # Format result as readable text
                    result["content"] = self._format_tool_result(
                        tool_name, tool_result
                    )

        return result

    def _describe_action(self, tool_name: str, tool_input: Dict) -> str:
        """Beschrijf een actie voor bevestiging"""
        if tool_name == "cancel_workshop":
            return f"Wil je de workshop met ID {tool_input.get('workshop_id')} annuleren?"

        elif tool_name == "create_workshop":
            return (
                f"Wil je een {tool_input.get('type_code')} workshop aanmaken "
                f"in {tool_input.get('location_code')} op {tool_input.get('start_date')}?"
            )

        return f"Wil je de actie '{tool_name}' uitvoeren?"

    async def _execute_tool(self, tool_name: str, tool_input: Dict) -> Dict[str, Any]:
        """Voer een tool uit en retourneer het resultaat"""
        if tool_name == "get_workshops":
            return await self._tool_get_workshops(tool_input)

        elif tool_name == "get_team_availability":
            return await self._tool_get_availability(tool_input)

        elif tool_name == "calculate_revenue":
            return await self._tool_calculate_revenue(tool_input)

        elif tool_name == "create_workshop":
            return await self._tool_create_workshop(tool_input)

        elif tool_name == "cancel_workshop":
            return await self._tool_cancel_workshop(tool_input)

        elif tool_name == "assign_instructor":
            return await self._tool_assign_instructor(tool_input)

        elif tool_name == "get_workshop_suggestions":
            return await self._tool_get_suggestions(tool_input)

        return {"error": f"Onbekende tool: {tool_name}"}

    def _format_tool_result(self, tool_name: str, result: Dict) -> str:
        """Format tool result als leesbare tekst"""
        if "error" in result:
            return f"Er ging iets mis: {result['error']}"

        if tool_name == "get_workshops":
            workshops = result.get("workshops", [])
            if not workshops:
                return "Geen workshops gevonden met deze filters."

            lines = [f"**{len(workshops)} workshops gevonden:**\n"]
            for w in workshops[:10]:  # Limit to 10
                lines.append(
                    f"- {w['display_code']}: {w['start_date']} ({w['status']})"
                )
            if len(workshops) > 10:
                lines.append(f"\n...en nog {len(workshops) - 10} meer")
            return "\n".join(lines)

        elif tool_name == "calculate_revenue":
            return (
                f"**Omzet prognose:**\n"
                f"- Totaal: €{result.get('total', 0):,.2f}\n"
                f"- Aantal workshops: {result.get('workshop_count', 0)}"
            )

        elif tool_name == "get_team_availability":
            available = result.get("available", [])
            unavailable = result.get("unavailable", [])

            lines = [f"**Beschikbaarheid op {result.get('date')}:**\n"]

            if available:
                lines.append("Beschikbaar:")
                for p in available:
                    lines.append(f"- {p['name']}")

            if unavailable:
                lines.append("\nNiet beschikbaar:")
                for p in unavailable:
                    lines.append(f"- {p['name']}: {p.get('reason', 'Geen reden')}")

            return "\n".join(lines)

        return json.dumps(result, indent=2, default=str)

    # ============================================
    # TOOL IMPLEMENTATIONS
    # ============================================

    async def _tool_get_workshops(self, input: Dict) -> Dict:
        """Implementatie van get_workshops tool"""
        query = (
            select(Workshop)
            .options(
                selectinload(Workshop.type),
                selectinload(Workshop.location),
            )
            .order_by(Workshop.start_date)
        )

        # Apply filters
        if input.get("status"):
            query = query.where(Workshop.status == input["status"])

        if input.get("location_code"):
            query = query.join(Location).where(Location.code == input["location_code"])

        if input.get("type_code"):
            query = query.join(WorkshopType).where(
                WorkshopType.code == input["type_code"]
            )

        result = await self.session.execute(query)
        workshops = result.scalars().all()

        return {
            "workshops": [
                {
                    "id": w.id,
                    "display_code": w.display_code,
                    "type": w.type.code,
                    "location": w.location.code,
                    "start_date": w.start_date.isoformat(),
                    "status": w.status.value,
                    "participants": w.current_participants,
                }
                for w in workshops
            ]
        }

    async def _tool_get_availability(self, input: Dict) -> Dict:
        """Implementatie van get_team_availability tool"""
        check_date = datetime.strptime(input["date"], "%Y-%m-%d").date()

        # Get all active persons
        query = select(Person).where(Person.is_active == True)

        if input.get("person_name"):
            query = query.where(Person.name.ilike(f"%{input['person_name']}%"))

        result = await self.session.execute(query)
        persons = result.scalars().all()

        available = []
        unavailable = []

        for person in persons:
            # Check availability entries
            from app.models.database import Availability, AvailabilityType
            from sqlalchemy import and_

            avail_query = select(Availability).where(
                and_(
                    Availability.person_id == person.id,
                    Availability.type == AvailabilityType.UNAVAILABLE,
                    Availability.start_date <= check_date,
                    Availability.end_date >= check_date,
                )
            )
            avail_result = await self.session.execute(avail_query)
            unavail_entry = avail_result.scalar_one_or_none()

            if unavail_entry:
                unavailable.append(
                    {
                        "name": person.name,
                        "reason": unavail_entry.reason,
                    }
                )
            else:
                available.append({"name": person.name, "type": person.type.value})

        return {
            "date": input["date"],
            "available": available,
            "unavailable": unavailable,
        }

    async def _tool_calculate_revenue(self, input: Dict) -> Dict:
        """Implementatie van calculate_revenue tool"""
        from_date = datetime.strptime(input["from_date"], "%Y-%m-%d").date()
        to_date = datetime.strptime(input["to_date"], "%Y-%m-%d").date()

        query = (
            select(Workshop)
            .options(selectinload(Workshop.type))
            .where(
                Workshop.start_date >= from_date,
                Workshop.start_date <= to_date,
                Workshop.status.in_(["PUBLISHED", "CONFIRMED"]),
            )
        )

        result = await self.session.execute(query)
        workshops = result.scalars().all()

        total = sum(
            float(w.type.price) * w.current_participants for w in workshops
        )

        by_type = {}
        for w in workshops:
            code = w.type.code
            revenue = float(w.type.price) * w.current_participants
            by_type[code] = by_type.get(code, 0) + revenue

        return {
            "from_date": input["from_date"],
            "to_date": input["to_date"],
            "total": total,
            "workshop_count": len(workshops),
            "by_type": by_type,
        }

    async def _tool_create_workshop(self, input: Dict) -> Dict:
        """Implementatie van create_workshop tool"""
        # Get type and location
        type_query = select(WorkshopType).where(
            WorkshopType.code == input["type_code"]
        )
        type_result = await self.session.execute(type_query)
        workshop_type = type_result.scalar_one_or_none()

        if not workshop_type:
            return {"error": f"Workshoptype {input['type_code']} niet gevonden"}

        loc_query = select(Location).where(Location.code == input["location_code"])
        loc_result = await self.session.execute(loc_query)
        location = loc_result.scalar_one_or_none()

        if not location:
            return {"error": f"Locatie {input['location_code']} niet gevonden"}

        start_date = datetime.strptime(input["start_date"], "%Y-%m-%d").date()

        # Create workshop
        workshop = Workshop(
            type_id=workshop_type.id,
            location_id=location.id,
            start_date=start_date,
            status="DRAFT",
        )
        self.session.add(workshop)
        await self.session.commit()
        await self.session.refresh(workshop)

        return {
            "success": True,
            "workshop_id": workshop.id,
            "display_code": f"{workshop_type.code}_{workshop.display_id}_{location.code[0]}",
            "message": f"Workshop aangemaakt: {workshop_type.name} in {location.name} op {start_date}",
        }

    async def _tool_cancel_workshop(self, input: Dict) -> Dict:
        """Implementatie van cancel_workshop tool"""
        query = select(Workshop).where(Workshop.id == input["workshop_id"])
        result = await self.session.execute(query)
        workshop = result.scalar_one_or_none()

        if not workshop:
            return {"error": "Workshop niet gevonden"}

        workshop.status = "CANCELLED"
        await self.session.commit()

        return {
            "success": True,
            "message": f"Workshop {workshop.display_code} is geannuleerd",
        }

    async def _tool_assign_instructor(self, input: Dict) -> Dict:
        """Implementatie van assign_instructor tool"""
        # Find person
        query = select(Person).where(Person.name.ilike(f"%{input['person_name']}%"))
        result = await self.session.execute(query)
        person = result.scalar_one_or_none()

        if not person:
            return {"error": f"Persoon '{input['person_name']}' niet gevonden"}

        # Create assignment
        assignment = Assignment(
            workshop_id=input["workshop_id"],
            person_id=person.id,
            role=input["role"],
        )
        self.session.add(assignment)
        await self.session.commit()

        return {
            "success": True,
            "message": f"{person.name} toegewezen als {input['role']}",
        }

    async def _tool_get_suggestions(self, input: Dict) -> Dict:
        """Implementatie van get_workshop_suggestions tool"""
        # This would use the optimizer service in a full implementation
        return {
            "suggestions": [
                {
                    "date": "2025-01-14",
                    "location": "UTR",
                    "available_instructors": ["Lune van der Meulen", "Camila Alfieri"],
                    "score": 0.9,
                },
                {
                    "date": "2025-01-16",
                    "location": "AMS",
                    "available_instructors": ["Nienke Cusell"],
                    "score": 0.8,
                },
            ],
            "note": "Dit is een placeholder - volledige implementatie volgt",
        }

    # ============================================
    # HELPER METHODS
    # ============================================

    async def _get_workshop_count(self) -> int:
        """Get total active workshop count"""
        from sqlalchemy import func

        query = select(func.count(Workshop.id)).where(Workshop.status != "CANCELLED")
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _get_team_count(self) -> int:
        """Get active team member count"""
        from sqlalchemy import func

        query = select(func.count(Person.id)).where(Person.is_active == True)
        result = await self.session.execute(query)
        return result.scalar() or 0
