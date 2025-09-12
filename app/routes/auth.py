from fastapi import APIRouter, Depends, Request
from loguru import logger
from app.core.route_limiters import limiter
from app.services.auth.firebase_auth import create_user, get_all_users, delete_user, update_user, get_user_by_id, get_current_user_uid
from app.errors.exceptions import DuplicateUserError, InternalServerError, WeakPasswordError, UserNotFound
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
async def register_user_route(request: Request, profile_data: PartialProfileData, session: Session = Depends(get_db_session)):
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

@router.get("/users")
@limiter.limit("10/minute")  # Custom limit for this endpoint
async def get_users_route(request: Request, session: Session = Depends(get_db_session)):
    """
    Endpoint to retrieve all users.
    """
    try:
        users = await get_all_users(session)
        return {
            "users": users
        }
    
    except Exception:
        logger.exception("Unhandled exception in get users endpoint")
        raise InternalServerError("An unexpected error occurred while retrieving users.")
@router.delete("/users/{uid}")
@limiter.limit("5/minute")  # Custom limit for this endpoint
async def delete_user_route(request: Request, uid: str, session: Session = Depends(get_db_session)):
    """
    Endpoint to delete a user by their UID.
    """
    try:
        result = await delete_user(uid, session)
        return result
    
    except UserNotFound:
        raise
    except Exception:
        logger.exception("Unhandled exception in delete user endpoint")
        raise InternalServerError("An unexpected error occurred while deleting the user.")
@router.put("/users/{uid}")
@limiter.limit("5/minute")  # Custom limit for this endpoint
async def update_user_route(request: Request, uid: str, user_updates: PartialProfileData, session: Session = Depends(get_db_session)):
    """
    Endpoint to update user details by their UID.
    """
    try:
        result = update_user(uid, user_updates, session)
        return result
    
    except UserNotFound:
        raise
    except Exception:
        logger.exception("Unhandled exception in update user endpoint")
        raise InternalServerError("An unexpected error occurred while updating the user.")
@router.get("/user")
@limiter.limit("10/minute")  # Custom limit for this endpoint
async def get_user_route(request: Request, current_uid: str = Depends(get_current_user_uid)):
    """
    Endpoint to retrieve the current authenticated user.
    """
    try:
        response = await get_user_by_id(current_uid)
        return response
    except UserNotFound:
        raise
    except Exception:
        logger.exception("Unhandled exception in get user endpoint")
        raise InternalServerError("An unexpected error occurred while retrieving the user.")
