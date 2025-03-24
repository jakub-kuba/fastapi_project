from pydantic import BaseModel, EmailStr, constr, validator
from typing import Optional
import re

# Schema for registering a user, validated using Pydantic


class UserRegister(BaseModel):
    username: constr(min_length=3, max_length=15)
    email: EmailStr
    password: constr(min_length=8, max_length=30)

    @validator('username')
    def validate_username(cls, value):
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise ValueError(
                'Username must contain only alphanumeric characters '
                'or underscores'
            )
        return value

    @validator('password')
    def validate_password(cls, value):
        if not re.search(r'[A-Z]', value):
            raise ValueError(
                'Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', value):
            raise ValueError(
                'Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', value):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValueError(
                'Password must contain at least one special character')
        if re.search(r'\s', value):
            raise ValueError('Password must not contain whitespace characters')
        return value


class UserLogin(BaseModel):
    username: constr(min_length=3, max_length=15)
    password: constr(min_length=8, max_length=30)

    @validator('username')
    def validate_username(cls, value):
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise ValueError(
                'Username must only contain alphanumeric characters '
                'or underscores'
            )
        return value


class UserResponse(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TuneCreate(BaseModel):
    title: constr(min_length=1, max_length=30)
    composer: Optional[constr(min_length=1, max_length=30)] = None
    rhythm: Optional[constr(min_length=1, max_length=30)] = None
    difficulty: Optional[int] = None
    progress: Optional[int] = None
    link: Optional[str] = None
    description: Optional[constr(min_length=1, max_length=400)] = None
    demo: bool = False

    @validator('difficulty')
    def validate_difficulty(cls, value):
        if value is not None and (value < 1 or value > 5):
            raise ValueError('Difficulty must be between 1 and 5')
        return value

    @validator('progress')
    def validate_progress(cls, value):
        if value is not None and (value < 1 or value > 100):
            raise ValueError('Progress must be between 1 and 100')
        return value


class TuneUpdate(BaseModel):
    title: Optional[constr(min_length=1, max_length=30)]
    composer: Optional[constr(min_length=1, max_length=30)]
    rhythm: Optional[constr(min_length=1, max_length=30)]
    difficulty: Optional[int]
    progress: Optional[int]
    link: Optional[str]
    description: Optional[constr(min_length=1, max_length=250)]
    demo: Optional[bool]

    @validator('difficulty')
    def validate_difficulty(cls, value):
        if value is not None and (value < 1 or value > 5):
            raise ValueError('Difficulty must be between 1 and 5')
        return value

    @validator('progress')
    def validate_progress(cls, value):
        if value is not None and (value < 1 or value > 100):
            raise ValueError('Progress must be between 1 and 100')
        return value


class Tune(TuneCreate):
    id: int

    class Config:
        orm_mode = True


class ProposalCreate(BaseModel):
    title: constr(min_length=1, max_length=30)
    composer: Optional[constr(min_length=1, max_length=30)]
    info: Optional[str]


class Proposal(ProposalCreate):
    id: int

    class Config:
        orm_mode = True


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
