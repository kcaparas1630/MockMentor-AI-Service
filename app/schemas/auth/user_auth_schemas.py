from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone

class ProfileData(BaseModel):
    name: str
    email: EmailStr
    job_role: str = Field(alias="jobRole")
    last_login: datetime = Field(default_factory=datetime.now(timezone.utc), alias="lastLogin")
    password: Optional[str] = None  # for admin auth, can be none for Oauth users

    class Config:
        populate_by_name = True # allows camelcase and snake_case interchangeably\
    
class UserAuthUpdateRequestSchema(BaseModel):
    profile: Optional[ProfileData] = None
