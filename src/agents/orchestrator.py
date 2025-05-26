"""Orchestrator agent for coordinating multi-agent workflows."""

from typing import Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage

from ..memory import Memory, MemoryType
from ..utils import AgentLogger
from .base import AgentConfig, AgentState, BaseAgent


class OrchestratorAgent(BaseAgent):
    """Agent responsible for orchestrating other agents."""

    def __init__(
        self,
        memory: Memory,
        available_agents: Dict[str, BaseAgent],
        logger: Optional[AgentLogger] = None,
    ):
        """Initialize orchestrator agent."""
        config = AgentConfig(
            name="orchestrator_agent",
            description="Coordenador do sistema multiagente regulatório",
            model="gpt-4.1",
            temperature=0.1,
            tools=[],
            system_prompt="""Você é o coordenador do Sistema Multiagente Regulatório do Grupo Soluto.

Você tem acesso aos seguintes agentes especializados:
1. **compliance_agent**: Especialista em conformidade regulatória
2. **legal_analysis_agent**: Especialista em análise jurídica
3. **risk_assessment_agent**: Especialista em avaliação de riscos
4. **document_review_agent**: Especialista em documentação
5. **research_agent**: Especialista em pesquisa

Sua responsabilidade é:
- Analisar a solicitação do usuário
- Decidir quais agentes devem ser acionados e em qual ordem
- Coordenar o fluxo de trabalho entre os agentes
- Garantir que todas as análises necessárias sejam realizadas
- Sintetizar os resultados em uma resposta coerente

Sempre priorize precisão, completude e conformidade regulatória.""",
        )
        super().__init__(config, memory, logger)
        self.available_agents = available_agents

    async def process(self, state: AgentState) -> AgentState:
        """Orchestrate the multi-agent workflow."""
        self.logger.log_action("starting_orchestration", {"task": state["task"]})
        
        # Analyze the task and plan the workflow
        workflow_plan = await self._plan_workflow(state)
        
        # Execute the workflow
        for agent_name, agent_task in workflow_plan:
            if state["iteration"] >= state["max_iterations"]:
                self.logger.log_action("max_iterations_reached", {"iteration": state["iteration"]})
                break
                
            state["current_agent"] = agent_name
            state["iteration"] += 1
            
            # Log agent activation
            self.logger.log_action(
                "activating_agent",
                {"agent": agent_name, "task": agent_task},
            )
            
            # Get the agent and process
            agent = self.available_agents.get(agent_name)
            if agent:
                try:
                    state = await agent.process(state)
                except Exception as e:
                    self.logger.log_error(
                        f"Agent {agent_name} failed",
                        exception=e,
                    )
                    state["error"] = str(e)
                    
        # Synthesize final response
        state = await self._synthesize_response(state)
        
        return state

    async def _plan_workflow(self, state: AgentState) -> List[Tuple[str, str]]:
        """Plan which agents to use and in what order."""
        planning_prompt = f"""
Analise a seguinte solicitação e determine quais agentes devem ser acionados e em qual ordem:

Solicitação: {state['task']}

Agentes disponíveis:
1. compliance_agent - Para análise de conformidade regulatória
2. legal_analysis_agent - Para análise jurídica e legislação
3. risk_assessment_agent - Para avaliação de riscos
4. document_review_agent - Para geração de documentos
5. research_agent - Para pesquisa adicional

Retorne uma lista ordenada dos agentes que devem ser acionados, no formato:
agent_name: tarefa específica para o agente

Exemplo:
research_agent: pesquisar regulamentações sobre [tópico]
compliance_agent: analisar conformidade com normas encontradas
legal_analysis_agent: verificar implicações legais
risk_assessment_agent: avaliar riscos identificados
document_review_agent: gerar relatório final

Seja específico sobre o que cada agente deve fazer.
"""
        
        response = await self.llm.ainvoke([
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": planning_prompt},
        ])
        
        # Parse the workflow plan
        workflow = []
        lines = response.content.strip().split("\n")
        
        for line in lines:
            if ":" in line and any(agent in line for agent in self.available_agents):
                parts = line.split(":", 1)
                agent_name = parts[0].strip()
                agent_task = parts[1].strip() if len(parts) > 1 else state["task"]
                
                if agent_name in self.available_agents:
                    workflow.append((agent_name, agent_task))
        
        # Default workflow if parsing fails
        if not workflow:
            workflow = [
                ("research_agent", state["task"]),
                ("compliance_agent", state["task"]),
                ("legal_analysis_agent", state["task"]),
                ("risk_assessment_agent", state["task"]),
                ("document_review_agent", state["task"]),
            ]
        
        self.logger.log_action("workflow_planned", {"workflow": workflow})
        
        # Store workflow plan in memory
        await self.memory.remember(
            content=f"Workflow plan: {workflow}",
            agent_id=self.config.name,
            memory_type=MemoryType.PROCEDURAL,
            thread_id=state.get("thread_id"),
            tags=["workflow", "planning"],
        )
        
        return workflow

    async def _synthesize_response(self, state: AgentState) -> AgentState:
        """Synthesize the final response from all agent outputs."""
        synthesis_prompt = f"""
Com base em todas as análises realizadas pelos agentes especializados, crie uma resposta final consolidada.

Tarefa original: {state['task']}

Contexto das análises:
{self._format_context(state['context'])}

Crie uma resposta que:
1. Responda diretamente à solicitação do usuário
2. Integre insights de todas as análises realizadas
3. Destaque as principais conclusões e recomendações
4. Mencione quaisquer documentos gerados
5. Forneça próximos passos claros

Seja conciso mas completo.
"""
        
        response = await self.llm.ainvoke([
            {"role": "system", "content": "Você é um assistente que sintetiza informações complexas de forma clara e acionável."},
            {"role": "user", "content": synthesis_prompt},
        ])
        
        # Store final synthesis
        await self.memory.remember(
            content=f"Síntese final: {response.content}",
            agent_id=self.config.name,
            memory_type=MemoryType.LONG_TERM,
            thread_id=state.get("thread_id"),
            tags=["synthesis", "final_response"],
        )
        
        # Update state with final output
        state["final_output"] = response.content
        state["messages"].append(AIMessage(content=response.content))
        
        # Consolidate memories if needed
        if len(state["memory_entries"]) > 10:
            consolidated_id = await self.memory.consolidate_memories(
                agent_id=self.config.name,
                thread_id=state.get("thread_id"),
            )
            if consolidated_id:
                self.logger.log_action(
                    "memories_consolidated",
                    {"consolidated_id": consolidated_id},
                )
        
        return state

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context for synthesis."""
        formatted = ""
        
        sections = {
            "research_findings": "Pesquisa",
            "compliance_analysis": "Análise de Conformidade",
            "legal_analysis": "Análise Jurídica",
            "risk_assessment": "Avaliação de Riscos",
            "final_report": "Relatório Final",
        }
        
        for key, title in sections.items():
            if key in context and context[key]:
                formatted += f"\n\n{title}:\n{context[key][:500]}..."
                
        return formatted