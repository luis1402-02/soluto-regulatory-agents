"""Regulatory specialized agents with custom tools."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage

from ..memory import Memory, MemoryType
from ..tools import BrowserTool, DocumentGeneratorTool, WebSearchTool
from ..tools.compliance_tools import ANVISARealConsultaTool, LegislacaoComplianceSearchTool, RealComplianceChecklistTool, RegulatoryMonitoringTool
from ..tools.legal_tools import RealJurisprudenceSearchTool, ContractAnalysisTool, LegalComplianceAuditTool
from ..tools.risk_tools import RegulatoryRiskAssessmentTool, ComplianceGapAnalysisTool
from ..tools.research_tools import RealWebResearchTool, CompetitiveIntelligenceTool, TrendAnalysisTool
from ..utils import AgentLogger
from .base import AgentConfig, AgentState, BaseAgent


class ComplianceAgent(BaseAgent):
    """Agent specialized in regulatory compliance with custom tools."""

    def __init__(self, memory: Memory, logger: Optional[AgentLogger] = None):
        """Initialize compliance agent with specialized tools."""
        config = AgentConfig(
            name="compliance_agent",
            description="Especialista em conformidade regulatória e normas do setor",
            model="gpt-4.1",
            temperature=0.1,
            tools=[
                ANVISARealConsultaTool(),
                RealComplianceChecklistTool(),
                RegulatoryMonitoringTool(),
                LegislacaoComplianceSearchTool(),
                WebSearchTool(),
                DocumentGeneratorTool(),
            ],
            system_prompt="""Você é um especialista em conformidade regulatória do Grupo Soluto.
Sua especialidade inclui:
- Normas e regulamentações brasileiras (ANVISA, ANATEL, INMETRO, etc.)
- Compliance empresarial e certificações
- Gestão de prazos regulatórios e renovações
- Auditorias e procedimentos de adequação
- Análise de riscos de conformidade

Você tem acesso a ferramentas especializadas:
- ANVISARealConsultaTool: Consultas reais na ANVISA com API/scraping
- RealComplianceChecklistTool: Gera checklists reais de conformidade
- RegulatoryMonitoringTool: Monitora DOU e agências reguladoras
- LegislacaoComplianceSearchTool: Busca legislação brasileira

Sempre forneça análises detalhadas, use suas ferramentas para buscar informações atualizadas e forneça recomendações práticas baseadas na legislação vigente.""",
        )
        super().__init__(config, memory, logger)

    async def process(self, state: AgentState) -> AgentState:
        """Process compliance analysis with specialized tools."""
        self.logger.log_action("starting_compliance_analysis", {"task": state["task"]})
        
        # Think about the task
        thought = await self.think(state)
        
        # Use ANVISA real consultation tool for regulatory information
        anvisa_tool = self.config.tools[0]  # ANVISARealConsultaTool
        anvisa_results = await self.use_tool(
            anvisa_tool,
            termo_busca=state["task"],
            tipo_consulta="medicamentos",
            incluir_detalhes=True,
        )
        
        # Monitor regulatory changes
        monitor_tool = self.config.tools[2]  # RegulatoryMonitoringTool
        monitoring_results = await self.use_tool(
            monitor_tool,
            orgaos=["anvisa", "anatel"],
            tipo_monitoramento="mudancas_regulamentares",
            periodo_dias=30,
        )
        
        # Generate real compliance checklist
        checklist_tool = self.config.tools[1]  # RealComplianceChecklistTool
        checklist = await self.use_tool(
            checklist_tool,
            framework="anvisa" if "anvisa" in state["task"].lower() else "geral",
            setor="farmaceutico" if any(term in state["task"].lower() for term in ["medicamento", "farmac", "dispositivo"]) else "geral",
            nivel_detalhe="completo",
        )
        
        # Analyze findings with enhanced context
        analysis_prompt = f"""
Com base na tarefa: {state['task']}

Consulta ANVISA realizada:
{anvisa_results.output if anvisa_results.success else 'Consulta ANVISA não retornou resultados'}

