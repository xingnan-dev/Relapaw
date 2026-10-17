from fastapi import APIRouter

from app.api.routes import analysis, baselines, capabilities, episodes, follow_ups, memory, owner_profiles, pets, resources

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(capabilities.router)
api_router.include_router(pets.router)
api_router.include_router(owner_profiles.router)
api_router.include_router(episodes.router)
api_router.include_router(follow_ups.router)
api_router.include_router(resources.router)
api_router.include_router(analysis.router)
api_router.include_router(memory.router)
api_router.include_router(baselines.router)
