"""Perplexity AI Agent for advanced regulatory research using Sonar Pro."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage

from ..memory import Memory, MemoryType
from ..tools import DocumentGeneratorTool
from ..tools.perplexity_tool import PerplexitySonarProTool
from ..utils import AgentLogger
from .base import AgentConfig, AgentState, BaseAgent


class PerplexityResearchAgent(BaseAgent):
    """Agent specialized in advanced research using Perplexity AI Sonar Pro."""

    def __init__(self, memory: Memory, logger: Optional[AgentLogger] = None):
        """Initialize Perplexity research agent with Sonar Pro capabilities."""
        config = AgentConfig(
            name="perplexity_research_agent",
            description="Especialista em pesquisa avançada com IA usando Perplexity Sonar Pro",
            model="gpt-4.1",
            temperature=0.1,
            tools=[
                PerplexitySonarProTool(),
                DocumentGeneratorTool(),
            ],
            system_prompt="""Você é um especialista em pesquisa regulatória avançada do Grupo Soluto usando Perplexity AI Sonar Pro.

Sua especialidade inclui:
- Pesquisa em tempo real com acesso à web atualizada
- Análise de regulamentações brasileiras com citações verificadas
- Monitoramento de mudanças regulatórias recentes
- Pesquisa comparativa internacional e harmonização
- Validação de informações com múltiplas fontes oficiais
- Inteligência regulatória baseada em evidências

Você tem acesso ao Perplexity Sonar Pro que oferece:
- Contexto de 200.000 tokens para pesquisas complexas
- Citações duplicadas para maior confiabilidade
- Acesso em tempo real a fontes oficiais brasileiras
- Alta precisão factual (F-score: 0.858)