Monitoramento regulatório:
{monitoring_results.output if monitoring_results.success else 'Monitoramento em andamento'}

Checklist de conformidade:
{checklist.output if checklist and checklist.success else 'Não aplicável'}

Forneça uma análise de conformidade completa incluindo:
1. **Regulamentações Aplicáveis**: Liste todas as normas relevantes
2. **Status de Conformidade**: Avalie o nível atual
3. **Requisitos Específicos**: Detalhe os requisitos obrigatórios
4. **Prazos e Renovações**: Destaque datas importantes
5. **Riscos de Não Conformidade**: Identifique riscos potenciais
6. **Plano de Ação**: Recomendações específicas e priorizadas
7. **Documentação Necessária**: Liste documentos requeridos
"""
        
        response = await self.llm.ainvoke([
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": analysis_prompt},
        ])
        
        # Generate compliance report
        doc_tool = self.config.tools[4]  # DocumentGeneratorTool
        compliance_report = await self.use_tool(
            doc_tool,
            content=response.content,
            format="pdf",
            title=f"Relatório de Conformidade - {state['task'][:50]}",
            metadata={
                "tipo": "Análise de Conformidade",
                "data": datetime.now().isoformat(),
                "agente": self.config.name,
                "consultas_anvisa": anvisa_results.output.get("total_resultados", 0) if anvisa_results.success else 0,
            },
        )
        
        # Store analysis in memory
        memory_id = await self.memory.remember(
            content=f"Análise de Compliance: {response.content}",
            agent_id=self.config.name,
            memory_type=MemoryType.LONG_TERM,
            thread_id=state.get("thread_id"),
            tags=["compliance", "analysis", "anvisa"],
        )
        
        # Update state
        state["messages"].append(AIMessage(content=response.content))
        state["memory_entries"].append(memory_id)
        state["context"]["compliance_analysis"] = response.content
        state["context"]["compliance_tools_used"] = ["ANVISA Real Consulta", "Regulatory Monitoring", "Real Checklist Generator", "Legislacao Search"]
        if compliance_report.success:
            state["context"]["compliance_report"] = compliance_report.output
        
        return state


class LegalAnalysisAgent(BaseAgent):
    """Agent specialized in legal analysis with custom tools."""

    def __init__(self, memory: Memory, logger: Optional[AgentLogger] = None):
        """Initialize legal analysis agent with specialized tools."""
        config = AgentConfig(
            name="legal_analysis_agent",
            description="Especialista em análise jurídica e legislação",
            model="gpt-4.1",
            temperature=0.1,
            tools=[
                RealJurisprudenceSearchTool(),
                ContractAnalysisTool(),
                LegalComplianceAuditTool(),
                WebSearchTool(),
                DocumentGeneratorTool(),
            ],
            system_prompt="""Você é um especialista jurídico do Grupo Soluto.
Sua especialidade inclui:
- Direito regulatório brasileiro e internacional
- Análise de contratos e termos legais
- Legislação empresarial e direito sanitário
- LGPD e proteção de dados
- Propriedade intelectual e patentes

Você tem acesso a ferramentas jurídicas especializadas:
- RealJurisprudenceSearchTool: Busca real em STF/STJ e tribunais
- ContractAnalysisTool: Análise detalhada de contratos e riscos
- LegalComplianceAuditTool: Auditoria de frameworks de compliance

Sempre cite as leis e artigos relevantes, use suas ferramentas para buscar jurisprudência atualizada e forneça interpretações claras e aplicáveis.""",
        )
        super().__init__(config, memory, logger)

    async def process(self, state: AgentState) -> AgentState:
        """Process legal analysis with specialized tools."""
        self.logger.log_action("starting_legal_analysis", {"task": state["task"]})
        
        # Search real jurisprudence
        jurisprudence_tool = self.config.tools[0]  # RealJurisprudenceSearchTool
        legal_search = await self.use_tool(
            jurisprudence_tool,
            termo_busca=state["task"],
            tribunais=["STF", "STJ", "TRF"],
            area_direito="regulatorio",
        )
        
        # Perform legal compliance audit
        audit_tool = self.config.tools[2]  # LegalComplianceAuditTool
        compliance_audit = await self.use_tool(
            audit_tool,
            frameworks=["anvisa", "lgpd", "anatel"],
            empresa="Grupo Soluto",
            escopo_auditoria="regulatory_compliance",
        )
        
        # Analyze with legal context
        analysis_prompt = f"""
