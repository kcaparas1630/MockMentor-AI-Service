import firebase_admin
from firebase_admin import auth, credentials

cred = credentials.Certificate("/config/firebase-admin-key.json")
firebase_admin.initialize_app(cred)


# TODO: Implement Firebase authentication functions here
def verify_id_token(id_token: str):
    # Verify the ID token while checking if the token is revoked by passing check_revoked=True.
    pass

def create_user():
    # Create a new user with the specified properties.
    pass

def get_all_users():
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
