from pydantic import BaseModel, Field
from app.models.scenario import ScenarioRequest


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class WorkspaceScenarioRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    request: ScenarioRequest


class WorkspaceDocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    domain: str = Field(min_length=2, max_length=32)
    text: str = Field(min_length=1, max_length=20_000)
