from pydantic import BaseModel, EmailStr
from typing import Optional

# Schema for registering a user, validated using Pydantic


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TuneCreate(BaseModel):
    title: str
    composer: str = None
    rhythm: str = None
    difficulty: int = None
    progress: int = None
    link: str = None
    description: str = None
    demo: bool = False


class TuneUpdate(BaseModel):
    title: Optional[str]
    composer: Optional[str]
    rhythm: Optional[str]
    difficulty: Optional[int]
    progress: Optional[int]
    link: Optional[str]
    description: Optional[str]
    demo: Optional[bool]


class Tune(TuneCreate):
    id: int

    class Config:
        orm_mode = True


class ProposalCreate(BaseModel):
    title: str
    composer: str = None
    info: str = None


class Proposal(ProposalCreate):
    id: int

    class Config:
        orm_mode = True
