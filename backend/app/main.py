"""
Stemacteren Workshop Planning System - FastAPI Backend
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import workshops, team, availability, config, chat, scheduling


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Stemacteren Planning API...")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="Stemacteren Workshop Planning API",
    description="AI-gestuurde workshop planning voor Stemacteren.nl",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(workshops.router, prefix=f"{settings.api_prefix}/workshops", tags=["Workshops"])
app.include_router(team.router, prefix=f"{settings.api_prefix}/team", tags=["Team"])
app.include_router(availability.router, prefix=f"{settings.api_prefix}/availability", tags=["Availability"])
app.include_router(config.router, prefix=f"{settings.api_prefix}/config", tags=["Configuration"])
app.include_router(chat.router, prefix=f"{settings.api_prefix}/chat", tags=["AI Chat"])
app.include_router(scheduling.router, prefix=f"{settings.api_prefix}/scheduling", tags=["Scheduling"])


@app.get("/")
async def root():
    return {
        "name": "Stemacteren Workshop Planning API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
