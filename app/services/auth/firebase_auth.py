"""Firebase Authentication Service Module

This module provides Firebase authentication services including user creation,
verification, and management. It integrates Firebase Auth with the application's
database to maintain user records and profiles.

The module contains functions for Firebase ID token verification, user registration,
and comprehensive user management operations. It serves as the primary interface
for Firebase authentication in the application's auth service layer.

Dependencies:
- firebase_admin: For Firebase authentication and user management.
- sqlalchemy: For database operations and session management.
- loguru: For logging operations.
- app.schemas.auth.user_auth_schemas: For user authentication data models.
- app.models.user_models: For User and Profile database models.
- app.errors.exceptions: For custom exception handling.

Author: @kcaparas1630
"""

import firebase_admin
from firebase_admin import auth, credentials
from firebase_admin.exceptions import InvalidArgumentError
from app.schemas.auth.user_auth_schemas import PartialProfileData
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, DataError, OperationalError
from app.models.user_models import User, Profile
from app.errors.exceptions import DuplicateUserError, WeakPasswordError, InternalServerError, UserNotFound, ValidationError
from fastapi import Request, HTTPException
import os
from loguru import logger

file_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
# Check if credentials exists
if not os.path.exists(file_path):
    logger.error(f"Firebase credentials file not found at {file_path}")
    raise FileNotFoundError(f"Firebase credentials file not found at {file_path}")

cred = credentials.Certificate(file_path)
firebase_admin.initialize_app(cred)

def verify_id_token(id_token: str):
    """Verify Firebase ID token and extract user information.
    
    Args:
        id_token (str): Firebase ID token to verify
        
    Returns:
        tuple: (decoded_token, uid) if valid, (None, None) if invalid
        
    Note:
        Checks if token is revoked using check_revoked=True parameter
    """
    try: 
        decoded_token = auth.verify_id_token(id_token, check_revoked=True)
        uid = decoded_token['uid']
        return decoded_token, uid
    except auth.InvalidIdTokenError:
        # Token is invalid, expired or revoked.
        return None, None

