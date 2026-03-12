"""
CRM Deduplication Tool - Python Backend
FastAPI application for duplicate detection and merge operations.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, scan, merge, hubspot

app = FastAPI(
    title="CRM Dedup API",
    description="Backend for CRM duplicate detection and merging",
    version="0.1.0",
)

# CORS configuration - update for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "https://*.netlify.app",  # Netlify preview
        # Add production domain here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(hubspot.router, prefix="/hubspot", tags=["HubSpot"])
app.include_router(scan.router, prefix="/scan", tags=["Scan"])
app.include_router(merge.router, prefix="/merge", tags=["Merge"])


@app.get("/")
async def root():
    return {"service": "crm-dedup-api", "status": "running"}
