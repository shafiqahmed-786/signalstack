# Domain Models Analysis — SignalStack Backend

## Executive Summary

The backend code references **3 critical domain models** that control the application's core functionality. All three currently exist but with a **critical import path issue**: code tries to import from `app.models.domain.*` but files are located at `app.models.db.domain.*`.

### Files Affected by Import Error

**Import statements failing**:
- `app/api/v1/research.py` (line 34)
- `app/api/dependencies.py` (line 9)
- `app/middleware/tenant.py` (line 6)
- `app/api/v1/auth.py` (line 9)
- `app/repositories/base.py` (line 9)
- `app/models/schemas/requests/research.py` (line 22)
- `app/models/schemas/responses/research.py` (line 22)
- `app/orchestration/state_machine.py` (line 41)
- `app/orchestration/prompts/registry.py` (line 77)

---

## Domain Model #1: TenantContext

### ✅ Current Status: EXISTS at `app/models/db/domain/tenant.py`

### Class Definition
```python
@dataclass(frozen=True)
class TenantContext:
    """
    Resolved tenant context for the current authenticated request.
    
    Frozen (immutable) for safety when passing through the call stack.
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
        return self.role in ("admin", "analyst")
    
    def __str__(self) -> str:
        return f"TenantContext(user={self.user_id}, org={self.org_id}, role={self.role!r})"
```

### Required Attributes
| Attribute | Type | Purpose | Source |
|-----------|------|---------|--------|
| `user_id` | `uuid.UUID` | User's database ID | Set in `resolve_tenant_context()` |
| `clerk_user_id` | `str` | Clerk JWT "sub" claim | From ClerkClaims |
| `org_id` | `uuid.UUID` | Organization's database ID | Set in `resolve_tenant_context()` |
| `clerk_org_id` | `str` | Clerk JWT "org_id" claim | From ClerkClaims |
| `role` | `str` | Either "admin" or "analyst" | From Member.role in DB |
| `email` | `str` | User's email address | From User.email in DB |

### Required Properties/Methods
- `is_admin` → bool (true if role == "admin")
- `is_analyst` → bool (true if role in ("admin", "analyst"))

### Usage Locations

**In Dependencies** (`app/api/dependencies.py`):
- Injected via `get_tenant_ctx()` dependency
- Used by `require_role()` to check `ctx.role`
- Accessed: `.user_id`, `.org_id`, `.role`

**In Auth Routes** (`app/api/v1/auth.py`):
- In `get_me()` route handler: `ctx.user_id`, `ctx.email`, `ctx.org_id`, `ctx.is_admin`, `ctx.role`

**In Repositories** (`app/repositories/base.py`):
- Used by `TenantAwareRepository._require_tenant()` to validate and extract `org_id`
- Used by `_org_filter()` to tenant-scope queries: `ctx.org_id`

**In Middleware** (`app/middleware/tenant.py`):
- Created in `resolve_tenant_context()` by combining ClerkClaims with DB lookups

**In Routes** (`app/api/v1/research.py`):
- Received via `Depends(require_analyst)` dependency
- Used to filter reports by tenant

---

## Domain Model #2: ReportStatus

### ❌ **Current Status: NOT FOUND**

ReportStatus is **referenced** in `app/orchestration/state_machine.py` (line 41) but the file **does not exist**.

### Expected Location
`app/models/domain/research.py` (or `app/models/db/domain/research.py`)

### Class Definition (Minimal)
```python
from enum import Enum

class ReportStatus(str, Enum):
    """Report lifecycle status enum."""
    
    CREATED = "created"
    PLANNING = "planning"
    DISPATCHING = "dispatching"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
    @property
    def is_terminal(self) -> bool:
        """True if status represents a terminal state (no more transitions allowed)."""
        return self in (ReportStatus.COMPLETED, ReportStatus.PARTIAL, 
                       ReportStatus.FAILED, ReportStatus.CANCELLED)
```

### Required Enum Values
| Status | Meaning | Terminal? | Valid Transitions |
|--------|---------|-----------|-------------------|
| `"created"` | Initial state after report row created | No | PLANNING, FAILED |
| `"planning"` | Planner analyzing query | No | DISPATCHING, FAILED |
| `"dispatching"` | Tools being executed | No | SYNTHESIZING, FAILED |
| `"synthesizing"` | LLM generating structured report | No | COMPLETED, PARTIAL, FAILED |
| `"completed"` | Fully successful | ✓ Yes | (none) |
| `"partial"` | Success with gaps | ✓ Yes | (none) |
| `"failed"` | Fatal error | ✓ Yes | (none) |
| `"cancelled"` | User cancelled | ✓ Yes | (none) |