def get_current_user_uid(request: Request):
    """Extract and verify Firebase ID token from request headers.
    
    This function serves as a FastAPI dependency to authenticate users
    by verifying their Firebase ID token from the Authorization header.
    
    Args:
        request (Request): FastAPI request object containing headers
        
    Returns:
        str: Firebase UID of the authenticated user
        
    Raises:
        HTTPException: 401 if authorization header is missing, invalid, or token is expired
        
    Example:
        Used as FastAPI dependency:
        @app.get("/protected")
        async def protected_route(uid: str = Depends(get_current_user_uid)):
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = auth_header.split(" ")[1]
    uid = verify_id_token(token)
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return uid

async def create_user(user: PartialProfileData, session: Session):
    """Create a new user in both Firebase and the application database.
    
    This function performs atomic user creation by:
    1. Checking for existing users with the same email
    2. Creating the user in Firebase Auth
    3. Creating corresponding database records (User and Profile)
    4. Rolling back if any step fails
    
    Args:
        user (PartialProfileData): User profile data for registration
        session (Session): SQLAlchemy database session
        
    Returns:
        dict: Contains firebase_user, db_user, and db_profile objects
        
    Raises:
        DuplicateUserError: If user with email already exists
        WeakPasswordError: If password doesn't meet Firebase requirements
        InternalServerError: If database operations fail
    """
    db_user = session.query(User).join(Profile).filter(Profile.email == user.email).first()
    if db_user:
        raise DuplicateUserError(user.email)
    # Create user in Firebase
    try: 
        auth_user = auth.create_user(
            email=user.email,
            password=user.password,
            email_verified=False,
        )
    except InvalidArgumentError as e:
        error_msg = str(e)
        if "EMAIL_EXISTS" in error_msg:
            raise DuplicateUserError(user.email) from e
        elif "PASSWORD_DOES_NOT_MEET_REQUIREMENTS" in error_msg:
            raise WeakPasswordError() from e
        else:
            logger.error(f"Error creating user in Firebase: {error_msg}")
            raise
    # Create database records
    new_user = User(firebase_uid=auth_user.uid)
    session.add(new_user)
    session.flush()  # to get new_user.id
    new_profile = Profile(
        user_id=new_user.id,
        name=user.name,
        email=user.email,
        job_role=user.job_role,
        last_login=user.last_login
    )
    session.add(new_profile)
    try:
        session.commit()
    except (IntegrityError, DataError, OperationalError) as e:
        # Rollback database changes.
        session.rollback()
        # cleanup orphaned Firebase user
        auth.delete_user(auth_user.uid)
        logger.error(f"Database commit failed, cleaned up Firebase user: {e}")
        raise InternalServerError("Failed to create user due to database error.") from e
    return {
        "firebase_user": auth_user,
        "db_user": new_user,
        "db_profile": new_profile
    }
    
async def get_all_users(session: Session):
    """Retrieve all users from the database with their profile information.
    
    Args:
        session (Session): SQLAlchemy database session
        
    Returns:
        list: List of user dictionaries containing id, firebase_uid, name, email,
              job_role, last_login, created_at, and updated_at
    """
    users = session.query(User).join(Profile).all()
    if not users:
        return []
    return [{
        'id': user.id,
        'firebase_uid': user.firebase_uid,
        'name': user.profile.name,
        'email': user.profile.email,
        'job_role': user.profile.job_role,
        'last_login': user.profile.last_login.isoformat() if user.profile.last_login else None,
        'created_at': user.created_at.isoformat(),
        'updated_at': user.updated_at.isoformat()
    } for user in users]

async def delete_user(uid: str, session: Session):
    """Delete a user from both Firebase and the application database.
    
    Performs cleanup in both Firebase Auth and the database. If Firebase
    deletion fails, the operation continues to remove the database record.
    
    Args:
        uid (str): Firebase UID of the user to delete
        session (Session): SQLAlchemy database session
        
    Returns:
        dict: Success message
        
    Raises:
        UserNotFound: If user with given UID doesn't exist in database
        InternalServerError: If deletion operations fail
    """
    user = session.query(User).filter(User.firebase_uid == uid).first()
    if not user:
        raise UserNotFound(uid)
    try:
        auth.delete_user(uid)
    except auth.UserNotFoundError:
        logger.warning(f"Firebase user {uid} not found during deletion.")
    except Exception as e:
        logger.error(f"Error deleting Firebase user {uid}: {e}")
        raise InternalServerError(f"Failed to delete Firebase user {uid}.")
    try:
        session.delete(user)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting user {uid} from database: {e}")
        raise InternalServerError(f"Failed to delete user {uid} from database.")
    return {"message": f"User deleted successfully."}

async def update_user(uid: str, user_updates: PartialProfileData, session: Session):
    """Update user profile information in the database.
    
    Updates only the fields provided in user_updates (partial update).
    
    Args:
        uid (str): Firebase UID of the user to update
        user_updates (PartialProfileData): Partial profile data with fields to update
        session (Session): SQLAlchemy database session
        
    Returns:
        dict: Success message
        
    Raises:
        UserNotFound: If user with given UID doesn't exist
        InternalServerError: If database update fails
    """
    user = session.query(User).filter(User.firebase_uid == uid).first()
    if not user:
        raise UserNotFound(uid)
    # Update user details here as needed.
    try:
        update_data = {k: v for k, v in user_updates.model_dump().items() if v is not None}
        session.query(Profile).filter(Profile.user_id == user.id).update(update_data)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating user {uid}: {e}")
        raise InternalServerError(f"Failed to update user {uid}.")
    return {"message": "User updated successfully."}

async def get_user_by_id(uid: str):
    """Retrieve Firebase user data and generate a custom token.
    
    Fetches user information from Firebase Auth and creates a custom token
    for the user. This is useful for client-side authentication.
    
    Args:
        uid (str): Firebase UID of the user to retrieve
        
    Returns:
        dict: Contains firebase_user object and custom_token string
        
    Raises:
        UserNotFound: If user with given UID doesn't exist in Firebase
        InternalServerError: If Firebase operations fail
    """
    try:
        firebase_user = auth.get_user(uid)
        custom_token = auth.create_custom_token(uid)
        return {
            "firebase_user": firebase_user,
            "custom_token": custom_token.decode('utf-8')
        }
    except auth.UserNotFoundError:
        raise UserNotFound(uid)
    except Exception as e:
        logger.error(f"Error retrieving user {uid}: {e}")
        raise InternalServerError(f"Failed to retrieve user {uid}.")
    
async def google_auth_controller(id_token: str, session: Session):
    """Handle Google OAuth authentication and user creation.
    
    Verifies Google ID token, creates user if new, or returns existing user.
    Matches the TypeScript implementation logic.
    
    Args:
        id_token (str): Google ID token from client
        session (Session): Database session
        
    Returns:
        dict: Success response with user data
        
    Raises:
        ValidationError: If ID token is invalid
        DuplicateUserError: If user already exists (for existing user flow)
        InternalServerError: If database operations fail
    """
    # Verify the Google ID token
    decoded_token, uid = verify_id_token(id_token)
    if not uid:
        raise ValidationError("Invalid Google ID token")
    
    # Extract user info from token
    email = decoded_token.get('email', '')
    name = decoded_token.get('name', '')
    
    logger.info(f"Google OAuth - Decoded token UID: {uid}")
    logger.info(f"Google OAuth - Email: {email}")
    logger.info(f"Google OAuth - Name: {name}")
    
    # Check if user already exists
    existing_user = session.query(User).filter(User.firebase_uid == uid).first()
    if existing_user:
        logger.info(f"Google OAuth - Found existing user: {existing_user.id}")
        return {
            "success": True,
            "user": {
                "id": existing_user.id,
                "firebase_uid": existing_user.firebase_uid,
                "name": existing_user.profile.name,
                "email": existing_user.profile.email,
                "job_role": existing_user.profile.job_role,
                "last_login": existing_user.profile.last_login.isoformat() if existing_user.profile.last_login else None,
                "created_at": existing_user.created_at.isoformat(),
                "updated_at": existing_user.updated_at.isoformat()
            }
        }
    
    # Check for email conflicts
    existing_email_user = session.query(User).join(Profile).filter(Profile.email == email).first()
    if existing_email_user:
        raise DuplicateUserError(email)
    
    # Create new user
    logger.info(f"Google OAuth - Creating new user for UID: {uid}")
    try:
        new_user = User(firebase_uid=uid)
        session.add(new_user)
        session.flush()  # to get new_user.id
        
        new_profile = Profile(
            user_id=new_user.id,
            name=name,
            email=email,
            job_role="",
            last_login=func.now()
        )
        session.add(new_profile)
        session.commit()
        
        logger.info(f"Google OAuth - Created new user: {new_user.id} with UID: {new_user.firebase_uid}")
        
        return {
            "success": True,
            "user": {
                "id": new_user.id,
                "firebase_uid": new_user.firebase_uid,
                "name": new_profile.name,
                "email": new_profile.email,
                "job_role": new_profile.job_role,
                "last_login": new_profile.last_login.isoformat() if new_profile.last_login else None,
                "created_at": new_user.created_at.isoformat(),
                "updated_at": new_user.updated_at.isoformat()
            }
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"Database commit failed during Google auth: {e}")
        raise InternalServerError("Failed to create user due to database error.")
