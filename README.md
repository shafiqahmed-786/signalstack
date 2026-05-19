SignalStack

AI-native investment research infrastructure built for structured market intelligence, deterministic orchestration, and real-time analytical workflows.

<p align="center"> <img src="https://img.shields.io/badge/Next.js-14-black?style=for-the-badge&logo=nextdotjs" /> <img src="https://img.shields.io/badge/FastAPI-Async-009688?style=for-the-badge&logo=fastapi" /> <img src="https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql" /> <img src="https://img.shields.io/badge/TypeScript-Strict-3178C6?style=for-the-badge&logo=typescript" /> <img src="https://img.shields.io/badge/Clerk-Auth-6C47FF?style=for-the-badge" /> <img src="https://img.shields.io/badge/SSE-Streaming-0EA5E9?style=for-the-badge" /> <img src="https://img.shields.io/badge/SQLAlchemy-Async-red?style=for-the-badge" /> <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" /> </p> <p align="center"> <a href="https://signalstack--ShafiqAhmed5.replit.app"><strong>Live Deployment</strong></a> · <a href="#system-architecture"><strong>Architecture</strong></a> · <a href="#local-development-setup"><strong>Local Setup</strong></a> · <a href="#streaming-architecture"><strong>Streaming Engine</strong></a> </p>
Overview

SignalStack is an AI-powered investment research platform designed around deterministic orchestration, structured report synthesis, and real-time analytical workflows.

The system transforms unstructured natural language research requests into production-grade structured intelligence reports through a multi-stage orchestration pipeline.

Unlike traditional “AI chat” interfaces, SignalStack is engineered around:

typed research contracts
composable orchestration pipelines
tenant-aware infrastructure
source-attributed synthesis
progressive streaming updates
async-first execution
structured frontend rendering

The platform was designed with the assumption that AI systems must remain:

explainable
inspectable
deterministic
observable
resilient under partial failure
Product Workflow
Research Query
      ↓
Planner Phase
      ↓
Parallel Tool Dispatch
      ↓
Market + News + Filing Retrieval
      ↓
Structured Synthesis
      ↓
SSE Streaming Updates
      ↓
Persistent Research Report
      ↓
Analytics + Historical Retrieval
Core Features
AI Research Orchestration

Deterministic planner → dispatcher → synthesizer architecture built around typed orchestration contracts rather than opaque agent loops.

Capabilities
Multi-step orchestration pipelines
Tool-aware planning
Parallel execution strategy
Structured synthesis generation
Failure-tolerant execution
Context-aware report assembly
Real-Time Streaming Research

SignalStack streams orchestration progress in real time using Server-Sent Events (SSE).

The frontend progressively renders:

planning stages
tool execution states
synthesis progress
report completion
orchestration failures
partial recovery states

without requiring polling or websocket infrastructure.

Structured Research Reports

AI output is schema-constrained and rendered as structured UI components instead of raw markdown.

Supported sections include:

executive summaries
company overviews
comparative analysis
earnings breakdowns
risk assessments
filing insights
news intelligence
sentiment aggregation
Multi-Tenant Architecture

SignalStack is designed as a tenant-aware platform from the database layer upward.

Isolation guarantees include:

org-scoped repositories
tenant context injection
RBAC enforcement
scoped report visibility
isolated audit trails
organization membership controls
Research Persistence

Every orchestration run is fully persisted.

Includes:

orchestration metadata
tool execution history
cached synthesis outputs
report versioning
audit events
source attribution metadata
Async-First Backend

The FastAPI backend is fully async-native.

Designed for:

concurrent orchestration execution
streaming workloads
external API fan-out
long-running synthesis tasks
scalable IO-heavy operations
System Architecture
High-Level Architecture
<img width="2165" height="1660" alt="mermaid-diagram" src="https://github.com/user-attachments/assets/ace45a6c-612b-4c67-974f-f0ed6898cf87" />

Orchestration Pipeline
<img width="3448" height="2012" alt="mermaid-diagram (1)" src="https://github.com/user-attachments/assets/f7cd2399-4e69-4b2d-9fe7-5945916a0a6f" />

Request Lifecycle
<img width="3038" height="326" alt="mermaid-diagram (2)" src="https://github.com/user-attachments/assets/120c7c82-9a3c-406f-9e90-42ebe66ac8fb" />

Frontend Architecture
Design Philosophy

The frontend is built as a structured analytical workspace rather than a generic dashboard.

Principles
information density without clutter
progressive disclosure
deterministic rendering
stream-first UX
strongly typed state boundaries
server/client separation
Frontend Stack
Layer	Technology
Framework	Next.js 14 App Router
Language	TypeScript
Styling	TailwindCSS
State	React Query
Auth	Clerk
Charts	Recharts
Streaming	Native EventSource
UI System	shadcn/ui-inspired architecture
Component Architecture
features/
├── dashboard/
├── reports/
├── research/
│   ├── api/
│   ├── hooks/
│   ├── components/
│   ├── orchestration/
│   └── streaming/
├── watchlist/
└── analytics/

The frontend follows feature-oriented isolation rather than global component sprawl.

