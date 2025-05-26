"""LangServe application for LangChain deployment compatibility."""

import os
from typing import Any, Dict, List

from fastapi import FastAPI
from langchain.pydantic_v1 import BaseModel, Field
from langserve import add_routes

from ..graph import RegulatoryMultiAgentSystem
from ..config.langsmith import configure_langsmith


class RegulatoryInput(BaseModel):
    """Input schema for regulatory analysis."""
    
    task: str = Field(
        ...,
        description="Regulatory task or question to analyze",
        example="Análise de conformidade ANVISA para dispositivos médicos classe II"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for the analysis"
    )
    thread_id: str = Field(
        default=None,
        description="Thread ID for conversation continuity"
    )
    max_iterations: int = Field(
        default=10,
        description="Maximum iterations for agent processing"
    )


class RegulatoryOutput(BaseModel):
    """Output schema for regulatory analysis."""
    
    success: bool = Field(..., description="Whether the analysis was successful")
    output: str = Field(None, description="Final analysis output")
    context: Dict[str, Any] = Field(..., description="Enriched context with all analyses")
    messages: List[Dict[str, str]] = Field(..., description="Conversation messages")
    confidence_score: float = Field(..., description="Overall confidence score")
    quality_checks: Dict[str, bool] = Field(..., description="Quality validation results")
    citations: List[Dict[str, Any]] = Field(default_factory=list, description="Citations from Perplexity")
    thread_id: str = Field(..., description="Thread ID for reference")
    langsmith_url: str = Field(None, description="LangSmith trace URL")


# Create Runnable wrapper for LangServe
class SolutoRegulatoryRunnable:
    """Runnable wrapper for the Soluto regulatory system."""
    
    def __init__(self):
        # Configure LangSmith
        configure_langsmith()
        
        # Initialize the system
        self.system = RegulatoryMultiAgentSystem()
        
    async def ainvoke(self, input_data: RegulatoryInput) -> RegulatoryOutput:
        """Async invoke the regulatory system."""
        try:
            # Run the system
            result = await self.system.run(
                task=input_data.task,
                thread_id=input_data.thread_id,
                max_iterations=input_data.max_iterations,
                context=input_data.context
            )
            
            # Extract citations from context
            citations = result.get("context", {}).get("perplexity_citations", [])
            
            # Build output
            return RegulatoryOutput(
                success=result["success"],
                output=result.get("output"),
                context=result.get("context", {}),
                messages=result.get("messages", []),
                confidence_score=result.get("confidence_score", 0.0),
                quality_checks=result.get("quality_checks", {}),
                citations=citations,
                thread_id=result.get("thread_id"),
                langsmith_url=get_langsmith_url(result.get("thread_id", ""))
            )
            
        except Exception as e:
            return RegulatoryOutput(
                success=False,
                output=str(e),
                context={},
                messages=[],
                confidence_score=0.0,
                quality_checks={},
                citations=[],
                thread_id=input_data.thread_id or "",
                langsmith_url=None
            )
    
    def invoke(self, input_data: RegulatoryInput) -> RegulatoryOutput:
        """Sync invoke (runs async internally)."""
        import asyncio
        return asyncio.run(self.ainvoke(input_data))
    
    async def astream(self, input_data: RegulatoryInput):
        """Stream results (yields final result for now)."""
        result = await self.ainvoke(input_data)
        yield result
    
    def stream(self, input_data: RegulatoryInput):
        """Sync stream (yields final result)."""
        result = self.invoke(input_data)
        yield result


def create_langserve_app() -> FastAPI:
    """Create FastAPI app with LangServe routes."""
    app = FastAPI(
        title="Soluto Regulatory Agents - LangServe",
        description="LangChain-compatible API for Soluto regulatory analysis system",
        version="1.0.0",
    )
    
    # Create the runnable
    regulatory_runnable = SolutoRegulatoryRunnable()
    
    # Add LangServe routes
    add_routes(
        app,
        regulatory_runnable,
        path="/regulatory",
        input_type=RegulatoryInput,
        output_type=RegulatoryOutput,
        config_keys=["configurable"],
        enable_feedback_endpoint=True,
        enable_public_trace_link_endpoint=True,
        playground_type="default",
    )
    
    @app.get("/")
    async def root():
        """Root endpoint with information."""
        return {
            "message": "Soluto Regulatory Agents - LangServe API",
            "version": "1.0.0",
            "endpoints": {
                "invoke": "/regulatory/invoke",
                "stream": "/regulatory/stream",
                "batch": "/regulatory/batch",
                "playground": "/regulatory/playground",
                "feedback": "/regulatory/feedback",
            },
            "langchain_compatibility": True,
            "langsmith_enabled": os.getenv("LANGCHAIN_TRACING_V2", "false") == "true",
        }
    
    return app


# Create the app
langserve_app = create_langserve_app()