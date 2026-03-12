"""Report endpoints."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.reports import ReportService
from app.services.supabase_client import get_supabase

router = APIRouter()


@router.post("/generate/{merge_id}")
async def generate_report(merge_id: str, user_id: str):
    """Generate a report for a completed merge."""
    service = ReportService()

    try:
        report = await service.generate_report(merge_id, user_id)
        return report
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{report_id}")
async def get_report(report_id: str):
    """Get report data."""
    supabase = get_supabase()

    result = supabase.table("reports").select("*").eq(
        "id", report_id
    ).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Report not found")

    return result.data


@router.get("/{report_id}/pdf")
async def download_report_pdf(report_id: str):
    """Download report as PDF."""
    service = ReportService()

    try:
        pdf_bytes = await service.generate_pdf(report_id)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=dedup-report-{report_id[:8]}.pdf"
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{user_id}")
async def list_user_reports(user_id: str, page: int = 1, per_page: int = 20):
    """List all reports for a user."""
    supabase = get_supabase()

    offset = (page - 1) * per_page

    result = supabase.table("reports").select("*").eq(
        "user_id", user_id
    ).order("created_at", desc=True).range(offset, offset + per_page - 1).execute()

    # Get total count
    count_result = supabase.table("reports").select(
        "id", count="exact"
    ).eq("user_id", user_id).execute()

    total = count_result.count if count_result.count else 0

    return {
        "reports": result.data or [],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
    }