Backend Architecture
Backend Layers
API Layer
    ↓
Service Layer
    ↓
Orchestration Layer
    ↓
Repository Layer
    ↓
Database Layer
Core Backend Principles
Async-First

All orchestration, database access, and external IO operations are async-native.

Deterministic Orchestration

No opaque “multi-agent swarm” abstractions.

The orchestration engine uses:

planner
dispatcher
synthesizer

with explicit typed boundaries.

Repository Isolation

Tenant filtering is enforced at the repository boundary.

No raw database access exists inside route handlers.

Tech Stack
Frontend
Technology	Purpose
Next.js 14	App Router frontend
TypeScript	Strict typing
React Query	Server state + caching
TailwindCSS	Design system
Clerk	Authentication
Recharts	Analytical visualizations
Backend
Technology	Purpose
FastAPI	Async API framework
SQLAlchemy Async	ORM layer
PostgreSQL	Persistent storage
Alembic	Database migrations
Pydantic	Validation contracts
SSE	Real-time orchestration streaming
AI + Retrieval
Technology	Purpose
Anthropic Claude	Structured synthesis
ChromaDB	Vector retrieval
News APIs	Financial news retrieval
Market APIs	Pricing + company data
VADER	Sentiment classification
Infrastructure
Technology	Purpose
Replit	Full-stack deployment
Railway	Backend hosting option
Vercel	Frontend deployment option
Supabase Postgres	Managed PostgreSQL
Docker	Containerization
Project Structure
signalstack/
├── frontend/
│   ├── app/
│   │   ├── dashboard/
│   │   ├── research/
│   │   ├── reports/
│   │   └── analytics/
│   │
│   ├── components/
│   │   ├── charts/
│   │   ├── layout/
│   │   ├── streaming/
│   │   └── ui/
│   │
│   ├── features/
│   │   ├── research/
│   │   ├── reports/
│   │   ├── dashboard/
│   │   └── watchlist/
│   │
│   ├── lib/
│   ├── hooks/
│   ├── providers/
│   ├── styles/
│   └── types/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │
│   │   ├── orchestration/
│   │   │   ├── prompts/
│   │   │   ├── planner.py
│   │   │   ├── dispatcher.py
│   │   │   ├── synthesizer.py
│   │   │   └── engine.py
│   │   │
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── middleware/
│   │   ├── security/
│   │   ├── tools/
│   │   ├── clients/
│   │   ├── models/
│   │   ├── db/
│   │   └── core/
│   │
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
│
├── docker-compose.yml
├── README.md
└── .env.example
Local Development Setup
Prerequisites
Node.js 20+
Python 3.11+
PostgreSQL 16+
pnpm / npm
Clerk account
Anthropic API key
Clone Repository
git clone https://github.com/shafiqahmed-786/signalstack.git

cd signalstack
Frontend Setup
cd frontend

npm install

Create environment file:

cp .env.example .env.local

Run development server:

npm run dev

Frontend runs on:

http://localhost:3000
Backend Setup
cd backend

python -m venv .venv

source .venv/bin/activate

Install dependencies:

pip install -r requirements.txt

Create environment file:

cp .env.example .env

Run migrations:

alembic upgrade head

Start backend:

uvicorn app.main:app --reload

Backend runs on:

http://localhost:8000
Docker Setup
docker-compose up --build
Environment Variables
Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
Backend
DATABASE_URL=
ANTHROPIC_API_KEY=

CLERK_SECRET_KEY=
CLERK_PUBLISHABLE_KEY=

NEWS_API_KEY=
ALPHA_VANTAGE_KEY=

ENVIRONMENT=development
LOG_LEVEL=INFO
API Overview
Research
Method	Endpoint	Description
POST	/api/v1/research	Submit research query
GET	/api/v1/research/{id}	Fetch report
GET	/api/v1/research	List reports
PATCH	/api/v1/research/{id}	Update metadata
DELETE	/api/v1/research/{id}	Archive report
Streaming
Method	Endpoint	Description
GET	/api/v1/research/{id}/stream	SSE orchestration stream
GET	/api/v1/research/{id}/status	Poll orchestration state
Organizations
Method	Endpoint	Description
GET	/api/v1/org/members	List organization members
POST	/api/v1/org/invite	Invite member
PATCH	/api/v1/org/roles	Update RBAC roles
Streaming Architecture
Why SSE Instead of WebSockets

SignalStack uses Server-Sent Events because orchestration is:

server → client dominant
sequential
append-oriented
stream-based

SSE significantly simplifies:

infrastructure complexity
reconnection semantics
HTTP compatibility
deployment stability
browser integration

while preserving real-time UX.

Event Lifecycle
created
planning
tool_started
tool_completed
synthesizing
completed
failed
partial
heartbeat
Streaming Flow
<img width="1629" height="129" alt="mermaid-diagram (3)" src="https://github.com/user-attachments/assets/493c5c21-d700-4b13-8f4c-30675a0be276" />

Frontend Synchronization

React Query and EventSource are synchronized through orchestration state reducers.

This enables:

optimistic rendering
incremental UI updates
tool-level progress tracking
live timeline rendering