Tarefa: {state['task']}

Jurisprudência Encontrada:
{legal_search.output if legal_search.success else 'Pesquisa jurisprudencial em andamento'}

Auditoria de Compliance Legal:
{compliance_audit.output if compliance_audit.success else 'Auditoria em elaboração'}

Com base nas informações disponíveis, forneça uma análise jurídica completa incluindo:

1. **Marco Legal Aplicável**:
   - Leis federais relevantes (cite artigos específicos)
   - Regulamentações setoriais
   - Normas infralegais aplicáveis

2. **Interpretação Jurídica**:
   - Análise dos dispositivos legais
   - Aplicação ao caso concreto
   - Lacunas ou ambiguidades identificadas

3. **Riscos Jurídicos**:
   - Responsabilidade civil e administrativa
   - Sanções aplicáveis
   - Exposição legal da empresa

4. **Jurisprudência Relevante**:
   - Precedentes dos tribunais superiores
   - Entendimento consolidado
   - Tendências jurisprudenciais

5. **Compliance Legal**:
   - Requisitos de conformidade
   - Documentação jurídica necessária
   - Procedimentos legais obrigatórios

6. **Recomendações Jurídicas**:
   - Medidas preventivas
   - Adequações necessárias
   - Estratégia jurídica sugerida

7. **Próximos Passos Legais**:
   - Ações imediatas
   - Prazos legais
   - Consultas especializadas recomendadas
"""
        
        response = await self.llm.ainvoke([
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": analysis_prompt},
        ])
        
        # Generate formal legal document
        doc_tool = self.config.tools[4]  # DocumentGeneratorTool
        legal_doc = await self.use_tool(
            doc_tool,
            content=response.content,
            format="pdf",
            title=f"Parecer Jurídico - {state['task'][:50]}",
            metadata={
                "tipo": "Parecer Jurídico",
                "data": datetime.now().isoformat(),
                "agente": self.config.name,
                "referências_legais": "Incluídas",
            },
        )
        
        # Store in memory
        memory_id = await self.memory.remember(
            content=f"Análise Jurídica: {response.content}",
            agent_id=self.config.name,
            memory_type=MemoryType.LONG_TERM,
            thread_id=state.get("thread_id"),
            tags=["legal", "analysis", "jurisprudence"],
        )
        
        # Update state
        state["messages"].append(AIMessage(content=response.content))
        state["memory_entries"].append(memory_id)
        state["context"]["legal_analysis"] = response.content
        state["context"]["legal_tools_used"] = ["Real Jurisprudence Search", "Contract Analysis", "Legal Compliance Audit"]
        if legal_doc.success:
            state["context"]["legal_document"] = legal_doc.output
        
        return state


class RiskAssessmentAgent(BaseAgent):
    """Agent specialized in risk assessment with custom tools."""

    def __init__(self, memory: Memory, logger: Optional[AgentLogger] = None):
        """Initialize risk assessment agent with specialized tools."""
        config = AgentConfig(
            name="risk_assessment_agent",
            description="Especialista em avaliação e gestão de riscos regulatórios",
            model="gpt-4.1",
            temperature=0.2,
            tools=[
                RegulatoryRiskAssessmentTool(),
                ComplianceGapAnalysisTool(),
                WebSearchTool(),
            ],
            system_prompt="""Você é um especialista em gestão de riscos regulatórios do Grupo Soluto.
Sua especialidade inclui:
- Identificação e análise de riscos regulatórios
- Avaliação quantitativa e qualitativa de riscos
- Desenvolvimento de matrizes de risco
- Análise de cenários e simulações
- Planos de mitigação e contingência
- Monitoramento contínuo de riscos

