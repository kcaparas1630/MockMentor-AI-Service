import firebase_admin
from firebase_admin import auth, credentials
from firebase_admin.exceptions import InvalidArgumentError
from app.schemas.auth.user_auth_schemas import PartialProfileData
from sqlalchemy.orm import Session
from app.models.user_models import User, Profile
from app.errors.exceptions import DuplicateUserError, WeakPasswordError, InternalServerError, UserNotFound, UserDisabled
from fastapi import Request
import os
from loguru import logger

file_path = "app/config/mockmentor-dev-firebase-adminsdk-fbsvc-3769206016.json"
# Check if credentials exists
if not os.path.exists(file_path):
    logger.error(f"Firebase credentials file not found at {file_path}")

cred = credentials.Certificate(file_path)
firebase_admin.initialize_app(cred)

def verify_id_token(id_token: str):
    # Verify the ID token while checking if the token is revoked by passing check_revoked=True.
    try: 
        decoded_token = auth.verify_id_token(id_token, check_revoked=True)
        uid = decoded_token['uid']
        return decoded_token, uid
    except auth.InvalidIdTokenError:
        # Token is invalid, expired or revoked.
        return None, None

def get_current_user_uid(request: Request):
    """Middleware to extract and verify Firebase ID token from request headers"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = auth_header.split(" ")[1]
    decoded_token, uid = verify_id_token(token)
    if not uid:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return uid

async def create_user(user: PartialProfileData, session: Session):
    # Create a new user with the specified properties.
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
            raise DuplicateUserError(user.email)
        elif "PASSWORD_DOES_NOT_MEET_REQUIREMENTS" in error_msg:
            raise WeakPasswordError()
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
    except Exception as e:
        # Rollback database changes.
        session.rollback()
        # cleanup orphaned Firebase user
        auth.delete_user(auth_user.uid)
        logger.error(f"Database commit failed, cleaned up Firebase user: {e}")
        raise InternalServerError("Failed to create user due to database error.")
    return {
        "firebase_user": auth_user,
        "db_user": new_user,
        "db_profile": new_profile
    }
    
async def get_all_users(session: Session):
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
    # Update user details for the user with the specified uid.
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
    # Get the user data corresponding to the provided uid.
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
