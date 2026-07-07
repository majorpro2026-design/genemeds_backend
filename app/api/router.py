from fastapi import APIRouter

from app.authentication.routes import router as authentication_router
from app.api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(authentication_router)
api_router.include_router(health_router)
