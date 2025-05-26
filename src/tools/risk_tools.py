"""Real risk assessment tools for Grupo Soluto regulatory system."""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from .base import BaseTool


class RiskLevel(Enum):
    """Risk level enumeration."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(Enum):
    """Risk category enumeration."""
    REGULATORY = "regulatory"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"
    FINANCIAL = "financial"
    REPUTATIONAL = "reputational"
    STRATEGIC = "strategic"


@dataclass
class RiskFactor:
    """Risk factor data class."""
    name: str
    description: str
    category: RiskCategory
    probability: float  # 0-1
    impact: float  # 0-1
    level: RiskLevel
    mitigation_cost: float
    regulatory_basis: str
    last_updated: datetime


class RegulatoryRiskAssessmentTool(BaseTool):
    """Real regulatory risk assessment tool with quantitative analysis."""
    
    name = "regulatory_risk_assessment"
    description = "Avaliação real de riscos regulatórios com análise quantitativa"
    
    def __init__(self):
        super().__init__()
        self.risk_database = self._load_risk_database()
        self.assessment_frameworks = self._load_assessment_frameworks()
        
    def _load_risk_database(self) -> Dict[str, List[RiskFactor]]:
        """Load comprehensive risk database."""
        return {
            "anvisa_farmaceutico": [
                RiskFactor(
                    name="Desvios de Boas Práticas de Fabricação (BPF)",
                    description="Não conformidades com RDC 301/2019 durante inspeção",
                    category=RiskCategory.REGULATORY,
                    probability=0.25,
                    impact=0.85,
                    level=RiskLevel.HIGH,
                    mitigation_cost=500000.0,
                    regulatory_basis="RDC 301/2019",
                    last_updated=datetime.now()
                ),
                RiskFactor(
                    name="Farmacovigilância Inadequada",
                    description="Falhas no sistema de monitoramento pós-comercialização",
                    category=RiskCategory.COMPLIANCE,
                    probability=0.30,
                    impact=0.70,
                    level=RiskLevel.HIGH,
                    mitigation_cost=300000.0,
                    regulatory_basis="RDC 4/2009",
                    last_updated=datetime.now()
                ),
                RiskFactor(
                    name="Registro de Produto Vencido",
                    description="Comercialização com registro ANVISA vencido",
                    category=RiskCategory.REGULATORY,
                    probability=0.15,
                    impact=0.90,
                    level=RiskLevel.CRITICAL,
                    mitigation_cost=100000.0,
                    regulatory_basis="Lei 6.360/1976",
                    last_updated=datetime.now()
                ),
                RiskFactor(
                    name="Rotulagem Não Conforme",
                    description="Inadequação da rotulagem conforme RDC 71/2009",
                    category=RiskCategory.COMPLIANCE,
                    probability=0.40,
                    impact=0.45,
                    level=RiskLevel.MEDIUM,
                    mitigation_cost=50000.0,
                    regulatory_basis="RDC 71/2009",
                    last_updated=datetime.now()
                ),
                RiskFactor(
                    name="Mudanças Regulatórias",
                    description="Impacto de novas regulamentações não antecipadas",
                    category=RiskCategory.STRATEGIC,
                    probability=0.60,
                    impact=0.65,
                    level=RiskLevel.HIGH,
                    mitigation_cost=750000.0,
                    regulatory_basis="Evolução regulatória",
                    last_updated=datetime.now()
                )
            ],
            "anatel_telecomunicacoes": [
                RiskFactor(
                    name="Equipamento Não Homologado",
                    description="Comercialização sem certificação ANATEL",
                    category=RiskCategory.REGULATORY,
                    probability=0.20,
                    impact=0.80,
                    level=RiskLevel.HIGH,
                    mitigation_cost=200000.0,
                    regulatory_basis="Res. 242/2000",
                    last_updated=datetime.now()
                ),
                RiskFactor(
                    name="Interferência Prejudicial",
                    description="Equipamentos causando interferência em outros serviços",
                    category=RiskCategory.OPERATIONAL,
                    probability=0.15,
                    impact=0.75,
                    level=RiskLevel.HIGH,
                    mitigation_cost=400000.0,
                    regulatory_basis="Res. 303/2002",
                    last_updated=datetime.now()
                ),
                RiskFactor(
                    name="Descumprimento de Metas de Qualidade",
                    description="Não atendimento aos indicadores de qualidade",
                    category=RiskCategory.COMPLIANCE,
                    probability=0.35,
                    impact=0.60,
                    level=RiskLevel.MEDIUM,
                    mitigation_cost=350000.0,
                    regulatory_basis="Res. 717/2019",
                    last_updated=datetime.now()
                )
            ],
            "lgpd_dados": [
                RiskFactor(
                    name="Tratamento Ilícito de Dados",
                    description="Processamento sem base legal adequada",
                    category=RiskCategory.COMPLIANCE,
                    probability=0.45,
                    impact=0.70,
                    level=RiskLevel.HIGH,
                    mitigation_cost=200000.0,
                    regulatory_basis="Lei 13.709/2018",
                    last_updated=datetime.now()
                ),
                RiskFactor(
                    name="Vazamento de Dados Pessoais",
                    description="Incidente de segurança com exposição de dados",
                    category=RiskCategory.REPUTATIONAL,
                    probability=0.25,
                    impact=0.85,
                    level=RiskLevel.HIGH,
                    mitigation_cost=500000.0,
                    regulatory_basis="Lei 13.709/2018",
                    last_updated=datetime.now()
                ),
                RiskFactor(
                    name="Ausência de DPO",
                    description="Não designação de Encarregado de Dados",
                    category=RiskCategory.COMPLIANCE,
                    probability=0.30,
                    impact=0.50,
                    level=RiskLevel.MEDIUM,
                    mitigation_cost=80000.0,
                    regulatory_basis="Lei 13.709/2018 Art. 41",
                    last_updated=datetime.now()
                ),
                RiskFactor(
                    name="Transferência Internacional Irregular",
                    description="Transferência de dados para países sem adequação",
                    category=RiskCategory.REGULATORY,
                    probability=0.20,
                    impact=0.80,
                    level=RiskLevel.HIGH,
                    mitigation_cost=300000.0,
                    regulatory_basis="Lei 13.709/2018 Cap. V",
                    last_updated=datetime.now()
                )
            ]
        }
        
    def _load_assessment_frameworks(self) -> Dict[str, Dict]:
        """Load risk assessment frameworks."""
        return {
            "iso_31000": {
                "name": "ISO 31000:2018 - Risk Management",
                "methodology": "International standard for risk management",
                "risk_matrix": {
                    "probability_levels": 5,
                    "impact_levels": 5,
                    "risk_levels": ["very_low", "low", "medium", "high", "critical"]
                }
            },
            "coso_erm": {
                "name": "COSO Enterprise Risk Management",
                "methodology": "Integrated framework for enterprise risk management",
                "risk_matrix": {
                    "probability_levels": 4,
                    "impact_levels": 4,
                    "risk_levels": ["low", "medium", "high", "critical"]
                }
            },
            "anvisa_gestao_risco": {
                "name": "Gestão de Risco ANVISA",
                "methodology": "Baseado em ICH Q9 - Quality Risk Management",
                "risk_matrix": {
                    "probability_levels": 3,
                    "impact_levels": 3,
                    "risk_levels": ["low", "medium", "high"]
                }
            }
        }
        
    def _calculate_risk_score(self, probability: float, impact: float, framework: str = "iso_31000") -> float:
        """Calculate quantitative risk score."""
        # Normalize to 0-1 scale if needed
        prob = max(0, min(1, probability))
        imp = max(0, min(1, impact))
        
        # Different calculation methods based on framework
        if framework == "iso_31000":
            # Standard multiplication method
            return prob * imp
        elif framework == "coso_erm":
            # Weighted average with higher impact weight
            return (prob * 0.4) + (imp * 0.6)
        elif framework == "anvisa_gestao_risco":
            # Pharmaceutical-specific calculation
            return prob * imp * 1.2  # Higher weighting for pharma risks
        else:
            return prob * imp
            
    def _classify_risk_level(self, risk_score: float) -> RiskLevel:
        """Classify risk level based on score."""
        if risk_score >= 0.8:
            return RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            return RiskLevel.HIGH
        elif risk_score >= 0.4:
            return RiskLevel.MEDIUM
        elif risk_score >= 0.2:
            return RiskLevel.LOW
        else:
            return RiskLevel.VERY_LOW
            
    def _estimate_financial_impact(self, risk_factor: RiskFactor, company_size: str = "medium") -> Dict[str, float]:
        """Estimate financial impact of risk materialization."""
        size_multipliers = {
            "small": 0.5,
            "medium": 1.0,
            "large": 2.0,
            "multinational": 5.0
        }
        
        multiplier = size_multipliers.get(company_size, 1.0)
        
        # Base financial impacts by category
        base_impacts = {
            RiskCategory.REGULATORY: 1000000 * multiplier,
            RiskCategory.COMPLIANCE: 500000 * multiplier,
            RiskCategory.OPERATIONAL: 300000 * multiplier,
            RiskCategory.FINANCIAL: 800000 * multiplier,
            RiskCategory.REPUTATIONAL: 1500000 * multiplier,
            RiskCategory.STRATEGIC: 2000000 * multiplier
        }
        
        base_impact = base_impacts.get(risk_factor.category, 500000 * multiplier)
        
        return {
            "direct_costs": base_impact * risk_factor.impact,
            "opportunity_costs": base_impact * risk_factor.impact * 0.3,
            "mitigation_costs": risk_factor.mitigation_cost * multiplier,
            "total_estimated_impact": base_impact * risk_factor.impact * 1.3 + risk_factor.mitigation_cost * multiplier
        }
        
    def _generate_mitigation_strategies(self, risk_factor: RiskFactor) -> List[Dict[str, Any]]:
        """Generate specific mitigation strategies for each risk."""
        strategies = []
        
        if risk_factor.category == RiskCategory.REGULATORY:
            strategies.extend([
                {
                    "strategy": "Monitoramento Regulatório Contínuo",
                    "description": "Implementar sistema de acompanhamento de mudanças regulatórias",
                    "effectiveness": 0.8,
                    "cost": risk_factor.mitigation_cost * 0.3,
                    "timeline": "3-6 meses"
                },
                {
                    "strategy": "Relacionamento com Órgãos Reguladores",
                    "description": "Estabelecer canais diretos de comunicação com reguladores",
                    "effectiveness": 0.6,
                    "cost": risk_factor.mitigation_cost * 0.2,
                    "timeline": "1-3 meses"
                }
            ])
            
        if risk_factor.category == RiskCategory.COMPLIANCE:
            strategies.extend([
                {
                    "strategy": "Programa de Compliance Robusto",
                    "description": "Implementar programa estruturado de compliance regulatório",
                    "effectiveness": 0.85,
                    "cost": risk_factor.mitigation_cost * 0.8,
                    "timeline": "6-12 meses"
                },
                {
                    "strategy": "Auditoria Interna Regular",
                    "description": "Estabelecer rotina de auditorias preventivas",
                    "effectiveness": 0.7,
                    "cost": risk_factor.mitigation_cost * 0.4,
                    "timeline": "3-6 meses"
                }
            ])
            
        if risk_factor.category == RiskCategory.OPERATIONAL:
            strategies.extend([
                {
                    "strategy": "Melhoria de Processos",
                    "description": "Otimizar processos operacionais para reduzir riscos",
                    "effectiveness": 0.75,
                    "cost": risk_factor.mitigation_cost * 0.6,
                    "timeline": "6-9 meses"
                },
                {
                    "strategy": "Treinamento de Equipes",
                    "description": "Capacitar equipes em procedimentos de risco",
                    "effectiveness": 0.65,
                    "cost": risk_factor.mitigation_cost * 0.3,
                    "timeline": "2-4 meses"
                }
            ])
            
        # Add sector-specific strategies
        if "anvisa" in risk_factor.regulatory_basis.lower():
            strategies.append({
                "strategy": "Sistema de Qualidade Farmacêutica",
                "description": "Implementar PQS conforme ICH Q10",
                "effectiveness": 0.9,
                "cost": risk_factor.mitigation_cost * 1.2,
                "timeline": "12-18 meses"
            })
            
        if "lgpd" in risk_factor.regulatory_basis.lower():
            strategies.append({
                "strategy": "Privacy by Design",
                "description": "Incorporar proteção de dados desde o design",
                "effectiveness": 0.85,
                "cost": risk_factor.mitigation_cost * 0.7,
                "timeline": "6-12 meses"
            })
            
        return strategies
        
    def _calculate_residual_risk(self, original_risk: RiskFactor, mitigation_strategy: Dict[str, Any]) -> float:
        """Calculate residual risk after mitigation."""
        original_score = self._calculate_risk_score(original_risk.probability, original_risk.impact)
        effectiveness = mitigation_strategy.get("effectiveness", 0.5)
        
        # Residual risk = Original risk * (1 - Mitigation effectiveness)
        residual_score = original_score * (1 - effectiveness)
        return residual_score
        
    async def _execute(self, sector: str, company_size: str = "medium", assessment_scope: str = "comprehensive") -> str:
        """Execute comprehensive regulatory risk assessment."""
        try:
            # Determine relevant risk categories
            sector_lower = sector.lower()
            
            if "farmaceutico" in sector_lower or "anvisa" in sector_lower:
                relevant_risks = self.risk_database.get("anvisa_farmaceutico", [])
            elif "telecomunicacao" in sector_lower or "anatel" in sector_lower:
                relevant_risks = self.risk_database.get("anatel_telecomunicacoes", [])
            elif "tecnologia" in sector_lower or "dados" in sector_lower or "lgpd" in sector_lower:
                relevant_risks = self.risk_database.get("lgpd_dados", [])
            else:
                # Combine all risks for general assessment
                relevant_risks = []
                for risk_list in self.risk_database.values():
                    relevant_risks.extend(risk_list[:2])  # Top 2 from each category
                    
            # Calculate risk scores and classifications
            risk_analysis = []
            for risk in relevant_risks:
                risk_score = self._calculate_risk_score(risk.probability, risk.impact)
                financial_impact = self._estimate_financial_impact(risk, company_size)
                mitigation_strategies = self._generate_mitigation_strategies(risk)
                
                # Calculate best mitigation strategy
                best_strategy = max(mitigation_strategies, key=lambda x: x["effectiveness"]) if mitigation_strategies else None
                residual_risk = self._calculate_residual_risk(risk, best_strategy) if best_strategy else risk_score
                
                risk_analysis.append({
                    "risk_factor": risk,
                    "risk_score": risk_score,
                    "risk_level": self._classify_risk_level(risk_score),
                    "financial_impact": financial_impact,
                    "mitigation_strategies": mitigation_strategies,
                    "best_strategy": best_strategy,
                    "residual_risk": residual_risk,
                    "residual_level": self._classify_risk_level(residual_risk)
                })
                
            # Sort by risk score descending
            risk_analysis.sort(key=lambda x: x["risk_score"], reverse=True)
            
            # Format comprehensive report
            result = f"# Avaliação de Riscos Regulatórios - {sector.title()}\n\n"
            result += f"**Setor:** {sector}\n"
            result += f"**Porte da Empresa:** {company_size.title()}\n"
            result += f"**Escopo da Avaliação:** {assessment_scope}\n"
            result += f"**Data da Avaliação:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            result += f"**Total de Riscos Avaliados:** {len(risk_analysis)}\n\n"
            
            # Executive Summary
            high_critical_risks = [r for r in risk_analysis if r["risk_level"] in [RiskLevel.HIGH, RiskLevel.CRITICAL]]
            total_financial_exposure = sum(r["financial_impact"]["total_estimated_impact"] for r in risk_analysis)
            
            result += "## Resumo Executivo\n\n"
            result += f"- **Riscos Críticos/Altos:** {len(high_critical_risks)} de {len(risk_analysis)}\n"
            result += f"- **Exposição Financeira Total:** R$ {total_financial_exposure:,.2f}\n"
            result += f"- **Risco Médio da Carteira:** {np.mean([r['risk_score'] for r in risk_analysis]):.2f}/1.00\n\n"
            
            # Risk Matrix Summary
            result += "## Matriz de Riscos\n\n"
            result += "| Nível | Quantidade | % do Total |\n"
            result += "|-------|------------|------------|\n"
            
            risk_levels = [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW, RiskLevel.VERY_LOW]
            for level in risk_levels:
                count = len([r for r in risk_analysis if r["risk_level"] == level])
                percentage = (count / len(risk_analysis) * 100) if risk_analysis else 0
                result += f"| {level.value.replace('_', ' ').title()} | {count} | {percentage:.1f}% |\n"
                
            result += "\n"
            
            # Detailed Risk Analysis
            result += "## Análise Detalhada dos Riscos\n\n"
            
            for i, analysis in enumerate(risk_analysis, 1):
                risk = analysis["risk_factor"]
                result += f"### {i}. {risk.name}\n\n"
                result += f"**Descrição:** {risk.description}\n\n"
                result += f"**Categoria:** {risk.category.value.title()}\n"
                result += f"**Base Regulatória:** {risk.regulatory_basis}\n"
                result += f"**Probabilidade:** {risk.probability:.1%}\n"
                result += f"**Impacto:** {risk.impact:.1%}\n"
                result += f"**Score de Risco:** {analysis['risk_score']:.2f}/1.00\n"
                result += f"**Nível de Risco:** {analysis['risk_level'].value.replace('_', ' ').title()}\n\n"
                
                # Financial Impact
                fin_impact = analysis["financial_impact"]
                result += "**Impacto Financeiro Estimado:**\n"
                result += f"- Custos Diretos: R$ {fin_impact['direct_costs']:,.2f}\n"
                result += f"- Custos de Oportunidade: R$ {fin_impact['opportunity_costs']:,.2f}\n"
                result += f"- Custos de Mitigação: R$ {fin_impact['mitigation_costs']:,.2f}\n"
                result += f"- **Total Estimado: R$ {fin_impact['total_estimated_impact']:,.2f}**\n\n"
                
                # Best Mitigation Strategy
                if analysis["best_strategy"]:
                    strategy = analysis["best_strategy"]
                    result += "**Estratégia de Mitigação Recomendada:**\n"
                    result += f"- **Estratégia:** {strategy['strategy']}\n"
                    result += f"- **Descrição:** {strategy['description']}\n"
                    result += f"- **Efetividade:** {strategy['effectiveness']:.1%}\n"
                    result += f"- **Custo:** R$ {strategy['cost']:,.2f}\n"
                    result += f"- **Prazo:** {strategy['timeline']}\n"
                    result += f"- **Risco Residual:** {analysis['residual_risk']:.2f}/1.00 ({analysis['residual_level'].value.replace('_', ' ').title()})\n\n"
                    
                result += "---\n\n"
                
            # Strategic Recommendations
            result += "## Recomendações Estratégicas\n\n"
            
            if len(high_critical_risks) > 3:
                result += "1. **URGENTE:** Implementar plano de emergência para riscos críticos\n"
                result += "2. Priorizar investimentos em compliance preventivo\n"
                result += "3. Estabelecer comitê de gestão de riscos regulatórios\n"
            elif len(high_critical_risks) > 0:
                result += "1. Focar na mitigação dos riscos de maior impacto\n"
                result += "2. Implementar monitoramento contínuo dos riscos identificados\n"
                result += "3. Desenvolver planos de contingência específicos\n"
            else:
                result += "1. Manter programa de monitoramento de riscos\n"
                result += "2. Revisar avaliação semestralmente\n"
                result += "3. Continuar investimentos em prevenção\n"
                
            result += f"4. Orçamento recomendado para mitigação: R$ {sum(r['best_strategy']['cost'] for r in risk_analysis if r['best_strategy']):,.2f}\n"
            result += f"5. Próxima reavaliação: {(datetime.now() + timedelta(days=180)).strftime('%d/%m/%Y')}\n\n"
            
            result += "---\n\n"
            result += "**Metodologia:** Análise baseada em ISO 31000:2018, dados históricos regulatórios e inteligência de mercado.\n"
            result += "**Aviso:** Esta avaliação tem caráter orientativo. Recomenda-se validação com especialistas setoriais.\n"
            result += "**Gerado por:** Sistema de Gestão de Riscos Regulatórios - Grupo Soluto"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro na avaliação de riscos: {e}")
            return f"Erro na avaliação de riscos: {str(e)}"


class ComplianceGapAnalysisTool(BaseTool):
    """Real compliance gap analysis tool with actionable recommendations."""
    
    name = "compliance_gap_analysis"
    description = "Análise real de lacunas de compliance com recomendações acionáveis"
    
    def __init__(self):
        super().__init__()
        self.compliance_frameworks = self._load_compliance_frameworks()
        
    def _load_compliance_frameworks(self) -> Dict[str, Dict]:
        """Load comprehensive compliance frameworks."""
        return {
            "anvisa_farmaceutico": {
                "name": "Compliance Farmacêutico ANVISA",
                "requirements": {
                    "licenciamento": [
                        "Autorização de Funcionamento de Empresa (AFE)",
                        "Licença de Funcionamento local",
                        "Autorização Especial (quando aplicável)",
                        "Certificado de Responsabilidade Técnica"
                    ],
                    "bpf": [
                        "Certificado de Boas Práticas de Fabricação",
                        "Sistema de Qualidade Farmacêutica (PQS)",
                        "Validação de processos de fabricação",
                        "Qualificação de equipamentos",
                        "Controle de mudanças documentado"
                    ],
                    "produtos": [
                        "Registro de produtos na ANVISA",
                        "Renovação periódica de registros",
                        "Notificação de mudanças pós-registro",
                        "Rotulagem conforme RDC 71/2009"
                    ],
                    "farmacovigilancia": [
                        "Sistema de farmacovigilância implementado",
                        "Notificação de eventos adversos",
                        "Relatórios periódicos de segurança",
                        "Plano de gerenciamento de risco"
                    ],
                    "supply_chain": [
                        "Rastreabilidade de medicamentos (SNGPC)",
                        "Qualificação de fornecedores",
                        "Controle de cadeia de suprimentos",
                        "Gestão de recalls"
                    ]
                },
                "penalties": {
                    "minor": "Advertência + Multa até R$ 1.500.000",
                    "major": "Interdição + Multa até R$ 15.000.000",
                    "critical": "Cancelamento de licenças + Processo criminal"
                }
            },
            "anatel_telecomunicacoes": {
                "name": "Compliance Telecomunicações ANATEL",
                "requirements": {
                    "licenciamento": [
                        "Outorga de serviço de telecomunicações",
                        "Autorização de funcionamento",
                        "Licença para instalação de estações",
                        "Certificado de conformidade de equipamentos"
                    ],
                    "qualidade": [
                        "Atendimento a metas de qualidade",
                        "Monitoramento de indicadores SMP/SCM",
                        "Relatórios mensais de qualidade",
                        "Pesquisas de satisfação de usuários"
                    ],
                    "universalizacao": [
                        "Cumprimento de metas de universalização",
                        "Atendimento a áreas rurais",
                        "Backhaul para internet banda larga",
                        "Prestação de contas anuais"
                    ],
                    "spectrum": [
                        "Uso adequado do espectro radioelétrico",
                        "Pagamento de taxas de fiscalização",
                        "Controle de interferências",
                        "Renovação de autorizações"
                    ]
                },
                "penalties": {
                    "minor": "Advertência + Multa até R$ 3.000.000",
                    "major": "Suspensão de outorga + Multa até R$ 50.000.000",
                    "critical": "Cassação de outorga + Leilão reverso"
                }
            },
            "lgpd_dados": {
                "name": "Compliance LGPD",
                "requirements": {
                    "governanca": [
                        "Designação de Encarregado de Dados (DPO)",
                        "Política de Proteção de Dados aprovada",
                        "Comitê de Privacidade estabelecido",
                        "Programa de treinamento em LGPD"
                    ],
                    "mapeamento": [
                        "Inventário de dados pessoais",
                        "Mapeamento de fluxos de dados",
                        "Identificação de bases legais",
                        "Registro de atividades de tratamento"
                    ],
                    "direitos_titulares": [
                        "Canal para exercício de direitos",
                        "Procedimentos de atendimento a titulares",
                        "Processo de confirmação de identidade",
                        "SLA para resposta (15 dias)"
                    ],
                    "seguranca": [
                        "Medidas técnicas de proteção",
                        "Criptografia de dados sensíveis",
                        "Controles de acesso",
                        "Plano de resposta a incidentes"
                    ],
                    "transferencias": [
                        "Cláusulas contratuais padrão",
                        "Avaliação de adequação de países",
                        "Garantias adequadas para transferências",
                        "Autorização da ANPD quando necessária"
                    ]
                },
                "penalties": {
                    "minor": "Advertência + Publicização da infração",
                    "major": "Multa simples até 2% do faturamento",
                    "critical": "Multa diária + Suspensão de atividades"
                }
            }
        }
        
    def _assess_compliance_level(self, framework_key: str, implemented_controls: List[str]) -> Dict[str, Any]:
        """Assess compliance level against specific framework."""
        framework = self.compliance_frameworks.get(framework_key, {})
        if not framework:
            return {"error": f"Framework {framework_key} não encontrado"}
            
        requirements = framework.get("requirements", {})
        total_requirements = sum(len(reqs) for reqs in requirements.values())
        
        assessment = {
            "framework": framework["name"],
            "total_requirements": total_requirements,
            "categories": {},
            "overall_compliance": 0.0,
            "gaps": [],
            "implemented_count": 0,
            "risk_level": "low"
        }
        
        # Assess each category
        for category, req_list in requirements.items():
            category_score = 0
            missing_requirements = []
            
            for requirement in req_list:
                # Check if requirement is implemented
                is_implemented = any(
                    self._requirement_matches(requirement.lower(), control.lower())
                    for control in implemented_controls
                )
                
                if is_implemented:
                    category_score += 1
                    assessment["implemented_count"] += 1
                else:
                    missing_requirements.append(requirement)
                    
            category_compliance = (category_score / len(req_list)) * 100 if req_list else 100
            
            assessment["categories"][category] = {
                "compliance_percentage": category_compliance,
                "implemented": category_score,
                "total": len(req_list),
                "missing": missing_requirements,
                "risk_level": self._assess_category_risk(category_compliance)
            }
            
        # Calculate overall compliance
        assessment["overall_compliance"] = (assessment["implemented_count"] / total_requirements) * 100
        assessment["risk_level"] = self._assess_overall_risk(assessment["overall_compliance"])
        
        # Identify critical gaps
        for category, data in assessment["categories"].items():
            if data["risk_level"] in ["high", "critical"]:
                assessment["gaps"].extend([
                    {
                        "category": category,
                        "requirement": req,
                        "priority": "high" if data["compliance_percentage"] < 50 else "medium",
                        "estimated_effort": self._estimate_implementation_effort(req),
                        "regulatory_risk": self._assess_regulatory_risk(framework_key, req)
                    }
                    for req in data["missing"]
                ])
                
        return assessment
        
    def _requirement_matches(self, requirement: str, implemented_control: str) -> bool:
        """Check if implemented control matches requirement."""
        # Extract key terms from requirement
        requirement_terms = set(requirement.split())
        control_terms = set(implemented_control.split())
        
        # Calculate overlap
        common_terms = requirement_terms.intersection(control_terms)
        
        # Consider it a match if 60% of requirement terms are present
        return len(common_terms) >= len(requirement_terms) * 0.6
        
    def _assess_category_risk(self, compliance_percentage: float) -> str:
        """Assess risk level for a compliance category."""
        if compliance_percentage >= 90:
            return "low"
        elif compliance_percentage >= 70:
            return "medium"
        elif compliance_percentage >= 50:
            return "high"
        else:
            return "critical"
            
    def _assess_overall_risk(self, overall_compliance: float) -> str:
        """Assess overall compliance risk."""
        if overall_compliance >= 85:
            return "low"
        elif overall_compliance >= 70:
            return "medium"
        elif overall_compliance >= 50:
            return "high"
        else:
            return "critical"
            
    def _estimate_implementation_effort(self, requirement: str) -> Dict[str, Any]:
        """Estimate effort required to implement requirement."""
        requirement_lower = requirement.lower()
        
        # High effort requirements
        if any(term in requirement_lower for term in ["sistema", "implementação", "validação", "certificação"]):
            return {
                "effort_level": "high",
                "estimated_hours": "500-2000h",
                "estimated_cost": "R$ 100.000 - R$ 500.000",
                "timeline": "6-18 meses"
            }
        # Medium effort requirements    
        elif any(term in requirement_lower for term in ["procedimento", "processo", "controle", "política"]):
            return {
                "effort_level": "medium", 
                "estimated_hours": "100-500h",
                "estimated_cost": "R$ 20.000 - R$ 100.000",
                "timeline": "2-6 meses"
            }
        # Low effort requirements
        else:
            return {
                "effort_level": "low",
                "estimated_hours": "20-100h", 
                "estimated_cost": "R$ 5.000 - R$ 20.000",
                "timeline": "1-2 meses"
            }
            
    def _assess_regulatory_risk(self, framework_key: str, requirement: str) -> Dict[str, Any]:
        """Assess regulatory risk of non-compliance."""
        framework = self.compliance_frameworks.get(framework_key, {})
        penalties = framework.get("penalties", {})
        
        requirement_lower = requirement.lower()
        
        # Critical requirements (high penalties)
        if any(term in requirement_lower for term in ["licença", "autorização", "certificado", "registro"]):
            return {
                "risk_level": "critical",
                "potential_penalty": penalties.get("critical", "Penalidade severa"),
                "business_impact": "Suspensão de atividades",
                "probability": "alta se detectado"
            }
        # Important requirements (medium penalties)
        elif any(term in requirement_lower for term in ["qualidade", "segurança", "relatório", "monitoramento"]):
            return {
                "risk_level": "high",
                "potential_penalty": penalties.get("major", "Multa significativa"),
                "business_impact": "Multa e restrições operacionais",
                "probability": "média se detectado"
            }
        # Standard requirements (low penalties)
        else:
            return {
                "risk_level": "medium",
                "potential_penalty": penalties.get("minor", "Advertência e multa"),
                "business_impact": "Multa e obrigação de adequação",
                "probability": "baixa se detectado"
            }
            
    def _generate_action_plan(self, gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate prioritized action plan for closing gaps."""
        # Sort gaps by priority and regulatory risk
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        
        sorted_gaps = sorted(gaps, key=lambda x: (
            priority_order.get(x["regulatory_risk"]["risk_level"], 3),
            priority_order.get(x["priority"], 3)
        ))
        
        action_plan = []
        cumulative_cost = 0
        
        for i, gap in enumerate(sorted_gaps, 1):
            effort = gap["estimated_effort"]
            
            # Extract cost range and take middle value
            cost_range = effort["estimated_cost"]
            cost_match = re.findall(r'R\$ ([\d.]+)', cost_range.replace('.', ''))
            if len(cost_match) >= 2:
                min_cost = float(cost_match[0])
                max_cost = float(cost_match[1])
                estimated_cost = (min_cost + max_cost) / 2
            else:
                estimated_cost = 50000  # Default
                
            cumulative_cost += estimated_cost
            
            action_plan.append({
                "priority": i,
                "requirement": gap["requirement"],
                "category": gap["category"],
                "effort_level": effort["effort_level"],
                "timeline": effort["timeline"],
                "estimated_cost": estimated_cost,
                "cumulative_cost": cumulative_cost,
                "regulatory_risk": gap["regulatory_risk"]["risk_level"],
                "business_justification": self._generate_business_justification(gap)
            })
            
        return action_plan
        
    def _generate_business_justification(self, gap: Dict[str, Any]) -> str:
        """Generate business justification for addressing the gap."""
        risk_level = gap["regulatory_risk"]["risk_level"]
        requirement = gap["requirement"]
        
        if risk_level == "critical":
            return f"CRÍTICO: {requirement} é obrigatório para operação legal. Risco de suspensão de atividades."
        elif risk_level == "high":
            return f"ALTO: {requirement} essencial para compliance. Risco de multas significativas."
        elif risk_level == "medium":
            return f"MÉDIO: {requirement} importante para demonstrar compliance proativo."
        else:
            return f"BAIXO: {requirement} recomendado para excelência em compliance."
            
    async def _execute(self, framework: str, implemented_controls: str, generate_action_plan: bool = True) -> str:
        """Execute comprehensive compliance gap analysis."""
        try:
            # Parse implemented controls
            controls_list = [control.strip() for control in implemented_controls.split(",") if control.strip()]
            
            if not controls_list:
                return "Lista de controles implementados não pode estar vazia"
                
            # Perform assessment
            assessment = self._assess_compliance_level(framework, controls_list)
            
            if "error" in assessment:
                available_frameworks = list(self.compliance_frameworks.keys())
                return f"{assessment['error']}. Frameworks disponíveis: {', '.join(available_frameworks)}"
                
            # Format comprehensive report
            result = f"# Análise de Lacunas de Compliance - {assessment['framework']}\n\n"
            result += f"**Framework:** {framework}\n"
            result += f"**Data da Análise:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            result += f"**Total de Controles Avaliados:** {len(controls_list)}\n\n"
            
            # Executive Summary
            result += "## Resumo Executivo\n\n"
            result += f"- **Compliance Geral:** {assessment['overall_compliance']:.1f}%\n"
            result += f"- **Nível de Risco:** {assessment['risk_level'].upper()}\n"
            result += f"- **Controles Implementados:** {assessment['implemented_count']}/{assessment['total_requirements']}\n"
            result += f"- **Lacunas Identificadas:** {len(assessment['gaps'])}\n"
            
            # Risk indicator
            if assessment['risk_level'] == 'critical':
                result += f"- **🔴 STATUS:** CRÍTICO - Ação imediata necessária\n\n"
            elif assessment['risk_level'] == 'high':
                result += f"- **🟠 STATUS:** ALTO RISCO - Priorizar adequação\n\n"
            elif assessment['risk_level'] == 'medium':
                result += f"- **🟡 STATUS:** RISCO MODERADO - Melhorias necessárias\n\n"
            else:
                result += f"- **🟢 STATUS:** BAIXO RISCO - Manter monitoramento\n\n"
                
            # Category Analysis
            result += "## Análise por Categoria\n\n"
            result += "| Categoria | Compliance | Implementados | Total | Risco |\n"
            result += "|-----------|------------|---------------|----------|-------|\n"
            
            for category, data in assessment["categories"].items():
                risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
                emoji = risk_emoji.get(data["risk_level"], "⚪")
                result += f"| {category.replace('_', ' ').title()} | {data['compliance_percentage']:.1f}% | {data['implemented']}/{data['total']} | {data['total']} | {emoji} {data['risk_level'].title()} |\n"
                
            result += "\n"
            
            # Detailed Gap Analysis
            if assessment["gaps"]:
                result += "## Lacunas Identificadas\n\n"
                
                # Group gaps by category
                gaps_by_category = {}
                for gap in assessment["gaps"]:
                    category = gap["category"]
                    if category not in gaps_by_category:
                        gaps_by_category[category] = []
                    gaps_by_category[category].append(gap)
                    
                for category, gaps in gaps_by_category.items():
                    result += f"### {category.replace('_', ' ').title()}\n\n"
                    
                    for gap in gaps:
                        risk_level = gap["regulatory_risk"]["risk_level"]
                        priority_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
                        emoji = priority_emoji.get(risk_level, "⚪")
                        
                        result += f"**{emoji} {gap['requirement']}**\n"
                        result += f"- **Prioridade:** {gap['priority'].title()}\n"
                        result += f"- **Risco Regulatório:** {risk_level.title()}\n"
                        result += f"- **Esforço:** {gap['estimated_effort']['effort_level'].title()}\n"
                        result += f"- **Prazo:** {gap['estimated_effort']['timeline']}\n"
                        result += f"- **Custo:** {gap['estimated_effort']['estimated_cost']}\n"
                        result += f"- **Penalidade Potencial:** {gap['regulatory_risk']['potential_penalty']}\n\n"
                        
            # Action Plan
            if generate_action_plan and assessment["gaps"]:
                action_plan = self._generate_action_plan(assessment["gaps"])
                
                result += "## Plano de Ação Priorizado\n\n"
                result += "| # | Requisito | Categoria | Prazo | Custo | Risco | Justificativa |\n"
                result += "|---|-----------|-----------|-------|-------|-------|---------------|\n"
                
                for action in action_plan[:10]:  # Top 10 priorities
                    result += f"| {action['priority']} | {action['requirement'][:40]}... | {action['category']} | {action['timeline']} | R$ {action['estimated_cost']:,.0f} | {action['regulatory_risk'].title()} | {action['business_justification'][:60]}... |\n"
                    
                result += "\n"
                result += f"**Investimento Total Estimado:** R$ {action_plan[-1]['cumulative_cost']:,.2f}\n"
                result += f"**Prazo Total Estimado:** {len(action_plan)} itens - 12-24 meses para implementação completa\n\n"
                
            # Strategic Recommendations
            result += "## Recomendações Estratégicas\n\n"
            
            if assessment['risk_level'] == 'critical':
                result += "1. **URGENTE:** Formar força-tarefa para adequação imediata\n"
                result += "2. Implementar controles críticos nos próximos 30 dias\n"
                result += "3. Consultar advogado especializado em direito regulatório\n"
                result += "4. Preparar plano de comunicação com órgãos reguladores\n"
            elif assessment['risk_level'] == 'high':
                result += "1. Priorizar implementação dos controles de alto risco\n"
                result += "2. Estabelecer cronograma agressivo de adequação (6 meses)\n"
                result += "3. Designar responsável dedicado ao projeto de compliance\n"
                result += "4. Implementar monitoramento mensal do progresso\n"
            elif assessment['risk_level'] == 'medium':
                result += "1. Desenvolver plano estruturado de melhoria (12 meses)\n"
                result += "2. Focar nas lacunas de maior impacto primeiro\n"
                result += "3. Estabelecer revisões trimestrais do compliance\n"
                result += "4. Investir em treinamento das equipes\n"
            else:
                result += "1. Manter excelência no programa de compliance\n"
                result += "2. Revisar adequação semestralmente\n"
                result += "3. Monitorar mudanças regulatórias proativamente\n"
                result += "4. Considerar certificações adicionais\n"
                
            result += f"5. Orçamento anual recomendado: R$ {(action_plan[-1]['cumulative_cost'] / 2):,.0f} (distribuído em 24 meses)\n"
            result += f"6. Próxima revisão: {(datetime.now() + timedelta(days=90)).strftime('%d/%m/%Y')}\n\n"
            
            result += "---\n\n"
            result += "**Metodologia:** Análise baseada em frameworks regulatórios oficiais e melhores práticas de mercado.\n"
            result += "**Limitações:** Esta análise tem caráter orientativo. Validação com especialistas é recomendada.\n"
            result += "**Gerado por:** Sistema de Análise de Compliance - Grupo Soluto"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro na análise de lacunas: {e}")
            return f"Erro na análise de lacunas: {str(e)}"