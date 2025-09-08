import firebase_admin
from firebase_admin import auth, credentials
from firebase_admin.exceptions import InvalidArgumentError
from app.schemas.auth.user_auth_schemas import PartialProfileData
from sqlalchemy.orm import Session
from app.models.user_models import User, Profile
from app.errors.exceptions import DuplicateUserError, WeakPasswordError, InternalServerError
import os
from loguru import logger

file_path = "app/config/mockmentor-dev-firebase-adminsdk-fbsvc-3769206016.json"
# Check if credentials exists
if not os.path.exists(file_path):
    logger.error(f"Firebase credentials file not found at {file_path}")

cred = credentials.Certificate(file_path)
firebase_admin.initialize_app(cred)

# TODO: Implement Firebase authentication functions here
def verify_id_token(id_token: str):
    # Verify the ID token while checking if the token is revoked by passing check_revoked=True.
    try: 
        decoded_token = auth.verify_id_token(id_token, check_revoked=True)
        uid = decoded_token['uid']
        return decoded_token, uid
    except auth.InvalidIdTokenError:
        # Token is invalid, expired or revoked.
        return None, None

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
    
async def get_all_users():
    # List all users. This will be a generator that yields UserRecord instances.
    pass

def delete_user(uid: str):
    # Delete a user identified by uid.
    pass

def update_user(uid: str):
    # Update user properties.
    pass

def get_user_by_id(uid: str):
    # Get the user data corresponding to the provided uid.
    pass
