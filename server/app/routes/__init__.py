"""
Routes package for defining API endpoints.

This module aggregates all route routers and provides a single router
for the main application to include.
"""

from fastapi import APIRouter

from . import auth

api_router = APIRouter(prefix="/rag")

api_router.include_router(auth.router, tags=["Authentication"])

__all__ = ["api_router"] 