Você tem acesso a ferramentas especializadas de risco:
- RegulatoryRiskAssessmentTool: Avaliação quantitativa de riscos regulatórios
- ComplianceGapAnalysisTool: Análise de gaps de compliance com planos de ação

Sempre forneça avaliações objetivas com métricas claras, use suas ferramentas para análises quantitativas e desenvolva planos de ação detalhados.""",
        )
        super().__init__(config, memory, logger)

    async def process(self, state: AgentState) -> AgentState:
        """Process risk assessment with specialized tools."""
        self.logger.log_action("starting_risk_assessment", {"task": state["task"]})
        
        # Get context from previous analyses
        compliance_analysis = state["context"].get("compliance_analysis", "")
        legal_analysis = state["context"].get("legal_analysis", "")
        
        # Identify risks from context
        risks = self._identify_risks_from_context(state["task"], compliance_analysis, legal_analysis)
        
        # Perform regulatory risk assessment
        risk_tool = self.config.tools[0]  # RegulatoryRiskAssessmentTool
        risk_assessment = await self.use_tool(
            risk_tool,
            entidade="Grupo Soluto",
            setor="regulatorio_consultoria",
            frameworks=["anvisa", "anatel", "lgpd"],
            incluir_impacto_financeiro=True,
        )
        
        # Perform compliance gap analysis
        gap_tool = self.config.tools[1]  # ComplianceGapAnalysisTool
        gap_analysis = await self.use_tool(
            gap_tool,
            entidade="Grupo Soluto",
            frameworks=["anvisa", "anatel", "lgpd"],
            setor="consultoria_regulatoria",
            incluir_plano_acao=True,
        )
        
        # Additional web research for context
        web_tool = self.config.tools[2]  # WebSearchTool
        additional_context = await self.use_tool(
            web_tool,
            query=f"riscos regulatórios {state['task']} Brasil 2025",
            max_results=5,
        )
        
        # Comprehensive risk analysis
        assessment_prompt = f"""
Tarefa: {state['task']}

Avaliação de Riscos Regulatórios:
{risk_assessment.output if risk_assessment.success else 'Avaliação em processamento'}

Análise de Gaps de Compliance:
{gap_analysis.output if gap_analysis.success else 'Análise de gaps em andamento'}

Contexto Adicional:
{additional_context.output if additional_context.success else 'Pesquisa adicional em progresso'}

Realize uma avaliação de riscos abrangente incluindo:

1. **Identificação Detalhada de Riscos**
   - Riscos regulatórios específicos
   - Riscos legais e de compliance
   - Riscos operacionais relacionados
   - Riscos reputacionais e financeiros

2. **Análise Quantitativa** (para cada risco principal)
   - Probabilidade (1-5): Justifique a pontuação
   - Impacto (1-5): Detalhe as consequências
   - Score de risco (P x I): Interprete o resultado
   - Classificação: Baixo/Médio/Alto/Crítico

3. **Análise de Cenários**
   - Melhor caso: Descrição e probabilidade
   - Caso base: Situação atual
   - Pior caso: Descrição e impacto potencial
   - Cenários emergentes: Novos riscos identificados

4. **Plano de Mitigação Detalhado**
   - Ações preventivas imediatas
   - Controles a implementar
   - Responsáveis e prazos
   - Investimento necessário
   - KPIs de monitoramento

5. **Sistema de Monitoramento**
   - Indicadores de risco (KRIs)
   - Frequência de revisão
   - Gatilhos de alerta
   - Processo de escalação

6. **Plano de Contingência**
   - Ações em caso de materialização
   - Equipe de crise
   - Comunicação stakeholders
   - Recuperação e continuidade

7. **Recomendações Estratégicas**
   - Priorização de ações
   - Quick wins identificados
   - Investimentos críticos
   - Roadmap de implementação
