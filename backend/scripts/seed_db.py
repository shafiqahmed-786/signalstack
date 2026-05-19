#!/usr/bin/env python3
"""
Seed script: creates two demo organizations with users, memberships,
and watchlist entries. Safe to re-run — uses upsert semantics.

Usage:
    python scripts/seed_db.py

Requires DATABASE_URL in environment (or .env file).
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

# Ensure the project root is on the path when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

from app.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.db import (  # noqa: F401 — registers all models with mapper
    AuditLog,
    Base,
    Organization,
    OrganizationMember,
    QueryCache,
    ResearchReport,
    ReportSource,
    User,
    WatchlistItem,
)
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository

log = structlog.get_logger("seed")

# ── Seed data definitions ──────────────────────────────────────────────────────

ORGANIZATIONS = [
    {
        "name": "Acme Capital",
        "slug": "acme-capital",
        "clerk_org_id": "org_seed_acme_capital_001",
        "plan": "pro",
    },
    {
        "name": "Pinnacle Investments",
        "slug": "pinnacle-investments",
        "clerk_org_id": "org_seed_pinnacle_inv_002",
        "plan": "free",
    },
]

USERS = [
    {
        "clerk_id": "user_seed_alice_001",
        "email": "alice@acme-capital.com",
        "full_name": "Alice Chen",
        "org_slug": "acme-capital",
        "role": "admin",
    },
    {
        "clerk_id": "user_seed_bob_002",
        "email": "bob@acme-capital.com",
        "full_name": "Bob Okafor",
        "org_slug": "acme-capital",
        "role": "analyst",
    },
    {
        "clerk_id": "user_seed_charlie_003",
        "email": "charlie@pinnacle-inv.com",
        "full_name": "Charlie Reyes",
        "org_slug": "pinnacle-investments",
        "role": "admin",
    },
    {
        "clerk_id": "user_seed_diana_004",
        "email": "diana@pinnacle-inv.com",
        "full_name": "Diana Park",
        "org_slug": "pinnacle-investments",
        "role": "analyst",
    },
]

WATCHLIST: dict[str, list[dict]] = {
    # org_slug → list of {user_email, ticker, company_name}
    "acme-capital": [
        {"user_email": "alice@acme-capital.com", "ticker": "NVDA", "company_name": "NVIDIA Corporation"},
        {"user_email": "alice@acme-capital.com", "ticker": "AMD",  "company_name": "Advanced Micro Devices"},
        {"user_email": "alice@acme-capital.com", "ticker": "MSFT", "company_name": "Microsoft Corporation"},
        {"user_email": "bob@acme-capital.com",   "ticker": "AAPL", "company_name": "Apple Inc."},
        {"user_email": "bob@acme-capital.com",   "ticker": "TSLA", "company_name": "Tesla Inc."},
    ],
    "pinnacle-investments": [
        {"user_email": "charlie@pinnacle-inv.com", "ticker": "JPM",  "company_name": "JPMorgan Chase & Co."},
        {"user_email": "charlie@pinnacle-inv.com", "ticker": "GS",   "company_name": "Goldman Sachs Group"},
        {"user_email": "diana@pinnacle-inv.com",   "ticker": "AMZN", "company_name": "Amazon.com Inc."},
    ],
}


async def seed() -> None:
    log.info("seed.starting")

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        org_repo = OrganizationRepository(session)

        # Track created entities by slug/email for later lookup
        orgs: dict[str, Organization] = {}
        users: dict[str, User] = {}

        # ── Organizations ──────────────────────────────────────────────────────
        log.info("seed.creating_organizations", count=len(ORGANIZATIONS))
        for org_data in ORGANIZATIONS:
            org, created = await org_repo.upsert_from_clerk(
                clerk_org_id=org_data["clerk_org_id"],
                name=org_data["name"],
                slug=org_data["slug"],
            )
            # Update plan separately (upsert_from_clerk doesn't handle plan)
            org.plan = org_data["plan"]
            await session.flush()
            orgs[org_data["slug"]] = org
            log.info(
                "seed.org_ready",
                slug=org.slug,
                org_id=str(org.id),
                created=created,
            )

        # ── Users ──────────────────────────────────────────────────────────────
        log.info("seed.creating_users", count=len(USERS))
        for user_data in USERS:
            user, created = await user_repo.upsert_from_clerk(
                clerk_id=user_data["clerk_id"],
                email=user_data["email"],
                full_name=user_data["full_name"],
            )
            users[user_data["email"]] = user
            log.info(
                "seed.user_ready",
                email=user.email,
                user_id=str(user.id),
                created=created,
            )

        # ── Memberships ────────────────────────────────────────────────────────
        log.info("seed.creating_memberships")
        for user_data in USERS:
            user = users[user_data["email"]]
            org = orgs[user_data["org_slug"]]
            existing = await org_repo.get_member(org.id, user.id)
            if existing is None:
                await org_repo.add_member(
                    org_id=org.id,
                    user_id=user.id,
                    role=user_data["role"],
                )
                log.info(
                    "seed.membership_created",
                    email=user_data["email"],
                    org=user_data["org_slug"],
                    role=user_data["role"],
                )
            else:
                if existing.role != user_data["role"]:
                    await org_repo.update_member_role(org.id, user.id, user_data["role"])
                log.info(
                    "seed.membership_exists",
                    email=user_data["email"],
                    org=user_data["org_slug"],
                )

        # ── Watchlist ──────────────────────────────────────────────────────────
        log.info("seed.creating_watchlist_items")
        for org_slug, items in WATCHLIST.items():
            org = orgs[org_slug]
            for item in items:
                user = users[item["user_email"]]
                # Check for existing entry (upsert via check-then-insert)
                from sqlalchemy import select
                result = await session.execute(
                    select(WatchlistItem).where(
                        WatchlistItem.organization_id == org.id,
                        WatchlistItem.user_id == user.id,
                        WatchlistItem.ticker == item["ticker"],
                    )
                )
                if result.scalar_one_or_none() is None:
                    wl = WatchlistItem(
                        organization_id=org.id,
                        user_id=user.id,
                        ticker=item["ticker"],
                        company_name=item["company_name"],
                    )
                    session.add(wl)
                    log.info(
                        "seed.watchlist_item_created",
                        ticker=item["ticker"],
                        user=item["user_email"],
                        org=org_slug,
                    )

        await session.commit()
        log.info("seed.complete")

    # ── Print summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("SEED COMPLETE — Demo Credentials")
    print("=" * 60)
    print("\nOrganization A: Acme Capital (Pro plan)")
    print("  Admin:   alice@acme-capital.com  | clerk_id: user_seed_alice_001")
    print("  Analyst: bob@acme-capital.com    | clerk_id: user_seed_bob_002")
    print("\nOrganization B: Pinnacle Investments (Free plan)")
    print("  Admin:   charlie@pinnacle-inv.com | clerk_id: user_seed_charlie_003")
    print("  Analyst: diana@pinnacle-inv.com   | clerk_id: user_seed_diana_004")
    print("\nNote: These are seed records. For full JWT auth, create real")
    print("      Clerk users and run the /auth/sync webhook flow.\n")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(seed())