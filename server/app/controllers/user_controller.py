from typing import Dict, Any

from ..models import UserResponse, UserUpdate, LLMConfigUpdate
from ..services import UserSerivce

class UserController:

    def __init__(self):
        self.user_service = UserSerivce()

    async def get_profile(self, user_id: str, db_session) -> UserResponse:
        """
        Get user profile.
        
        Args:
            user_id: Current user ID
            db_session: Database session
            
        Returns:
            UserResponse: User profile information
        """
        user = await self.user_service.get_user_profile(user_id, db_session)
        return UserResponse.model_validate(user)
    
    async def update_profile(
        self, 
        user_id: str, 
        user_update: UserUpdate, 
        db_session
    ) -> UserResponse:
        """
        Update user profile.
        
        Args:
            user_id: Current user ID
            user_update: Profile update data
            db_session: Database session
            
        Returns:
            UserResponse: Updated user information
        """
        user = await self.user_service.update_user_profile(
            user_id, user_update, db_session
        )
        return UserResponse.model_validate(user)
    
    async def change_password(
        self, 
        user_id: str, 
        current_password: str, 
        new_password: str, 
        db_session
    ) -> Dict[str, str]:
        """
        Change user password.
        
        Args:
            user_id: Current user ID
            current_password: Current password
            new_password: New password
            db_session: Database session
            
        Returns:
            Dict containing success message
        """
        await self.user_service.change_password(
            user_id, current_password, new_password, db_session
        )
        return {"message": "Password changed successfully"}
    
    async def update_llm_config(
        self, 
        user_id: str, 
        llm_config: LLMConfigUpdate, 
        db_session
    ) -> Dict[str, Any]:
        """
        Update user's LLM configuration - delegates to service.
        
        Args:
            user_id: Current user ID
            llm_config: LLM configuration update data
            db_session: Database session
            
        Returns:
            Dict containing success message and updated config
        """
        return await self.user_service.update_llm_config(user_id, llm_config, db_session)
    
    async def get_llm_config(self, user_id: str, db_session) -> Dict[str, Any]:
        """
        Get user's LLM configuration - delegates to service.
        
        Args:
            user_id: Current user ID  
            db_session: Database session
            
        Returns:
            Dict containing LLM configuration
        """
        return await self.user_service.get_llm_config(user_id, db_session)