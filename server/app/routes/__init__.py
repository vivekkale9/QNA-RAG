"""
Routes package for defining API endpoints.

This module aggregates all route routers and provides a single router
for the main application to include.
"""

from fastapi import APIRouter

from . import auth_routes, chat_routes, user_routes, upload_routes, admin_routes

api_router = APIRouter(prefix="/rag")

api_router.include_router(auth_routes.router, tags=["Authentication"])
api_router.include_router(user_routes.router, tags=["User"])
api_router.include_router(upload_routes.router, tags=["Document Upload"])
api_router.include_router(chat_routes.router, tags=["Chat"])
api_router.include_router(admin_routes.router, tags=["Admin"])

__all__ = ["api_router"] 