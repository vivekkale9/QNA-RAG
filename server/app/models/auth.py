from typing import Optional
from datetime import datetime
from pydantic import Field, EmailStr, BaseModel

class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User email address")

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    role: str = Field(default="user", description="User role (user/admin)")

class UserResponse(UserBase):
    id: str = Field(..., description="User ID")
    role: str = Field(..., description="User role")
    created_at: datetime = Field(..., description="Account creation timestamp")
    document_count: int = Field(default=0, description="Number of uploaded documents")
    query_count: int = Field(default=0, description="Total number of queries made")

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    """Model for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")