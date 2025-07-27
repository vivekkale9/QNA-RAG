import logging
from typing import Optional
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from ..db.postgres import User
from ..models.auth import UserCreate, UserResponse, UserLogin
from ..utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token
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
    
    async def login_user(
        self, 
        login_data: UserLogin,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Authenticate user login.
        
        Args:
            login_data: User login credentials
            client_ip: Client IP address
            db: PostgreSQL database session
            
        Returns:
            Dict[str, Any]: Authentication tokens and user info
            
        Raises:
            HTTPException: If login fails
        """
        try:
            # Get user by email
            user = await self._get_user_by_email(db, login_data.email)
            
            if not user or not verify_password(login_data.password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login failed for {login_data.email}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login failed"
            )
        
    async def refresh_token(self, refresh_token: str, db: AsyncSession) -> Dict[str, Any]:
        """
        Handle token refresh.
        
        Args:
            refresh_token: Refresh token string
            db: Database session
            
        Returns:
            Dict containing new access token and user info
            
        Raises:
            HTTPException: If refresh token is invalid or user not found
        """
        try:
            # Verify the refresh token and extract payload
            token_data = verify_refresh_token(refresh_token)
            user_id = token_data.get("user_id")
            print("user_id",user_id)
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token payload"
                )
            
            # Fetch user from PostgreSQL database
            user = await self._get_user_by_id(db, user_id)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            # Create new access and refresh tokens
            new_token_data = {"sub": user.email, "user_id": str(user.id), "role": user.role}
            
            new_access_token = create_access_token(new_token_data)
            new_refresh_token = create_refresh_token(new_token_data)
            
            # Update user's last login time
            user.last_login = datetime.now(timezone.utc)
            await db.commit()
            
            # Return token response
            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": settings.access_token_expire_minutes * 60,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "role": user.role,
                    "created_at": user.created_at,
                    "document_count": 0,  # TODO: Get actual count from MongoDB
                    "query_count": 0,     # TODO: Get actual count from MongoDB
                }
            }
            
        except HTTPException:
            # Re-raise HTTPExceptions (like invalid token)
            raise
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
    
    async def _get_user_by_id(self, db: AsyncSession, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none() 