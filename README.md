# Red Forge

**AI-Powered Regulatory Compliance Intelligence Platform**

Red Forge converts unstructured regulatory data into structured, actionable compliance intelligence. It continuously monitors regulations, detects security vulnerabilities in your tech stack, maps them to compliance obligations, and auto-generates remediation tasks with regulatory deadlines.

---

## Architecture

```
                    +-------------------+
                    |   Next.js Dashboard  |
                    |   (Real-time UI)     |
                    +--------+----------+
                             |
                         Nginx (Reverse Proxy + Rate Limiting)
                             |
                    +--------+----------+
                    |   FastAPI Backend    |
                    |   (API + Background  |
                    |    Scanners)         |
                    +--------+----------+
                             |
          +------------------+------------------+
          |                  |                  |
   +------+------+   +------+------+   +------+------+
   |  PostgreSQL  |   |    Neo4j    |   |   Qdrant    |
   |  (Supabase)  |   | (Knowledge |   |  (Vector    |
   |  Relational  |   |   Graph)   |   |   Search)   |
   +--------------+   +------------+   +-------------+
```

### Core Stack

| Layer | Technology |
|---|---|
| AI/ML | LangGraph + LangChain + Google Vertex AI (Gemini 2.0 Flash) |
| Backend | FastAPI (Python 3.11) |
| Frontend | Next.js 14 + TypeScript |
| Relational DB | PostgreSQL via Supabase |
| Knowledge Graph | Neo4j Aura |
| Vector Store | Qdrant |
| Caching | Redis |
| Monitoring | Prometheus + Grafana |
| Deployment | Docker Compose + Nginx + AWS EC2 |
| CI/CD | GitHub Actions |

---

## Features

### 1. Multi-Agent Compliance Pipeline

LangGraph orchestrates 5 specialized AI agents that process regulatory documents end-to-end:

```
Document → Scanner → Extractor → Impact Analyst → Action Planner → Validator → Results
```

| Agent | Role |
|---|---|
| **Scanner** | Classifies document relevance and sector applicability |
| **Extractor** | Extracts structured obligations (who, what, deadline, penalty) |
| **Impact Analyst** | Maps obligations to org controls, identifies gaps, fetches CVEs |
| **Action Planner** | Generates prioritized action items with deadlines and owners |
| **Validator** | Cross-checks outputs for consistency and completeness |

### 2. Proactive CVE Monitoring

Continuously scans your registered tech stack against real vulnerability databases:

- **OSV.dev** — exact package+version vulnerability lookup (PyPI, npm, Maven, Go)
- **NVD** — NIST National Vulnerability Database with CVSS scoring
- **CISA KEV** — Known Exploited Vulnerabilities catalog (actively exploited = CRITICAL)

Every new CVE is automatically:
- Mapped to compliance obligations (which regulations does this violate?)
- Scored for blast radius (total fine exposure across jurisdictions)
- Pushed to Slack + Jira with full remediation steps

### 3. Cross-CVE Blast Radius

Calculates total regulatory fine exposure when a vulnerability is found:

```json
POST /api/v1/cve/blast-radius
{
  "cve_id": "CVE-2024-3094",
  "cvss_score": 9.8,
  "cwes": ["CWE-311"],
  "org_annual_revenue_usd": 5000000
}
→
{
  "total_exposure_usd": 21640000,
  "jurisdictions_triggered": ["EU", "India", "Global"],
  "earliest_deadline_hours": 48,
  "breakdown": [
    {"framework": "GDPR", "fine_usd": 20000000, "deadline_hours": 72},
    {"framework": "RBI_PA", "fine_usd": 600000, "deadline_hours": 48},
    {"framework": "PCI_DSS", "fine_usd": 300000, "deadline_hours": 48}
  ]
}
```

Fine schedules are loaded from `knowledge/regulatory/fine_schedules.json` — not hardcoded. Covers: GDPR, DPDP, RBI, PCI-DSS, DORA, NIS2, SEC, SEBI, HIPAA, ISO 27001.

### 4. Regulation Diff Engine

When a regulation is re-processed, the system snapshots its obligations and diffs against the previous version:

- New obligations added
- Obligations removed
- Deadline changes (tightened or relaxed)
- Penalty changes

Each diff is classified by severity: `critical` (deadline tightened) → `major` (obligations added/removed) → `minor` (text changes).

### 5. Regulatory Horizon Scanning

Background task monitors live regulatory feeds every 12 hours:

| Source | Coverage |
|---|---|
| Federal Register API | US regulations (SEC, CFPB, OCC) |
| EUR-Lex RSS | EU regulations (GDPR, AI Act, DORA) |
| SEBI RSS | Indian capital markets regulations |

New regulations are auto-ingested, checked for relevance, and high-priority ones trigger Slack alerts.

### 6. AI Q&A Assistant

RAG-based question answering over your entire compliance knowledge base:

```json
POST /api/v1/ask
{
  "question": "What are the RBI KYC requirements for payment aggregators?",
  "jurisdiction": "India"
}
→
{
  "answer": "According to RBI PA Guidelines...",
  "sources": [{"text": "...", "score": 0.92, "source_id": "..."}],
  "controls_referenced": ["CTRL-ENC-001", "CTRL-LOG-003"]
}
```

Searches Qdrant vectors + Neo4j knowledge graph, then synthesizes via Gemini.

### 7. Compliance Health Score

Single API call returns organization-wide compliance posture:

```json
GET /api/v1/compliance
→
{
  "score": 67.3,
  "risk_level": "MEDIUM",
  "breakdown": {
    "control_coverage": {"score": 72.0, "weight": 0.4},
    "action_completion": {"score": 45.0, "weight": 0.25},
    "regulation_coverage": {"score": 80.0, "weight": 0.2},
    "cve_resolved": {"score": 60.0, "weight": 0.15}
  }
}
```

### 8. Audit Report Generation

Produces structured, audit-ready compliance reports:

```
GET /api/v1/reports/audit
```

Includes: compliance score, all controls with coverage, open action items by priority, regulation tracking status, active CVE alerts, identified gaps, and risk summary.

### 9. Auto-Notifications

When the pipeline detects critical findings:

| Trigger | Action |
|---|---|
| Risk score >= 8/10 | Slack alert auto-sent |
| CISA KEV CVE found | Slack alert auto-sent |
| CRITICAL action items | Jira tickets auto-created |
| New high-risk regulation discovered | Slack alert via horizon scanner |
| New CRITICAL/HIGH CVE in tech stack | Slack + Jira via proactive scanner |

### 10. Cross-Jurisdiction Conflict Detection

Queries the Neo4j knowledge graph to find regulations that contradict each other across jurisdictions (e.g., GDPR right-to-erasure vs SEC 7-year retention).

---

## API Reference

All `/api/v1/*` endpoints require `X-API-Key` header when `API_KEY` is set in `.env`.

### Compliance Intelligence
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/compliance` | Overall compliance score (0-100) |
| `GET` | `/api/v1/compliance/summary` | Executive summary |
| `POST` | `/api/v1/ask` | AI Q&A over regulations + controls |
| `GET` | `/api/v1/reports/audit` | Full audit report |
| `GET` | `/api/v1/reports/audit/regulation/{id}` | Per-regulation audit |

### CVE Intelligence
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/cve/suggest-fix` | CVE ID → patch + compliance obligations + deadlines |
| `POST` | `/api/v1/cve/blast-radius` | Fine exposure calculation |
| `POST` | `/api/v1/cve/upload-stack` | Upload requirements.txt / package.json / stack.json |
| `POST` | `/api/v1/cve/scan-now` | Trigger immediate CVE scan |
| `GET` | `/api/v1/cve/alerts` | List proactively detected CVE alerts |
| `GET` | `/api/v1/cve/regulation-diffs` | Regulations with detected changes |

### Regulations & Pipeline
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/regulations/process` | Run 5-agent pipeline on a document |
| `GET` | `/api/v1/regulations/feed` | Live regulatory feed (FR + EUR-Lex + SEBI) |
| `POST` | `/api/v1/regulations/search` | Semantic search over regulations |
| `GET` | `/api/v1/stream/{doc_id}` | SSE stream of pipeline progress |

### Controls & Actions
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/controls` | List compliance controls |
| `GET` | `/api/v1/controls/gaps/summary` | Compliance gap analysis |
| `GET` | `/api/v1/controls/drift` | 12-month compliance drift trend |
| `GET` | `/api/v1/controls/conflicts` | Cross-jurisdiction conflicts |
| `GET` | `/api/v1/actions` | List action items |
| `PATCH` | `/api/v1/actions/{id}/status` | Update action status |
| `POST` | `/api/v1/actions/export/jira` | Export actions to Jira |

### Organization
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/org/import-controls` | Upload controls (CSV/XLSX/PDF/JSON) |
| `POST` | `/api/v1/alerts/slack` | Send Slack alert |
| `POST` | `/api/v1/alerts/email` | Send email alert |

---

## Project Structure

```
red_forge/
├── agents/                    # LangGraph AI agents
│   ├── graph.py               # Orchestration graph
│   ├── scanner.py             # Relevance classification
│   ├── extractor.py           # Obligation extraction
│   ├── impact_analyst.py      # Gap analysis + CVE fetching
│   ├── action_planner.py      # Action item generation
│   ├── validator.py           # Output validation
│   └── state.py               # Shared state schema
├── api/                       # FastAPI backend
│   ├── main.py                # App + lifespan + middleware
│   ├── auth.py                # API key authentication
│   └── routes/
│       ├── regulations.py     # Pipeline + feed endpoints
│       ├── cve.py             # CVE intelligence API
│       ├── compliance.py      # Health score
│       ├── ask.py             # AI Q&A assistant
│       ├── reports.py         # Audit reports
│       ├── controls.py        # Controls + gaps + drift
│       ├── actions.py         # Action items + Jira
│       ├── alerts.py          # Slack + email
│       ├── upload.py          # File import (CSV/XLSX/PDF/JSON)
│       └── stream.py          # SSE streaming
├── ingestion/                 # Data connectors
│   ├── connectors/
│   │   ├── nvd.py             # NVD + CISA KEV
│   │   ├── osv.py             # OSV.dev package vulnerabilities
│   │   ├── federal_register.py
│   │   ├── eur_lex.py
│   │   └── sebi.py
│   ├── parsers/               # Document parsing (Docling)
│   └── chunkers/              # Semantic chunking
├── knowledge/                 # Knowledge management
│   ├── graph/
│   │   └── neo4j_client.py    # Knowledge graph operations
│   ├── vectors/
│   │   └── qdrant_store.py    # Vector search
│   ├── security/
│   │   ├── cve_control_mapper.py  # CVE → compliance mapping
│   │   └── blast_radius.py    # Fine exposure calculator
│   └── regulatory/
│       └── fine_schedules.json    # Regulatory fine data (not hardcoded)
├── monitoring/                # Background tasks
│   ├── proactive_scanner.py   # CVE scanner (every 6h)
│   ├── horizon_scanner.py     # Regulation scanner (every 12h)
│   └── regulation_differ.py   # Obligation diff engine
├── org_context/               # Organization data layer
│   └── models/
│       ├── schemas.py         # SQLAlchemy models
│       └── database.py        # CRUD operations
├── dashboard/                 # Next.js frontend
│   └── src/app/demo/
│       ├── page.tsx           # Main demo page
│       ├── lib/api.ts         # API client
│       └── components/        # UI components
├── docker/
│   ├── Dockerfile.api         # Python backend image
│   └── Dockerfile.frontend    # Next.js production image
├── nginx/
│   └── nginx.conf             # Reverse proxy config
├── scripts/
│   ├── setup-ec2.sh           # One-time EC2 setup
│   ├── deploy.sh              # Deploy/update on EC2
│   └── upload-to-ec2.ps1     # Upload from Windows
├── .github/workflows/
│   ├── deploy.yml             # CI/CD: test → build → deploy
│   └── pr-check.yml           # PR validation
├── docker-compose.prod.yml    # Production deployment
├── docker-compose.yml         # Local development
└── config.py                  # Pydantic settings
```

---

## Quick Start

### Local Development

```bash
# 1. Clone
git clone https://github.com/Arun973150/hack_a_war.git
cd hack_a_war

