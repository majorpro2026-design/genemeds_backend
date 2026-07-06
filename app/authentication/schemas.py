from pydantic import BaseModel


class AuthenticationHealthResponse(BaseModel):
    status: str = "ready"
