"""Real legal analysis tools for Grupo Soluto regulatory system."""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin

import aiohttp
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from .base import BaseTool


class BrazilianLegalDatabase(BaseModel):
    """Database of Brazilian legal sources and courts."""
    
    sources: Dict[str, Dict[str, Any]] = Field(default_factory=lambda: {
        "stf": {
            "name": "Supremo Tribunal Federal",
            "base_url": "https://portal.stf.jus.br",
            "search_endpoint": "/jurisprudencia/pesquisar",
            "areas": ["constitucional", "administrativo", "tributario"]
        },
        "stj": {
            "name": "Superior Tribunal de Justiça",
            "base_url": "https://www.stj.jus.br",
            "search_endpoint": "/sites/portalp/Paginas/Jurisprudencia/pesquisa-jurisprudencia.aspx",
            "areas": ["civil", "penal", "administrativo", "tributario"]
        },
        "tst": {
            "name": "Tribunal Superior do Trabalho",
            "base_url": "https://www.tst.jus.br",
            "search_endpoint": "/jurisprudencia/pesquisa-jurisprudencia",
            "areas": ["trabalhista"]
        },
        "tcu": {
            "name": "Tribunal de Contas da União",
            "base_url": "https://www.tcu.gov.br",
            "search_endpoint": "/jurisprudencia/pesquisa",
            "areas": ["administrativo", "financeiro", "orcamentario"]
        },
        "cjf": {
            "name": "Conselho da Justiça Federal",
            "base_url": "https://www.cjf.jus.br",
            "search_endpoint": "/jurisprudencia/unificada",
            "areas": ["federal", "previdenciario", "tributario"]
        }
    })