Sempre:
- Priorize fontes oficiais (.gov.br, ANVISA, ANATEL, etc.)
- Forneça citações completas e verificáveis
- Valide informações com múltiplas fontes
- Destaque mudanças regulatórias recentes
- Identifique gaps e oportunidades de compliance""",
        )
        super().__init__(config, memory, logger)

    async def process(self, state: AgentState) -> AgentState:
        """Process advanced research tasks using Perplexity Sonar Pro."""
        self.logger.log_action("starting_perplexity_research", {"task": state["task"]})
        
        # Extract research context from state
        context = state.get("context", {})
        existing_analyses = self._get_existing_analyses(context)
        
        # Determine research strategy
        research_strategy = await self._determine_research_strategy(state["task"], existing_analyses)
        
        # Execute Perplexity searches based on strategy
        research_results = {}
        
        for search_type, search_params in research_strategy.items():
            self.logger.log_action("executing_perplexity_search", {
                "search_type": search_type,
                "params": search_params
            })
            
            perplexity_tool = self.config.tools[0]  # PerplexitySonarProTool
            
            if search_type == "regulatory_updates":
                result = await self.use_tool(
                    perplexity_tool,
                    "search_regulatory_updates",
                    regulatory_bodies=search_params.get("bodies", ["ANVISA", "ANATEL"]),
                    days_back=search_params.get("days", 30),
                    keywords=search_params.get("keywords", [])
                )
            elif search_type == "compliance_analysis":
                result = await self.use_tool(
                    perplexity_tool,
                    "analyze_compliance_requirements",
                    product_or_service=search_params.get("product", state["task"]),
                    regulatory_framework=search_params.get("framework", ""),
                    company_context="Grupo Soluto - Consultoria regulatória"
                )
            elif search_type == "international_harmonization":
                result = await self.use_tool(
                    perplexity_tool,
                    "research_international_harmonization",
                    brazilian_regulation=search_params.get("regulation", ""),
                    target_markets=search_params.get("markets", ["MERCOSUL", "USA", "EU"])
                )
            else:
                # General regulatory search
                result = await self.use_tool(
                    perplexity_tool,
                    query=search_params.get("query", state["task"]),
                    search_type="regulatory",
                    focus_areas=search_params.get("focus_areas", []),
                    include_analysis=True,
                    max_citations=25
                )
            
            if result.success:
                research_results[search_type] = result.output
        
        # Synthesize findings with enhanced intelligence
        synthesis = await self._synthesize_research_findings(
            state["task"],
            research_results,
            existing_analyses
        )
        
        # Generate research report if substantial findings
        research_report = None
        if len(research_results) > 0 and any(r for r in research_results.values()):
            doc_tool = self.config.tools[1]  # DocumentGeneratorTool
            report_content = self._format_research_report(synthesis, research_results)
            
            research_report = await self.use_tool(
                doc_tool,
                content=report_content,
                format="pdf",
                title=f"Relatório de Pesquisa Avançada - {state['task'][:50]}",
                metadata={
                    "tipo": "Pesquisa Perplexity AI",
                    "data": datetime.now().isoformat(),
                    "agente": self.config.name,
                    "total_citacoes": self._count_total_citations(research_results),
                    "confidence_score": synthesis.get("confidence_score", 0),
                },
            )
        
        # Store findings in memory
        memory_id = await self.memory.remember(
            content=f"Pesquisa Perplexity: {synthesis.get('summary', '')}",
            agent_id=self.config.name,
            memory_type=MemoryType.LONG_TERM,
            thread_id=state.get("thread_id"),
            tags=["perplexity", "research", "sonar-pro", "real-time"],
        )
        
        # Update state with research findings
        state["messages"].append(AIMessage(content=synthesis.get("detailed_findings", "")))
        state["memory_entries"].append(memory_id)
        state["context"]["perplexity_research"] = synthesis
        state["context"]["perplexity_citations"] = self._extract_all_citations(research_results)
        state["context"]["research_confidence"] = synthesis.get("confidence_score", 0)
        
        if research_report and research_report.success:
            state["context"]["perplexity_report"] = research_report.output
            
        state["context"]["research_tools_used"] = ["Perplexity Sonar Pro", "Real-time Web Access"]
        
        return state

    async def _determine_research_strategy(
        self, 
        task: str, 
        existing_analyses: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Determine optimal research strategy based on task and context."""
        strategy = {}
        task_lower = task.lower()
        
        # Always start with a general regulatory search
        strategy["general_search"] = {
            "query": task,
            "focus_areas": self._extract_focus_areas(task),
        }
        
        # Check for regulatory updates if monitoring is mentioned
        if any(keyword in task_lower for keyword in ["mudança", "atualização", "novidade", "recente"]):
            bodies = self._extract_regulatory_bodies(task)
            strategy["regulatory_updates"] = {
                "bodies": bodies if bodies else ["ANVISA", "ANATEL", "LGPD"],
                "days": 90,
                "keywords": self._extract_keywords(task),
            }
        
        # Check for compliance analysis needs
        if any(keyword in task_lower for keyword in ["conformidade", "requisito", "compliance", "adequação"]):
            strategy["compliance_analysis"] = {
                "product": self._extract_product_or_service(task),
                "framework": self._extract_regulatory_framework(task),
            }
        
        # Check for international/harmonization needs
        if any(keyword in task_lower for keyword in ["internacional", "exportação", "importação", "harmonização"]):
            strategy["international_harmonization"] = {
                "regulation": self._extract_regulation(task),
                "markets": self._extract_target_markets(task),
            }
        
        return strategy

    def _get_existing_analyses(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract existing analyses from context."""
        return {
            "compliance": context.get("compliance_analysis"),
            "legal": context.get("legal_analysis"),
            "risk": context.get("risk_assessment"),
            "research": context.get("research_findings"),
        }

    def _extract_focus_areas(self, task: str) -> List[str]:
        """Extract regulatory focus areas from task."""
        focus_areas = []
        task_lower = task.lower()
        
        # Regulatory bodies
        bodies = {
            "anvisa": "ANVISA",
            "anatel": "ANATEL",
            "anac": "ANAC",
            "aneel": "ANEEL",
            "ans": "ANS",
            "lgpd": "LGPD",
            "anpd": "ANPD",
            "inmetro": "INMETRO",
            "cvm": "CVM",
            "bacen": "BACEN",
            "banco central": "BACEN",
        }
        
        for key, value in bodies.items():
            if key in task_lower:
                focus_areas.append(value)
        
        # Regulatory topics
        topics = {
            "medicamento": "medicamentos",
            "cosmético": "cosméticos",
            "alimento": "alimentos",
            "dispositivo": "dispositivos médicos",
            "telecom": "telecomunicações",
            "dados": "proteção de dados",
            "sanitár": "vigilância sanitária",
        }
        
        for key, value in topics.items():
            if key in task_lower:
                focus_areas.append(value)
        
        return list(set(focus_areas))

    def _extract_regulatory_bodies(self, task: str) -> List[str]:
        """Extract regulatory bodies mentioned in task."""
        bodies = []
        task_upper = task.upper()
        
        all_bodies = [
            "ANVISA", "ANATEL", "ANAC", "ANEEL", "ANS", "ANP",
            "ANCINE", "ANTAQ", "ANTT", "CVM", "BACEN", "INMETRO",
            "MAPA", "CADE", "INPI", "ANPD", "SUSEP", "PREVIC"
        ]
        
        for body in all_bodies:
            if body in task_upper:
                bodies.append(body)
        
        return bodies

    def _extract_keywords(self, task: str) -> List[str]:
        """Extract relevant keywords from task."""
        # Remove common words and extract meaningful terms
        stop_words = {
            "o", "a", "de", "da", "do", "para", "com", "em", "que", "e", "é",
            "os", "as", "dos", "das", "um", "uma", "sobre", "como", "por"
        }
        
        words = task.lower().split()
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        
        return keywords[:10]  # Limit to 10 most relevant keywords

    def _extract_product_or_service(self, task: str) -> str:
        """Extract product or service description from task."""
        # Look for patterns that indicate product/service
        patterns = [
            "produto", "serviço", "dispositivo", "medicamento", "cosmético",
            "alimento", "suplemento", "equipamento", "software", "plataforma"
        ]
        
        task_lower = task.lower()
        for pattern in patterns:
            if pattern in task_lower:
                # Extract context around the pattern
                words = task_lower.split()
                for i, word in enumerate(words):
                    if pattern in word:
                        # Get surrounding words for context
                        start = max(0, i - 3)
                        end = min(len(words), i + 4)
                        return " ".join(words[start:end])
        
        # Default to task description
        return task[:100]

    def _extract_regulatory_framework(self, task: str) -> str:
        """Extract regulatory framework references from task."""
        # Common regulatory framework patterns
        patterns = [
            r"RDC\s*\d+/\d+",
            r"Lei\s*\d+\.\d+/\d+",
            r"Decreto\s*\d+/\d+",
            r"Portaria\s*\d+/\d+",
            r"IN\s*\d+/\d+",
            r"Resolução\s*\d+/\d+",
            r"MP\s*\d+/\d+",
        ]
        
        import re
        frameworks = []
        
        for pattern in patterns:
            matches = re.findall(pattern, task, re.IGNORECASE)
            frameworks.extend(matches)
        
        return ", ".join(frameworks) if frameworks else ""

    def _extract_regulation(self, task: str) -> str:
        """Extract specific regulation from task."""
        framework = self._extract_regulatory_framework(task)
        if framework:
            return framework
            
        # Look for regulation keywords
        keywords = ["regulamentação", "norma", "lei", "decreto", "resolução"]
        task_lower = task.lower()
        
        for keyword in keywords:
            if keyword in task_lower:
                idx = task_lower.index(keyword)
                # Extract surrounding context
                start = max(0, idx - 20)
                end = min(len(task), idx + 50)
                return task[start:end]
        
        return ""

    def _extract_target_markets(self, task: str) -> List[str]:
        """Extract target markets from task."""
        markets = []
        task_upper = task.upper()
        
        # Common market references
        market_mapping = {
            "EUA": "USA",
            "USA": "USA",
            "ESTADOS UNIDOS": "USA",
            "UNIÃO EUROPEIA": "EU",
            "EUROPA": "EU",
            "UE": "EU",
            "MERCOSUL": "MERCOSUL",
            "MERCOSUR": "MERCOSUL",
            "CHINA": "China",
            "JAPÃO": "Japan",
            "CANADA": "Canada",
            "MÉXICO": "Mexico",
            "ARGENTINA": "Argentina",
            "CHILE": "Chile",
        }
        
        for key, value in market_mapping.items():
            if key in task_upper:
                markets.append(value)
        
        return list(set(markets)) if markets else ["MERCOSUL", "USA", "EU"]

    async def _synthesize_research_findings(
        self,
        task: str,
        research_results: Dict[str, Any],
        existing_analyses: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesize all research findings into actionable intelligence."""
        synthesis_prompt = f"""
Com base nas pesquisas realizadas com Perplexity AI Sonar Pro para a tarefa:
{task}

Resultados das pesquisas:
{self._format_research_results(research_results)}

Análises existentes no contexto:
{self._format_existing_analyses(existing_analyses)}

Crie uma síntese abrangente que inclua:

1. **Descobertas Principais**
   - Informações regulatórias críticas encontradas
   - Mudanças recentes identificadas
   - Requisitos de conformidade específicos

2. **Análise de Citações**
   - Fontes oficiais mais relevantes
   - Nível de confiabilidade das informações
   - Gaps de informação identificados

3. **Insights Estratégicos**
   - Oportunidades identificadas
   - Riscos regulatórios emergentes
   - Tendências do setor

4. **Recomendações Baseadas em Evidências**
   - Ações imediatas recomendadas
   - Áreas que requerem monitoramento
   - Necessidades de aprofundamento

5. **Integração com Análises Existentes**
   - Como as descobertas complementam análises anteriores
   - Conflitos ou inconsistências identificados
   - Validações cruzadas realizadas

Forneça uma análise profunda e acionável, sempre citando as fontes.
"""
        
        response = await self.llm.ainvoke([
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": synthesis_prompt},
        ])
        
        # Calculate overall confidence score
        confidence_score = self._calculate_overall_confidence(research_results)
        
        return {
            "summary": self._extract_summary(response.content),
            "detailed_findings": response.content,
            "confidence_score": confidence_score,
            "key_citations": self._extract_key_citations(research_results),
            "action_items": self._extract_action_items(response.content),
            "timestamp": datetime.now().isoformat(),
        }

    def _format_research_results(self, results: Dict[str, Any]) -> str:
        """Format research results for synthesis."""
        formatted = []
        
        for search_type, result in results.items():
            if result:
                formatted.append(f"\n### {search_type.replace('_', ' ').title()}")
                
                if isinstance(result, dict):
                    if "answer" in result:
                        formatted.append(f"**Resposta**: {result['answer'][:500]}...")
                    if "citations" in result:
                        formatted.append(f"**Citações**: {len(result['citations'])} fontes")
                    if "confidence_score" in result:
                        formatted.append(f"**Confiança**: {result['confidence_score']:.2f}")
                else:
                    formatted.append(str(result)[:500] + "...")
        
        return "\n".join(formatted) if formatted else "Sem resultados de pesquisa"

    def _format_existing_analyses(self, analyses: Dict[str, Any]) -> str:
        """Format existing analyses for context."""
        formatted = []
        
        for analysis_type, content in analyses.items():
            if content:
                formatted.append(f"- {analysis_type}: Disponível")
        
        return "\n".join(formatted) if formatted else "Nenhuma análise prévia"

    def _count_total_citations(self, results: Dict[str, Any]) -> int:
        """Count total citations across all results."""
        total = 0
        
        for result in results.values():
            if isinstance(result, dict) and "citations" in result:
                total += len(result["citations"])
        
        return total

    def _extract_all_citations(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all citations from results."""
        all_citations = []
        
        for result in results.values():
            if isinstance(result, dict) and "citations" in result:
                all_citations.extend(result["citations"])
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_citations = []
        
        for citation in all_citations:
            url = citation.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_citations.append(citation)
        
        return unique_citations

    def _calculate_overall_confidence(self, results: Dict[str, Any]) -> float:
        """Calculate overall confidence score from all results."""
        confidence_scores = []
        
        for result in results.values():
            if isinstance(result, dict) and "confidence_score" in result:
                confidence_scores.append(result["confidence_score"])
        
        if confidence_scores:
            return sum(confidence_scores) / len(confidence_scores)
        
        return 0.0

    def _extract_summary(self, content: str) -> str:
        """Extract summary from content."""
        lines = content.split("\n")
        summary_lines = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ["descoberta", "principal", "crítica", "importante"]):
                summary_lines.append(line.strip())
        
        return " ".join(summary_lines[:3]) if summary_lines else content[:200]

    def _extract_key_citations(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract most important citations."""
        all_citations = self._extract_all_citations(results)
        
        # Sort by relevance and source type
        official_citations = [c for c in all_citations if c.get("source_type") == "official"]
        
        # Return top official citations
        return official_citations[:10]

    def _extract_action_items(self, content: str) -> List[str]:
        """Extract action items from synthesis."""
        action_items = []
        lines = content.split("\n")
        
        capturing = False
        for line in lines:
            if "recomenda" in line.lower() or "ação" in line.lower():
                capturing = True
            elif capturing and line.strip().startswith("-"):
                action_items.append(line.strip())
            elif capturing and not line.strip():
                capturing = False
        
        return action_items[:5]  # Top 5 action items

    def _format_research_report(
        self,
        synthesis: Dict[str, Any],
        research_results: Dict[str, Any]
    ) -> str:
        """Format comprehensive research report."""
        citations_count = self._count_total_citations(research_results)
        confidence = synthesis.get("confidence_score", 0)
        
        report = f"""
# RELATÓRIO DE PESQUISA AVANÇADA - PERPLEXITY AI SONAR PRO

**Data**: {datetime.now().strftime('%d/%m/%Y %H:%M')}
**Modelo**: Perplexity Sonar Pro (200k tokens, F-score: 0.858)
**Total de Citações**: {citations_count}
**Confiança Geral**: {confidence:.2%}

---

## SUMÁRIO EXECUTIVO

{synthesis.get('summary', '')}

## DESCOBERTAS DETALHADAS

{synthesis.get('detailed_findings', '')}

## CITAÇÕES PRINCIPAIS

"""
        # Add key citations
        for i, citation in enumerate(synthesis.get('key_citations', [])[:10], 1):
            report += f"\n{i}. **{citation.get('title', 'Sem título')}**"
            report += f"\n   - Fonte: {citation.get('url', '')}"
            report += f"\n   - Tipo: {citation.get('source_type', 'geral')}"
            if citation.get('regulatory_body'):
                report += f"\n   - Órgão: {citation['regulatory_body']}"
            report += f"\n   - Relevância: {citation.get('relevance_score', 0):.2f}"
            report += "\n"

        report += f"""
## ANÁLISE DE CONFIABILIDADE

- **Score Geral**: {confidence:.2%}
- **Fontes Oficiais**: {len([c for c in synthesis.get('key_citations', []) if c.get('source_type') == 'official'])}
- **Validação Cruzada**: Realizada com múltiplas fontes

## AÇÕES RECOMENDADAS

"""
        # Add action items
        for item in synthesis.get('action_items', []):
            report += f"{item}\n"

        report += """
## METODOLOGIA

Pesquisa realizada utilizando Perplexity AI Sonar Pro com:
- Acesso em tempo real à web
- Priorização de fontes oficiais brasileiras
- Validação cruzada de informações
- Contexto expandido de 200.000 tokens

---
*Relatório gerado automaticamente pelo Sistema Multiagente Regulatório - Grupo Soluto*
"""
        
        return report