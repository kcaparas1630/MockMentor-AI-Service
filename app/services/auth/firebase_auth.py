import firebase_admin
from firebase_admin import auth, credentials
from app.schemas.auth.user_auth_schemas import PartialProfileData
from sqlalchemy.orm import joinedload, Session
from app.models.user_models import User, Profile
from app.errors.exceptions import DuplicateUserError
import os

file_path = "app/config/mockmentor-dev-firebase-adminsdk-fbsvc-3769206016.json"
if os.path.exists(file_path):
    print("File exists")
else:
    print("File not found")

print(f"Current working directory: {os.getcwd()}")
print(f"Files in current directory: {os.listdir('.')}")

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
    auth_user = auth.create_user(
        email=user.email,
        password=user.password,
    )
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
    session.commit()
    custom_token = auth.create_custom_token(auth_user.uid)
    return {
        "firebase_user": auth_user,
        "custom_token": custom_token,
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
