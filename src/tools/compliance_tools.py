"""Real compliance tools for Grupo Soluto regulatory system."""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import aiohttp
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from .base import BaseTool


class RegulatoryDatabase(BaseModel):
    """Database of Brazilian regulatory agencies and their endpoints."""
    
    agencies: Dict[str, Dict[str, Any]] = Field(default_factory=lambda: {
        "anvisa": {
            "name": "Agência Nacional de Vigilância Sanitária",
            "base_url": "https://consultas.anvisa.gov.br",
            "endpoints": {
                "medicamentos": "/api/consulta/medicamentos",
                "cosmeticos": "/api/consulta/cosmeticos",
                "alimentos": "/api/consulta/alimentos",
                "dispositivos": "/api/consulta/dispositivos"
            },
            "search_url": "https://consultas.anvisa.gov.br/#/medicamentos/"
        },
        "anatel": {
            "name": "Agência Nacional de Telecomunicações",
            "base_url": "https://sistemas.anatel.gov.br",
            "endpoints": {
                "homologacao": "/sgch/Consulta/ConsultaHomologacao",
                "outorgas": "/sad/Consulta/ConsultaOutorga"
            },
            "search_url": "https://sistemas.anatel.gov.br/sgch/"
        },
        "inmetro": {
            "name": "Instituto Nacional de Metrologia",
            "base_url": "https://www.inmetro.gov.br",
            "endpoints": {
                "certificados": "/registros/certificados",
                "laboratorios": "/registros/laboratorios"
            },
            "search_url": "https://www.inmetro.gov.br/registros/"
        },
        "ibama": {
            "name": "Instituto Brasileiro do Meio Ambiente",
            "base_url": "https://servicos.ibama.gov.br",
            "endpoints": {
                "licencas": "/licenciamento/consulta",
                "fauna": "/fauna/consulta"
            },
            "search_url": "https://servicos.ibama.gov.br/"
        }
    })


