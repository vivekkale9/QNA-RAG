from fastapi import APIRouter, Depends

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