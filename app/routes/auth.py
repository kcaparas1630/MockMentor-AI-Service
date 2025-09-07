from fastapi import APIRouter, Depends
from loguru import logger
from app.services.auth.firebase_auth import create_user
from app.errors.exceptions import InternalServerError
from sqlalchemy.orm import Session
from app.database import get_db_session
from app.schemas.auth.user_auth_schemas import PartialProfileData

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}}
)

@router.post("/register")
async def auth_endpoint(profile_data: PartialProfileData, session: Session = Depends(get_db_session)):
    """
    Auth endpoint to handle user registration and login.
    """
    try:
        logger.debug(f"Auth endpoint called with profile_data: {profile_data}")
        user = await create_user(profile_data, session)
        return {
            "message": "User created successfully",
            "user": user
        }
    except InternalServerError:
        raise
    except Exception as e:
        logger.exception("Unhandled exception in auth endpoint")
        raise InternalServerError("An unexpected error occurred in the auth endpoint.")