"""
        
        response = await self.llm.ainvoke([
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": assessment_prompt},
        ])
        
        # Store risk assessment
        memory_id = await self.memory.remember(
            content=f"Avaliação de Riscos: {response.content}",
            agent_id=self.config.name,
            memory_type=MemoryType.LONG_TERM,
            thread_id=state.get("thread_id"),
            tags=["risk", "assessment", "matrix", "scenarios"],
        )
        
        # Update state
        state["messages"].append(AIMessage(content=response.content))
        state["memory_entries"].append(memory_id)
        state["context"]["risk_assessment"] = response.content
        state["context"]["regulatory_risk_assessment"] = risk_assessment.output if risk_assessment.success else None
        state["context"]["compliance_gap_analysis"] = gap_analysis.output if gap_analysis.success else None
        state["context"]["risk_tools_used"] = ["Regulatory Risk Assessment", "Compliance Gap Analysis", "Web Research"]
        
        return state

    def _identify_risks_from_context(
        self,
        task: str,
        compliance_analysis: str,
        legal_analysis: str,
    ) -> List[Dict[str, Any]]:
        """Extract and structure risks from context."""
        # This is a simplified version - in production, use NLP to extract risks
        risks = [
            {
                "id": "RISK-001",
                "name": "Não conformidade com regulamentações",
                "probability": 3,
                "impact": 4,
                "category": "Regulatório",
            },
            {
                "id": "RISK-002",
                "name": "Mudanças na legislação",
                "probability": 4,
                "impact": 3,
                "category": "Legal",
            },
            {
                "id": "RISK-003",
                "name": "Falha em auditorias",
                "probability": 2,
                "impact": 5,
                "category": "Operacional",
            },
            {
                "id": "RISK-004",
                "name": "Sanções e multas",
                "probability": 2,
                "impact": 4,
                "category": "Financeiro",
            },
            {
                "id": "RISK-005",
                "name": "Danos à reputação",
                "probability": 2,
                "impact": 5,
                "category": "Reputacional",
            },
        ]
        
        return risks


class DocumentReviewAgent(BaseAgent):
    """Agent specialized in document review and generation."""

    def __init__(self, memory: Memory, logger: Optional[AgentLogger] = None):
        """Initialize document review agent."""
        config = AgentConfig(
            name="document_review_agent",
            description="Especialista em revisão e geração de documentos regulatórios",
            model="gpt-4.1",
            temperature=0.1,
            tools=[DocumentGeneratorTool()],
            system_prompt="""Você é um especialista em documentação regulatória do Grupo Soluto.
Sua especialidade inclui:
- Revisão de documentos técnicos e regulatórios
- Elaboração de relatórios de conformidade
- Criação de políticas e procedimentos
- Documentação para auditorias e inspeções
- Templates e padrões documentais
- Gestão de documentos regulatórios

Sempre garanta clareza, precisão, completude e conformidade com padrões regulatórios. 
Estruture documentos de forma profissional e inclua todos os elementos obrigatórios.""",
        )
        super().__init__(config, memory, logger)

    async def process(self, state: AgentState) -> AgentState:
        """Process document review and generation."""
        self.logger.log_action("starting_document_review", {"task": state["task"]})
        
        # Compile information from all analyses
        context = state["context"]
        
        # Generate comprehensive executive report
        report_prompt = f"""
Com base em todas as análises realizadas para a tarefa: {state['task']}

Informações disponíveis:
- Análise de Conformidade: {'Sim' if context.get('compliance_analysis') else 'Não'}
- Análise Jurídica: {'Sim' if context.get('legal_analysis') else 'Não'}
- Avaliação de Riscos: {'Sim' if context.get('risk_assessment') else 'Não'}
- Pesquisa: {'Sim' if context.get('research_findings') else 'Não'}

Crie um relatório executivo profissional e completo seguindo esta estrutura:

# RELATÓRIO EXECUTIVO - ANÁLISE REGULATÓRIA

## SUMÁRIO EXECUTIVO
[Resumo conciso de 3-5 parágrafos com os principais achados e recomendações]

## 1. OBJETIVO E ESCOPO
[Descreva claramente o objetivo desta análise e seu escopo]

