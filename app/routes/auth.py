"""Authentication Routes Module

This module defines FastAPI routes for user authentication and management.
Provides endpoints for user registration, retrieval, updates, and deletion
with Firebase authentication integration.

The module contains route handlers that manage user authentication workflows,
including registration, user management, and protected endpoint access. It serves
as the primary interface for authentication operations in the application's API layer.

Dependencies:
- fastapi: For API routing and dependency injection.
- loguru: For logging operations.
- app.core.route_limiters: For rate limiting middleware.
- app.services.auth.firebase_auth: For Firebase authentication services.
- app.errors.exceptions: For custom exception handling.
- app.schemas.auth.user_auth_schemas: For user authentication data models.

Author: @kcaparas1630
"""

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPBearer
from loguru import logger
from app.core.route_limiters import limiter
from app.services.auth.firebase_auth import create_user, get_all_users, delete_user, update_user, get_user_by_id, get_current_user_uid, google_auth_controller
from app.errors.exceptions import DuplicateUserError, InternalServerError, WeakPasswordError, UserNotFound, ValidationError
from sqlalchemy.orm import Session
from app.database import get_db_session
from app.schemas.auth.user_auth_schemas import PartialProfileData

# Security scheme
security = HTTPBearer()

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}}
)

@router.post("/register")
@limiter.limit("5/minute")  # Custom limit for this endpoint
async def register_user_route(request: Request, profile_data: PartialProfileData, session: Session = Depends(get_db_session)):
    """Register a new user with Firebase authentication and database storage.
    
    Creates a new user account in both Firebase Auth and the application database.
    The operation is atomic - if either fails, both are rolled back.
    
    Args:
        request (Request): FastAPI request object for rate limiting
        profile_data (PartialProfileData): User registration data
        session (Session): Database session dependency
        
    Returns:
        dict: Success message and user data
        
    Raises:
        DuplicateUserError: If user with email already exists
        WeakPasswordError: If password doesn't meet requirements
        InternalServerError: If registration fails
        
    Rate Limit:
        5 requests per minute per client
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
    except Exception as e:
        logger.exception("Unhandled exception in auth endpoint")
        raise InternalServerError("An unexpected error occurred in the auth endpoint.") from e

@router.get("/users")
@limiter.limit("10/minute")  # Custom limit for this endpoint
async def get_users_route(request: Request, session: Session = Depends(get_db_session)):
    """Retrieve all registered users from the database.
    
    Returns a list of all users with their profile information.
    
    Args:
        request (Request): FastAPI request object for rate limiting
        session (Session): Database session dependency
        
    Returns:
        dict: Dictionary containing list of users
        
    Raises:
        InternalServerError: If database query fails
        
    Rate Limit:
        10 requests per minute per client
    """
    try:
        users = await get_all_users(session)
        return {
            "users": users
        }
    
    except Exception as e:
        logger.exception("Unhandled exception in get users endpoint")
        raise InternalServerError("An unexpected error occurred while retrieving users.") from e
@router.delete("/users/{uid}")
@limiter.limit("5/minute")  # Custom limit for this endpoint
async def delete_user_route(request: Request, uid: str, session: Session = Depends(get_db_session)):
    """Delete a user by their Firebase UID.
    
    Removes the user from both Firebase Auth and the application database.
    
    Args:
        request (Request): FastAPI request object for rate limiting
        uid (str): Firebase UID of the user to delete
        session (Session): Database session dependency
        
    Returns:
        dict: Success message
        
    Raises:
        UserNotFound: If user with given UID doesn't exist
        InternalServerError: If deletion fails
        
    Rate Limit:
        5 requests per minute per client
    """
    try:
        result = await delete_user(uid, session)
        return result
    
    except UserNotFound:
        raise
    except Exception as e:
        logger.exception("Unhandled exception in delete user endpoint")
        raise InternalServerError("An unexpected error occurred while deleting the user.") from e
@router.put("/users/{uid}")
@limiter.limit("5/minute")  # Custom limit for this endpoint
async def update_user_route(request: Request, uid: str, user_updates: PartialProfileData, session: Session = Depends(get_db_session)):
    """Update user profile information by Firebase UID.
    
    Updates user profile data in the database. Only provided fields are updated.
    
    Args:
        request (Request): FastAPI request object for rate limiting
        uid (str): Firebase UID of the user to update
        user_updates (PartialProfileData): Profile data to update
        session (Session): Database session dependency
        
    Returns:
        dict: Success message
        
    Raises:
        UserNotFound: If user with given UID doesn't exist
        InternalServerError: If update fails
        
    Rate Limit:
        5 requests per minute per client
    """
    try:
        result = await update_user(uid, user_updates, session)
        return result
    
    except UserNotFound:
        raise
    except Exception as e:
        logger.exception("Unhandled exception in update user endpoint")
        raise InternalServerError("An unexpected error occurred while updating the user.") from e
@router.get("/user")
@limiter.limit("10/minute")  # Custom limit for this endpoint
async def get_user_route(request: Request, current_uid: str = Depends(get_current_user_uid), token: str = Depends(security)):
    """Retrieve the current authenticated user's information.
    
    Returns Firebase user data and generates a custom token for the authenticated user.
    Requires valid Firebase ID token in Authorization header.
    
    Args:
        request (Request): FastAPI request object for rate limiting
        current_uid (str): Firebase UID extracted from token (dependency)
        token (str): Bearer token from Authorization header (dependency)
        
    Returns:
        dict: Firebase user data and custom token
        
    Raises:
        HTTPException: 401 if token is missing, invalid, or expired
        UserNotFound: If user doesn't exist in Firebase
        InternalServerError: If Firebase operations fail
        
    Rate Limit:
        10 requests per minute per client
        
    Authentication:
        Requires Bearer token in Authorization header
    """
    try:
        response = await get_user_by_id(current_uid)
        return response
    except UserNotFound:
        raise
    except Exception as e:
        logger.exception("Unhandled exception in get user endpoint")
        raise InternalServerError("An unexpected error occurred while retrieving the user.") from e
@router.post("/google-signin")
@limiter.limit("10/minute")  # Custom limit for this endpoint
async def google_signin_route(request: Request, session: Session = Depends(get_db_session)):
    """Handle Google Sign-In authentication.
    
    This endpoint is a placeholder for handling Google Sign-In authentication.
    The actual implementation would involve verifying the Google ID token,
    creating or retrieving the user in Firebase and the application database,
    and returning the appropriate user data and tokens.
    
    Args:
        request (Request): FastAPI request object for rate limiting
        session (Session): Database session dependency
        
    Returns:
        dict: Placeholder message indicating unimplemented functionality
        
    Raises:
        InternalServerError: If any error occurs during the process
        
    Rate Limit:
        10 requests per minute per client
    """
    try:
        # Get request body
        body = await request.json()
        id_token = body.get("idToken")

        if not id_token:
            raise ValidationError("ID token is required for Google Sign-In.")
        
        # Process Google authentication
        result = await google_auth_controller(id_token, session)
        return result
        
    except ValidationError:
        raise
    except DuplicateUserError:
        raise
    except Exception as e:
        logger.exception("Unhandled exception in google signin endpoint")
        raise InternalServerError("An unexpected error occurred during Google Sign-In.") from e
