"""Dashboard endpoints for monitoring the multi-agent system."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..services.database import RegulationDatabase
from ..utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DashboardStats(BaseModel):
    """Dashboard statistics model."""

    total_tasks: int
    tasks_today: int
    tasks_this_week: int
    success_rate: float
    average_execution_time: float
    active_agents: List[str]
    recent_regulations: int
    compliance_alerts: int


class AgentPerformance(BaseModel):
    """Agent performance metrics."""

    agent_name: str
    tasks_completed: int
    average_time: float
    success_rate: float
    tools_used: Dict[str, int]


class ComplianceAlert(BaseModel):
    """Compliance alert model."""

    id: str
    type: str
    severity: str
    message: str
    agency: str
    date: datetime
    action_required: bool


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    time_range: str = Query("week", regex="^(day|week|month)$"),
):
    """Get dashboard statistics."""
    try:
        # In production, fetch from actual data
        stats = DashboardStats(
            total_tasks=156,
            tasks_today=12,
            tasks_this_week=45,
            success_rate=0.94,
            average_execution_time=34.5,
            active_agents=[
                "compliance_agent",
                "legal_analysis_agent",
                "risk_assessment_agent",
                "document_review_agent",
                "research_agent",
            ],
            recent_regulations=8,
            compliance_alerts=3,
        )
        
        return stats
        
    except Exception as e:
        logger.error("dashboard_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch stats")


@router.get("/agents/performance", response_model=List[AgentPerformance])
async def get_agents_performance(
    time_range: str = Query("week", regex="^(day|week|month)$"),
):
    """Get performance metrics for all agents."""
    try:
        # In production, calculate from actual metrics
        performance = [
            AgentPerformance(
                agent_name="compliance_agent",
                tasks_completed=42,
                average_time=28.3,
                success_rate=0.95,
                tools_used={
                    "ANVISASearchTool": 35,
                    "ComplianceChecklistTool": 28,
                    "RegulatoryDeadlineTool": 15,
                },
            ),
            AgentPerformance(
                agent_name="legal_analysis_agent",
                tasks_completed=38,
                average_time=35.7,
                success_rate=0.92,
                tools_used={
                    "LegalDatabaseSearchTool": 32,
                    "ContractAnalysisTool": 18,
                    "LegalOpinionGeneratorTool": 22,
                },
            ),
            AgentPerformance(
                agent_name="risk_assessment_agent",
                tasks_completed=35,
                average_time=42.1,
                success_rate=0.94,
                tools_used={
                    "RiskMatrixTool": 30,
                    "RiskScenarioAnalysisTool": 25,
                    "ComplianceRiskAssessmentTool": 20,
                },
            ),
            AgentPerformance(
                agent_name="document_review_agent",
                tasks_completed=32,
                average_time=25.8,
                success_rate=0.97,
                tools_used={
                    "DocumentGeneratorTool": 96,
                },
            ),
            AgentPerformance(
                agent_name="research_agent",
                tasks_completed=45,
                average_time=31.2,
                success_rate=0.93,
                tools_used={
                    "RegulatoryNewsMonitorTool": 40,
                    "BenchmarkingTool": 25,
                    "RegulatoryIntelligenceTool": 30,
                },
            ),
        ]
        
        return performance
        
    except Exception as e:
        logger.error("agent_performance_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch performance")


@router.get("/compliance/alerts", response_model=List[ComplianceAlert])
async def get_compliance_alerts(
    severity: Optional[str] = Query(None, regex="^(low|medium|high|critical)$"),
    agency: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
):
    """Get recent compliance alerts."""
    try:
        # In production, fetch from monitoring system
        alerts = [
            ComplianceAlert(
                id="ALERT-001",
                type="deadline",
                severity="high",
                message="Renovação de AFE vence em 45 dias",
                agency="ANVISA",
                date=datetime.now() - timedelta(hours=2),
                action_required=True,
            ),
            ComplianceAlert(
                id="ALERT-002",
                type="regulation_change",
                severity="medium",
                message="Nova RDC publicada - Dispositivos Médicos",
                agency="ANVISA",
                date=datetime.now() - timedelta(days=1),
                action_required=True,
            ),
            ComplianceAlert(
                id="ALERT-003",
                type="audit",
                severity="low",
                message="Auditoria interna programada",
                agency="Internal",
                date=datetime.now() - timedelta(days=3),
                action_required=False,
            ),
        ]
        
        # Filter by severity
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        # Filter by agency
        if agency:
            alerts = [a for a in alerts if a.agency == agency]
        
        return alerts[:limit]
        
    except Exception as e:
        logger.error("compliance_alerts_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")


@router.get("/tasks/timeline")
async def get_tasks_timeline(
    days: int = Query(7, ge=1, le=30),
):
    """Get task execution timeline."""
    try:
        # In production, fetch from task history
        timeline = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            timeline.append({
                "date": date.strftime("%Y-%m-%d"),
                "total_tasks": 20 - i,
                "successful": 18 - i,
                "failed": 2,
                "average_time": 30 + (i * 2),
            })
        
        return timeline
        
    except Exception as e:
        logger.error("task_timeline_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch timeline")


@router.get("/regulations/updates")
async def get_regulation_updates(
    days: int = Query(30, ge=1, le=90),
    agency: Optional[str] = None,
):
    """Get recent regulatory updates."""
    try:
        # In production, use actual database
        db = RegulationDatabase()
        await db.initialize()
        
        updates = await db.get_recent_updates(days=days, agency=agency)
        
        await db.close()
        
        # Convert to dict for response
        return [
            {
                "id": update.id,
                "agency": update.agency,
                "title": update.title,
                "summary": update.summary,
                "url": update.url,
                "impact_level": update.impact_level,
                "published_date": update.published_date.isoformat() if update.published_date else None,
            }
            for update in updates
        ]
        
    except Exception as e:
        logger.error("regulation_updates_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch updates")


@router.get("/metrics/summary")
async def get_metrics_summary():
    """Get overall system metrics summary."""
    try:
        summary = {
            "system_health": "healthy",
            "uptime_hours": 720,  # 30 days
            "total_requests": 4567,
            "cache_hit_rate": 0.78,
            "memory_usage_mb": 512,
            "active_connections": 12,
            "queue_size": 3,
            "error_rate": 0.02,
            "response_time_p50": 250,
            "response_time_p95": 800,
            "response_time_p99": 1200,
        }
        
        return summary
        
    except Exception as e:
        logger.error("metrics_summary_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch metrics")