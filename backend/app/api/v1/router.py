"""
app/api/v1/router.py

Aggregates all v1 API sub-routers into a single APIRouter.

Registration order determines OpenAPI tag ordering.
Each sub-router owns its own prefix and tags.

Day 2 additions:
  - research router (POST/GET/PATCH/DELETE /research/*)
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, health, research

router = APIRouter(prefix="/api/v1")

# ── System ─────────────────────────────────────────────────────────────────────
router.include_router(health.router)

# ── Authentication / tenant sync ───────────────────────────────────────────────
router.include_router(auth.router)

# ── Core product ───────────────────────────────────────────────────────────────
router.include_router(research.router)

# Future Day 4+ routers:
# from app.api.v1 import watchlist, organization
# router.include_router(watchlist.router)
# router.include_router(organization.router)