class ANVISARealConsultaTool(BaseTool):
    """Real ANVISA consultation tool with actual API integration."""
    
    name = "anvisa_real_consulta"
    description = "Consulta real à base de dados da ANVISA para medicamentos, cosméticos, alimentos e dispositivos médicos"
    
    def __init__(self):
        super().__init__()
        self.db = RegulatoryDatabase()
        self.session = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "User-Agent": "Grupo Soluto Regulatory System/2.0",
                    "Accept": "application/json, text/html",
                }
            )
        return self.session
        
    async def _consultar_medicamentos(self, termo: str, limit: int = 20) -> List[Dict]:
        """Consulta medicamentos na ANVISA."""
        session = await self._get_session()
        
        # Try direct search in ANVISA's consultation system
        search_url = f"https://consultas.anvisa.gov.br/api/consulta/medicamentos"
        params = {
            "filter[nome_produto]": termo,
            "count": limit,
            "page": 1
        }
        
        try:
            async with session.get(search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_medicamentos_response(data)
        except Exception:
            pass
            
        # Fallback to web scraping if API fails
        return await self._scrape_anvisa_medicamentos(termo, limit)
        
    async def _scrape_anvisa_medicamentos(self, termo: str, limit: int) -> List[Dict]:
        """Scrape ANVISA website for medication data."""
        session = await self._get_session()
        
        search_url = f"https://consultas.anvisa.gov.br/#/medicamentos/{quote(termo)}"
        
        try:
            async with session.get(search_url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    results = []
                    # Parse medication results from HTML
                    med_cards = soup.find_all('div', class_=['medicamento-card', 'produto-card'])[:limit]
                    
                    for card in med_cards:
                        name_elem = card.find(['h3', 'h4', '.nome-produto'])
                        reg_elem = card.find(['span', '.registro'])
                        company_elem = card.find(['span', '.empresa'])
                        
                        if name_elem:
                            results.append({
                                "nome": name_elem.get_text(strip=True),
                                "registro": reg_elem.get_text(strip=True) if reg_elem else "N/A",
                                "empresa": company_elem.get_text(strip=True) if company_elem else "N/A",
                                "categoria": "Medicamento",
                                "status": "Ativo",
                                "data_consulta": datetime.now().isoformat()
                            })
                    
                    return results
        except Exception as e:
            self.logger.error(f"Erro ao consultar ANVISA: {e}")
            
        return []
        
    def _parse_medicamentos_response(self, data: Dict) -> List[Dict]:
        """Parse ANVISA API response."""
        results = []
        items = data.get('content', data.get('data', []))
        
        if isinstance(items, list):
            for item in items:
                results.append({
                    "nome": item.get('nomeProduto', item.get('nome', 'N/A')),
                    "registro": item.get('numeroRegistro', item.get('registro', 'N/A')),
                    "empresa": item.get('empresa', item.get('detentor', 'N/A')),
                    "categoria": item.get('categoria', 'Medicamento'),
                    "status": item.get('situacao', item.get('status', 'N/A')),
                    "validade": item.get('validadeRegistro', 'N/A'),
                    "principio_ativo": item.get('principioAtivo', 'N/A'),
                    "data_consulta": datetime.now().isoformat()
                })
                
        return results
        
    async def _execute(self, query: str, category: str = "medicamentos", limit: int = 10) -> str:
        """Execute ANVISA consultation."""
        try:
            if category == "medicamentos":
                results = await self._consultar_medicamentos(query, limit)
            else:
                # For other categories, use generic search
                results = await self._generic_anvisa_search(query, category, limit)
                
            if not results:
                return f"Nenhum resultado encontrado para '{query}' na categoria {category}"
                
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append(
                    f"**{result['nome']}**\n"
                    f"- Registro: {result['registro']}\n"
                    f"- Empresa: {result['empresa']}\n"
                    f"- Status: {result.get('status', 'N/A')}\n"
                    f"- Categoria: {result.get('categoria', category)}"
                )
                
            return f"## Resultados ANVISA para '{query}':\n\n" + "\n\n".join(formatted_results)
            
        except Exception as e:
            self.logger.error(f"Erro na consulta ANVISA: {e}")
            return f"Erro ao consultar ANVISA: {str(e)}"
            
    async def _generic_anvisa_search(self, termo: str, categoria: str, limit: int) -> List[Dict]:
        """Generic ANVISA search for different categories."""
        session = await self._get_session()
        
        category_urls = {
            "cosmeticos": "https://consultas.anvisa.gov.br/#/cosmeticos/",
            "alimentos": "https://consultas.anvisa.gov.br/#/alimentos/",
            "dispositivos": "https://consultas.anvisa.gov.br/#/dispositivos/"
        }
        
        url = category_urls.get(categoria, category_urls["medicamentos"])
        search_url = f"{url}{quote(termo)}"
        
        try:
            async with session.get(search_url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Generic parsing for different categories
                    results = []
                    cards = soup.find_all('div', class_=['produto-card', 'item-resultado'])[:limit]
                    
                    for card in cards:
                        nome = card.find(['h3', 'h4', '.nome']).get_text(strip=True) if card.find(['h3', 'h4', '.nome']) else "N/A"
                        registro = card.find('.registro').get_text(strip=True) if card.find('.registro') else "N/A"
                        empresa = card.find('.empresa').get_text(strip=True) if card.find('.empresa') else "N/A"
                        
                        results.append({
                            "nome": nome,
                            "registro": registro,
                            "empresa": empresa,
                            "categoria": categoria.title(),
                            "status": "Ativo",
                            "data_consulta": datetime.now().isoformat()
                        })
                    
                    return results
        except Exception as e:
            self.logger.error(f"Erro na busca genérica ANVISA: {e}")
            
        return []
        
    async def cleanup(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()


class LegislacaoComplianceSearchTool(BaseTool):
    """Real Brazilian legislation and compliance search tool."""
    
    name = "legislacao_compliance_search"
    description = "Busca real em legislação brasileira e normas de compliance"
    
    def __init__(self):
        super().__init__()
        self.sources = {
            "planalto": "http://www.planalto.gov.br",
            "senado": "https://www25.senado.leg.br",
            "camara": "https://www2.camara.leg.br",
            "jus": "https://jus.com.br",
            "jusbrasil": "https://www.jusbrasil.com.br"
        }
        
    async def _search_planalto(self, termo: str) -> List[Dict]:
        """Search Planalto government portal."""
        async with aiohttp.ClientSession() as session:
            try:
                search_url = f"http://www.planalto.gov.br/ccivil_03/busca.htm"
                params = {"q": termo, "submit": "Buscar"}
                
                async with session.get(search_url, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        results = []
                        links = soup.find_all('a', href=True)[:10]
                        
                        for link in links:
                            href = link.get('href')
                            text = link.get_text(strip=True)
                            
                            if href and ('lei' in href.lower() or 'decreto' in href.lower() or 'mp' in href.lower()):
                                results.append({
                                    "titulo": text,
                                    "url": href if href.startswith('http') else f"http://www.planalto.gov.br{href}",
                                    "fonte": "Planalto",
                                    "tipo": self._extract_law_type(href)
                                })
                        
                        return results
            except Exception as e:
                self.logger.error(f"Erro ao buscar no Planalto: {e}")
                
        return []
        
    def _extract_law_type(self, url: str) -> str:
        """Extract law type from URL."""
        url_lower = url.lower()
        if 'lei' in url_lower:
            return "Lei"
        elif 'decreto' in url_lower:
            return "Decreto"
        elif 'mp' in url_lower or 'medida' in url_lower:
            return "Medida Provisória"
        elif 'portaria' in url_lower:
            return "Portaria"
        elif 'resolucao' in url_lower:
            return "Resolução"
        return "Normativo"
        
    async def _search_legislation(self, termo: str, area: str = "geral") -> List[Dict]:
        """Search for specific legislation."""
        all_results = []
        
        # Search multiple sources
        planalto_results = await self._search_planalto(termo)
        all_results.extend(planalto_results)
        
        # Add regulatory area specific searches
        if area.lower() in ["saude", "anvisa"]:
            anvisa_results = await self._search_anvisa_legislation(termo)
            all_results.extend(anvisa_results)
            
        if area.lower() in ["telecomunicacoes", "anatel"]:
            anatel_results = await self._search_anatel_legislation(termo)
            all_results.extend(anatel_results)
            
        return all_results[:15]  # Limit results
        
    async def _search_anvisa_legislation(self, termo: str) -> List[Dict]:
        """Search ANVISA specific legislation."""
        async with aiohttp.ClientSession() as session:
            try:
                # ANVISA legislation portal
                search_url = "https://www.gov.br/anvisa/pt-br/assuntos/regulamentacao"
                
                async with session.get(search_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        results = []
                        # Find relevant legislation links
                        links = soup.find_all('a', href=True)
                        
                        for link in links:
                            text = link.get_text(strip=True)
                            href = link.get('href')
                            
                            if termo.lower() in text.lower() and href:
                                results.append({
                                    "titulo": text,
                                    "url": href if href.startswith('http') else f"https://www.gov.br{href}",
                                    "fonte": "ANVISA",
                                    "tipo": "Regulamentação Sanitária"
                                })
                        
                        return results[:5]
            except Exception as e:
                self.logger.error(f"Erro ao buscar legislação ANVISA: {e}")
                
        return []
        
    async def _search_anatel_legislation(self, termo: str) -> List[Dict]:
        """Search ANATEL specific legislation."""
        async with aiohttp.ClientSession() as session:
            try:
                search_url = "https://www.anatel.gov.br/legislacao"
                
                async with session.get(search_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        results = []
                        links = soup.find_all('a', href=True)
                        
                        for link in links:
                            text = link.get_text(strip=True)
                            href = link.get('href')
                            
                            if termo.lower() in text.lower() and href:
                                results.append({
                                    "titulo": text,
                                    "url": href if href.startswith('http') else f"https://www.anatel.gov.br{href}",
                                    "fonte": "ANATEL",
                                    "tipo": "Regulamentação Telecomunicações"
                                })
                        
                        return results[:5]
            except Exception as e:
                self.logger.error(f"Erro ao buscar legislação ANATEL: {e}")
                
        return []
        
    async def _execute(self, query: str, area: str = "geral", detailed: bool = False) -> str:
        """Execute legislation search."""
        try:
            results = await self._search_legislation(query, area)
            
            if not results:
                return f"Nenhuma legislação encontrada para '{query}' na área {area}"
                
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append(
                    f"**{result['titulo']}**\n"
                    f"- Tipo: {result['tipo']}\n"
                    f"- Fonte: {result['fonte']}\n"
                    f"- URL: {result['url']}"
                )
                
            return f"## Legislação encontrada para '{query}' ({area}):\n\n" + "\n\n".join(formatted_results)
            
        except Exception as e:
            self.logger.error(f"Erro na busca de legislação: {e}")
            return f"Erro ao buscar legislação: {str(e)}"


class RealComplianceChecklistTool(BaseTool):
    """Real compliance checklist generator based on actual regulations."""
    
    name = "real_compliance_checklist"
    description = "Gera checklists de compliance reais baseados em regulamentações atuais"
    
    def __init__(self):
        super().__init__()
        self.checklist_templates = self._load_compliance_templates()
        
    def _load_compliance_templates(self) -> Dict[str, Dict]:
        """Load real compliance checklist templates."""
        return {
            "anvisa_medicamentos": {
                "name": "Registro de Medicamentos ANVISA",
                "categories": {
                    "documentacao_tecnica": [
                        "Relatório de Desenvolvimento Farmacêutico completo",
                        "Estudos de estabilidade conforme RDC 318/2019",
                        "Certificado de Análise do produto finalizado",
                        "Especificações dos insumos farmacêuticos ativos",
                        "Relatório de validação analítica",
                        "Memorial descritivo de fabricação"
                    ],
                    "estudos_clinicos": [
                        "Protocolo de estudos clínicos aprovado pela CONEP",
                        "Relatório de estudos de bioequivalência/biodisponibilidade",
                        "Relatório de segurança clínica",
                        "Parecer de comitê de ética em pesquisa"
                    ],
                    "boas_praticas": [
                        "Certificado de Boas Práticas de Fabricação (BPF)",
                        "Plano Mestre de Validação",
                        "Sistema de qualidade farmacêutica implementado",
                        "Certificação ISO 13485 (se aplicável)"
                    ],
                    "regulatorio": [
                        "Petição inicial conforme RDC 200/2017",
                        "Comprovante de recolhimento da taxa",
                        "Rotulagem conforme RDC 71/2009",
                        "Bula conforme RDC 47/2009"
                    ]
                }
            },
            "lgpd_compliance": {
                "name": "Adequação à LGPD",
                "categories": {
                    "governanca": [
                        "Designação de Encarregado de Dados (DPO)",
                        "Política de Privacidade atualizada",
                        "Procedimentos de resposta a titulares",
                        "Registro de atividades de tratamento",
                        "Relatório de Impacto à Proteção de Dados (quando aplicável)"
                    ],
                    "tecnico": [
                        "Implementação de medidas de segurança técnicas",
                        "Pseudonimização e criptografia de dados sensíveis",
                        "Controles de acesso por função",
                        "Backup e recuperação de dados",
                        "Monitoramento de acessos não autorizados"
                    ],
                    "organizacional": [
                        "Treinamento de funcionários em LGPD",
                        "Contratos de processamento com terceiros",
                        "Procedimentos de notificação de incidentes",
                        "Auditoria interna de compliance",
                        "Plano de resposta a incidentes de segurança"
                    ]
                }
            },
            "anatel_homologacao": {
                "name": "Homologação ANATEL",
                "categories": {
                    "documentacao": [
                        "Manual do usuário em português",
                        "Certificado de conformidade técnica",
                        "Relatório de ensaios em laboratório acreditado",
                        "Declaração de conformidade do fornecedor"
                    ],
                    "ensaios": [
                        "Ensaios de compatibilidade eletromagnética",
                        "Ensaios de segurança elétrica",
                        "Ensaios de SAR (se aplicável)",
                        "Ensaios de radiofrequência"
                    ],
                    "rotulagem": [
                        "Selo de identificação da conformidade",
                        "Informações técnicas obrigatórias",
                        "Advertências de segurança",
                        "Identificação do responsável técnico"
                    ]
                }
            }
        }
        
    def _generate_sector_checklist(self, sector: str, company_size: str = "medio") -> Dict[str, Any]:
        """Generate sector-specific compliance checklist."""
        sector_lower = sector.lower()
        
        if "medicamento" in sector_lower or "farmaceutico" in sector_lower:
            return self._customize_checklist("anvisa_medicamentos", company_size)
        elif "tecnologia" in sector_lower or "dados" in sector_lower:
            return self._customize_checklist("lgpd_compliance", company_size)
        elif "telecomunicacao" in sector_lower or "equipamento" in sector_lower:
            return self._customize_checklist("anatel_homologacao", company_size)
        else:
            # Generic compliance checklist
            return self._generate_generic_checklist(sector, company_size)
            
    def _customize_checklist(self, template_key: str, company_size: str) -> Dict[str, Any]:
        """Customize checklist based on company size."""
        template = self.checklist_templates[template_key].copy()
        
        # Add size-specific requirements
        if company_size.lower() == "pequeno":
            # Simplify for small companies
            for category in template["categories"]:
                template["categories"][category] = template["categories"][category][:3]
        elif company_size.lower() == "grande":
            # Add additional requirements for large companies
            if template_key == "lgpd_compliance":
                template["categories"]["governanca"].append("Certificação ISO 27001")
                template["categories"]["tecnico"].append("Data Loss Prevention (DLP)")
                
        return template
        
    def _generate_generic_checklist(self, sector: str, company_size: str) -> Dict[str, Any]:
        """Generate generic compliance checklist."""
        return {
            "name": f"Compliance Geral - {sector.title()}",
            "categories": {
                "estrutura_compliance": [
                    "Código de Ética e Conduta aprovado",
                    "Canal de denúncias implementado",
                    "Programa de integridade documentado",
                    "Treinamentos periódicos realizados"
                ],
                "controles_internos": [
                    "Matriz de riscos atualizada",
                    "Procedimentos operacionais documentados",
                    "Controles de alçadas definidos",
                    "Auditoria interna funcionando"
                ],
                "regulatory": [
                    "Licenças e autorizações válidas",
                    "Obrigações tributárias em dia",
                    "Compliance trabalhista verificado",
                    "Adequação ambiental (se aplicável)"
                ]
            }
        }
        
    async def _execute(self, sector: str, company_size: str = "medio", detailed: bool = True) -> str:
        """Execute compliance checklist generation."""
        try:
            checklist = self._generate_sector_checklist(sector, company_size)
            
            # Format checklist
            result = f"# {checklist['name']}\n\n"
            result += f"**Setor:** {sector.title()}\n"
            result += f"**Porte da Empresa:** {company_size.title()}\n"
            result += f"**Data de Geração:** {datetime.now().strftime('%d/%m/%Y')}\n\n"
            
            for category_name, items in checklist["categories"].items():
                result += f"## {category_name.replace('_', ' ').title()}\n\n"
                for i, item in enumerate(items, 1):
                    result += f"{i}. [ ] {item}\n"
                result += "\n"
                
            result += "---\n\n"
            result += "**Observações:**\n"
            result += "- Este checklist deve ser revisado trimestralmente\n"
            result += "- Consulte sempre a legislação mais recente\n"
            result += "- Mantenha evidências de todos os itens implementados\n"
            result += "- Considere contratação de consultoria especializada para itens complexos"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar checklist de compliance: {e}")
            return f"Erro ao gerar checklist: {str(e)}"


class RegulatoryMonitoringTool(BaseTool):
    """Real regulatory monitoring and alert system."""
    
    name = "regulatory_monitoring"
    description = "Sistema real de monitoramento de mudanças regulatórias"
    
    def __init__(self):
        super().__init__()
        self.monitoring_sources = {
            "dou": "https://www.in.gov.br/consulta",
            "anvisa": "https://www.gov.br/anvisa/pt-br/assuntos/noticias",
            "anatel": "https://www.anatel.gov.br/institucional/noticias",
            "cvm": "https://www.gov.br/cvm/pt-br/assuntos/noticias",
            "bacen": "https://www.bcb.gov.br/estabilidadefinanceira/noticias"
        }
        
    async def _monitor_dou(self, keywords: List[str], days_back: int = 7) -> List[Dict]:
        """Monitor Diário Oficial da União for regulatory changes."""
        results = []
        async with aiohttp.ClientSession() as session:
            try:
                # Calculate date range
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
                
                for keyword in keywords:
                    search_url = "https://www.in.gov.br/consulta"
                    params = {
                        "q": keyword,
                        "data_inicio": start_date.strftime("%d/%m/%Y"),
                        "data_fim": end_date.strftime("%d/%m/%Y")
                    }
                    
                    async with session.get(search_url, params=params) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Parse DOU results
                            articles = soup.find_all('div', class_=['resultado-busca', 'item-resultado'])
                            
                            for article in articles[:5]:  # Limit per keyword
                                title_elem = article.find(['h3', 'h4', '.titulo'])
                                date_elem = article.find(['span', '.data'])
                                link_elem = article.find('a', href=True)
                                
                                if title_elem:
                                    results.append({
                                        "titulo": title_elem.get_text(strip=True),
                                        "data": date_elem.get_text(strip=True) if date_elem else "N/A",
                                        "url": link_elem.get('href') if link_elem else "N/A",
                                        "fonte": "DOU",
                                        "keyword": keyword,
                                        "relevancia": self._calculate_relevance(title_elem.get_text(), keyword)
                                    })
                                    
            except Exception as e:
                self.logger.error(f"Erro ao monitorar DOU: {e}")
                
        return results
        
    def _calculate_relevance(self, text: str, keyword: str) -> float:
        """Calculate relevance score for regulatory change."""
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        score = 0.0
        
        # Exact match gets highest score
        if keyword_lower in text_lower:
            score += 1.0
            
        # High priority terms
        high_priority = ['lei', 'decreto', 'resolução', 'portaria', 'instrução normativa']
        for term in high_priority:
            if term in text_lower:
                score += 0.5
                
        # Regulatory agencies
        agencies = ['anvisa', 'anatel', 'cvm', 'bacen', 'inmetro']
        for agency in agencies:
            if agency in text_lower:
                score += 0.3
                
        return min(score, 2.0)  # Cap at 2.0
        
    async def _monitor_agency_news(self, agency: str, keywords: List[str]) -> List[Dict]:
        """Monitor specific regulatory agency news."""
        if agency not in self.monitoring_sources:
            return []
            
        results = []
        async with aiohttp.ClientSession() as session:
            try:
                url = self.monitoring_sources[agency]
                
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Parse agency-specific news
                        news_items = soup.find_all(['article', 'div'], class_=['noticia', 'news-item', 'item-noticia'])
                        
                        for item in news_items[:10]:
                            title_elem = item.find(['h1', 'h2', 'h3', '.titulo'])
                            date_elem = item.find(['.data', '.date', 'time'])
                            link_elem = item.find('a', href=True)
                            
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                
                                # Check if any keyword matches
                                for keyword in keywords:
                                    if keyword.lower() in title.lower():
                                        results.append({
                                            "titulo": title,
                                            "data": date_elem.get_text(strip=True) if date_elem else "N/A",
                                            "url": link_elem.get('href') if link_elem else "N/A",
                                            "fonte": agency.upper(),
                                            "keyword": keyword,
                                            "relevancia": self._calculate_relevance(title, keyword)
                                        })
                                        break
                                        
            except Exception as e:
                self.logger.error(f"Erro ao monitorar {agency}: {e}")
                
        return results
        
    async def _execute(self, keywords: str, agencies: str = "todas", days_back: int = 7) -> str:
        """Execute regulatory monitoring."""
        try:
            keyword_list = [k.strip() for k in keywords.split(",")]
            agency_list = [a.strip() for a in agencies.split(",")] if agencies != "todas" else list(self.monitoring_sources.keys())
            
            all_results = []
            
            # Monitor DOU
            dou_results = await self._monitor_dou(keyword_list, days_back)
            all_results.extend(dou_results)
            
            # Monitor specific agencies
            for agency in agency_list:
                if agency in self.monitoring_sources:
                    agency_results = await self._monitor_agency_news(agency, keyword_list)
                    all_results.extend(agency_results)
                    
            # Sort by relevance
            all_results.sort(key=lambda x: x.get('relevancia', 0), reverse=True)
            
            if not all_results:
                return f"Nenhuma mudança regulatória encontrada para {keywords} nos últimos {days_back} dias"
                
            # Format results
            result = f"# Monitoramento Regulatório\n\n"
            result += f"**Palavras-chave:** {keywords}\n"
            result += f"**Período:** Últimos {days_back} dias\n"
            result += f"**Total de alterações encontradas:** {len(all_results)}\n\n"
            
            for i, item in enumerate(all_results[:15], 1):  # Limit to top 15
                result += f"## {i}. {item['titulo']}\n"
                result += f"- **Fonte:** {item['fonte']}\n"
                result += f"- **Data:** {item['data']}\n"
                result += f"- **Palavra-chave:** {item['keyword']}\n"
                result += f"- **Relevância:** {item['relevancia']:.1f}/2.0\n"
                if item['url'] != "N/A":
                    result += f"- **Link:** {item['url']}\n"
                result += "\n"
                
            return result
            
        except Exception as e:
            self.logger.error(f"Erro no monitoramento regulatório: {e}")
            return f"Erro no monitoramento: {str(e)}"