### Required Property
- `is_terminal` → bool: True for COMPLETED, PARTIAL, FAILED, CANCELLED

### Valid State Transitions
```
CREATED → {PLANNING, FAILED}
PLANNING → {DISPATCHING, FAILED}
DISPATCHING → {SYNTHESIZING, FAILED}
SYNTHESIZING → {COMPLETED, PARTIAL, FAILED}
COMPLETED → {}  (terminal)
PARTIAL → {}    (terminal)
FAILED → {}     (terminal)
CANCELLED → {}  (terminal)
```

### Usage Locations

**In State Machine** (`app/orchestration/state_machine.py`):
- Line 41: `from app.models.domain.research import ReportStatus`
- Lines 47-56: Used in `VALID_TRANSITIONS` dict as both key and value
- Line 109: `self._current = ReportStatus.CREATED`
- Line 119: `return self._current.is_terminal` (property access)
- Multiple lines: `.value` attribute used for string representation

---

## Domain Model #3: ResearchReport

### ❌ **Current Status: NOT FULLY DEFINED**

ResearchReport is referenced in:
- `app/models/schemas/requests/research.py` (line 22)
- `app/models/schemas/responses/research.py` (line 22)
- `app/orchestration/prompts/registry.py` (line 77 - imported from `report_output`)

### Expected Location
`app/models/domain/research.py` (or potentially `app/models/domain/report_output.py`)

### Class Definition (Minimal)
```python
from pydantic import BaseModel
from typing import Any, Optional

class ResearchReport(BaseModel):
    """
    Full structured research report output.
    
    This is the JSON schema returned after synthesis completes.
    Stored as JSONB in research_reports.report_data column.
    """
    
    # Metadata
    schema_version: str = "1.0"
    query: str
    generated_at: str  # ISO 8601 timestamp
    processing_time_ms: int
    
    # Structured content
    companies: list[dict]  # CompanySnapshot[]
    sections: list[dict]   # ReportSection[]
    executive_summary: str
    risk_assessment: Optional[dict] = None  # RiskSection content
    sources: list[dict]    # SourceAttribution[]
    data_gaps: list[dict]  # DataGap[]
    
    class Config:
        # Allow arbitrary dict types from JSON deserialization
        arbitrary_types_allowed = True
```

### Required Attributes
| Attribute | Type | Purpose | Source |
|-----------|------|---------|--------|
| `schema_version` | `str` | Output format version | Hardcoded "1.0" |
| `query` | `str` | Original research query | From ResearchReport DB |
| `generated_at` | `str` (ISO 8601) | When report was generated | Synthesizer output timestamp |
| `processing_time_ms` | `int` | Total execution time | Calculated by orchestrator |
| `companies` | `list[dict]` | Analyzed companies with snapshots | Planner + market data tool |
| `sections` | `list[dict]` | Content sections (news, sentiment, etc.) | Synthesizer output |
| `executive_summary` | `str` | High-level summary | Synthesizer output |
| `risk_assessment` | `dict \| None` | Risk analysis | Synthesizer output |
| `sources` | `list[dict]` | Citations and attributions | News + vector data sources |
| `data_gaps` | `list[dict]` | Missing or unavailable data | Synthesizer analysis |

### Nested Structure Details
From frontend `types/report.ts` (mirror of backend):

```typescript
// CompanySnapshot
{
  symbol: string
  full_name: string
  current_price: number | null
  price_change_pct: number | null
  market_cap: string | null
  sector: string | null
}

// ReportSection
{
  heading: string
  content: string
  data_type: "news" | "sentiment" | "fundamental" | "technical" | "ai_analysis"
  confidence_level: "high" | "medium" | "low"
  source_count: number
}

// SourceAttribution
{
  id: string
  url: string
  title: string
  source_type: "news" | "api" | "vector" | "internal"
  published_at: string | null
  retrieved_at: string
}

// DataGap
{
  company: string
  gap_type: "no_recent_news" | "api_limit_reached" | "insufficient_data"
  description: string
}
```

### Usage Locations

**In Request Schemas** (`app/models/schemas/requests/research.py`):
- Line 22: `from app.models.domain.research import ResearchReport`
- The ResearchQueryRequest validates user input before it reaches orchestration

