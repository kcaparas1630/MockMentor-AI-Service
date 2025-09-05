import firebase_admin
from firebase_admin import auth, credentials
from app.schemas.auth.user_auth_schemas import ProfileData
from sqlalchemy.orm import joinedload

cred = credentials.Certificate("/config/firebase-admin-key.json")
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

async def create_user(user: ProfileData):
    # Create a new user with the specified properties.
    pass
    
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
