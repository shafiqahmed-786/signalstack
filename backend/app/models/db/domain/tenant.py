from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class TenantContext:
    """
    Resolved tenant context for the current authenticated request.

    Injected by the get_tenant_ctx FastAPI dependency after resolving
    the Clerk JWT claims against our database. Frozen (immutable) so
    it can be safely passed through the call stack without mutation.

    Roles:
      'admin'   — full org access: can manage members, view all reports,
                  delete any report, change thresholds.
      'analyst' — can create/view/edit own research; cannot manage org.
    """

    user_id: uuid.UUID
    clerk_user_id: str      # Clerk's "sub" claim (e.g., "user_2abc...")
    org_id: uuid.UUID
    clerk_org_id: str       # Clerk's "org_id" claim (e.g., "org_2abc...")
    role: str               # "admin" | "analyst"
    email: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_analyst(self) -> bool:
        # Admins have all analyst permissions
        return self.role in ("admin", "analyst")

    def __str__(self) -> str:
        return (
            f"TenantContext(user={self.user_id}, org={self.org_id}, role={self.role!r})"
        )