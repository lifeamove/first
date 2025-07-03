from fastapi import APIRouter
from .auth import router as auth_router
from .search import router as search_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(search_router)
