from fastapi import APIRouter

from app.api.routes import episodes, follow_ups, owner_profiles, pets, resources

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(pets.router)
api_router.include_router(owner_profiles.router)
api_router.include_router(episodes.router)
api_router.include_router(follow_ups.router)
api_router.include_router(resources.router)
