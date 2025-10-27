from pydantic import BaseModel


class LoginParams(BaseModel):
    username: str
    password: str


class LoginResult(BaseModel):
    accessToken: str


class UserInfo(BaseModel):
    username: str
    userId: int
    realName: str | None = None
    roles: list[str]
