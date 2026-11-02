from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    college_name: str
    environment: str
    database: str
    schema_ready: bool
    detail: str | None = None
    services: dict[str, str] = {}
