import logging
from typing import Dict, Any
from fastapi import HTTPException, status
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from .auth_service import AuthService
from ..models.auth import UserResponse, UserUpdate, LLMConfigUpdate
from ..utils.auth import (
    hash_password,
    verify_password
)

settings = get_settings()
logger = logging.getLogger(__name__)

class UserSerivce:

    def __init__(self):
        self.auth_service = AuthService()

    async def get_user_profile(
        self, 
        user_id: str, 
        db: AsyncSession
    ) -> UserResponse:
        """
        Get user profile information.
        
        Args:
            user_id: User ID
            db: PostgreSQL database session
            
        Returns:
            UserResponse: User profile information
            
        Raises:
            HTTPException: If user not found
        """
        try:
            user = await self.auth_service._get_user_by_id(db, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Calculate activity counts
            from ..db.mongodb import get_mongodb_database
            mongo_db = await get_mongodb_database()
            
            # Count documents uploaded by user
            document_count = await mongo_db["documents"].count_documents({"user_id": user_id})
            
            # Count total queries made by user
            query_count = await mongo_db["query_logs"].count_documents({"user_id": user_id})
            
            return UserResponse(
                id=str(user.id),
                email=user.email,
                role=user.role,
                created_at=user.created_at,
                document_count=document_count,
                query_count=query_count
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get profile failed for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve profile"
            )
        
    async def update_user_profile(
        self, 
        user_id: str, 
        update_data: UserUpdate, 
        db: AsyncSession
    ) -> UserResponse:
        """
        Update user profile information.
        
        Args:
            user_id: User ID
            update_data: Profile update data
            db: PostgreSQL database session
            
        Returns:
            UserResponse: Updated user information
            
        Raises:
            HTTPException: If update fails
        """
        try:
            user = await self.auth_service._get_user_by_id(db, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Update fields if provided
            if update_data.full_name is not None:
                user.full_name = update_data.full_name
            if update_data.role is not None:
                user.role = update_data.role
            
            if update_data.email is not None:
                # Check if new email is already taken
                existing_user = await self.auth_service._get_user_by_email(db, update_data.email)
                if existing_user and existing_user.id != user.id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already in use"
                    )
                user.email = update_data.email
            
            user.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(user)
            
            logger.info(f"Profile updated for user: {user.email}")
            
            # Calculate activity counts
            from ..db.mongodb import get_mongodb_database
            mongo_db = await get_mongodb_database()
            
            # Count documents uploaded by user
            document_count = await mongo_db["documents"].count_documents({"user_id": user_id})
            
            # Count total queries made by user
            query_count = await mongo_db["query_logs"].count_documents({"user_id": user_id})
            
            return UserResponse(
                id=str(user.id),
                email=user.email,
                role=user.role,
                created_at=user.created_at,
                document_count=document_count,
                query_count=query_count
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Profile update failed for user {user_id}: {str(e)}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Profile update failed"
            )
        
    async def change_password(
        self, 
        user_id: str, 
        current_password: str, 
        new_password: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Change user password.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            db: PostgreSQL database session
            
        Returns:
            Dict[str, Any]: Success message
            
        Raises:
            HTTPException: If password change fails
        """
        try:
            user = await self.auth_service._get_user_by_id(db, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Verify current password
            if not verify_password(current_password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            
            # Update password
            user.hashed_password = hash_password(new_password)
            user.updated_at = datetime.now(timezone.utc)
            await db.commit()
            
            logger.info(f"Password changed for user: {user.email}")
            
            return {"message": "Password changed successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Password change failed for user {user_id}: {str(e)}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password change failed"
            )
        
    async def update_llm_config(
        self, 
        user_id: str, 
        llm_config: LLMConfigUpdate, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Update user's LLM configuration.
        
        Args:
            user_id: User ID
            llm_config: LLM configuration update data
            db: Database session
            
        Returns:
            Dict containing success message and updated config
            
        Raises:
            HTTPException: If user not found or update fails
        """
        try:
            user = await self.auth_service._get_user_by_id(db, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Build the LLM config dictionary
            config_dict = {}
            if llm_config.model:
                config_dict["model"] = llm_config.model
            if llm_config.api_key:
                config_dict["api_key"] = llm_config.api_key
            if llm_config.max_tokens:
                config_dict["max_tokens"] = llm_config.max_tokens
            if llm_config.base_url:
                config_dict["base_url"] = llm_config.base_url
            
            # Update user's LLM configuration
            if llm_config.llm_provider:
                user.llm_provider = llm_config.llm_provider
            
            if config_dict:
                # Merge with existing config if it exists
                existing_config = user.llm_config or {}
                existing_config.update(config_dict)
                user.llm_config = existing_config
            
            user.updated_at = datetime.now(timezone.utc)
            await db.commit()
            
            logger.info(f"Updated LLM config for user {user_id}")
            
            return {
                "message": "LLM configuration updated successfully",
                "llm_provider": user.llm_provider,
                "llm_config": user.llm_config
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"LLM config update failed for user {user_id}: {str(e)}")
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LLM configuration update failed"
            )
        
    async def get_llm_config(self, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        """
        Get user's LLM configuration.
        
        Args:
            user_id: User ID
            db: Database session
            
        Returns:
            Dict containing LLM configuration
            
        Raises:
            HTTPException: If user not found
        """
        try:
            user = await self.auth_service._get_user_by_id(db, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return {
                "llm_provider": user.llm_provider,
                "llm_config": user.llm_config or {},
                "is_configured": bool(user.llm_provider and user.llm_config)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get LLM config failed for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve LLM configuration"
            )