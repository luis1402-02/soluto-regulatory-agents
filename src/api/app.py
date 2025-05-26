"""FastAPI application for the multi-agent system."""

import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from ..config import get_settings
from ..graph import RegulatoryMultiAgentSystem
from ..memory import RedisMemoryStore
from ..services.database import RegulationDatabase
from ..utils import get_logger, setup_logging
from .dashboard import router as dashboard_router
from .monitoring import router as monitoring_router, monitoring_service
from .models import HealthResponse, MemoryQuery, MemoryResponse, TaskRequest, TaskResponse

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting Soluto Regulatory Agents API")
    setup_logging()
    
    # Initialize memory store
    memory_store = RedisMemoryStore()
    await memory_store.initialize()
    
    # Initialize database
    db = RegulationDatabase()
    await db.initialize()
    await db.populate_initial_data()
    
    # Initialize system
    app.state.system = RegulatoryMultiAgentSystem(memory_store)
    app.state.db = db
    
    yield
    
    # Shutdown
    logger.info("Shutting down Soluto Regulatory Agents API")
    await app.state.system.cleanup()
    await memory_store.close()
    await db.close()


def create_app() -> FastAPI:
    """Create FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Soluto Regulatory Agents API",
        description="Sistema Multiagente Avançado para Conformidade Regulatória - Grupo Soluto",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(dashboard_router, prefix="/api")
    app.include_router(monitoring_router)
    
    # Add exception handler
    @app.exception_handler(Exception)
    async def exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_exception", error=str(exc), exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
    
    # Authentication middleware
    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        # Skip auth for health check and docs
        if request.url.path in ["/health", "/", "/api/docs", "/api/redoc"]:
            return await call_next(request)
            
        # Skip auth for static files
        if request.url.path.startswith("/static"):
            return await call_next(request)
            
        # Extract API key
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            # Try to get from query params for WebSocket
            api_key = request.query_params.get("api_key")
            
        if api_key != settings.api_key.get_secret_value():
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid API key"},
            )
            
        return await call_next(request)
    
    # Routes
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Root endpoint with system information."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Soluto Regulatory Agents</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .header {{
                    background: #1a1a1a;
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                }}
                .card {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                }}
                .agent {{
                    display: inline-block;
                    background: #007bff;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 20px;
                    margin: 5px;
                }}
                .tool {{
                    display: inline-block;
                    background: #28a745;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 15px;
                    margin: 3px;
                    font-size: 0.9em;
                }}
                code {{
                    background: #f4f4f4;
                    padding: 2px 6px;
                    border-radius: 3px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🤖 Sistema Multiagente Regulatório - Grupo Soluto</h1>
                <p>Sistema avançado de conformidade regulatória powered by LangGraph e GPT-4.1</p>
            </div>
            
            <div class="card">
                <h2>📊 Status do Sistema</h2>
                <p>✅ Sistema operacional</p>
                <p>📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p>🔧 Versão: 1.0.0</p>
            </div>
            
            <div class="card">
                <h2>🤖 Agentes Disponíveis</h2>
                <div>
                    <span class="agent">Compliance Agent</span>
                    <span class="agent">Legal Analysis Agent</span>
                    <span class="agent">Risk Assessment Agent</span>
                    <span class="agent">Document Review Agent</span>
                    <span class="agent">Research Agent</span>
                    <span class="agent" style="background: #8b5cf6;">Perplexity AI Agent</span>
                </div>
            </div>
            
            <div class="card">
                <h2>🛠️ Tools Especializadas</h2>
                <h4>Compliance Tools:</h4>
                <span class="tool">ANVISA Search</span>
                <span class="tool">Compliance Checklist</span>
                <span class="tool">Regulatory Deadline</span>
                
                <h4>Legal Tools:</h4>
                <span class="tool">Legal Database</span>
                <span class="tool">Contract Analysis</span>
                <span class="tool">Legal Opinion</span>
                
                <h4>Risk Tools:</h4>
                <span class="tool">Risk Matrix</span>
                <span class="tool">Scenario Analysis</span>
                <span class="tool">Compliance Risk</span>
                
                <h4>Research Tools:</h4>
                <span class="tool">News Monitor</span>
                <span class="tool">Benchmarking</span>
                <span class="tool">Intelligence</span>
                
                <h4>Perplexity AI Tools:</h4>
                <span class="tool" style="background: #8b5cf6;">Sonar Pro</span>
                <span class="tool" style="background: #8b5cf6;">Real-time Web</span>
                <span class="tool" style="background: #8b5cf6;">200k Context</span>
                <span class="tool" style="background: #8b5cf6;">Citations</span>
            </div>
            
            <div class="card">
                <h2>📚 API Endpoints</h2>
                <ul>
                    <li><code>POST /api/tasks</code> - Submeter tarefa para análise</li>
                    <li><code>POST /api/memories</code> - Consultar memórias dos agentes</li>
                    <li><code>GET /api/dashboard/stats</code> - Estatísticas do sistema</li>
                    <li><code>GET /api/dashboard/agents/performance</code> - Performance dos agentes</li>
                    <li><code>GET /api/dashboard/compliance/alerts</code> - Alertas de conformidade</li>
                    <li><code>GET /health</code> - Status de saúde do sistema</li>
                    <li><code>WS /ws</code> - WebSocket para interação em tempo real</li>
                </ul>
                <p>📖 Documentação completa: <a href="/api/docs">/api/docs</a></p>
            </div>
            
            <div class="card">
                <h2>🔐 Autenticação</h2>
                <p>Use o header <code>X-API-Key</code> com sua chave de API em todas as requisições.</p>
            </div>
        </body>
        </html>
        """
        return html_content
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Check system health."""
        try:
            # Check Redis
            redis_status = "healthy"
            try:
                await app.state.system.memory_store.redis.ping()
            except Exception:
                redis_status = "unhealthy"
                
            # Check Database
            db_status = "healthy"
            try:
                # Simple query to check connection
                await app.state.db.get_recent_updates(days=1)
            except Exception:
                db_status = "unhealthy"
                
            return HealthResponse(
                status="healthy" if redis_status == "healthy" and db_status == "healthy" else "degraded",
                version="1.0.0",
                services={
                    "redis": redis_status,
                    "database": db_status,
                    "agents": "healthy",
                },
            )
        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service unhealthy",
            )
    
    @app.post("/api/tasks", response_model=TaskResponse)
    async def submit_task(request: TaskRequest):
        """Submit a task to the multi-agent system."""
        task_id = str(uuid4())
        start_time = time.time()
        
        logger.info(
            "task_submitted",
            task_id=task_id,
            task=request.task[:100],
            thread_id=request.thread_id,
        )
        
        try:
            # Start monitoring for this execution
            await monitoring_service.start_execution(
                execution_id=task_id,
                thread_id=request.thread_id or task_id,
                task=request.task
            )
            
            # Run the multi-agent system
            result = await app.state.system.run(
                task=request.task,
                thread_id=request.thread_id,
                max_iterations=request.max_iterations,
                context=request.context,
            )
            
            execution_time = time.time() - start_time
            
            # Update monitoring with completion
            await monitoring_service.update_execution(task_id, {
                "status": "completed" if result["success"] else "failed",
                "end_time": datetime.now(),
                "confidence_scores": result.get("context", {}).get("confidence_scores", {}),
                "total_iterations": result.get("iterations", 0)
            })
            
            # Extract documents from context
            documents = None
            if "documents" in result.get("context", {}):
                documents = result["context"]["documents"]
            
            # Log task completion
            logger.info(
                "task_completed",
                task_id=task_id,
                success=result["success"],
                execution_time=execution_time,
                iterations=result.get("iterations", 0),
            )
            
            response = TaskResponse(
                success=result["success"],
                task_id=task_id,
                output=result.get("output"),
                error=result.get("error"),
                context=result.get("context", {}),
                messages=[{"role": m["role"], "content": m["content"]} for m in result.get("messages", [])],
                iterations=result.get("iterations", 0),
                memory_entries=result.get("memory_entries", []),
                documents=documents,
                execution_time=execution_time,
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "task_failed",
                task_id=task_id,
                error=str(e),
                exc_info=e,
            )
            
            return TaskResponse(
                success=False,
                task_id=task_id,
                error=str(e),
                iterations=0,
                execution_time=time.time() - start_time,
            )
    
    @app.post("/api/memories", response_model=MemoryResponse)
    async def get_memories(query: MemoryQuery):
        """Get memories for a specific agent."""
        try:
            memories = await app.state.system.get_agent_memories(
                agent_name=query.agent_name,
                thread_id=query.thread_id,
                limit=query.limit,
            )
            
            return MemoryResponse(
                agent_name=query.agent_name,
                memories=memories,
                count=len(memories),
            )
            
        except Exception as e:
            logger.error(
                "get_memories_failed",
                agent_name=query.agent_name,
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve memories",
            )
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket):
        """WebSocket endpoint for real-time interaction."""
        await websocket.accept()
        
        try:
            while True:
                # Receive message
                data = await websocket.receive_json()
                
                # Validate API key
                if data.get("api_key") != settings.api_key.get_secret_value():
                    await websocket.send_json({
                        "error": "Invalid API key",
                        "success": False,
                    })
                    continue
                
                # Process task
                task_request = TaskRequest(
                    task=data.get("task", ""),
                    thread_id=data.get("thread_id"),
                    max_iterations=data.get("max_iterations", 10),
                    context=data.get("context"),
                    api_key=data.get("api_key"),
                )
                
                task_id = str(uuid4())
                
                # Send acknowledgment
                await websocket.send_json({
                    "type": "task_started",
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat(),
                })
                
                # Run task
                result = await app.state.system.run(
                    task=task_request.task,
                    thread_id=task_request.thread_id,
                    max_iterations=task_request.max_iterations,
                    context=task_request.context,
                )
                
                # Send result
                await websocket.send_json({
                    "type": "task_completed",
                    "task_id": task_id,
                    "result": result,
                    "timestamp": datetime.now().isoformat(),
                })
                
        except Exception as e:
            logger.error("websocket_error", error=str(e))
            await websocket.send_json({
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            })
        finally:
            await websocket.close()
    
    return app