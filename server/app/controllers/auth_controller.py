from typing import Dict, Any
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ..services import AuthService
from ..models import UserCreate, UserResponse, UserLogin
from ..utils import create_user_token
from ..middlewares import rate_limiter

class AuthController:

    def __init__(self):
        self.auth_service = AuthService()

    async def register(self, user_data: UserCreate, db_session) -> UserResponse:
        """
        Handle user registration.
        
        Args:
            user_data: User registration data
            db_session: Database session
            
        Returns:
            UserResponse: Created user information
        """
        user = await self.auth_service.register_user(user_data, db_session)
        return user
    
    async def login(
        self, 
        form_data: OAuth2PasswordRequestForm, 
        client_ip: str,
        db_session
    ) -> Dict[str, Any]:
        """
        Handle user login.
        
        Args:
            form_data: OAuth2 login form data
            client_ip: Client IP address for rate limiting
            db_session: Database session
            
        Returns:
            Dict containing access token and user info
        """
        try:
            # Authenticate user via service
            user = await self.auth_service.login_user(
                login_data=UserLogin(
                    email=form_data.username,
                    password=form_data.password
                ),
                db=db_session,
            )
            
            # Create tokens
            token_data = create_user_token(user)

            user_dict = {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
            }
            
            return {
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "token_type": "bearer",
                "expires_in": token_data["expires_in"],
                "user": user_dict
            }
            
        except Exception as e:
            # Record failed login attempt for rate limiting
            rate_limiter.record_failed_login(client_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
    async def refresh_token(self, refresh_token: str, db: AsyncSession) -> Dict[str, Any]:
        """
        Handle token refresh - delegates to service.
        
        Args:
            refresh_token: Refresh token string
            db: Database session
            
        Returns:
            Dict containing new access token and user info
        """
        return await self.auth_service.refresh_token(refresh_token, db)