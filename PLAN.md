# Stemacteren.nl Workshop Planning System

## Project Overview

AI-gestuurde workshop planning tool voor Nederland's grootste voice-over opleidingsinstituut (Stemacteren.nl).

**Kernprobleem**: Handmatige planning van 5+ workshoptypes, 10 teamleden, 3 locaties met complexe constraints.

**Oplossing**: Intelligent planningssysteem met conversational AI interface.

---

## Architectuur Beslissing

**Gekozen**: Option C - Next.js Frontend + Python FastAPI AI Service

**Rationale**:
- Python heeft betere libraries voor constraint satisfaction (OR-Tools)
- AI/optimalisatie logica geïsoleerd en schaalbaar
- Railway ondersteunt beide services
- Meest robuuste oplossing voor complexe scheduling

```
┌─────────────────────────────────────────────────────────────────┐
│                         RAILWAY                                  │
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐    ┌───────────┐  │
│  │   Next.js 14     │◄──►│  FastAPI + AI    │◄──►│PostgreSQL │  │
│  │   UI/Dashboard   │    │  Claude + OR-Tools│    │   Data    │  │
│  └──────────────────┘    └──────────────────┘    └───────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## MVP Scope (Fase 1-3)

### Fase 1: Basisplanning
- Database schema (locaties, workshoptypes, team, workshops)
- Constraint engine (validatie business rules)
- Workshop CRUD met kalenderweergave
- Docent/technicus toewijzing

### Fase 2: AI Chat Interface
- Claude API integratie
- Function calling voor CRUD operaties
- Conversational interface in UI
- Bevestigingsdialogen

### Fase 3: Beschikbaarheidsbeheer
- Beschikbaarheid per teamlid
- Vakanties/uitzonderingen
- Bevestiging workflow
- Mobiele interface docenten

---

## Tech Stack

| Component | Technologie |
|-----------|-------------|
| Frontend | Next.js 14, Tailwind, shadcn/ui |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| AI | Claude API (Anthropic) |
| Constraint Solver | Google OR-Tools CP-SAT |
| Database | PostgreSQL (Railway) |
| Auth | NextAuth.js |
| Calendar UI | FullCalendar.js |

---

## Project Structuur

```
planningtool/
├── frontend/           # Next.js 14
├── backend/            # Python FastAPI
├── shared/             # Shared schema
├── docker-compose.yml  # Local dev
└── railway.toml        # Deployment
```

---

## Business Rules (Constraints)

### Locatie
- Max 1 workshop tegelijk per locatie
- Leiden: geen woensdag voor BWS

### Docent
- Moet workshoptype mogen geven
- Max dagen per week respecteren
- Energie: bootcamp-dag = geen avondles

### Publicatie
- Ideaal: 8 weken voor start
- Minimum: 4 weken voor start

### Speciaal
- BWS les 9: altijd Barnier
- Max 2 stemtesten per docent per dag

---

## Open Vragen

- [ ] Exacte technicus-vereisten per les
- [ ] Prijzen ontbrekende workshoptypes
- [ ] Google Workspace details
- [ ] CMS integratie ja/nee

---

*Versie 1.0 - December 2024*
