"""
Error Handler Middleware

Handles exceptions and provides consistent error responses.
"""

import traceback
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

settings = get_settings()


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle exceptions and provide consistent error responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and handle any exceptions.
        
        Args:
            request (Request): FastAPI request
            call_next (Callable): Next middleware/route handler
            
        Returns:
            Response: Response with error handling
        """
        try:
            response = await call_next(request)
            return response
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": True,
                    "message": e.detail,
                    "status_code": e.status_code,
                    "path": str(request.url.path)
                }
            )
            
        except ValueError as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": True,
                    "message": str(e),
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "path": str(request.url.path)
                }
            )
            
        except Exception as e:
            # Log the error in production
            if settings.ENVIRONMENT == "production":
                # In production, log the full traceback but return generic message
                print(f"Unhandled exception: {traceback.format_exc()}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "error": True,
                        "message": "Internal server error",
                        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                        "path": str(request.url.path)
                    }
                )
            else:
                # In development, return detailed error info
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "error": True,
                        "message": str(e),
                        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                        "path": str(request.url.path),
                        "traceback": traceback.format_exc() if settings.DEBUG else None
                    }
                ) 