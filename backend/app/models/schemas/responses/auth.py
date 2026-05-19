from __future__ import annotations

from pydantic import BaseModel


class OrganizationResponse(BaseModel):
    """Public representation of an organization for API responses."""

    id: str
    name: str
    slug: str
    plan: str


class UserMeResponse(BaseModel):
    """
    Response body for GET /api/v1/auth/me.

    Returns the authenticated user's profile plus their resolved
    organization context and role. This is the primary way the
    frontend learns what the current user is allowed to do.
    """

    user_id: str
    email: str
    full_name: str | None
    avatar_url: str | None
    organization: OrganizationResponse
    role: str
    is_admin: bool


class WebhookAckResponse(BaseModel):
    """
    Minimal acknowledgement returned from the Clerk webhook handler.
    Clerk requires a 2xx response; body content is ignored by Clerk.
    """

    received: bool = True
    event_type: str


class HealthCheckDetail(BaseModel):
    status: str
    latency_ms: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str   # "healthy" | "degraded" | "unhealthy"
    version: str
    environment: str
    checks: dict[str, HealthCheckDetail]