## 2. METODOLOGIA
[Explique a abordagem utilizada e as ferramentas aplicadas]

## 3. ANÁLISE DE CONFORMIDADE REGULATÓRIA
### 3.1 Regulamentações Aplicáveis
[Liste e descreva todas as normas relevantes]

### 3.2 Status de Conformidade
[Avalie o nível atual de conformidade]

### 3.3 Gaps Identificados
[Detalhe lacunas e não conformidades]

## 4. ANÁLISE JURÍDICA
### 4.1 Marco Legal
[Apresente a base legal aplicável]

### 4.2 Interpretação e Aplicação
[Análise da aplicação ao caso concreto]

### 4.3 Riscos Jurídicos
[Identifique exposições legais]

## 5. AVALIAÇÃO DE RISCOS
### 5.1 Matriz de Riscos
[Apresente os riscos identificados e classificados]

### 5.2 Análise de Impacto
[Detalhe impactos potenciais]

### 5.3 Plano de Mitigação
[Estratégias de mitigação propostas]

## 6. RECOMENDAÇÕES ESTRATÉGICAS
### 6.1 Ações Imediatas (0-30 dias)
[Liste ações prioritárias]

### 6.2 Ações de Curto Prazo (30-90 dias)
[Ações de implementação rápida]

### 6.3 Ações de Médio/Longo Prazo (>90 dias)
[Iniciativas estratégicas]

## 7. PLANO DE IMPLEMENTAÇÃO
### 7.1 Cronograma
[Timeline detalhado]

### 7.2 Responsabilidades
[Matriz RACI]

### 7.3 Recursos Necessários
[Pessoas, tempo, orçamento]

### 7.4 Indicadores de Sucesso
[KPIs para monitoramento]

## 8. CONCLUSÃO
[Síntese final e considerações importantes]

## ANEXOS
- Checklist de Conformidade
- Documentos de Referência
- Contatos Relevantes

---
Documento preparado por: Sistema Multiagente Regulatório - Grupo Soluto
Data: {datetime.now().strftime('%d/%m/%Y')}
Classificação: Confidencial
"""
        
        response = await self.llm.ainvoke([
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": report_prompt},
        ])
        
        # Generate final documents in multiple formats
        doc_tool = self.config.tools[0]
        
        # Generate PDF executive report
        pdf_report = await self.use_tool(
            doc_tool,
            content=response.content,
            format="pdf",
            title=f"Relatório Executivo - {state['task'][:50]}",
            metadata={
                "tipo": "Relatório Executivo",
                "data": datetime.now().isoformat(),
                "sistema": "Sistema Multiagente Regulatório",
                "versão": "1.0",
                "classificação": "Confidencial",
                "empresa": "Grupo Soluto",
            },
        )
        
        # Generate HTML version for web viewing
        html_report = await self.use_tool(
            doc_tool,
            content=response.content,
            format="html",
            title=f"Relatório Regulatório - {state['task'][:50]}",
        )
        
        # Generate TXT summary
        summary_content = f"""
RESUMO EXECUTIVO - {state['task']}
{'=' * 60}

Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}
Sistema: Multiagente Regulatório Soluto

PRINCIPAIS CONCLUSÕES:
{self._extract_key_points(response.content)}

RECOMENDAÇÕES CRÍTICAS:
{self._extract_recommendations(response.content)}

PRÓXIMOS PASSOS:
{self._extract_next_steps(response.content)}

