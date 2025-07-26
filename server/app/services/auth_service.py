import logging
from typing import Optional
from fastapi import HTTPException, status
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from ..db.postgres import User
from ..models.auth import UserCreate, UserResponse
from ..utils.auth import (
    hash_password
)

settings = get_settings()
logger = logging.getLogger(__name__)

class AuthService:

    async def register_user(
        self, 
        user_data: UserCreate, 
        db: AsyncSession
    ) -> UserResponse:
        """
        Register a new user.
        
        Args:
            user_data: User registration data
            db: PostgreSQL database session
            
        Returns:
            UserResponse: Created user information
            
        Raises:
            HTTPException: If registration fails
        """
        try:
            # Check if user already exists
            existing_user = await self._get_user_by_email(db, user_data.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )
            
            # Create new user
            user = User(
                email=user_data.email,
                hashed_password=hash_password(user_data.password),
                role="user",  # Default role
            )
            
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            logger.info(f"User registered successfully: {user.email}")
            
            return UserResponse(
                id=str(user.id),
                email=user.email,
                role=user.role,
                created_at=user.created_at,
                status=user.status,
                updated_at=user.updated_at,
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User registration failed: {str(e)}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed"
            )
        
    async def _get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()