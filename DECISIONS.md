# Technical Decisions

## Why Next.js
Chosen for App Router architecture, scalable routing, React Server Components support, and strong frontend ecosystem integration.

## Why FastAPI
FastAPI provides async-first backend architecture, excellent typing support, and efficient SSE streaming capabilities.

## Why Clerk
Clerk simplified authentication, organization management, and session handling while reducing implementation complexity.

## Why SSE Instead of WebSockets
SSE was selected because the orchestration pipeline is primarily server-to-client streaming. SSE reduced infrastructure complexity while preserving real-time updates.

## Why PostgreSQL
PostgreSQL provides strong relational consistency and flexible JSONB support for storing structured AI research reports.

## Why React Query
React Query simplified async state synchronization, caching, retries, and background refetching for dashboard/report workflows.

## Tradeoffs
- Multi-tenant enforcement was relaxed in development to accelerate debugging.
- Some orchestration flows were simplified due to project time constraints.
- Replit deployment was prioritized for rapid frontend stabilization and demo readiness.

## Future Improvements
- Background task queue
- Redis caching
- WebSocket fallback support
- Better observability dashboards
- Streaming retry persistence
