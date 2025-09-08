from fastapi import APIRouter, Depends
from loguru import logger
from app.core.route_limiters import limiter
from app.services.auth.firebase_auth import create_user
from app.errors.exceptions import DuplicateUserError, InternalServerError, WeakPasswordError
from sqlalchemy.orm import Session
from app.database import get_db_session
from app.schemas.auth.user_auth_schemas import PartialProfileData

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}}
)

@router.post("/register")
@limiter.limit("5/minute")  # Custom limit for this endpoint
async def auth_endpoint(profile_data: PartialProfileData, session: Session = Depends(get_db_session)):
    """
    Auth endpoint to handle user registration and login.
    """
    try:
        user = await create_user(profile_data, session)
        return {
            "message": "User created successfully",
            "user": user
        }
    
    except DuplicateUserError:
        raise
    except WeakPasswordError:
        raise
    except Exception:
        logger.exception("Unhandled exception in auth endpoint")
        raise InternalServerError("An unexpected error occurred in the auth endpoint.")
