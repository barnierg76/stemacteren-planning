# Learnings - Stemacteren Workshop Planning System

## 2024-12 - MVP Development

### Wat Werkte

- **Option C architectuur** (Next.js + Python FastAPI) geeft goede scheiding tussen UI en AI/optimalisatie logica
- **SQLAlchemy async** werkt goed met FastAPI voor complexe queries
- **Pydantic v2** voor schema validatie is elegant en type-safe
- **Settings tabel pattern** voor configureerbare business rules - voorkomt hardcoding

### Wat Niet Werkte / Aandachtspunten

#### Code Duplicatie (te refactoren in volgende iteratie)
- `_get_entity` helper methods zijn 4x gedupliceerd in constraint_engine
- Availability checks staan op 3 plaatsen (constraint_engine, optimizer, ai_service)
- Tool formatting logica in ai_service is repetitief

#### Over-engineering
- AI Service doet te veel (God Object) - zou gesplitst moeten worden in:
  - API calling service
  - Tool execution service
  - Confirmation handling service
- Slot scoring weights zijn hardcoded - moeten naar Settings

### Security Bevindingen (voor productie)

**KRITIEK - Moet gefixed voor productie:**
1. Geen authenticatie op endpoints - implementeer NextAuth.js + FastAPI Security
2. CORS te permissief (`allow_credentials=True` + `allow_methods=["*"]`)
3. Geen rate limiting op AI endpoints

**HOOG:**
4. Dynamic `setattr()` zonder whitelist in update endpoints
5. Error messages lekken implementation details

**MEDIUM:**
6. Chat session isolation ontbreekt (iedereen kan elke sessie lezen)
7. Date inputs zijn strings ipv proper date types

### Patterns om te Hergebruiken

#### Configureerbare Settings Pattern
```python
# In plaats van hardcoded waarden:
if weeks_until < 4:  # HARDCODED!

# Gebruik settings:
min_weeks = await self._get_setting("publication_lead_time_minimum_weeks", 4)
if weeks_until < min_weeks:
```

#### Validation Result Pattern
```python
# Consistente validatie responses:
ValidationResult(
    is_valid=len(errors) == 0,
    errors=errors,      # Blokkerend
    warnings=warnings,  # Adviserend
)
```

### Volgende Iteratie

1. **Authenticatie** - NextAuth.js frontend, FastAPI Security backend
2. **Refactor duplicatie** - Shared availability validator
3. **Split AI Service** - Kleinere, gefocuste services
4. **Rate limiting** - slowapi voor FastAPI
5. **CORS hardening** - Expliciete origins en methods