---
Documento completo disponível em PDF e HTML
"""
        
        txt_summary = await self.use_tool(
            doc_tool,
            content=summary_content,
            format="txt",
            title="Resumo Executivo",
        )
        
        # Store in memory
        memory_id = await self.memory.remember(
            content=f"Relatório Final: {response.content[:1000]}...",
            agent_id=self.config.name,
            memory_type=MemoryType.LONG_TERM,
            thread_id=state.get("thread_id"),
            tags=["report", "executive", "final"],
        )
        
        # Update state
        state["messages"].append(AIMessage(content=response.content))
        state["memory_entries"].append(memory_id)
        state["context"]["final_report"] = response.content
        state["context"]["documents"] = {
            "pdf": pdf_report.output if pdf_report.success else None,
            "html": html_report.output if html_report.success else None,
            "txt": txt_summary.output if txt_summary.success else None,
        }
        
        return state

    def _extract_key_points(self, content: str) -> str:
        """Extract key points from content."""
        # Simplified extraction - in production use NLP
        lines = content.split('\n')
        key_points = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['principal', 'importante', 'crítico', 'essencial']):
                key_points.append(f"• {line.strip()}")
        return '\n'.join(key_points[:5]) if key_points else "• Análise completa disponível no relatório"

    def _extract_recommendations(self, content: str) -> str:
        """Extract recommendations from content."""
        lines = content.split('\n')
        recommendations = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['recomenda', 'sugere', 'deve', 'necessário']):
                recommendations.append(f"• {line.strip()}")
        return '\n'.join(recommendations[:5]) if recommendations else "• Ver seção de recomendações no relatório"

    def _extract_next_steps(self, content: str) -> str:
        """Extract next steps from content."""
        lines = content.split('\n')
        next_steps = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['próximo', 'passo', 'ação', 'implementar']):
                next_steps.append(f"• {line.strip()}")
        return '\n'.join(next_steps[:5]) if next_steps else "• Consultar plano de implementação no relatório"


class ResearchAgent(BaseAgent):
    """Agent specialized in research and information gathering with custom tools."""

    def __init__(self, memory: Memory, logger: Optional[AgentLogger] = None):
        """Initialize research agent with specialized tools."""
        config = AgentConfig(
            name="research_agent",
            description="Especialista em pesquisa e inteligência regulatória",
            model="gpt-4.1-mini",  # Using mini model for cost efficiency in research
            temperature=0.3,
            tools=[
                RealWebResearchTool(),
                CompetitiveIntelligenceTool(),
                TrendAnalysisTool(),
                WebSearchTool(),
                BrowserTool(),
            ],
            system_prompt="""Você é um especialista em pesquisa e inteligência regulatória do Grupo Soluto.
Sua especialidade inclui:
- Monitoramento de mudanças regulatórias
- Pesquisa aprofundada de informações
- Benchmarking e melhores práticas
- Inteligência competitiva regulatória
- Análise de tendências do setor
- Identificação de oportunidades estratégicas

Você tem acesso a ferramentas especializadas:
- RealWebResearchTool: Pesquisa web em fontes oficiais (DOU, gov.br, JusBrasil)
- CompetitiveIntelligenceTool: Análise de mercado e inteligência competitiva
- TrendAnalysisTool: Análise de tendências regulatórias

Sempre forneça informações verificadas, cite fontes confiáveis e identifique tendências e oportunidades relevantes.""",
        )
        super().__init__(config, memory, logger)

    async def process(self, state: AgentState) -> AgentState:
        """Process research tasks with specialized tools."""
        self.logger.log_action("starting_research", {"task": state["task"]})
        
        # Perform real web research
        research_tool = self.config.tools[0]  # RealWebResearchTool
        research_results = await self.use_tool(
            research_tool,
            query=state["task"],
            fontes=["dou", "gov_br", "jusbrasil", "scholar"],
            limite_resultados=20,
        )
        
        # Perform competitive intelligence
        intelligence_tool = self.config.tools[1]  # CompetitiveIntelligenceTool
        intelligence_results = await self.use_tool(
            intelligence_tool,
            setor="consultoria_regulatoria",
            foco_analise="compliance_trends",
            incluir_benchmarking=True,
        )
        
        # Analyze regulatory trends
        trend_tool = self.config.tools[2]  # TrendAnalysisTool
        trend_analysis = await self.use_tool(
            trend_tool,
            area_foco="regulamentacao_brasileira",
            periodo_analise="12_meses",
            incluir_previsoes=True,
        )
        
        # Comprehensive research synthesis
        synthesis_prompt = f"""
