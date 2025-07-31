"""
Unit tests for UserService.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.services.user_service import UserSerivce
from app.models.auth import UserResponse, UserUpdate, PasswordUpdate, LLMConfigUpdate
from app.db.postgres import User, UserRole, UserStatus


@pytest.mark.unit
@pytest.mark.auth
class TestUserService:
    """Test cases for UserService."""

    async def test_get_user_profile_success(self, user_service, async_db_session, test_user):
        """Test successful user profile retrieval."""
        with patch.object(user_service.auth_service, '_get_user_by_id', return_value=test_user):
            result = await user_service.get_user_profile(test_user.id, async_db_session)
            
            assert isinstance(result, UserResponse)
            assert result.id == test_user.id
            assert result.email == test_user.email

    async def test_get_user_profile_not_found(self, user_service, async_db_session):
        """Test user profile retrieval when user doesn't exist."""
        with patch.object(user_service.auth_service, '_get_user_by_id', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await user_service.get_user_profile("nonexistent_user", async_db_session)
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert "User not found" in exc_info.value.detail

    async def test_update_user_profile_success(self, user_service, async_db_session, test_user):
        """Test successful user profile update."""
        update_data = UserUpdate(
            first_name="John",
            last_name="Doe"
        )
        
        with patch.object(user_service.auth_service, '_get_user_by_id', return_value=test_user):
            with patch.object(async_db_session, 'commit') as mock_commit:
                with patch.object(async_db_session, 'refresh') as mock_refresh:
                    result = await user_service.update_user_profile(
                        test_user.id, update_data, async_db_session
                    )
                    
                    assert isinstance(result, UserResponse)
                    assert test_user.first_name == "John"
                    assert test_user.last_name == "Doe"
                    mock_commit.assert_called_once()
                    mock_refresh.assert_called_once()

    async def test_update_user_profile_not_found(self, user_service, async_db_session):
        """Test user profile update when user doesn't exist."""
        update_data = UserUpdate(first_name="John")
        
        with patch.object(user_service.auth_service, '_get_user_by_id', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await user_service.update_user_profile(
                    "nonexistent_user", update_data, async_db_session
                )
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_change_password_success(self, user_service, async_db_session, test_user):
        """Test successful password change."""
        password_data = PasswordUpdate(
            current_password="testpassword123",
            new_password="newpassword123"
        )
        
        with patch.object(user_service.auth_service, '_get_user_by_id', return_value=test_user):
            with patch('app.utils.auth.verify_password', return_value=True):
                with patch('app.utils.auth.hash_password', return_value="new_hashed_password"):
                    with patch.object(async_db_session, 'commit') as mock_commit:
                        result = await user_service.change_password(
                            test_user.id, password_data, async_db_session
                        )
                        
                        assert result["message"] == "Password updated successfully"
                        assert test_user.password_hash == "new_hashed_password"
                        mock_commit.assert_called_once()

    async def test_change_password_invalid_current(self, user_service, async_db_session, test_user):
        """Test password change with invalid current password."""
        password_data = PasswordUpdate(
            current_password="wrongpassword",
            new_password="newpassword123"
        )
        
        with patch.object(user_service.auth_service, '_get_user_by_id', return_value=test_user):
            with patch('app.utils.auth.verify_password', return_value=False):
                with pytest.raises(HTTPException) as exc_info:
                    await user_service.change_password(
                        test_user.id, password_data, async_db_session
                    )
                
                assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
                assert "Current password is incorrect" in exc_info.value.detail

    async def test_change_password_user_not_found(self, user_service, async_db_session):
        """Test password change when user doesn't exist."""
        password_data = PasswordUpdate(
            current_password="testpassword123",
            new_password="newpassword123"
        )
        
        with patch.object(user_service.auth_service, '_get_user_by_id', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await user_service.change_password(
                    "nonexistent_user", password_data, async_db_session
                )
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_llm_config_success(self, user_service, async_db_session, test_user):
        """Test successful LLM configuration update."""
        llm_config = LLMConfigUpdate(
            provider="openai",
            model="gpt-4",
            api_key="test_api_key",
            temperature=0.7
        )
        
        with patch.object(user_service.auth_service, '_get_user_by_id', return_value=test_user):
            with patch.object(async_db_session, 'commit') as mock_commit:
                with patch.object(async_db_session, 'refresh') as mock_refresh:
                    result = await user_service.update_llm_config(
                        test_user.id, llm_config, async_db_session
                    )
                    
                    assert result["message"] == "LLM configuration updated successfully"
                    assert test_user.llm_provider == "openai"
                    assert test_user.llm_model == "gpt-4"
                    mock_commit.assert_called_once()

    async def test_update_llm_config_user_not_found(self, user_service, async_db_session):
        """Test LLM config update when user doesn't exist."""
        llm_config = LLMConfigUpdate(provider="openai", model="gpt-4")
        
        with patch.object(user_service.auth_service, '_get_user_by_id', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await user_service.update_llm_config(
                    "nonexistent_user", llm_config, async_db_session
                )
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_user_stats_success(self, user_service, async_db_session, test_user):
        """Test successful user statistics retrieval."""
        with patch.object(user_service.auth_service, '_get_user_by_id', return_value=test_user):
            with patch('app.db.mongodb.Document.find') as mock_find_docs:
                mock_find_docs.return_value.count.return_value = AsyncMock(return_value=5)
                with patch('app.db.mongodb.Conversation.find') as mock_find_convs:
                    mock_find_convs.return_value.count.return_value = AsyncMock(return_value=3)
                    with patch('app.db.mongodb.QueryLog.find') as mock_find_queries:
                        mock_find_queries.return_value.count.return_value = AsyncMock(return_value=10)
                        
                        result = await user_service.get_user_stats(test_user.id, async_db_session)
                        
                        assert result["document_count"] == 5
                        assert result["conversation_count"] == 3
                        assert result["query_count"] == 10

    async def test_get_user_stats_user_not_found(self, user_service, async_db_session):
        """Test user stats retrieval when user doesn't exist."""
        with patch.object(user_service.auth_service, '_get_user_by_id', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await user_service.get_user_stats("nonexistent_user", async_db_session)
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_deactivate_account_success(self, user_service, async_db_session, test_user):
        """Test successful account deactivation."""
        with patch.object(user_service.auth_service, '_get_user_by_id', return_value=test_user):
            with patch.object(async_db_session, 'commit') as mock_commit:
                result = await user_service.deactivate_account(test_user.id, async_db_session)
                
                assert result["message"] == "Account deactivated successfully"
                assert test_user.status == UserStatus.INACTIVE
                mock_commit.assert_called_once()

    async def test_deactivate_account_user_not_found(self, user_service, async_db_session):
        """Test account deactivation when user doesn't exist."""
        with patch.object(user_service.auth_service, '_get_user_by_id', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await user_service.deactivate_account("nonexistent_user", async_db_session)
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_reactivate_account_success(self, user_service, async_db_session, test_user):
        """Test successful account reactivation."""
        test_user.status = UserStatus.INACTIVE
        
        with patch.object(user_service.auth_service, '_get_user_by_id', return_value=test_user):
            with patch.object(async_db_session, 'commit') as mock_commit:
                result = await user_service.reactivate_account(test_user.id, async_db_session)
                
                assert result["message"] == "Account reactivated successfully"
                assert test_user.status == UserStatus.ACTIVE
                mock_commit.assert_called_once()

    async def test_delete_account_success(self, user_service, async_db_session, test_user):
        """Test successful account deletion."""
        with patch.object(user_service.auth_service, '_get_user_by_id', return_value=test_user):
            with patch('app.db.mongodb.Document.find') as mock_find_docs:
                mock_find_docs.return_value.delete_many = AsyncMock()
                with patch('app.db.mongodb.Conversation.find') as mock_find_convs:
                    mock_find_convs.return_value.delete_many = AsyncMock()
                    with patch('app.db.mongodb.QueryLog.find') as mock_find_logs:
                        mock_find_logs.return_value.delete_many = AsyncMock()
                        with patch.object(async_db_session, 'delete') as mock_delete:
                            with patch.object(async_db_session, 'commit') as mock_commit:
                                result = await user_service.delete_account(
                                    test_user.id, async_db_session
                                )
                                
                                assert result["message"] == "Account deleted successfully"
                                mock_delete.assert_called_once_with(test_user)
                                mock_commit.assert_called_once()

    async def test_delete_account_user_not_found(self, user_service, async_db_session):
        """Test account deletion when user doesn't exist."""
        with patch.object(user_service.auth_service, '_get_user_by_id', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await user_service.delete_account("nonexistent_user", async_db_session)
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND 