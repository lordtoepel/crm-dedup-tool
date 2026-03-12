# CRM Deduplication Tool

A web application for detecting and merging duplicate records in HubSpot and Salesforce CRMs.

## Features

- **Duplicate Detection**: Exact and fuzzy matching across contacts, companies, and deals
- **Intelligent Winner Selection**: Configurable rules (oldest, most recent, most associations)
- **Field Blending**: Winner fields with gap-filling from losers
- **Bulk Merge**: Execute merges at scale with progress tracking
- **Client Reports**: Downloadable PDF reports

## Tech Stack

- **Frontend**: Next.js 14, React, Tailwind CSS
- **Backend**: Python FastAPI, Celery, RapidFuzz
- **Database**: Supabase (PostgreSQL)
- **Queue**: Redis
- **Hosting**: Netlify (frontend), Railway (backend)

## Local Development

### Prerequisites

- Node.js 20+
- Python 3.11+
- Redis (for background jobs)

### Frontend

```bash
npm install
npm run dev
```

### Backend

```bash
cd api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Celery Worker

```bash
cd api
celery -A app.tasks.celery_app worker --loglevel=info
```

## Environment Variables

See `.env.local.example` (frontend) and `api/.env.example` (backend).

## Database Setup

Run the migration in Supabase SQL Editor:

```bash
cat supabase/migrations/001_initial_schema.sql
```

## License

Proprietary - LeanScale