Tarefa de pesquisa: {state['task']}

Pesquisa Web Real:
{research_results.output if research_results.success else 'Pesquisa em andamento'}

Inteligência Competitiva:
{intelligence_results.output if intelligence_results.success else 'Análise de mercado em progresso'}

Análise de Tendências:
{trend_analysis.output if trend_analysis.success else 'Análise de tendências em andamento'}

Com base na pesquisa realizada, crie uma síntese abrangente incluindo:

1. **Contexto Regulatório Atual**
   - Principais desenvolvimentos recentes
   - Mudanças regulatórias em vigor
   - Tendências identificadas

2. **Análise de Mercado**
   - Panorama do setor
   - Práticas de mercado
   - Posicionamento competitivo

3. **Benchmarking Detalhado**
   - Melhores práticas identificadas
   - Gaps em relação aos líderes
   - Oportunidades de melhoria

4. **Inteligência Estratégica**
   - Movimentos dos concorrentes
   - Oportunidades regulatórias
   - Ameaças emergentes

5. **Casos de Sucesso**
   - Exemplos relevantes do mercado
   - Lições aprendidas
   - Aplicabilidade ao Grupo Soluto

6. **Tendências e Previsões**
   - Direção do mercado
   - Mudanças regulatórias esperadas
   - Preparação necessária

7. **Recomendações Baseadas em Evidências**
   - Ações sugeridas com base nos dados
   - Priorização estratégica
   - ROI esperado

8. **Fontes e Referências**
   - Liste todas as fontes consultadas
   - Indique confiabilidade
   - Sugira fontes adicionais
"""
        
        response = await self.llm.ainvoke([
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": synthesis_prompt},
        ])
        
        # Store research findings
        memory_id = await self.memory.remember(
            content=f"Pesquisa e Inteligência: {response.content}",
            agent_id=self.config.name,
            memory_type=MemoryType.LONG_TERM,
            thread_id=state.get("thread_id"),
            tags=["research", "intelligence", "benchmarking", "trends"],
        )
        
        # Update state
        state["messages"].append(AIMessage(content=response.content))
        state["memory_entries"].append(memory_id)
        state["context"]["research_findings"] = response.content
        state["context"]["research_tools_used"] = ["Real Web Research", "Competitive Intelligence", "Trend Analysis"]
        state["context"]["research_data"] = {
            "research_results_count": research_results.output.get("total_resultados", 0) if research_results.success else 0,
            "competitive_insights": len(intelligence_results.output.get("insights", [])) if intelligence_results.success else 0,
            "trends_identified": len(trend_analysis.output.get("tendencias", [])) if trend_analysis.success else 0,
        }
        
        return state

    def _extract_topics_from_task(self, task: str) -> List[str]:
        """Extract relevant topics from task description."""
        # Simplified extraction - in production use NLP
        topics = ["regulamentação", "compliance", "ANVISA"]
        
        keywords_map = {
            "medicamento": ["farmacêutico", "ANVISA", "RDC"],
            "dispositivo": ["dispositivo médico", "ANVISA", "certificação"],
            "telecom": ["ANATEL", "telecomunicações", "homologação"],
            "dados": ["LGPD", "proteção de dados", "ANPD"],
        }
        
        for keyword, related in keywords_map.items():
            if keyword in task.lower():
                topics.extend(related)
                
        return list(set(topics))

    def _identify_relevant_industries(self, task: str) -> List[str]:
        """Identify relevant industries from task."""
        industries = []
        
        industry_keywords = {
            "pharmaceutical": ["medicamento", "farmac", "drug"],
            "medical_devices": ["dispositivo", "equipment", "medical device"],
            "telecom": ["telecom", "anatel", "comunicação"],
            "technology": ["software", "tecnologia", "digital"],
        }
        
        task_lower = task.lower()
        for industry, keywords in industry_keywords.items():
            if any(keyword in task_lower for keyword in keywords):
                industries.append(industry)
                
        return industries if industries else ["pharmaceutical", "medical_devices"]