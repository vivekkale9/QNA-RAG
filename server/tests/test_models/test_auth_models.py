"""
Unit tests for authentication Pydantic models.
"""

import pytest
from pydantic import ValidationError
from datetime import datetime, timezone

from app.models.auth import (
    UserCreate, UserLogin, UserResponse, UserUpdate, 
    PasswordUpdate, LLMConfigUpdate
)


@pytest.mark.unit
@pytest.mark.auth
class TestAuthModels:
    """Test cases for auth models."""

    def test_user_create_valid(self):
        """Test valid user creation model."""
        user_data = {
            "email": "test@example.com",
            "password": "strongpassword123"
        }
        user = UserCreate(**user_data)
        
        assert user.email == "test@example.com"
        assert user.password == "strongpassword123"

    def test_user_create_invalid_email(self):
        """Test user creation with invalid email."""
        user_data = {
            "email": "invalid-email",
            "password": "strongpassword123"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**user_data)
        
        assert "value is not a valid email address" in str(exc_info.value)

    def test_user_create_missing_password(self):
        """Test user creation without password."""
        user_data = {
            "email": "test@example.com"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**user_data)
        
        assert "field required" in str(exc_info.value)

    def test_user_create_weak_password(self):
        """Test user creation with weak password."""
        user_data = {
            "email": "test@example.com",
            "password": "123"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**user_data)
        
        assert "at least 8 characters" in str(exc_info.value)

    def test_user_login_valid(self):
        """Test valid user login model."""
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        login = UserLogin(**login_data)
        
        assert login.email == "test@example.com"
        assert login.password == "password123"

    def test_user_login_invalid_email(self):
        """Test user login with invalid email."""
        login_data = {
            "email": "not-an-email",
            "password": "password123"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(**login_data)
        
        assert "value is not a valid email address" in str(exc_info.value)

    def test_user_response_valid(self):
        """Test valid user response model."""
        user_data = {
            "id": "user_123",
            "email": "test@example.com",
            "role": "user",
            "created_at": datetime.now(timezone.utc),
            "document_count": 5,
            "query_count": 10
        }
        user = UserResponse(**user_data)
        
        assert user.id == "user_123"
        assert user.email == "test@example.com"
        assert user.role == "user"
        assert user.document_count == 5
        assert user.query_count == 10

    def test_user_response_defaults(self):
        """Test user response model with default values."""
        user_data = {
            "id": "user_123",
            "email": "test@example.com",
            "role": "user",
            "created_at": datetime.now(timezone.utc)
        }
        user = UserResponse(**user_data)
        
        assert user.document_count == 0
        assert user.query_count == 0

    def test_user_update_valid(self):
        """Test valid user update model."""
        update_data = {
            "first_name": "John",
            "last_name": "Doe",
            "bio": "Software developer"
        }
        update = UserUpdate(**update_data)
        
        assert update.first_name == "John"
        assert update.last_name == "Doe"
        assert update.bio == "Software developer"

    def test_user_update_partial(self):
        """Test partial user update."""
        update_data = {
            "first_name": "John"
        }
        update = UserUpdate(**update_data)
        
        assert update.first_name == "John"
        assert update.last_name is None
        assert update.bio is None

    def test_user_update_empty(self):
        """Test empty user update."""
        update = UserUpdate()
        
        assert update.first_name is None
        assert update.last_name is None
        assert update.bio is None

    def test_password_update_valid(self):
        """Test valid password update model."""
        password_data = {
            "current_password": "oldpassword123",
            "new_password": "newpassword123"
        }
        password_update = PasswordUpdate(**password_data)
        
        assert password_update.current_password == "oldpassword123"
        assert password_update.new_password == "newpassword123"

    def test_password_update_weak_new_password(self):
        """Test password update with weak new password."""
        password_data = {
            "current_password": "oldpassword123",
            "new_password": "123"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            PasswordUpdate(**password_data)
        
        assert "at least 8 characters" in str(exc_info.value)

    def test_password_update_missing_fields(self):
        """Test password update with missing fields."""
        with pytest.raises(ValidationError) as exc_info:
            PasswordUpdate(current_password="test123")
        
        assert "field required" in str(exc_info.value)

    def test_llm_config_update_valid(self):
        """Test valid LLM config update model."""
        config_data = {
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "sk-test123",
            "temperature": 0.7,
            "max_tokens": 1000
        }
        config = LLMConfigUpdate(**config_data)
        
        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.api_key == "sk-test123"
        assert config.temperature == 0.7
        assert config.max_tokens == 1000

    def test_llm_config_update_partial(self):
        """Test partial LLM config update."""
        config_data = {
            "provider": "openai",
            "model": "gpt-3.5-turbo"
        }
        config = LLMConfigUpdate(**config_data)
        
        assert config.provider == "openai"
        assert config.model == "gpt-3.5-turbo"
        assert config.api_key is None
        assert config.temperature is None

    def test_llm_config_update_invalid_temperature(self):
        """Test LLM config with invalid temperature."""
        config_data = {
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 2.5  # Should be between 0 and 2
        }
        
        with pytest.raises(ValidationError) as exc_info:
            LLMConfigUpdate(**config_data)
        
        assert "ensure this value is less than or equal to 2" in str(exc_info.value)

    def test_llm_config_update_invalid_max_tokens(self):
        """Test LLM config with invalid max_tokens."""
        config_data = {
            "provider": "openai",
            "model": "gpt-4",
            "max_tokens": -100
        }
        
        with pytest.raises(ValidationError) as exc_info:
            LLMConfigUpdate(**config_data)
        
        assert "ensure this value is greater than 0" in str(exc_info.value)

    def test_email_validation_edge_cases(self):
        """Test email validation edge cases."""
        # Valid emails
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "123@456.com"
        ]
        
        for email in valid_emails:
            user = UserCreate(email=email, password="password123")
            assert user.email == email
        
        # Invalid emails
        invalid_emails = [
            "plainaddress",
            "@missingdomain.com",
            "missing@.com",
            "spaces @domain.com",
            "double..dot@domain.com"
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                UserCreate(email=email, password="password123")

    def test_model_serialization(self):
        """Test model serialization to dict."""
        user_data = {
            "id": "user_123",
            "email": "test@example.com",
            "role": "user",
            "created_at": datetime.now(timezone.utc),
            "document_count": 5,
            "query_count": 10
        }
        user = UserResponse(**user_data)
        
        serialized = user.model_dump()
        assert isinstance(serialized, dict)
        assert serialized["id"] == "user_123"
        assert serialized["email"] == "test@example.com"

    def test_model_json_serialization(self):
        """Test model JSON serialization."""
        user_data = {
            "id": "user_123",
            "email": "test@example.com",
            "role": "user",
            "created_at": datetime.now(timezone.utc)
        }
        user = UserResponse(**user_data)
        
        json_str = user.model_dump_json()
        assert isinstance(json_str, str)
        assert "user_123" in json_str
        assert "test@example.com" in json_str 