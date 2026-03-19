"""
CRM Deduplication Tool - Python Backend
FastAPI application for duplicate detection and merge operations.
"""
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import health, scan, merge, hubspot, salesforce, reports

app = FastAPI(
    title="CRM Dedup API",
    description="Backend for CRM duplicate detection and merging",
    version="0.1.0",
)

settings = get_settings()

# CORS: use exact origins from config + regex for Netlify preview deploys
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://[a-z0-9\-]+--crm-dedup-tool\.netlify\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(hubspot.router, prefix="/hubspot", tags=["HubSpot"])
app.include_router(salesforce.router, prefix="/salesforce", tags=["Salesforce"])
app.include_router(scan.router, prefix="/scan", tags=["Scan"])
app.include_router(merge.router, prefix="/merge", tags=["Merge"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])


@app.get("/")
async def root():
    return {"service": "crm-dedup-api", "status": "running"}
