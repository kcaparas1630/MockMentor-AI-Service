from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone

class PartialProfileData(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    job_role: Optional[str] = Field(None, alias="jobRole")
    last_login: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), alias="lastLogin")
    password: Optional[str] = None  # for admin auth, can be none for Oauth users

    class Config:
        populate_by_name = True # allows camelcase and snake_case interchangeably
    
class UserAuthUpdateRequestSchema(BaseModel):
    profile: Optional[PartialProfileData] = None