without invalidating full report state repeatedly.

Research Pipeline
1. Planning

The planner converts free-form research intent into a deterministic execution graph.

Produces:

companies
tool requirements
orchestration intent
dependency graph
2. Dispatching

Independent tools execute concurrently using:

asyncio.gather(...)

Includes:

timeout protection
retry handling
partial failure isolation
confidence scoring
3. Synthesis

The synthesizer combines tool outputs into structured report contracts.

Output is validated against typed schemas before persistence.

4. Persistence

Final reports are persisted as JSONB-backed structured contracts.

Includes:

report metadata
orchestration metrics
tool outputs
source attribution
5. Finalization

The system emits final orchestration states:

completed
partial
failed

with deterministic recovery semantics.

Database Design
Major Entities
Organizations

Tenant root entity.

All scoped resources inherit organization ownership.

Users

Mapped from Clerk identities.

Includes:

auth metadata
org membership
audit relationships
Research Reports

Core persistent analytical artifact.

Stores:

orchestration state
structured reports
synthesis metadata
execution metrics
Organization Memberships

RBAC layer controlling:

admins
analysts
scoped permissions
Audit Logs

Immutable operational history.

Tracks:

entity mutations
request correlation
tenant activity
Frontend Design System
Tailwind Strategy

SignalStack uses a token-driven Tailwind architecture.

Design goals:

high-density layouts
dark-first interfaces
analytical readability
strong visual hierarchy
Dark Mode

The platform is optimized around dark analytical interfaces.

Palette includes:

deep navy backgrounds
teal orchestration accents
muted grayscale hierarchy
semantic risk colors
React Query Strategy

React Query is used for:

server-state synchronization
report caching
optimistic mutations
stale invalidation
orchestration hydration
Deployment
Replit Deployment

SignalStack is deployable directly through Replit for rapid full-stack hosting.

Production deployment includes:

frontend serving
backend API hosting
environment secret management
persistent storage configuration
Production Considerations
Recommended Production Topology
Frontend → Vercel
Backend → Railway/Fly.io
Database → Managed PostgreSQL
Vector Store → Persistent Volume
Scalability Considerations
Horizontal Scaling

The backend is stateless outside persistence layers.

Supports:

multi-instance orchestration workers
distributed streaming
queue-backed execution
Database

PostgreSQL JSONB storage allows flexible report evolution without constant schema migration churn.

Streaming

SSE infrastructure is lightweight enough for high concurrent research workloads.

Engineering Decisions
Why FastAPI
async-native
excellent Pydantic integration
strong typing ergonomics
ideal for orchestration workloads
Why Next.js 14
App Router architecture
server/client composition
strong caching semantics
production-grade rendering pipeline
Why SSE
simpler than WebSockets
ideal for orchestration streams
easier infrastructure model
reliable HTTP semantics
Why Clerk

Authentication is infrastructure, not product differentiation.

Clerk provides:

org management
secure session handling
JWT lifecycle management
production-grade auth UX

allowing engineering effort to focus on orchestration quality.

Why PostgreSQL

The workload requires:

relational integrity
JSONB flexibility
transactional consistency
analytical querying

PostgreSQL fits the model naturally.

Why React Query

Research workloads are heavily asynchronous.

React Query provides:

cache coordination
stale invalidation
request deduplication
mutation synchronization

without custom client-state complexity.

Performance & Scalability
Async Orchestration

All external IO operations execute concurrently.

This minimizes:

orchestration latency
API wait chains
blocking operations
Query Caching

Multi-layer caching includes:

report-level cache
tool-level cache
frontend fetch cache
Token Budgeting

The synthesizer uses token budgeting strategies to:

trim low-priority context
preserve high-value signals
reduce hallucination risk
Partial Failure Recovery

SignalStack intentionally supports degraded execution.

Examples:

news API failure
filing retrieval timeout
incomplete market data

The orchestrator still generates partial reports with explicit confidence metadata.

Security Considerations
Clerk Authentication

JWT validation occurs at middleware boundaries before any tenant resolution occurs.

Tenant Isolation

Every repository operation is organization-scoped.

Cross-tenant access paths are explicitly prevented.

Backend Guards

RBAC enforcement occurs:

before service invocation
before repository access
before mutation operations
SSE Protection

Streaming endpoints require:

authenticated sessions
tenant validation
scoped report ownership
Structured Validation

All AI outputs pass through typed validation contracts before persistence or rendering.

This prevents:

malformed synthesis payloads
schema drift
frontend instability
Future Improvements
Planned Roadmap
AI Layer
tool confidence calibration
ranking-based retrieval
reinforcement feedback loops
portfolio-level synthesis
Infrastructure
Redis-backed distributed queues
background worker orchestration
horizontal streaming workers
distributed cache invalidation
Product
collaborative research sessions
analyst annotations
portfolio tracking
scheduled research automation
PDF export pipeline
webhook integrations
Screenshots
Dashboard
/docs/screenshots/dashboard.png
Real-Time Research Streaming
/docs/screenshots/streaming.png
Structured Report Rendering
/docs/screenshots/report.png
License

MIT License

Copyright © 2026 SignalStack