**In Response Schemas** (`app/models/schemas/responses/research.py`):
- Line 22: `from app.models.domain.research import ResearchReport`
- Used in `ResearchReportResponse` as optional field: `report: ResearchReport | None`
- Serialized to JSON in API responses when available

**In Orchestration** (`app/orchestration/state_machine.py`):
- Used to validate state transitions that include report_data
- Serialized via `.model_dump(mode='json')` in SSE events

**In Prompt Registry** (`app/orchestration/prompts/registry.py`):
- Line 77: `from app.models.domain.report_output import ResearchReport`
- Used as return type hint for synthesis functions

---

## Database Schema Context

### ResearchReport Database Model
Location: `app/models/db/report.py`

The **ResearchReport ORM model** (database row) stores:
- `status: str` — Current lifecycle status
- `report_data: dict | None` — The full ResearchReport JSON blob (JSONB column)
- Metadata: `query`, `title`, `companies`, `tags`, etc.
- Observability: `processing_time_ms`, `total_tokens_used`, `model_used`, `tools_called`

### Status Constraint
```sql
CHECK (status IN ('created','planning','dispatching','synthesizing','completed','partial','failed','cancelled'))
```

This matches the ReportStatus enum exactly.

---

## Import Path Resolution

### Current Problem
```python
# ❌ These imports fail:
from app.models.domain.tenant import TenantContext
from app.models.domain.research import ReportStatus, ResearchReport

# ✓ Files actually exist at:
# app/models/db/domain/tenant.py (TenantContext)
# app/models/domain/research.py OR app/models/db/domain/research.py (others)
```

### Solution Options

**Option A (Recommended)**: Move existing `app/models/db/domain/` to `app/models/domain/`
- Creates consistent import path across all files
- All imports would be `from app.models.domain.*`
- Cleaner separation: domain models ≠ database models

**Option B**: Update all import statements
- Keep files at `app/models/db/domain/*`
- Update 9 files to import from `app.models.db.domain.*`
- Less refactoring but less clean organization

**Option C**: Create symlink or alias
- Advanced Python package organization
- Both import paths work
- Most complex to maintain

---

## Minimal Implementation Checklist

To fix all import errors and prevent runtime failures, ensure:

### TenantContext (`app/models/domain/tenant.py` OR `app/models/db/domain/tenant.py`)
- [x] Dataclass with `frozen=True`
- [x] Attributes: `user_id`, `clerk_user_id`, `org_id`, `clerk_org_id`, `role`, `email`
- [x] Property: `is_admin`
- [x] Property: `is_analyst`

### ReportStatus (`app/models/domain/research.py` OR `app/models/db/domain/research.py`)
- [ ] Enum class inheriting from `str, Enum`
- [ ] Values: "created", "planning", "dispatching", "synthesizing", "completed", "partial", "failed", "cancelled"
- [ ] Property: `is_terminal`

### ResearchReport (`app/models/domain/research.py` OR `app/models/domain/report_output.py`)
- [ ] Pydantic BaseModel
- [ ] Attributes: `schema_version`, `query`, `generated_at`, `processing_time_ms`, `companies`, `sections`, `executive_summary`, `risk_assessment`, `sources`, `data_gaps`
- [ ] Config: `arbitrary_types_allowed = True` to handle nested dicts

---

## Testing Import Paths

After implementation, verify all imports work:

```bash
# Test from backend directory
python -c "from app.models.domain.tenant import TenantContext; print('✓ TenantContext')"
python -c "from app.models.domain.research import ReportStatus; print('✓ ReportStatus')"
python -c "from app.models.domain.research import ResearchReport; print('✓ ResearchReport')"

# Or test the actual imports in affected files
python -m mypy app/api/v1/research.py
python -m mypy app/orchestration/state_machine.py
```

---

## References

### Existing Files That Import These Models
- Request validation: `app/models/schemas/requests/research.py`
- Response serialization: `app/models/schemas/responses/research.py`
- API dependencies: `app/api/dependencies.py`
- Route handlers: `app/api/v1/research.py`, `app/api/v1/auth.py`
- Tenant middleware: `app/middleware/tenant.py`
- Repository base: `app/repositories/base.py`
- State machine: `app/orchestration/state_machine.py`
- Prompt registry: `app/orchestration/prompts/registry.py`

### Frontend Type Definitions (Mirrors)
- `frontend/types/report.ts` — ResearchReport interface
- `frontend/types/api.ts` — ReportStatus type
- `frontend/features/research/types/api.ts` — Additional API types