class RealJurisprudenceSearchTool(BaseTool):
    """Real jurisprudence search tool with actual court integrations."""
    
    name = "jurisprudence_search"
    description = "Busca real de jurisprudência nos tribunais superiores brasileiros"
    
    def __init__(self):
        super().__init__()
        self.db = BrazilianLegalDatabase()
        self.session = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60),
                headers={
                    "User-Agent": "Grupo Soluto Legal Research/2.0",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
            )
        return self.session
        
    async def _search_stf(self, termo: str, area: str = None, limit: int = 10) -> List[Dict]:
        """Search STF jurisprudence."""
        session = await self._get_session()
        
        try:
            # STF search endpoint
            search_url = "https://portal.stf.jus.br/jurisprudencia/pesquisar"
            
            # Prepare search parameters
            params = {
                "termo": termo,
                "limite": limit,
                "ordenacao": "relevancia"
            }
            
            if area:
                params["area"] = area
                
            async with session.get(search_url, params=params) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_stf_results(html, termo)
                    
        except Exception as e:
            self.logger.error(f"Erro ao buscar STF: {e}")
            
        # Fallback to web scraping
        return await self._scrape_stf_jurisprudence(termo, limit)
        
    async def _scrape_stf_jurisprudence(self, termo: str, limit: int) -> List[Dict]:
        """Scrape STF website for jurisprudence."""
        session = await self._get_session()
        
        try:
            search_url = f"https://portal.stf.jus.br/jurisprudencia/pesquisar?termo={quote(termo)}"
            
            async with session.get(search_url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    results = []
                    jurisprudence_items = soup.find_all('div', class_=['resultado-jurisprudencia', 'item-jurisprudencia'])[:limit]
                    
                    for item in jurisprudence_items:
                        # Extract case information
                        processo_elem = item.find(['span', 'strong'], class_=['numero-processo', 'processo'])
                        relator_elem = item.find(['span'], text=re.compile(r'Rel\.?\s*Min\.?'))
                        ementa_elem = item.find(['div', 'p'], class_=['ementa', 'texto-ementa'])
                        data_elem = item.find(['span'], class_=['data-julgamento', 'data'])
                        
                        if processo_elem or ementa_elem:
                            results.append({
                                "processo": processo_elem.get_text(strip=True) if processo_elem else "N/A",
                                "relator": self._extract_relator(relator_elem.get_text() if relator_elem else ""),
                                "ementa": ementa_elem.get_text(strip=True)[:500] + "..." if ementa_elem else "N/A",
                                "data_julgamento": data_elem.get_text(strip=True) if data_elem else "N/A",
                                "tribunal": "STF",
                                "url": self._extract_case_url(item),
                                "relevancia": self._calculate_case_relevance(ementa_elem.get_text() if ementa_elem else "", termo)
                            })
                    
                    return results
                    
        except Exception as e:
            self.logger.error(f"Erro ao fazer scraping STF: {e}")
            
        return []
        
    def _parse_stf_results(self, html: str, termo: str) -> List[Dict]:
        """Parse STF search results."""
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Parse JSON results if available
        script_tags = soup.find_all('script', type='application/json')
        for script in script_tags:
            try:
                data = json.loads(script.string)
                if 'resultados' in data:
                    for item in data['resultados']:
                        results.append({
                            "processo": item.get('numeroProcesso', 'N/A'),
                            "relator": item.get('relator', 'N/A'),
                            "ementa": item.get('ementa', 'N/A')[:500] + "...",
                            "data_julgamento": item.get('dataJulgamento', 'N/A'),
                            "tribunal": "STF",
                            "url": item.get('url', 'N/A'),
                            "relevancia": self._calculate_case_relevance(item.get('ementa', ''), termo)
                        })
                    break
            except json.JSONDecodeError:
                continue
                
        return results
        
    async def _search_stj(self, termo: str, area: str = None, limit: int = 10) -> List[Dict]:
        """Search STJ jurisprudence."""
        session = await self._get_session()
        
        try:
            # STJ has a different search interface
            search_url = "https://www.stj.jus.br/sites/portalp/Paginas/Jurisprudencia/pesquisa-jurisprudencia.aspx"
            
            async with session.get(search_url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find search form and extract necessary parameters
                    form = soup.find('form', id=['frmPesquisa', 'form1'])
                    if form:
                        # Prepare POST data for search
                        form_data = {
                            '__VIEWSTATE': soup.find('input', {'name': '__VIEWSTATE'})['value'] if soup.find('input', {'name': '__VIEWSTATE'}) else '',
                            'txtPesquisaLivre': termo,
                            'btnPesquisar': 'Pesquisar'
                        }
                        
                        async with session.post(search_url, data=form_data) as search_response:
                            if search_response.status == 200:
                                search_html = await search_response.text()
                                return self._parse_stj_results(search_html, termo)
                                
        except Exception as e:
            self.logger.error(f"Erro ao buscar STJ: {e}")
            
        return []
        
    def _parse_stj_results(self, html: str, termo: str) -> List[Dict]:
        """Parse STJ search results."""
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # STJ specific result parsing
        result_items = soup.find_all('div', class_=['resultado', 'item-resultado'])
        
        for item in result_items:
            processo_elem = item.find(['strong', 'span'], text=re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}'))
            relator_elem = item.find(text=re.compile(r'Ministr[oa]'))
            ementa_elem = item.find(['div', 'p'], class_=['ementa', 'texto'])
            
            if processo_elem or ementa_elem:
                results.append({
                    "processo": processo_elem.get_text(strip=True) if processo_elem else "N/A",
                    "relator": self._extract_relator(relator_elem.parent.get_text() if relator_elem else ""),
                    "ementa": ementa_elem.get_text(strip=True)[:500] + "..." if ementa_elem else "N/A",
                    "data_julgamento": "N/A",
                    "tribunal": "STJ",
                    "url": self._extract_case_url(item),
                    "relevancia": self._calculate_case_relevance(ementa_elem.get_text() if ementa_elem else "", termo)
                })
                
        return results
        
    def _extract_relator(self, text: str) -> str:
        """Extract relator name from text."""
        # Common patterns for relator extraction
        patterns = [
            r'Rel\.?\s*Min\.?\s*([A-ZÁÇÃÕ\s]+)',
            r'Ministr[oa]\s+([A-ZÁÇÃÕ\s]+)',
            r'Relator[a]?\s*:\s*([A-ZÁÇÃÕ\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
                
        return "N/A"
        
    def _extract_case_url(self, element) -> str:
        """Extract case URL from element."""
        link = element.find('a', href=True)
        if link:
            href = link.get('href')
            if href.startswith('http'):
                return href
            elif href.startswith('/'):
                return f"https://portal.stf.jus.br{href}"
        return "N/A"
        
    def _calculate_case_relevance(self, ementa: str, termo: str) -> float:
        """Calculate relevance score for jurisprudence case."""
        if not ementa:
            return 0.0
            
        ementa_lower = ementa.lower()
        termo_lower = termo.lower()
        
        score = 0.0
        
        # Exact term match
        if termo_lower in ementa_lower:
            score += 1.0
            
        # Legal importance indicators
        importance_terms = [
            'constitucional', 'inconstitucionalidade', 'recurso extraordinário',
            'repercussão geral', 'precedente', 'jurisprudência consolidada',
            'súmula', 'orientação jurisprudencial'
        ]
        
        for term in importance_terms:
            if term in ementa_lower:
                score += 0.3
                
        # Regulatory terms relevant to Grupo Soluto
        regulatory_terms = [
            'anvisa', 'anatel', 'inmetro', 'regulação', 'vigilância sanitária',
            'telecomunicações', 'agência reguladora', 'compliance', 'lgpd'
        ]
        
        for term in regulatory_terms:
            if term in ementa_lower:
                score += 0.5
                
        return min(score, 2.0)
        
    async def _execute(self, query: str, tribunal: str = "todos", area: str = None, limit: int = 15) -> str:
        """Execute jurisprudence search."""
        try:
            all_results = []
            
            # Search specific tribunal or all
            if tribunal.lower() == "stf" or tribunal.lower() == "todos":
                stf_results = await self._search_stf(query, area, limit // 2)
                all_results.extend(stf_results)
                
            if tribunal.lower() == "stj" or tribunal.lower() == "todos":
                stj_results = await self._search_stj(query, area, limit // 2)
                all_results.extend(stj_results)
                
            # Sort by relevance
            all_results.sort(key=lambda x: x.get('relevancia', 0), reverse=True)
            
            if not all_results:
                return f"Nenhuma jurisprudência encontrada para '{query}' no(s) tribunal(is) {tribunal}"
                
            # Format results
            result = f"# Jurisprudência Encontrada\n\n"
            result += f"**Termo pesquisado:** {query}\n"
            result += f"**Tribunal(is):** {tribunal}\n"
            result += f"**Área:** {area or 'Todas'}\n"
            result += f"**Total de resultados:** {len(all_results)}\n\n"
            
            for i, case in enumerate(all_results[:limit], 1):
                result += f"## {i}. Processo: {case['processo']}\n"
                result += f"**Tribunal:** {case['tribunal']}\n"
                result += f"**Relator:** {case['relator']}\n"
                result += f"**Data:** {case['data_julgamento']}\n"
                result += f"**Relevância:** {case['relevancia']:.1f}/2.0\n\n"
                result += f"**Ementa:** {case['ementa']}\n\n"
                if case['url'] != "N/A":
                    result += f"**Link:** {case['url']}\n"
                result += "\n---\n\n"
                
            return result
            
        except Exception as e:
            self.logger.error(f"Erro na busca de jurisprudência: {e}")
            return f"Erro na busca de jurisprudência: {str(e)}"
            
    async def cleanup(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()


class ContractAnalysisTool(BaseTool):
    """Real contract analysis tool with legal validation."""
    
    name = "contract_analysis"
    description = "Análise real de contratos com validação legal e identificação de riscos"
    
    def __init__(self):
        super().__init__()
        self.risk_patterns = self._load_risk_patterns()
        self.clause_templates = self._load_clause_templates()
        
    def _load_risk_patterns(self) -> Dict[str, List[str]]:
        """Load contract risk patterns."""
        return {
            "high_risk": [
                r"sem limite de responsabilidade",
                r"responsabilidade ilimitada",
                r"renúncia.*direitos",
                r"irrevogável.*irretratável",
                r"multa.*superior.*30%",
                r"cláusula.*leonina",
                r"foro.*exclusivo.*[^brasil]"
            ],
            "medium_risk": [
                r"rescisão.*imotivada",
                r"multa.*rescisória",
                r"prazo.*prorrogação.*automática",
                r"alteração.*unilateral",
                r"confidencialidade.*período.*superior.*5.*anos"
            ],
            "compliance_risk": [
                r"sem.*adequação.*lgpd",
                r"transferência.*dados.*exterior",
                r"ausência.*cláusula.*anticorrupção",
                r"não.*menciona.*compliance",
                r"sem.*auditoria.*terceiros"
            ],
            "regulatory_risk": [
                r"não.*atende.*anvisa",
                r"sem.*certificação.*anatel",
                r"ausência.*licenças.*ambientais",
                r"não.*contempla.*normas.*técnicas",
                r"sem.*validação.*inmetro"
            ]
        }
        
    def _load_clause_templates(self) -> Dict[str, str]:
        """Load standard clause templates."""
        return {
            "lgpd_compliance": """
            CLÁUSULA DE PROTEÇÃO DE DADOS PESSOAIS
            
            As partes declaram conhecer e se comprometem a cumprir integralmente as disposições da Lei nº 13.709/2018 (Lei Geral de Proteção de Dados Pessoais - LGPD), especialmente:
            
            a) Implementar medidas técnicas e organizacionais apropriadas para proteger os dados pessoais;
            b) Garantir que o tratamento de dados pessoais seja realizado apenas para as finalidades autorizadas;
            c) Notificar a outra parte sobre qualquer incidente de segurança em até 24 horas;
            d) Permitir auditoria sobre as práticas de proteção de dados.
            """,
            
            "anticorrupcao": """
            CLÁUSULA ANTICORRUPÇÃO
            
            As partes declaram conhecer e se comprometem a cumprir rigorosamente as disposições da Lei nº 12.846/2013 (Lei Anticorrupção), comprometendo-se a:
            
            a) Não oferecer, prometer, dar ou autorizar pagamento de qualquer quantia ou vantagem;
            b) Manter controles internos adequados para prevenir atos de corrupção;
            c) Reportar imediatamente qualquer suspeita de ato de corrupção;
            d) Permitir auditorias periódicas de compliance.
            """,
            
            "responsabilidade_limitada": """
            CLÁUSULA DE LIMITAÇÃO DE RESPONSABILIDADE
            
            A responsabilidade das partes por danos diretos será limitada ao valor total do contrato nos 12 (doze) meses anteriores ao evento que deu origem ao dano.
            
            Fica excluída a responsabilidade por danos indiretos, lucros cessantes, danos morais ou consequenciais, exceto em casos de dolo ou culpa grave.
            """,
            
            "resolucao_disputas": """
            CLÁUSULA DE RESOLUÇÃO DE DISPUTAS
            
            As partes se comprometem a resolver eventuais controvérsias preferencialmente através de:
            
            1. Negociação direta entre as partes (30 dias);
            2. Mediação por câmara especializada (60 dias);
            3. Arbitragem perante câmara arbitral, conforme Lei nº 9.307/96.
            
            O foro será da comarca de São Paulo/SP, aplicando-se a lei brasileira.
            """
        }
        
    def _analyze_contract_text(self, contract_text: str) -> Dict[str, Any]:
        """Analyze contract text for risks and compliance."""
        analysis = {
            "risk_score": 0.0,
            "identified_risks": [],
            "missing_clauses": [],
            "compliance_gaps": [],
            "recommendations": []
        }
        
        contract_lower = contract_text.lower()
        
        # Analyze risk patterns
        for risk_level, patterns in self.risk_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, contract_lower, re.IGNORECASE)
                if matches:
                    risk_weight = {"high_risk": 1.0, "medium_risk": 0.6, "compliance_risk": 0.8, "regulatory_risk": 0.7}
                    analysis["risk_score"] += risk_weight.get(risk_level, 0.5) * len(matches)
                    
                    analysis["identified_risks"].append({
                        "pattern": pattern,
                        "level": risk_level,
                        "matches": len(matches),
                        "description": self._get_risk_description(pattern, risk_level)
                    })
                    
        # Check for missing essential clauses
        essential_clauses = {
            "lgpd": ["lgpd", "proteção.*dados", "privacidade", "dados.*pessoais"],
            "anticorrupcao": ["anticorrupção", "compliance", "integridade", "lei.*12.846"],
            "responsabilidade": ["responsabilidade", "limitação.*danos", "indenização"],
            "resolucao_disputas": ["foro", "arbitragem", "mediação", "jurisdição"]
        }
        
        for clause_type, keywords in essential_clauses.items():
            if not any(re.search(keyword, contract_lower) for keyword in keywords):
                analysis["missing_clauses"].append(clause_type)
                
        # Compliance gap analysis
        if "lgpd" in analysis["missing_clauses"]:
            analysis["compliance_gaps"].append("Ausência de cláusulas de proteção de dados conforme LGPD")
            
        if "anticorrupcao" in analysis["missing_clauses"]:
            analysis["compliance_gaps"].append("Ausência de cláusulas anticorrupção conforme Lei 12.846/2013")
            
        # Generate recommendations
        analysis["recommendations"] = self._generate_recommendations(analysis)
        
        # Normalize risk score (0-10)
        analysis["risk_score"] = min(analysis["risk_score"], 10.0)
        
        return analysis
        
    def _get_risk_description(self, pattern: str, risk_level: str) -> str:
        """Get description for identified risk pattern."""
        descriptions = {
            "sem limite de responsabilidade": "Responsabilidade ilimitada pode expor a empresa a riscos financeiros excessivos",
            "multa.*superior.*30%": "Multa excessiva pode indicar desequilíbrio contratual",
            "rescisão.*imotivada": "Possibilidade de rescisão sem justa causa pode criar instabilidade",
            "não.*adequação.*lgpd": "Ausência de adequação à LGPD pode resultar em multas regulatórias",
            "transferência.*dados.*exterior": "Transferência internacional de dados requer salvaguardas especiais"
        }
        
        for desc_pattern, description in descriptions.items():
            if re.search(desc_pattern, pattern):
                return description
                
        return f"Risco identificado no padrão: {pattern}"
        
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        if analysis["risk_score"] > 7:
            recommendations.append("ALTO RISCO: Recomenda-se revisão jurídica completa antes da assinatura")
            
        if analysis["risk_score"] > 4:
            recommendations.append("Negociar limitação de responsabilidade e inclusão de cláusulas protetivas")
            
        for missing_clause in analysis["missing_clauses"]:
            if missing_clause == "lgpd":
                recommendations.append("Incluir cláusula específica de proteção de dados conforme LGPD")
            elif missing_clause == "anticorrupcao":
                recommendations.append("Adicionar cláusula anticorrupção conforme Lei 12.846/2013")
            elif missing_clause == "responsabilidade":
                recommendations.append("Definir limitação clara de responsabilidade e danos")
            elif missing_clause == "resolucao_disputas":
                recommendations.append("Estabelecer mecanismo claro de resolução de disputas")
                
        if len(analysis["compliance_gaps"]) > 0:
            recommendations.append("Realizar adequação às normas de compliance aplicáveis")
            
        return recommendations
        
    async def _execute(self, contract_text: str, contract_type: str = "geral", detailed_analysis: bool = True) -> str:
        """Execute contract analysis."""
        try:
            if len(contract_text) < 100:
                return "Texto do contrato muito curto para análise efetiva. Forneça o texto completo."
                
            analysis = self._analyze_contract_text(contract_text)
            
            # Format analysis results
            result = f"# Análise de Contrato - {contract_type.title()}\n\n"
            result += f"**Data da Análise:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            result += f"**Tamanho do Contrato:** {len(contract_text)} caracteres\n\n"
            
            # Risk Score
            risk_level = "BAIXO" if analysis["risk_score"] < 3 else "MÉDIO" if analysis["risk_score"] < 7 else "ALTO"
            result += f"## Pontuação de Risco: {analysis['risk_score']:.1f}/10.0 ({risk_level})\n\n"
            
            # Identified Risks
            if analysis["identified_risks"]:
                result += "## Riscos Identificados\n\n"
                for risk in analysis["identified_risks"]:
                    result += f"- **{risk['level'].upper()}**: {risk['description']}\n"
                result += "\n"
                
            # Missing Clauses
            if analysis["missing_clauses"]:
                result += "## Cláusulas Ausentes\n\n"
                for clause in analysis["missing_clauses"]:
                    result += f"- {clause.upper()}: {self._get_clause_importance(clause)}\n"
                result += "\n"
                
            # Compliance Gaps
            if analysis["compliance_gaps"]:
                result += "## Lacunas de Compliance\n\n"
                for gap in analysis["compliance_gaps"]:
                    result += f"- {gap}\n"
                result += "\n"
                
            # Recommendations
            if analysis["recommendations"]:
                result += "## Recomendações\n\n"
                for i, rec in enumerate(analysis["recommendations"], 1):
                    result += f"{i}. {rec}\n"
                result += "\n"
                
            # Suggested Clauses
            if detailed_analysis and analysis["missing_clauses"]:
                result += "## Cláusulas Sugeridas\n\n"
                for missing_clause in analysis["missing_clauses"]:
                    if missing_clause in self.clause_templates:
                        result += f"### {missing_clause.upper()}\n"
                        result += self.clause_templates[missing_clause]
                        result += "\n\n"
                        
            result += "---\n\n"
            result += "**Aviso Legal:** Esta análise é apenas informativa e não substitui a consultoria jurídica especializada.\n"
            result += "**Recomendação:** Sempre consulte um advogado antes de assinar contratos importantes."
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro na análise de contrato: {e}")
            return f"Erro na análise de contrato: {str(e)}"
            
    def _get_clause_importance(self, clause_type: str) -> str:
        """Get importance description for missing clause."""
        importance_map = {
            "lgpd": "Obrigatório para contratos que envolvem tratamento de dados pessoais",
            "anticorrupcao": "Exigido para contratos com empresas públicas e recomendado para todos",
            "responsabilidade": "Essencial para limitação de riscos financeiros",
            "resolucao_disputas": "Importante para definir jurisdição e método de resolução"
        }
        return importance_map.get(clause_type, "Cláusula recomendada para melhor proteção jurídica")


class LegalComplianceAuditTool(BaseTool):
    """Real legal compliance audit tool."""
    
    name = "legal_compliance_audit"
    description = "Auditoria real de compliance legal com verificação de conformidade regulatória"
    
    def __init__(self):
        super().__init__()
        self.compliance_frameworks = self._load_compliance_frameworks()
        
    def _load_compliance_frameworks(self) -> Dict[str, Dict]:
        """Load compliance frameworks for different areas."""
        return {
            "geral": {
                "name": "Compliance Geral Empresarial",
                "requirements": [
                    "Código de Ética e Conduta aprovado",
                    "Canal de denúncias implementado",
                    "Programa de treinamento em compliance",
                    "Procedimentos de due diligence",
                    "Controles internos documentados",
                    "Auditoria interna de compliance",
                    "Comitê de compliance estabelecido"
                ]
            },
            "lgpd": {
                "name": "Compliance LGPD",
                "requirements": [
                    "Encarregado de Dados (DPO) designado",
                    "Inventário de dados pessoais",
                    "Base legal definida para tratamentos",
                    "Política de Privacidade atualizada",
                    "Procedimentos de resposta a titulares",
                    "Relatório de Impacto (RIPD) quando aplicável",
                    "Contratos de processamento com terceiros",
                    "Medidas de segurança implementadas",
                    "Procedimentos de notificação de incidentes"
                ]
            },
            "anticorrupcao": {
                "name": "Compliance Anticorrupção",
                "requirements": [
                    "Política anticorrupção aprovada",
                    "Due diligence de terceiros",
                    "Controles de presentes e hospitalidades",
                    "Monitoramento de pagamentos",
                    "Treinamento específico anticorrupção",
                    "Canal de denúncias específico",
                    "Auditoria de riscos de corrupção",
                    "Certificações anticorrupção"
                ]
            },
            "trabalhista": {
                "name": "Compliance Trabalhista",
                "requirements": [
                    "Registros de empregados atualizados",
                    "Cumprimento de jornada de trabalho",
                    "Pagamento de verbas trabalhistas",
                    "Segurança e saúde ocupacional (SSO)",
                    "Programas obrigatórios (PPRA, PCMSO)",
                    "Comissões internas (CIPA, etc.)",
                    "Adequação a convenções coletivas",
                    "Licenças e autorizações do trabalho"
                ]
            },
            "ambiental": {
                "name": "Compliance Ambiental",
                "requirements": [
                    "Licenças ambientais válidas",
                    "Controle de emissões e efluentes",
                    "Gestão de resíduos sólidos",
                    "Monitoramento ambiental",
                    "Planos de contingência ambiental",
                    "Treinamento em questões ambientais",
                    "Relatórios de sustentabilidade",
                    "Adequação a normas ISO 14001"
                ]
            }
        }
        
    def _assess_compliance_level(self, area: str, implemented_items: List[str]) -> Dict[str, Any]:
        """Assess compliance level for specific area."""
        if area not in self.compliance_frameworks:
            return {"error": f"Área de compliance '{area}' não reconhecida"}
            
        framework = self.compliance_frameworks[area]
        total_requirements = len(framework["requirements"])
        
        # Match implemented items with requirements
        implemented_count = 0
        missing_items = []
        
        for requirement in framework["requirements"]:
            requirement_met = False
            for item in implemented_items:
                if self._items_match(requirement.lower(), item.lower()):
                    requirement_met = True
                    break
                    
            if requirement_met:
                implemented_count += 1
            else:
                missing_items.append(requirement)
                
        compliance_percentage = (implemented_count / total_requirements) * 100
        
        # Determine compliance level
        if compliance_percentage >= 90:
            level = "EXCELENTE"
            color = "🟢"
        elif compliance_percentage >= 75:
            level = "BOM"
            color = "🟡"
        elif compliance_percentage >= 50:
            level = "REGULAR"
            color = "🟠"
        else:
            level = "INADEQUADO"
            color = "🔴"
            
        return {
            "area": area,
            "framework_name": framework["name"],
            "total_requirements": total_requirements,
            "implemented_count": implemented_count,
            "compliance_percentage": compliance_percentage,
            "compliance_level": level,
            "status_color": color,
            "missing_items": missing_items,
            "recommendations": self._generate_compliance_recommendations(area, missing_items)
        }
        
    def _items_match(self, requirement: str, implemented: str) -> bool:
        """Check if implemented item matches requirement."""
        # Simple keyword matching - can be enhanced with NLP
        requirement_keywords = set(requirement.split())
        implemented_keywords = set(implemented.split())
        
        # If 60% of requirement keywords are in implemented item, consider it a match
        common_keywords = requirement_keywords.intersection(implemented_keywords)
        return len(common_keywords) >= len(requirement_keywords) * 0.6
        
    def _generate_compliance_recommendations(self, area: str, missing_items: List[str]) -> List[str]:
        """Generate specific recommendations for compliance gaps."""
        recommendations = []
        
        if not missing_items:
            recommendations.append(f"Compliance {area} está adequado. Manter monitoramento contínuo.")
            return recommendations
            
        # Priority recommendations based on area
        if area == "lgpd":
            if any("encarregado" in item.lower() or "dpo" in item.lower() for item in missing_items):
                recommendations.append("PRIORIDADE ALTA: Designar Encarregado de Dados (DPO)")
            if any("inventário" in item.lower() for item in missing_items):
                recommendations.append("PRIORIDADE ALTA: Realizar inventário completo de dados pessoais")
                
        elif area == "anticorrupcao":
            if any("política" in item.lower() for item in missing_items):
                recommendations.append("PRIORIDADE ALTA: Aprovar política anticorrupção")
            if any("due diligence" in item.lower() for item in missing_items):
                recommendations.append("PRIORIDADE MÉDIA: Implementar due diligence de terceiros")
                
        elif area == "trabalhista":
            if any("sso" in item.lower() or "segurança" in item.lower() for item in missing_items):
                recommendations.append("PRIORIDADE ALTA: Adequar programas de segurança ocupacional")
                
        elif area == "ambiental":
            if any("licenças" in item.lower() for item in missing_items):
                recommendations.append("PRIORIDADE CRÍTICA: Regularizar licenças ambientais")
                
        # Generic recommendations
        recommendations.append(f"Implementar {len(missing_items)} itens pendentes de compliance")
        recommendations.append("Estabelecer cronograma de adequação com prazos definidos")
        recommendations.append("Designar responsáveis para cada item pendente")
        recommendations.append("Agendar auditoria de acompanhamento em 90 dias")
        
        return recommendations
        
    async def _execute(self, area: str, implemented_items: str, generate_action_plan: bool = True) -> str:
        """Execute legal compliance audit."""
        try:
            # Parse implemented items
            items_list = [item.strip() for item in implemented_items.split(",") if item.strip()]
            
            if not items_list:
                return "Lista de itens implementados não pode estar vazia"
                
            # Assess compliance
            assessment = self._assess_compliance_level(area, items_list)
            
            if "error" in assessment:
                available_areas = list(self.compliance_frameworks.keys())
                return f"{assessment['error']}. Áreas disponíveis: {', '.join(available_areas)}"
                
            # Format audit report
            result = f"# Auditoria de Compliance - {assessment['framework_name']}\n\n"
            result += f"**Data da Auditoria:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            result += f"**Área Auditada:** {area.upper()}\n\n"
            
            # Compliance Status
            result += f"## Status de Compliance {assessment['status_color']}\n\n"
            result += f"**Nível:** {assessment['compliance_level']}\n"
            result += f"**Percentual:** {assessment['compliance_percentage']:.1f}%\n"
            result += f"**Itens Implementados:** {assessment['implemented_count']}/{assessment['total_requirements']}\n\n"
            
            # Missing Items
            if assessment['missing_items']:
                result += "## Itens Pendentes de Implementação\n\n"
                for i, item in enumerate(assessment['missing_items'], 1):
                    result += f"{i}. {item}\n"
                result += "\n"
                
            # Recommendations
            if assessment['recommendations']:
                result += "## Recomendações\n\n"
                for i, rec in enumerate(assessment['recommendations'], 1):
                    result += f"{i}. {rec}\n"
                result += "\n"
                
            # Action Plan
            if generate_action_plan and assessment['missing_items']:
                result += "## Plano de Ação Sugerido\n\n"
                result += "| Item | Responsável | Prazo | Prioridade |\n"
                result += "|------|-------------|-------|------------|\n"
                
                for item in assessment['missing_items'][:10]:  # Limit to top 10
                    priority = "Alta" if any(keyword in item.lower() for keyword in ["política", "dpo", "licenças"]) else "Média"
                    prazo = "30 dias" if priority == "Alta" else "60 dias"
                    result += f"| {item} | A definir | {prazo} | {priority} |\n"
                    
                result += "\n"
                
            result += "---\n\n"
            result += "**Próximos Passos:**\n"
            result += "1. Definir responsáveis para cada item pendente\n"
            result += "2. Estabelecer cronograma detalhado de implementação\n"
            result += "3. Agendar revisões periódicas de progresso\n"
            result += "4. Realizar nova auditoria em 90 dias\n\n"
            result += "**Aviso:** Esta auditoria é baseada em análise preliminar. "
            result += "Recomenda-se validação por consultoria jurídica especializada."
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro na auditoria de compliance: {e}")
            return f"Erro na auditoria de compliance: {str(e)}"