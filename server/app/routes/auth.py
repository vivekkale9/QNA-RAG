from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from ..controllers import AuthController
from ..db import get_postgres_database
from ..models import UserCreate, UserResponse, UserUpdate, PasswordUpdate
from ..utils import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_controller = AuthController()

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db_session = Depends(get_postgres_database)
):
    return await auth_controller.register(user_data, db_session)

@router.post("/login", response_model=dict)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db_session = Depends(get_postgres_database)
):
    client_ip = request.client.host
    return await auth_controller.login(form_data, client_ip, db_session)

@router.post("/refresh", response_model=dict)
async def refresh_token(
    refresh_token: str,
    db_session = Depends(get_postgres_database)
):
    return await auth_controller.refresh_token(refresh_token, db_session)

@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user = Depends(get_current_user),
    db_session = Depends(get_postgres_database)
):
    return await auth_controller.get_profile(current_user.id, db_session)

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user = Depends(get_current_user),
    db_session = Depends(get_postgres_database)
):
    """Update profile endpoint - delegates to controller."""
    return await auth_controller.update_profile(
        current_user.id, user_update, db_session
    )

@router.post("/change-password", response_model=dict)
async def change_password(
    password_data: PasswordUpdate,
    current_user = Depends(get_current_user),
    db_session = Depends(get_postgres_database)
):
    return await auth_controller.change_password(
        current_user.id, password_data.current_password, password_data.new_password, db_session
    )