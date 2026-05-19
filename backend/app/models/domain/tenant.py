"""Re-export TenantContext from db models for backwards compatibility."""

from app.models.db.domain.tenant import TenantContext

__all__ = ["TenantContext"]
