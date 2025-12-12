# Stemacteren.nl Workshop Planning System

AI-gestuurde workshop planning tool voor Nederland's grootste voice-over opleidingsinstituut.

## Kernprincipe

**Alles is configureerbaar, niets is hardcoded.**

Workshoptypes, locaties, teamleden, prijzen, regels - alles kan aangepast worden via de admin interface.

## Stack

- **Frontend**: Next.js 14 + Tailwind + FullCalendar
- **Backend**: Python FastAPI + SQLAlchemy
- **AI**: Claude API (Anthropic) voor conversational interface
- **Optimization**: Google OR-Tools voor scheduling
- **Database**: PostgreSQL
- **Deployment**: Railway

## Features

- Workshop planning met kalenderweergave
- AI chat interface ("Hoeveel omzet hebben we in Q1?")
- Constraint validatie (locatie, docent, beschikbaarheid)
- Team en beschikbaarheidsbeheer
- Omzet prognoses en scenario analyses

## Development

### Met Docker (aanbevolen)

```bash
# Start alle services
docker-compose up

# Seed de database met voorbeelddata
docker-compose exec backend python -m scripts.seed
```

### Lokaal

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (nieuwe terminal)
cd frontend
npm install
npm run dev

# Database seeden
cd backend
python -m scripts.seed
```

### Environment Variables

Kopieer de `.env.example` bestanden:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Belangrijke variabelen:
- `DATABASE_URL` - PostgreSQL connectie string
- `ANTHROPIC_API_KEY` - Voor AI chat functionaliteit

## Project Structuur

```
planningtool/
├── frontend/           # Next.js 14 app
│   ├── app/           # Pages en routes
│   ├── components/    # React components
│   └── lib/           # API client, utilities
├── backend/            # Python FastAPI
│   ├── app/
│   │   ├── routers/   # API endpoints
│   │   ├── services/  # Business logic
│   │   └── models/    # Database models
│   └── scripts/       # Utilities (seed, etc.)
├── shared/             # Shared schema
└── docker-compose.yml
```

## Documentatie

- [Implementatieplan](./PLAN.md)
- [Briefing](./docs/BRIEFING.md)

## API Endpoints

| Endpoint | Beschrijving |
|----------|--------------|
| `GET /api/workshops` | Lijst workshops |
| `POST /api/workshops` | Nieuwe workshop |
| `POST /api/chat` | AI chat bericht |
| `GET /api/team` | Lijst teamleden |
| `GET /api/config/workshop-types` | Workshoptypes |
| `GET /api/config/locations` | Locaties |
| `GET /api/scheduling/suggestions` | Planning suggesties |

## Status

MVP in ontwikkeling:
- [x] Database schema
- [x] Backend API (workshops, team, beschikbaarheid)
- [x] Constraint engine
- [x] AI chat service
- [x] Frontend basis (home, kalender, chat)
- [ ] Volledige UI implementatie
- [ ] Google Calendar sync
- [ ] Twilio integratie
