from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from typing import Optional, List
import asyncio
from uuid import uuid4

from ..models.schemas import (
    ResearchRequest, 
    ResearchResponse, 
    JobStatus,
    ResearchResult
)
from ..core.orchestrator import ResearchOrchestrator
from ..utils.export import ExportService

# Initialize services
orchestrator = ResearchOrchestrator()
export_service = ExportService()

# Create router
router = APIRouter(prefix="/api/v1", tags=["research"])

@router.post("/research", response_model=ResearchResponse)
async def create_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks
):
    """Start a new research job"""
    try:
        job_id = str(uuid4())
        
        # Start research in background
        background_tasks.add_task(
            orchestrator.research,
            query=request.query,
            max_results=request.max_results,
            freshness=request.freshness,
            style=request.style.value,
            search_engines=[e.value for e in request.search_engines]
        )
        
        return ResearchResponse(
            job_id=job_id,
            status="started",
            message="Research job started successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get job status"""
    status = orchestrator.get_job_status(job_id)
    
    if status["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatus(**status)

@router.get("/research/{job_id}")
async def get_research_result(job_id: str):
    """Get research results"""
    result = await orchestrator.get_result(job_id)
    
    if not result:
        status = orchestrator.get_job_status(job_id)
        if status["status"] == "not_found":
            raise HTTPException(status_code=404, detail="Job not found")
        elif status["status"] == "failed":
            raise HTTPException(status_code=500, detail=status.get("error", "Research failed"))
        else:
            raise HTTPException(status_code=202, detail=f"Job still {status['status']}")
    
    return result

@router.get("/export/{job_id}")
async def export_research(
    job_id: str,
    format: str = "pdf"
):
    """Export research results"""
    result = await orchestrator.get_result(job_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    if format.lower() == "pdf":
        pdf_bytes = export_service.to_pdf(result)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf"
        )