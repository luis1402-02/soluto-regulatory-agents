"""LangGraph v0.2.38 implementation for the multi-agent regulatory system."""

import time
import uuid
from typing import Any, Dict, List, Optional, Literal, Annotated

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from .agents import (
    AgentState,
    ComplianceAgent,
    DocumentReviewAgent,
    LegalAnalysisAgent,
    ResearchAgent,
    RiskAssessmentAgent,
    PerplexityResearchAgent,
)
from .memory import Memory, SQLiteMemoryStore

try:
    from .memory import RedisMemoryStore
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    RedisMemoryStore = None

from .utils import get_logger
from .config.langsmith import trace_function, get_langsmith_url

logger = get_logger(__name__)

# Import monitoring service if available
try:
    from .api.monitoring import monitoring_service, AgentEvent
    MONITORING_ENABLED = True
except ImportError:
    monitoring_service = None
    AgentEvent = None
    MONITORING_ENABLED = False
    logger.warning("Monitoring service not available")


class EnhancedAgentState(AgentState):
    """Enhanced state with Command-based communication support."""
    
    # Core messages with LangGraph message management
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Agent routing and coordination
    next_agent: Optional[str] = None
    current_agent: str = "orchestrator"
    agent_reasoning: str = ""
    handoff_context: Dict[str, Any] = {}
    
    # Task management
    task: str = ""
    subtasks: List[Dict[str, Any]] = []
    completed_subtasks: List[str] = []
    
    # System state
    iteration: int = 0
    max_iterations: int = 10
    thread_id: Optional[str] = None
    
    # Results and outputs
    context: Dict[str, Any] = {}
    memory_entries: List[str] = []
    final_output: Optional[str] = None
    error: Optional[str] = None
    
    # Quality and monitoring
    confidence_score: float = 0.0
    quality_checks: Dict[str, bool] = {}
    performance_metrics: Dict[str, Any] = {}


