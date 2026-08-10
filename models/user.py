# models/user.py
from sqlmodel import SQLModel, Field
from typing import Optional

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    hashed_password: str
    is_admin: bool = Field(default=False)

class UserCreate(SQLModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None

class UserResponse(SQLModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_admin: bool

class Token(SQLModel):
    access_token: str
    token_type: str