# 2. Copy and fill in your credentials
cp .env.example .env

# 3. Start infrastructure
docker compose up qdrant redis -d

# 4. Start backend
python -m venv venv
source venv/bin/activate        # or venv\Scripts\activate on Windows
pip install -e .
uvicorn api.main:app --reload --port 8000

# 5. Start frontend (separate terminal)
cd dashboard
npm install
npm run dev

# 6. Open
# Dashboard: http://localhost:3000/demo
# API docs:  http://localhost:8000/docs
```

### Production (AWS EC2)

```bash
# On your local machine
.\scripts\upload-to-ec2.ps1 -KeyFile "key.pem" -EC2IP "your-ip"

# On the EC2 instance
bash scripts/setup-ec2.sh    # first time only
bash scripts/deploy.sh
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string (Supabase) |
| `NEO4J_URI` | Yes | Neo4j Aura connection URI |
| `NEO4J_PASSWORD` | Yes | Neo4j password |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | Path to GCP service account JSON |
| `VERTEX_PROJECT` | Yes | GCP project ID |
| `API_KEY` | Recommended | API key for X-API-Key auth (empty = open) |
| `SLACK_WEBHOOK_URL` | Optional | Slack incoming webhook for alerts |
| `JIRA_BASE_URL` | Optional | Jira Cloud URL for ticket creation |
| `JIRA_API_TOKEN` | Optional | Jira API token |
| `SMTP_SENDER_EMAIL` | Optional | Gmail address for email alerts |
| `SMTP_APP_PASSWORD` | Optional | Gmail App Password |
| `SCAN_INTERVAL_HOURS` | Optional | CVE scan frequency (default: 6) |
| `HORIZON_SCAN_INTERVAL_HOURS` | Optional | Regulation scan frequency (default: 12) |

---

## How It Works (End-to-End Flow)

```
1. INGEST
   Customer uploads: policies, controls, tech stack (requirements.txt)
   System monitors: Federal Register, EUR-Lex, SEBI, NVD, CISA KEV

2. PROCESS
   New regulation found → 5-agent LangGraph pipeline:
   Scanner → Extractor → Impact Analyst → Action Planner → Validator
   CVE found → compliance mapping → blast radius calculation

3. MAP
   Regulation obligations ↔ Organization controls (Neo4j graph)
   CVE CWEs → compliance frameworks → regulatory deadlines

4. ALERT
   Risk >= 8 → Slack
   CISA KEV → Slack
   CRITICAL action → Jira ticket (auto-created)
   New regulation → Slack notification

5. REPORT
   Compliance score (0-100)
   Gap analysis
   Audit-ready reports
   Regulation version diffs
```

---

## CI/CD

GitHub Actions pipeline (`.github/workflows/deploy.yml`):

```
Push to main → Test (import checks) → Build (Docker images) → Deploy (SSH to EC2)
```

Required GitHub Secrets:
- `EC2_HOST` — EC2 public IP
- `EC2_SSH_KEY` — PEM private key
- `EC2_USER` — `ubuntu`
- `GHCR_TOKEN` — GitHub PAT with `write:packages`

---

## License

Proprietary. All rights reserved.
