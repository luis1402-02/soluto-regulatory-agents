"""Real-time monitoring dashboard for agent interactions using LangGraph v0.2.38 patterns."""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..utils import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class AgentEvent(BaseModel):
    """Event from agent execution."""
    
    event_id: str
    timestamp: datetime
    agent_name: str
    event_type: str  # started, completed, error, tool_call, handoff
    iteration: int
    confidence: float = 0.0
    duration_ms: Optional[int] = None
    data: Dict[str, Any] = {}
    error: Optional[str] = None


class GraphState(BaseModel):
    """Current state of the graph execution."""
    
    execution_id: str
    thread_id: str
    status: str  # running, completed, failed
    current_agent: str
    iteration: int
    total_iterations: int
    agents_visited: List[str]
    confidence_scores: Dict[str, float]
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_ms: Optional[int] = None


class MonitoringService:
    """Service for monitoring agent executions."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.executions: Dict[str, GraphState] = {}
        self.events: Dict[str, List[AgentEvent]] = {}
        
    async def connect(self, websocket: WebSocket):
        """Connect a new monitoring client."""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Send current state to new connection
        await websocket.send_json({
            "type": "connection_established",
            "executions": [exec.dict() for exec in self.executions.values()],
            "timestamp": datetime.now().isoformat()
        })
        
    def disconnect(self, websocket: WebSocket):
        """Disconnect a monitoring client."""
        self.active_connections.remove(websocket)
        
    async def broadcast_event(self, event: AgentEvent):
        """Broadcast event to all connected clients."""
        event_data = {
            "type": "agent_event",
            "event": event.dict(),
            "timestamp": datetime.now().isoformat()
        }
        
        # Store event
        execution_id = event.data.get("execution_id")
        if execution_id:
            if execution_id not in self.events:
                self.events[execution_id] = []
            self.events[execution_id].append(event)
        
        # Broadcast to all connections
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(event_data)
            except Exception:
                disconnected.append(connection)
                
        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.remove(conn)
            
    async def start_execution(self, execution_id: str, thread_id: str, task: str):
        """Start monitoring a new execution."""
        state = GraphState(
            execution_id=execution_id,
            thread_id=thread_id,
            status="running",
            current_agent="orchestrator",
            iteration=0,
            total_iterations=0,
            agents_visited=["orchestrator"],
            confidence_scores={},
            start_time=datetime.now()
        )
        
        self.executions[execution_id] = state
        self.events[execution_id] = []
        
        # Broadcast start event
        await self.broadcast_event(AgentEvent(
            event_id=str(uuid4()),
            timestamp=datetime.now(),
            agent_name="system",
            event_type="execution_started",
            iteration=0,
            data={
                "execution_id": execution_id,
                "thread_id": thread_id,
                "task": task
            }
        ))
        
    async def update_execution(self, execution_id: str, updates: Dict[str, Any]):
        """Update execution state."""
        if execution_id in self.executions:
            state = self.executions[execution_id]
            
            for key, value in updates.items():
                if hasattr(state, key):
                    setattr(state, key, value)
                    
            # Calculate duration if completed
            if state.status in ["completed", "failed"] and state.end_time:
                state.total_duration_ms = int(
                    (state.end_time - state.start_time).total_seconds() * 1000
                )
                
            # Broadcast state update
            await self.broadcast_state_update(execution_id)
            
    async def broadcast_state_update(self, execution_id: str):
        """Broadcast execution state update."""
        if execution_id in self.executions:
            state = self.executions[execution_id]
            
            update_data = {
                "type": "state_update",
                "execution_id": execution_id,
                "state": state.dict(),
                "timestamp": datetime.now().isoformat()
            }
            
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_json(update_data)
                except Exception:
                    disconnected.append(connection)
                    
            for conn in disconnected:
                self.active_connections.remove(conn)


# Global monitoring service instance
monitoring_service = MonitoringService()


@router.get("/dashboard", response_class=HTMLResponse)
async def monitoring_dashboard():
    """Serve the monitoring dashboard."""
    return """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Soluto Agents - Monitoring Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-tertiary: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #cbd5e1;
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
            --accent-green: #10b981;
            --accent-yellow: #f59e0b;
            --accent-red: #ef4444;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: var(--bg-secondary);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-size: 2rem;
            color: var(--text-primary);
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--accent-green);
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid var(--bg-tertiary);
        }
        
        .card h2 {
            font-size: 1.25rem;
            margin-bottom: 15px;
            color: var(--text-primary);
        }
        
        .agent-flow {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            min-height: 400px;
        }
        
        .events-timeline {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 20px;
            max-height: 600px;
            overflow-y: auto;
        }
        
        .event-item {
            background: var(--bg-tertiary);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
            transition: all 0.3s ease;
        }
        
        .event-item:hover {
            transform: translateX(5px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        
        .event-icon {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }
        
        .agent-orchestrator { background: var(--accent-blue); }
        .agent-perplexity { background: var(--accent-purple); }
        .agent-compliance { background: var(--accent-green); }
        .agent-legal { background: var(--accent-yellow); }
        .agent-risk { background: var(--accent-red); }
        
        .metric-value {
            font-size: 2rem;
            font-weight: bold;
            color: var(--accent-blue);
        }
        
        .metric-label {
            color: var(--text-secondary);
            font-size: 0.875rem;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: var(--bg-tertiary);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple));
            transition: width 0.3s ease;
        }
        
        #mermaidDiagram {
            background: var(--bg-tertiary);
            border-radius: 8px;
            padding: 20px;
            min-height: 350px;
        }
        
        .confidence-chart {
            max-width: 100%;
            height: 300px !important;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🤖 Soluto Regulatory Agents - Live Monitor</h1>
                <p style="color: var(--text-secondary);">Sistema Multiagente em Tempo Real</p>
            </div>
            <div class="status-indicator">
                <span class="status-dot"></span>
                <span id="connectionStatus">Conectado</span>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>📊 Métricas em Tempo Real</h2>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                    <div>
                        <div class="metric-value" id="activeExecutions">0</div>
                        <div class="metric-label">Execuções Ativas</div>
                    </div>
                    <div>
                        <div class="metric-value" id="totalAgents">7</div>
                        <div class="metric-label">Agentes Disponíveis</div>
                    </div>
                    <div>
                        <div class="metric-value" id="avgConfidence">0%</div>
                        <div class="metric-label">Confiança Média</div>
                    </div>
                    <div>
                        <div class="metric-value" id="avgDuration">0s</div>
                        <div class="metric-label">Duração Média</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>🎯 Execução Atual</h2>
                <div id="currentExecution">
                    <p style="color: var(--text-secondary);">Aguardando execução...</p>
                </div>
            </div>
        </div>
        
        <div class="agent-flow">
            <h2>🔄 Fluxo de Agentes</h2>
            <div id="mermaidDiagram">
                <div class="mermaid">
                    graph LR
                        Start([Início]) --> Orchestrator[Orchestrator]
                        Orchestrator --> Perplexity[Perplexity AI]
                        Orchestrator --> Compliance[Compliance]
                        Orchestrator --> Legal[Legal Analysis]
                        Orchestrator --> Risk[Risk Assessment]
                        Orchestrator --> Research[Research]
                        Perplexity --> Orchestrator
                        Compliance --> Orchestrator
                        Legal --> Orchestrator
                        Risk --> Orchestrator
                        Research --> Orchestrator
                        Orchestrator --> QC[Quality Control]
                        QC --> Doc[Document Review]
                        Doc --> End([Fim])
                        
                        classDef orchestratorClass fill:#3b82f6,stroke:#fff,stroke-width:2px,color:#fff
                        classDef perplexityClass fill:#8b5cf6,stroke:#fff,stroke-width:2px,color:#fff
                        classDef complianceClass fill:#10b981,stroke:#fff,stroke-width:2px,color:#fff
                        classDef legalClass fill:#f59e0b,stroke:#fff,stroke-width:2px,color:#fff
                        classDef riskClass fill:#ef4444,stroke:#fff,stroke-width:2px,color:#fff
                        
                        class Orchestrator orchestratorClass
                        class Perplexity perplexityClass
                        class Compliance complianceClass
                        class Legal legalClass
                        class Risk riskClass
                </div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>📈 Confiança por Agente</h2>
                <canvas id="confidenceChart" class="confidence-chart"></canvas>
            </div>
            
            <div class="card">
                <h2>⏱️ Tempo de Execução</h2>
                <canvas id="durationChart" class="confidence-chart"></canvas>
            </div>
        </div>
        
        <div class="events-timeline">
            <h2>📋 Timeline de Eventos</h2>
            <div id="eventsContainer"></div>
        </div>
    </div>
    
    <script>
        // Initialize Mermaid
        mermaid.initialize({ 
            theme: 'dark',
            themeVariables: {
                primaryColor: '#3b82f6',
                primaryTextColor: '#fff',
                primaryBorderColor: '#7c3aed',
                lineColor: '#5b21b6',
                secondaryColor: '#1e293b',
                tertiaryColor: '#334155',
                background: '#0f172a',
                mainBkg: '#1e293b',
                secondBkg: '#334155',
                tertiaryBkg: '#475569'
            }
        });
        
        // WebSocket connection
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.host}/monitoring/ws`);
        
        // State
        let currentExecutions = {};
        let events = [];
        
        // Charts
        const confidenceCtx = document.getElementById('confidenceChart').getContext('2d');
        const confidenceChart = new Chart(confidenceCtx, {
            type: 'radar',
            data: {
                labels: ['Orchestrator', 'Perplexity', 'Compliance', 'Legal', 'Risk', 'Research'],
                datasets: [{
                    label: 'Confiança',
                    data: [0, 0, 0, 0, 0, 0],
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 2,
                    pointBackgroundColor: 'rgba(59, 130, 246, 1)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgba(59, 130, 246, 1)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 1,
                        grid: { color: '#334155' },
                        ticks: { color: '#cbd5e1' }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
        
        const durationCtx = document.getElementById('durationChart').getContext('2d');
        const durationChart = new Chart(durationCtx, {
            type: 'bar',
            data: {
                labels: ['Perplexity', 'Compliance', 'Legal', 'Risk', 'Research', 'Document'],
                datasets: [{
                    label: 'Duração (ms)',
                    data: [0, 0, 0, 0, 0, 0],
                    backgroundColor: [
                        'rgba(139, 92, 246, 0.8)',
                        'rgba(16, 185, 129, 0.8)',
                        'rgba(245, 158, 11, 0.8)',
                        'rgba(239, 68, 68, 0.8)',
                        'rgba(99, 102, 241, 0.8)',
                        'rgba(20, 184, 166, 0.8)'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: '#334155' },
                        ticks: { color: '#cbd5e1' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#cbd5e1' }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
        
        // WebSocket handlers
        ws.onopen = () => {
            console.log('Connected to monitoring service');
            updateConnectionStatus(true);
        };
        
        ws.onclose = () => {
            console.log('Disconnected from monitoring service');
            updateConnectionStatus(false);
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleMonitoringEvent(data);
        };
        
        function updateConnectionStatus(connected) {
            const status = document.getElementById('connectionStatus');
            const dot = document.querySelector('.status-dot');
            
            if (connected) {
                status.textContent = 'Conectado';
                dot.style.background = 'var(--accent-green)';
            } else {
                status.textContent = 'Desconectado';
                dot.style.background = 'var(--accent-red)';
            }
        }
        
        function handleMonitoringEvent(data) {
            switch (data.type) {
                case 'connection_established':
                    initializeExecutions(data.executions);
                    break;
                case 'agent_event':
                    handleAgentEvent(data.event);
                    break;
                case 'state_update':
                    updateExecutionState(data.execution_id, data.state);
                    break;
            }
        }
        
        function initializeExecutions(executions) {
            executions.forEach(exec => {
                currentExecutions[exec.execution_id] = exec;
            });
            updateMetrics();
        }
        
        function handleAgentEvent(event) {
            events.unshift(event);
            if (events.length > 50) events.pop();
            
            addEventToTimeline(event);
            updateAgentFlow(event);
            
            if (event.event_type === 'tool_call' && event.data.tool === 'perplexity_sonar_pro') {
                highlightPerplexityActivity();
            }
        }
        
        function updateExecutionState(executionId, state) {
            currentExecutions[executionId] = state;
            updateMetrics();
            updateCurrentExecution(state);
            updateCharts(state);
        }
        
        function updateMetrics() {
            const activeCount = Object.values(currentExecutions).filter(e => e.status === 'running').length;
            document.getElementById('activeExecutions').textContent = activeCount;
            
            const confidenceScores = [];
            Object.values(currentExecutions).forEach(exec => {
                Object.values(exec.confidence_scores).forEach(score => {
                    confidenceScores.push(score);
                });
            });
            
            const avgConfidence = confidenceScores.length > 0 
                ? (confidenceScores.reduce((a, b) => a + b, 0) / confidenceScores.length * 100).toFixed(0)
                : 0;
            document.getElementById('avgConfidence').textContent = avgConfidence + '%';
            
            const durations = Object.values(currentExecutions)
                .filter(e => e.total_duration_ms)
                .map(e => e.total_duration_ms);
            
            const avgDuration = durations.length > 0
                ? (durations.reduce((a, b) => a + b, 0) / durations.length / 1000).toFixed(1)
                : 0;
            document.getElementById('avgDuration').textContent = avgDuration + 's';
        }
        
        function updateCurrentExecution(state) {
            const container = document.getElementById('currentExecution');
            
            if (state.status === 'running') {
                container.innerHTML = `
                    <div>
                        <p><strong>Thread ID:</strong> ${state.thread_id}</p>
                        <p><strong>Agente Atual:</strong> <span style="color: var(--accent-blue)">${formatAgentName(state.current_agent)}</span></p>
                        <p><strong>Iteração:</strong> ${state.iteration}</p>
                        <p><strong>Agentes Visitados:</strong> ${state.agents_visited.length}</p>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${(state.iteration / 15) * 100}%"></div>
                        </div>
                    </div>
                `;
            } else {
                container.innerHTML = `
                    <p style="color: var(--text-secondary);">Nenhuma execução ativa</p>
                `;
            }
        }
        
        function updateCharts(state) {
            // Update confidence chart
            const confidenceData = [
                state.confidence_scores.orchestrator || 0,
                state.confidence_scores.perplexity_research_agent || 0,
                state.confidence_scores.compliance_agent || 0,
                state.confidence_scores.legal_analysis_agent || 0,
                state.confidence_scores.risk_assessment_agent || 0,
                state.confidence_scores.research_agent || 0
            ];
            
            confidenceChart.data.datasets[0].data = confidenceData;
            confidenceChart.update();
        }
        
        function addEventToTimeline(event) {
            const container = document.getElementById('eventsContainer');
            
            const eventElement = document.createElement('div');
            eventElement.className = 'event-item';
            eventElement.style.opacity = '0';
            
            const icon = getAgentIcon(event.agent_name);
            const color = getAgentColor(event.agent_name);
            
            eventElement.innerHTML = `
                <div class="event-icon" style="background: ${color}">
                    ${icon}
                </div>
                <div style="flex: 1">
                    <div style="font-weight: bold">${formatAgentName(event.agent_name)}</div>
                    <div style="color: var(--text-secondary); font-size: 0.875rem">
                        ${event.event_type} - ${new Date(event.timestamp).toLocaleTimeString('pt-BR')}
                    </div>
                    ${event.data.tool ? `<div style="color: var(--accent-purple); font-size: 0.75rem">Tool: ${event.data.tool}</div>` : ''}
                </div>
                ${event.confidence > 0 ? `
                    <div style="text-align: right">
                        <div style="font-size: 1.25rem; font-weight: bold; color: ${getConfidenceColor(event.confidence)}">
                            ${(event.confidence * 100).toFixed(0)}%
                        </div>
                        <div style="color: var(--text-secondary); font-size: 0.75rem">confiança</div>
                    </div>
                ` : ''}
            `;
            
            container.insertBefore(eventElement, container.firstChild);
            
            // Animate entry
            setTimeout(() => {
                eventElement.style.opacity = '1';
                eventElement.style.transition = 'opacity 0.3s ease';
            }, 10);
            
            // Limit timeline to 20 events
            while (container.children.length > 20) {
                container.removeChild(container.lastChild);
            }
        }
        
        function updateAgentFlow(event) {
            // This would update the Mermaid diagram to show active agent
            // For now, we'll just re-render with highlighting
            if (event.event_type === 'started') {
                highlightAgent(event.agent_name);
            }
        }
        
        function highlightAgent(agentName) {
            // Add visual feedback for active agent
            const mermaidDiv = document.querySelector('.mermaid');
            mermaidDiv.style.animation = 'pulse 0.5s';
            setTimeout(() => {
                mermaidDiv.style.animation = '';
            }, 500);
        }
        
        function highlightPerplexityActivity() {
            // Special highlighting for Perplexity AI activity
            const header = document.querySelector('.header');
            header.style.borderColor = 'var(--accent-purple)';
            header.style.transition = 'border-color 0.3s ease';
            setTimeout(() => {
                header.style.borderColor = 'transparent';
            }, 2000);
        }
        
        function formatAgentName(name) {
            const nameMap = {
                'orchestrator': 'Orchestrator',
                'perplexity_research_agent': 'Perplexity AI',
                'compliance_agent': 'Compliance',
                'legal_analysis_agent': 'Legal Analysis',
                'risk_assessment_agent': 'Risk Assessment',
                'research_agent': 'Research',
                'document_review_agent': 'Document Review',
                'quality_control': 'Quality Control'
            };
            return nameMap[name] || name;
        }
        
        function getAgentIcon(name) {
            const iconMap = {
                'orchestrator': '🎯',
                'perplexity_research_agent': '🔮',
                'compliance_agent': '✅',
                'legal_analysis_agent': '⚖️',
                'risk_assessment_agent': '⚠️',
                'research_agent': '🔍',
                'document_review_agent': '📄',
                'quality_control': '🔍',
                'system': '⚙️'
            };
            return iconMap[name] || '🤖';
        }
        
        function getAgentColor(name) {
            const colorMap = {
                'orchestrator': 'var(--accent-blue)',
                'perplexity_research_agent': 'var(--accent-purple)',
                'compliance_agent': 'var(--accent-green)',
                'legal_analysis_agent': 'var(--accent-yellow)',
                'risk_assessment_agent': 'var(--accent-red)',
                'research_agent': '#6366f1',
                'document_review_agent': '#14b8a6',
                'quality_control': '#f97316',
                'system': 'var(--bg-tertiary)'
            };
            return colorMap[name] || 'var(--bg-tertiary)';
        }
        
        function getConfidenceColor(confidence) {
            if (confidence >= 0.8) return 'var(--accent-green)';
            if (confidence >= 0.6) return 'var(--accent-blue)';
            if (confidence >= 0.4) return 'var(--accent-yellow)';
            return 'var(--accent-red)';
        }
        
        // Auto-refresh charts every 5 seconds
        setInterval(() => {
            if (Object.keys(currentExecutions).length > 0) {
                updateMetrics();
            }
        }, 5000);
    </script>
</body>
</html>
"""


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time monitoring."""
    await monitoring_service.connect(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        monitoring_service.disconnect(websocket)


# Export for use in other modules
__all__ = ["router", "monitoring_service", "AgentEvent", "GraphState"]