class RegulatoryMultiAgentSystem:
    """Production-ready multi-agent system using LangGraph v0.2.38 patterns."""

    def __init__(self, memory_store=None):
        """Initialize the enhanced multi-agent system."""
        # Initialize memory with proper error handling
        self._initialize_memory(memory_store)
        
        # Initialize specialized agents with enhanced capabilities
        self.agents = self._initialize_agents()
        
        # Build the graph with Command-based patterns
        self.graph = self._build_enhanced_graph()
        self.app = self.graph.compile()
        
        logger.info("regulatory_multiagent_system_initialized", 
                   agents=list(self.agents.keys()),
                   memory_type=type(self.memory_store).__name__)

    def _initialize_memory(self, memory_store):
        """Initialize memory store with fallback options."""
        if memory_store is None:
            if REDIS_AVAILABLE:
                try:
                    self.memory_store = RedisMemoryStore()
                    logger.info("redis_memory_store_initialized")
                except Exception as e:
                    logger.warning("redis_fallback_to_sqlite", error=str(e))
                    self.memory_store = SQLiteMemoryStore()
            else:
                self.memory_store = SQLiteMemoryStore()
        else:
            self.memory_store = memory_store
            
        self.memory = Memory(self.memory_store)

    def _initialize_agents(self) -> Dict[str, Any]:
        """Initialize all specialized agents."""
        agents = {
            "compliance_agent": ComplianceAgent(self.memory),
            "legal_analysis_agent": LegalAnalysisAgent(self.memory),
            "risk_assessment_agent": RiskAssessmentAgent(self.memory),
            "research_agent": ResearchAgent(self.memory),
            "perplexity_agent": PerplexityResearchAgent(self.memory),
            "document_review_agent": DocumentReviewAgent(self.memory),
        }
        
        logger.info("agents_initialized", count=len(agents))
        return agents

    def _build_enhanced_graph(self) -> StateGraph:
        """Build enhanced LangGraph workflow with Command-based communication."""
        # Create workflow with enhanced state
        workflow = StateGraph(EnhancedAgentState)
        
        # Add orchestrator node
        workflow.add_node("orchestrator", self._orchestrator_node)
        
        # Add specialized agent nodes
        for agent_name, agent in self.agents.items():
            workflow.add_node(agent_name, self._create_agent_wrapper(agent))
        
        # Add quality control and finalization nodes
        workflow.add_node("quality_control", self._quality_control_node)
        workflow.add_node("finalize_output", self._finalize_output_node)
        
        # Define routing logic with Command-based handoffs
        workflow.add_conditional_edges(
            "orchestrator",
            self._orchestrator_routing,
            {
                "compliance_agent": "compliance_agent",
                "legal_analysis_agent": "legal_analysis_agent", 
                "risk_assessment_agent": "risk_assessment_agent",
                "research_agent": "research_agent",
                "perplexity_agent": "perplexity_agent",
                "document_review_agent": "document_review_agent",
                "quality_control": "quality_control",
                "end": END,
            }
        )
        
        # Agent handoff patterns - each agent can route to others or back to orchestrator
        for agent_name in self.agents.keys():
            workflow.add_conditional_edges(
                agent_name,
                self._agent_handoff_routing,
                {
                    "orchestrator": "orchestrator",
                    "compliance_agent": "compliance_agent",
                    "legal_analysis_agent": "legal_analysis_agent",
                    "risk_assessment_agent": "risk_assessment_agent", 
                    "research_agent": "research_agent",
                    "perplexity_agent": "perplexity_agent",
                    "document_review_agent": "document_review_agent",
                    "quality_control": "quality_control",
                    "end": END,
                }
            )
        
        # Quality control routing
        workflow.add_conditional_edges(
            "quality_control",
            self._quality_control_routing,
            {
                "orchestrator": "orchestrator",
                "finalize_output": "finalize_output",
                "end": END,
            }
        )
        
        # Finalization always ends
        workflow.add_edge("finalize_output", END)
        
        # Set entry point
        workflow.set_entry_point("orchestrator")
        
        return workflow

    async def _orchestrator_node(self, state: EnhancedAgentState) -> Command[Literal["compliance_agent", "legal_analysis_agent", "risk_assessment_agent", "research_agent", "perplexity_agent", "document_review_agent", "quality_control", "end"]]:
        """Enhanced orchestrator with Command-based routing."""
        logger.info("orchestrator_processing", iteration=state["iteration"], task=state["task"][:100])
        
        # Send monitoring event
        if MONITORING_ENABLED and monitoring_service:
            await self._send_monitoring_event(
                agent_name="orchestrator",
                event_type="started",
                state=state,
                data={"task": state["task"][:200]}
            )
        
        # Increment iteration
        state["iteration"] += 1
        
        # Check termination conditions
        if state["iteration"] > state["max_iterations"]:
            logger.warning("max_iterations_reached", iterations=state["iteration"])
            return Command(goto="end", update={"error": "Maximum iterations reached"})
        
        # Analyze current state and determine next action
        next_action = await self._analyze_orchestrator_state(state)
        
        # Update orchestrator reasoning
        state["agent_reasoning"] = f"Orchestrator iteration {state['iteration']}: {next_action['reasoning']}"
        
        # Add orchestrator message
        orchestrator_msg = AIMessage(
            content=f"🎯 **Orchestrator Analysis (Iteration {state['iteration']})**\n\n"
                   f"**Current Task**: {state['task']}\n\n"
                   f"**Next Action**: {next_action['action']}\n\n"
                   f"**Reasoning**: {next_action['reasoning']}\n\n"
                   f"**Progress**: {len(state['completed_subtasks'])}/{len(state['subtasks'])} subtasks completed"
        )
        
        return Command(
            goto=next_action["next_agent"],
            update={
                "messages": [orchestrator_msg],
                "next_agent": next_action["next_agent"],
                "current_agent": "orchestrator",
                "handoff_context": next_action.get("handoff_context", {}),
            }
        )

    async def _analyze_orchestrator_state(self, state: EnhancedAgentState) -> Dict[str, Any]:
        """Analyze current state and determine next action."""
        # Check if we have all required analyses
        context = state["context"]
        
        # Define required analyses for a complete regulatory assessment
        required_analyses = {
            "perplexity_research": "perplexity_agent",  # High-priority real-time research
            "compliance_analysis": "compliance_agent",
            "legal_analysis": "legal_analysis_agent",
            "risk_assessment": "risk_assessment_agent",
            "research_findings": "research_agent",
        }
        
        # Find missing analyses
        missing_analyses = [
            (analysis, agent) for analysis, agent in required_analyses.items()
            if analysis not in context or not context[analysis]
        ]
        
        # If we have all analyses, move to quality control
        if not missing_analyses:
            if not context.get("quality_checked"):
                return {
                    "action": "Quality Control",
                    "next_agent": "quality_control", 
                    "reasoning": "All analyses complete, performing quality control"
                }
            else:
                return {
                    "action": "Finalize",
                    "next_agent": "document_review_agent",
                    "reasoning": "Quality control passed, generating final report"
                }
        
        # Prioritize missing analyses based on dependencies
        analysis_priorities = {
            "perplexity_research": 1,  # Perplexity AI real-time research first
            "research_findings": 2,    # Foundation research second
            "compliance_analysis": 3,  # Core compliance assessment
            "legal_analysis": 4,       # Legal framework analysis
            "risk_assessment": 5,      # Risk analysis using previous results
        }
        
        # Select highest priority missing analysis
        next_analysis = min(missing_analyses, key=lambda x: analysis_priorities.get(x[0], 5))
        
        return {
            "action": f"Execute {next_analysis[0].replace('_', ' ').title()}",
            "next_agent": next_analysis[1],
            "reasoning": f"Missing {next_analysis[0].replace('_', ' ')}, required for complete assessment",
            "handoff_context": {
                "analysis_type": next_analysis[0],
                "dependencies": self._get_analysis_dependencies(next_analysis[0], context),
            }
        }

    def _get_analysis_dependencies(self, analysis_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get dependencies for specific analysis types."""
        dependencies = {}
        
        if analysis_type == "risk_assessment":
            dependencies["compliance_data"] = context.get("compliance_analysis", "")
            dependencies["legal_data"] = context.get("legal_analysis", "")
            
        elif analysis_type == "legal_analysis":
            dependencies["research_data"] = context.get("research_findings", "")
            
        elif analysis_type == "compliance_analysis":
            dependencies["research_data"] = context.get("research_findings", "")
            
        return dependencies

    def _create_agent_wrapper(self, agent):
        """Create a wrapper for agent execution with Command returns."""
        async def agent_wrapper(state: EnhancedAgentState) -> Command[Literal["orchestrator", "compliance_agent", "legal_analysis_agent", "risk_assessment_agent", "research_agent", "perplexity_agent", "document_review_agent", "quality_control", "end"]]:
            logger.info("agent_processing", agent=agent.config.name, iteration=state["iteration"])
            
            # Send monitoring event for agent start
            if MONITORING_ENABLED and monitoring_service:
                await self._send_monitoring_event(
                    agent_name=agent.config.name,
                    event_type="started",
                    state=state,
                    data={"agent_description": agent.config.description}
                )
            
            start_time = time.time()
            
            try:
                # Execute agent processing
                updated_state = await agent.process(state)
                
                # Update performance metrics
                confidence = self._calculate_agent_confidence(agent, updated_state)
                updated_state["confidence_score"] = confidence
                
                # Send monitoring event for agent completion
                duration_ms = int((time.time() - start_time) * 1000)
                if MONITORING_ENABLED and monitoring_service:
                    await self._send_monitoring_event(
                        agent_name=agent.config.name,
                        event_type="completed",
                        state=updated_state,
                        data={
                            "confidence": confidence,
                            "duration_ms": duration_ms,
                            "tools_used": updated_state["context"].get(f"{agent.config.name}_tools_used", [])
                        }
                    )
                
                # Determine next step based on agent completion
                if agent.config.name == "document_review_agent":
                    # Document review agent completes the workflow
                    return Command(
                        goto="end",
                        update={
                            **updated_state,
                            "final_output": updated_state["context"].get("final_report"),
                            "current_agent": agent.config.name,
                        }
                    )
                else:
                    # Return to orchestrator for next coordination
                    return Command(
                        goto="orchestrator", 
                        update={
                            **updated_state,
                            "current_agent": agent.config.name,
                        }
                    )
                
            except Exception as e:
                logger.error("agent_processing_error", agent=agent.config.name, error=str(e))
                return Command(
                    goto="end",
                    update={
                        "error": f"Agent {agent.config.name} failed: {str(e)}",
                        "current_agent": agent.config.name,
                    }
                )
        
        return agent_wrapper

    def _calculate_agent_confidence(self, agent, state: EnhancedAgentState) -> float:
        """Calculate confidence score for agent output."""
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on successful tool usage
        context = state["context"]
        
        if agent.config.name == "compliance_agent":
            if context.get("compliance_analysis") and len(context.get("compliance_analysis", "")) > 100:
                confidence += 0.3
            if context.get("consultas_anvisa", 0) > 0:
                confidence += 0.2
                
        elif agent.config.name == "legal_analysis_agent":
            if context.get("legal_analysis") and len(context.get("legal_analysis", "")) > 100:
                confidence += 0.3
            if context.get("legal_tools_used"):
                confidence += 0.2
                
        elif agent.config.name == "risk_assessment_agent":
            if context.get("risk_assessment") and len(context.get("risk_assessment", "")) > 100:
                confidence += 0.3
            if context.get("regulatory_risk_assessment"):
                confidence += 0.2
                
        elif agent.config.name == "research_agent":
            if context.get("research_findings") and len(context.get("research_findings", "")) > 100:
                confidence += 0.3
            if context.get("research_data", {}).get("research_results_count", 0) > 0:
                confidence += 0.2
                
        elif agent.config.name == "perplexity_research_agent":
            if context.get("perplexity_research") and context.get("perplexity_research", {}).get("confidence_score", 0) > 0.7:
                confidence += 0.4
            if context.get("perplexity_citations") and len(context.get("perplexity_citations", [])) > 10:
                confidence += 0.1
        
        return min(confidence, 1.0)

    async def _quality_control_node(self, state: EnhancedAgentState) -> Command[Literal["orchestrator", "finalize_output", "end"]]:
        """Quality control node to validate outputs."""
        logger.info("quality_control_processing", iteration=state["iteration"])
        
        quality_checks = {
            "has_perplexity_research": bool(state["context"].get("perplexity_research")),
            "has_compliance_analysis": bool(state["context"].get("compliance_analysis")),
            "has_legal_analysis": bool(state["context"].get("legal_analysis")),
            "has_risk_assessment": bool(state["context"].get("risk_assessment")),
            "has_research_findings": bool(state["context"].get("research_findings")),
            "sufficient_confidence": state.get("confidence_score", 0) > 0.6,
            "has_citations": len(state["context"].get("perplexity_citations", [])) > 5,
        }
        
        all_checks_passed = all(quality_checks.values())
        
        quality_msg = AIMessage(
            content=f"🔍 **Quality Control Results**\n\n"
                   f"**Perplexity AI Research**: {'✅' if quality_checks['has_perplexity_research'] else '❌'}\n"
                   f"**Compliance Analysis**: {'✅' if quality_checks['has_compliance_analysis'] else '❌'}\n"
                   f"**Legal Analysis**: {'✅' if quality_checks['has_legal_analysis'] else '❌'}\n" 
                   f"**Risk Assessment**: {'✅' if quality_checks['has_risk_assessment'] else '❌'}\n"
                   f"**Research Findings**: {'✅' if quality_checks['has_research_findings'] else '❌'}\n"
                   f"**Citations Available**: {'✅' if quality_checks['has_citations'] else '❌'}\n"
                   f"**Confidence Score**: {state.get('confidence_score', 0):.2f} {'✅' if quality_checks['sufficient_confidence'] else '❌'}\n\n"
                   f"**Overall Status**: {'PASS ✅' if all_checks_passed else 'NEEDS IMPROVEMENT ⚠️'}"
        )
        
        if all_checks_passed:
            return Command(
                goto="finalize_output",
                update={
                    "messages": [quality_msg],
                    "quality_checks": quality_checks,
                    "context": {**state["context"], "quality_checked": True},
                }
            )
        else:
            return Command(
                goto="orchestrator",
                update={
                    "messages": [quality_msg],
                    "quality_checks": quality_checks,
                    "context": {**state["context"], "quality_issues": quality_checks},
                }
            )

    async def _finalize_output_node(self, state: EnhancedAgentState) -> EnhancedAgentState:
        """Finalize the output and prepare final response."""
        logger.info("finalizing_output", iteration=state["iteration"])
        
        # This triggers the document review agent to create the final report
        return state

    def _orchestrator_routing(self, state: EnhancedAgentState) -> str:
        """Route from orchestrator based on state analysis."""
        return state.get("next_agent", "end")

    def _agent_handoff_routing(self, state: EnhancedAgentState) -> str:
        """Route from agents - typically back to orchestrator or to specific agent."""
        if state.get("error"):
            return "end"
        
        # Document review agent ends the workflow
        if state.get("current_agent") == "document_review_agent":
            return "end"
        
        # Other agents return to orchestrator for coordination
        return "orchestrator"

    def _quality_control_routing(self, state: EnhancedAgentState) -> str:
        """Route from quality control."""
        if state.get("error"):
            return "end"
            
        quality_checks = state.get("quality_checks", {})
        if all(quality_checks.values()):
            return "finalize_output"
        else:
            return "orchestrator"

    @trace_function(name="regulatory_multiagent_run")
    async def run(
        self,
        task: str,
        thread_id: Optional[str] = None,
        max_iterations: int = 15,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run the enhanced multi-agent system on a task."""
        if not thread_id:
            thread_id = str(uuid.uuid4())
            
        logger.info(
            "starting_enhanced_multiagent_system",
            task=task[:100],
            thread_id=thread_id,
            max_iterations=max_iterations,
        )
        
        # Initialize enhanced state
        initial_state: EnhancedAgentState = {
            "messages": [HumanMessage(content=task)],
            "current_agent": "orchestrator",
            "next_agent": None,
            "agent_reasoning": "",
            "handoff_context": {},
            "task": task,
            "subtasks": [],
            "completed_subtasks": [],
            "iteration": 0,
            "max_iterations": max_iterations,
            "thread_id": thread_id,
            "context": context or {},
            "memory_entries": [],
            "final_output": None,
            "error": None,
            "confidence_score": 0.0,
            "quality_checks": {},
            "performance_metrics": {},
        }
        
        try:
            # Execute the enhanced workflow
            final_state = await self.app.ainvoke(initial_state)
            
            success = bool(final_state.get("final_output")) and not final_state.get("error")
            
            logger.info(
                "enhanced_multiagent_system_completed",
                task=task[:100],
                iterations=final_state.get("iteration", 0),
                success=success,
                confidence=final_state.get("confidence_score", 0),
            )
            
            return {
                "success": success,
                "output": final_state.get("final_output"),
                "context": final_state.get("context", {}),
                "messages": [
                    {
                        "role": "human" if isinstance(msg, HumanMessage) else "assistant", 
                        "content": msg.content
                    }
                    for msg in final_state.get("messages", [])
                ],
                "iterations": final_state.get("iteration", 0),
                "memory_entries": final_state.get("memory_entries", []),
                "confidence_score": final_state.get("confidence_score", 0),
                "quality_checks": final_state.get("quality_checks", {}),
                "performance_metrics": final_state.get("performance_metrics", {}),
                "thread_id": thread_id,
            }
            
        except Exception as e:
            logger.error(
                "enhanced_multiagent_system_failed",
                task=task[:100],
                error=str(e),
                exc_info=True,
            )
            
            return {
                "success": False,
                "error": str(e),
                "output": None,
                "context": {},
                "messages": [],
                "iterations": 0,
                "memory_entries": [],
                "confidence_score": 0.0,
                "quality_checks": {},
                "performance_metrics": {},
                "thread_id": thread_id,
            }

    async def get_agent_memories(
        self,
        agent_name: str,
        thread_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get memories for a specific agent."""
        memories = await self.memory.search_memories(
            query="",
            agent_id=agent_name,
            thread_id=thread_id,
            limit=limit,
        )
        
        return [
            {
                "id": m.id,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "type": m.type.value,
                "tags": m.tags,
            }
            for m in memories
        ]

    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health and performance metrics."""
        try:
            # Test memory store
            memory_health = await self._test_memory_health()
            
            # Test agent initialization
            agent_health = {agent_name: True for agent_name in self.agents.keys()}
            
            return {
                "status": "healthy",
                "memory_store": memory_health,
                "agents": agent_health,
                "timestamp": str(uuid.uuid4()),
            }
            
        except Exception as e:
            logger.error("system_health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": str(uuid.uuid4()),
            }

    async def _test_memory_health(self) -> Dict[str, Any]:
        """Test memory store health."""
        try:
            # Try to store and retrieve a test memory
            test_id = await self.memory.remember(
                content="System health test",
                agent_id="system",
                thread_id="health_check",
                tags=["test"],
            )
            
            memories = await self.memory.search_memories(
                query="System health test",
                agent_id="system",
                limit=1,
            )
            
            return {
                "status": "healthy",
                "can_write": bool(test_id),
                "can_read": len(memories) > 0,
                "type": type(self.memory_store).__name__,
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "type": type(self.memory_store).__name__,
            }

    async def cleanup(self) -> None:
        """Clean up system resources."""
        logger.info("cleaning_up_system_resources")
        
        # Clean up browser tools in agents
        for agent in self.agents.values():
            for tool in agent.config.tools:
                if hasattr(tool, "cleanup"):
                    try:
                        await tool.cleanup()
                    except Exception as e:
                        logger.warning("tool_cleanup_failed", tool=type(tool).__name__, error=str(e))
        
        # Clean up memory store
        try:
            if hasattr(self.memory_store, "close"):
                await self.memory_store.close()
        except Exception as e:
            logger.warning("memory_store_cleanup_failed", error=str(e))
        
        logger.info("system_cleanup_completed")
    
    async def _send_monitoring_event(
        self,
        agent_name: str,
        event_type: str,
        state: EnhancedAgentState,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """Send monitoring event if monitoring is enabled."""
        if not MONITORING_ENABLED or not monitoring_service:
            return
            
        try:
            event = AgentEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                agent_name=agent_name,
                event_type=event_type,
                iteration=state.get("iteration", 0),
                confidence=state.get("confidence_score", 0.0),
                data={
                    "execution_id": state.get("thread_id", ""),
                    "current_agent": state.get("current_agent", ""),
                    **(data or {})
                },
                error=error
            )
            
            await monitoring_service.broadcast_event(event)
            
        except Exception as e:
            logger.warning("monitoring_event_failed", error=str(e))