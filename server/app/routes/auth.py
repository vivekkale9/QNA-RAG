from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from ..controllers import AuthController
from ..db import get_postgres_database
from ..models import UserCreate, UserResponse

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