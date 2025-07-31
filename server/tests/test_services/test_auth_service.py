"""
Unit tests for AuthService.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import AuthService
from app.models.auth import UserCreate, UserLogin, UserResponse
from app.db.postgres import User, UserRole, UserStatus
from app.utils.auth import verify_password, create_access_token


@pytest.mark.unit
@pytest.mark.auth
class TestAuthService:
    """Test cases for AuthService."""

    async def test_register_user_success(self, auth_service, async_db_session, mock_settings):
        """Test successful user registration."""
        user_data = UserCreate(
            email="newuser@example.com",
            password="strongpassword123"
        )
        
        with patch.object(auth_service, '_get_user_by_email', return_value=None):
            with patch.object(async_db_session, 'add') as mock_add:
                with patch.object(async_db_session, 'commit') as mock_commit:
                    with patch.object(async_db_session, 'refresh') as mock_refresh:
                        # Mock the created user
                        mock_user = User(
                            id="new_user_123",
                            email=user_data.email,
                            role=UserRole.USER,
                            status=UserStatus.ACTIVE,
                            created_at=datetime.now(timezone.utc)
                        )
                        mock_refresh.side_effect = lambda user: setattr(user, 'id', 'new_user_123')
                        
                        result = await auth_service.register(user_data, async_db_session)
                        
                        assert isinstance(result, dict)
                        assert "access_token" in result
                        assert "refresh_token" in result
                        assert "user" in result
                        assert result["token_type"] == "bearer"
                        mock_add.assert_called_once()
                        mock_commit.assert_called_once()

    async def test_register_user_already_exists(self, auth_service, async_db_session):
        """Test registration with existing email."""
        user_data = UserCreate(
            email="existing@example.com",
            password="password123"
        )
        
        existing_user = User(
            id="existing_123",
            email=user_data.email,
            role=UserRole.USER,
            status=UserStatus.ACTIVE
        )
        
        with patch.object(auth_service, '_get_user_by_email', return_value=existing_user):
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.register(user_data, async_db_session)
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "already registered" in exc_info.value.detail

    async def test_login_success(self, auth_service, async_db_session, test_user, mock_settings):
        """Test successful user login."""
        login_data = UserLogin(
            email=test_user.email,
            password="testpassword123"
        )
        
        with patch.object(auth_service, '_get_user_by_email', return_value=test_user):
            with patch('app.utils.auth.verify_password', return_value=True):
                result = await auth_service.login(login_data, async_db_session)
                
                assert isinstance(result, dict)
                assert "access_token" in result
                assert "refresh_token" in result
                assert "user" in result
                assert result["token_type"] == "bearer"

    async def test_login_invalid_credentials(self, auth_service, async_db_session, test_user):
        """Test login with invalid credentials."""
        login_data = UserLogin(
            email=test_user.email,
            password="wrongpassword"
        )
        
        with patch.object(auth_service, '_get_user_by_email', return_value=test_user):
            with patch('app.utils.auth.verify_password', return_value=False):
                with pytest.raises(HTTPException) as exc_info:
                    await auth_service.login(login_data, async_db_session)
                
                assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
                assert "Invalid credentials" in exc_info.value.detail

    async def test_login_user_not_found(self, auth_service, async_db_session):
        """Test login with non-existent user."""
        login_data = UserLogin(
            email="nonexistent@example.com",
            password="password123"
        )
        
        with patch.object(auth_service, '_get_user_by_email', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.login(login_data, async_db_session)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid credentials" in exc_info.value.detail

    async def test_login_inactive_user(self, auth_service, async_db_session):
        """Test login with inactive user."""
        inactive_user = User(
            id="inactive_123",
            email="inactive@example.com",
            password_hash="hashed_password",
            role=UserRole.USER,
            status=UserStatus.INACTIVE
        )
        
        login_data = UserLogin(
            email=inactive_user.email,
            password="password123"
        )
        
        with patch.object(auth_service, '_get_user_by_email', return_value=inactive_user):
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.login(login_data, async_db_session)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Account is inactive" in exc_info.value.detail

    async def test_get_current_user_success(self, auth_service, async_db_session, test_user, test_access_token):
        """Test successful token validation and user retrieval."""
        with patch.object(auth_service, '_get_user_by_id', return_value=test_user):
            with patch('app.utils.auth.decode_access_token', return_value={"sub": test_user.id}):
                result = await auth_service.get_current_user(test_access_token, async_db_session)
                
                assert result.id == test_user.id
                assert result.email == test_user.email

    async def test_get_current_user_invalid_token(self, auth_service, async_db_session):
        """Test token validation with invalid token."""
        with patch('app.utils.auth.decode_access_token', side_effect=HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )):
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.get_current_user("invalid_token", async_db_session)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_current_user_not_found(self, auth_service, async_db_session, test_access_token):
        """Test token validation when user doesn't exist."""
        with patch('app.utils.auth.decode_access_token', return_value={"sub": "nonexistent_id"}):
            with patch.object(auth_service, '_get_user_by_id', return_value=None):
                with pytest.raises(HTTPException) as exc_info:
                    await auth_service.get_current_user(test_access_token, async_db_session)
                
                assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
                assert "User not found" in exc_info.value.detail

    async def test_refresh_token_success(self, auth_service, async_db_session, test_user, mock_settings):
        """Test successful token refresh."""
        refresh_token = create_access_token(
            data={"sub": test_user.id, "type": "refresh"},
            secret_key=mock_settings.secret_key,
            expires_delta=timedelta(days=7)
        )
        
        with patch.object(auth_service, '_get_user_by_id', return_value=test_user):
            with patch('app.utils.auth.decode_access_token', return_value={"sub": test_user.id, "type": "refresh"}):
                result = await auth_service.refresh_token(refresh_token, async_db_session)
                
                assert isinstance(result, dict)
                assert "access_token" in result
                assert "refresh_token" in result
                assert result["token_type"] == "bearer"

    async def test_refresh_token_invalid_type(self, auth_service, async_db_session, test_access_token):
        """Test refresh with access token instead of refresh token."""
        with patch('app.utils.auth.decode_access_token', return_value={"sub": "user_id", "type": "access"}):
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.refresh_token(test_access_token, async_db_session)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid refresh token" in exc_info.value.detail

    async def test_get_user_by_id(self, auth_service, async_db_session, test_user):
        """Test internal method to get user by ID."""
        with patch.object(async_db_session, 'get', return_value=test_user):
            result = await auth_service._get_user_by_id(async_db_session, test_user.id)
            
            assert result == test_user
            async_db_session.get.assert_called_once_with(User, test_user.id)

    async def test_get_user_by_email(self, auth_service, async_db_session, test_user):
        """Test internal method to get user by email."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = test_user
        
        with patch.object(async_db_session, 'execute', return_value=mock_result):
            result = await auth_service._get_user_by_email(async_db_session, test_user.email)
            
            assert result == test_user
            async_db_session.execute.assert_called_once() 