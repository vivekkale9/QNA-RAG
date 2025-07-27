from fastapi import APIRouter, Depends

from ..controllers import UserController
from ..db import get_postgres_database
from ..models import UserResponse, UserUpdate, PasswordUpdate, LLMConfigUpdate
from ..utils import get_current_user, require_role

router = APIRouter(prefix="/user", tags=["User"])
user_controller = UserController()

@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user = Depends(get_current_user),
    db_session = Depends(get_postgres_database)
):
    return await user_controller.get_profile(current_user.id, db_session)

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user = Depends(get_current_user),
    db_session = Depends(get_postgres_database)
):
    return await user_controller.update_profile(
        current_user.id, user_update, db_session
    )

@router.post("/change-password", response_model=dict)
async def change_password(
    password_data: PasswordUpdate,
    current_user = Depends(get_current_user),
    db_session = Depends(get_postgres_database)
):
    return await user_controller.change_password(
        current_user.id, password_data.current_password, password_data.new_password, db_session
    )

@router.put("/llm-config", response_model=dict)
async def update_llm_config(
    llm_config: LLMConfigUpdate,
    current_user = Depends(require_role("admin")),
    db_session = Depends(get_postgres_database)
):
    return await user_controller.update_llm_config(
        current_user.id, llm_config, db_session
    ) 

@router.get("/llm-config", response_model=dict)
async def get_llm_config(
    current_user = Depends(require_role("admin")),
    db_session = Depends(get_postgres_database)
):
    return await user_controller.get_llm_config(current_user.id, db_session)