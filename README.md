# Stemacteren.nl Workshop Planning System

AI-gestuurde workshop planning tool voor Nederland's grootste voice-over opleidingsinstituut.

## Stack

- **Frontend**: Next.js 14 + Tailwind + shadcn/ui
- **Backend**: Python FastAPI + OR-Tools + Claude API
- **Database**: PostgreSQL
- **Deployment**: Railway

## Development

```bash
# Start alle services
docker-compose up

# Of apart:
cd frontend && npm run dev
cd backend && uvicorn app.main:app --reload
```

## Documentatie

- [Implementatieplan](./PLAN.md)
- [Briefing](./docs/BRIEFING.md)

## Status

🚧 In ontwikkeling - Fase 1 (Basisplanning)
