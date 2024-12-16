from pydantic import BaseModel, EmailStr

# Schema for registering a user, validated using Pydantic


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
