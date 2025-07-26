from ..services import AuthService
from ..models import UserCreate, UserResponse

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