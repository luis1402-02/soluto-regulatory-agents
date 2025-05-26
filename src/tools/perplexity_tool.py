"""Perplexity AI Sonar Pro integration for advanced regulatory research."""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import aiohttp
from pydantic import BaseModel, Field

from ..config import get_settings
from ..utils import get_logger
from .base import BaseTool, ToolResult

logger = get_logger(__name__)


class PerplexitySearchResult(BaseModel):
    """Structured search result from Perplexity."""
    
    answer: str = Field(..., description="The comprehensive answer from Perplexity")
    citations: List[Dict[str, Any]] = Field(default_factory=list, description="List of citations")
    sources: List[str] = Field(default_factory=list, description="Source URLs")
    confidence_score: float = Field(0.0, description="Confidence score of the answer")
    search_query: str = Field(..., description="The original search query")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PerplexitySonarProTool(BaseTool):
    """
    Perplexity AI Sonar Pro tool for advanced research with real-time information.
    
    This tool uses Perplexity's Sonar Pro model which features:
    - 200,000 token context window
    - Real-time web access
    - Double citations compared to standard Sonar
    - Superior factuality (F-score: 0.858)
    - Brazilian regulatory focus optimization
    """
    
    name = "perplexity_sonar_pro"
    description = "Advanced AI-powered research using Perplexity Sonar Pro with real-time web access"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Perplexity Sonar Pro tool."""
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            logger.warning("PERPLEXITY_API_KEY not found in environment")
            
        self.base_url = "https://api.perplexity.ai"
        self.model = "sonar-pro"
        self.max_tokens = 4096
        self.temperature = 0.1  # Low temperature for factual accuracy
        
        # Brazilian regulatory context optimization
        self.regulatory_context = """You are an expert researcher for Grupo Soluto, a Brazilian regulatory consultancy. 
Focus on Brazilian regulations, laws, and compliance requirements. When searching:
- Prioritize Brazilian official sources (gov.br, ANVISA, ANATEL, etc.)
- Include relevant RDCs, Laws, Decrees, and Normative Instructions
- Provide citations in Portuguese when available
- Consider MERCOSUL harmonization when relevant"""

    async def execute(
        self,
        query: str,
        search_type: str = "regulatory",
        focus_areas: Optional[List[str]] = None,
        include_analysis: bool = True,
        language: str = "pt-BR",
        max_citations: int = 20,
    ) -> ToolResult:
        """
        Execute advanced search using Perplexity Sonar Pro.
        
        Args:
            query: The search query
            search_type: Type of search (regulatory, legal, technical, market)
            focus_areas: Specific areas to focus on (e.g., ["ANVISA", "LGPD"])
            include_analysis: Whether to include analytical insights
            language: Language preference (pt-BR for Brazilian Portuguese)
            max_citations: Maximum number of citations to return
        """
        start_time = time.time()
        
        try:
            # Enhance query with regulatory context
            enhanced_query = self._enhance_query(query, search_type, focus_areas, language)
            
            # Execute Perplexity search
            result = await self._search_with_sonar_pro(
                enhanced_query,
                include_analysis,
                max_citations
            )
            
            # Process and structure results for regulatory use
            processed_result = self._process_for_regulatory_use(result, query, search_type)
            
            return ToolResult(
                success=True,
                output=processed_result.dict(),
                execution_time=time.time() - start_time,
                metadata={
                    "model": self.model,
                    "search_type": search_type,
                    "citations_count": len(processed_result.citations),
                    "confidence": processed_result.confidence_score,
                }
            )
            
        except Exception as e:
            logger.error("perplexity_search_failed", error=str(e), query=query[:100])
            return ToolResult(
                success=False,
                output=None,
                error=f"Perplexity search failed: {str(e)}",
                execution_time=time.time() - start_time,
            )

    def _enhance_query(
        self,
        query: str,
        search_type: str,
        focus_areas: Optional[List[str]],
        language: str
    ) -> str:
        """Enhance query with regulatory context and specifications."""
        enhanced_parts = [self.regulatory_context]
        
        # Add search type specific instructions
        search_instructions = {
            "regulatory": "Focus on official regulatory requirements, compliance standards, and government publications.",
            "legal": "Emphasize legal frameworks, jurisprudence, laws, and court decisions.",
            "technical": "Prioritize technical specifications, standards, and implementation guidelines.",
            "market": "Include market analysis, competitor practices, and industry trends.",
        }
        
        if search_type in search_instructions:
            enhanced_parts.append(search_instructions[search_type])
        
        # Add focus areas
        if focus_areas:
            areas_str = ", ".join(focus_areas)
            enhanced_parts.append(f"Pay special attention to these regulatory bodies/areas: {areas_str}")
        
        # Add language preference
        if language == "pt-BR":
            enhanced_parts.append("Prioritize Brazilian Portuguese sources and provide responses in Portuguese when possible.")
        
        # Add the original query
        enhanced_parts.append(f"\nSearch Query: {query}")
        
        # Add citation requirements
        enhanced_parts.append("\nProvide comprehensive citations with URLs, publication dates, and regulatory body information.")
        
        return "\n\n".join(enhanced_parts)

    async def _search_with_sonar_pro(
        self,
        query: str,
        include_analysis: bool,
        max_citations: int
    ) -> Dict[str, Any]:
        """Execute the actual Perplexity API call."""
        if not self.api_key:
            raise ValueError("Perplexity API key not configured")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Prepare the request payload
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a regulatory research expert providing accurate, well-cited information."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "return_citations": True,
            "return_images": False,
            "return_related_questions": True,
            "search_recency_filter": "year",  # Focus on recent regulatory changes
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Perplexity API error: {response.status} - {error_text}")
                
                return await response.json()

    def _process_for_regulatory_use(
        self,
        perplexity_result: Dict[str, Any],
        original_query: str,
        search_type: str
    ) -> PerplexitySearchResult:
        """Process Perplexity results for regulatory compliance use."""
        # Extract the main response
        choices = perplexity_result.get("choices", [])
        if not choices:
            raise ValueError("No response from Perplexity")
            
        message = choices[0].get("message", {})
        content = message.get("content", "")
        
        # Extract citations
        citations = perplexity_result.get("citations", [])
        processed_citations = []
        
        for citation in citations:
            processed_citation = {
                "title": citation.get("title", ""),
                "url": citation.get("url", ""),
                "snippet": citation.get("snippet", ""),
                "published_date": citation.get("published_date"),
                "source_type": self._classify_source(citation.get("url", "")),
                "regulatory_body": self._extract_regulatory_body(citation.get("url", "")),
                "relevance_score": citation.get("score", 0.0),
            }
            processed_citations.append(processed_citation)
        
        # Sort citations by relevance and source type
        processed_citations.sort(
            key=lambda x: (
                x["source_type"] == "official",
                x["relevance_score"]
            ),
            reverse=True
        )
        
        # Extract source URLs
        source_urls = [c["url"] for c in processed_citations if c["url"]]
        
        # Calculate confidence score based on citations and source quality
        confidence_score = self._calculate_confidence(processed_citations, search_type)
        
        # Create structured result
        return PerplexitySearchResult(
            answer=content,
            citations=processed_citations,
            sources=source_urls,
            confidence_score=confidence_score,
            search_query=original_query,
            metadata={
                "search_type": search_type,
                "model": self.model,
                "total_citations": len(citations),
                "official_sources": sum(1 for c in processed_citations if c["source_type"] == "official"),
                "related_questions": perplexity_result.get("related_questions", []),
            }
        )

    def _classify_source(self, url: str) -> str:
        """Classify the source type based on URL."""
        url_lower = url.lower()
        
        # Official Brazilian government sources
        official_domains = [
            "gov.br", "anvisa.gov.br", "anatel.gov.br", "in.gov.br",
            "planalto.gov.br", "senado.leg.br", "camara.leg.br",
            "stf.jus.br", "stj.jus.br", "trf", "cvm.gov.br",
            "receita.fazenda.gov.br", "bcb.gov.br", "inmetro.gov.br"
        ]
        
        # Legal and jurisprudence sources
        legal_domains = [
            "jusbrasil.com.br", "conjur.com.br", "migalhas.com.br",
            "direitonet.com.br"
        ]
        
        # Academic and research sources
        academic_domains = [
            "scielo.br", "scholar.google", "repositorio", ".edu.br",
            "periodicos.capes.gov.br"
        ]
        
        if any(domain in url_lower for domain in official_domains):
            return "official"
        elif any(domain in url_lower for domain in legal_domains):
            return "legal"
        elif any(domain in url_lower for domain in academic_domains):
            return "academic"
        else:
            return "general"

    def _extract_regulatory_body(self, url: str) -> Optional[str]:
        """Extract regulatory body from URL."""
        url_lower = url.lower()
        
        regulatory_mapping = {
            "anvisa": "ANVISA",
            "anatel": "ANATEL",
            "anac": "ANAC",
            "aneel": "ANEEL",
            "ans": "ANS",
            "anp": "ANP",
            "ancine": "ANCINE",
            "antaq": "ANTAQ",
            "antt": "ANTT",
            "cvm": "CVM",
            "bcb": "Banco Central",
            "inmetro": "INMETRO",
            "mapa": "MAPA",
            "cade": "CADE",
            "inpi": "INPI",
        }
        
        for key, body in regulatory_mapping.items():
            if key in url_lower:
                return body
                
        return None

    def _calculate_confidence(self, citations: List[Dict[str, Any]], search_type: str) -> float:
        """Calculate confidence score based on citation quality."""
        if not citations:
            return 0.0
            
        # Base confidence
        confidence = 0.5
        
        # Boost for official sources
        official_count = sum(1 for c in citations if c["source_type"] == "official")
        confidence += min(0.3, official_count * 0.05)
        
        # Boost for regulatory body sources
        regulatory_count = sum(1 for c in citations if c.get("regulatory_body"))
        confidence += min(0.15, regulatory_count * 0.03)
        
        # Boost for recent sources (within last year)
        recent_count = sum(1 for c in citations if self._is_recent(c.get("published_date")))
        confidence += min(0.05, recent_count * 0.01)
        
        # Ensure confidence is between 0 and 1
        return min(1.0, max(0.0, confidence))

    def _is_recent(self, date_str: Optional[str], days: int = 365) -> bool:
        """Check if a date string represents a recent date."""
        if not date_str:
            return False
            
        try:
            # Parse various date formats
            from dateutil import parser
            date = parser.parse(date_str)
            return (datetime.now() - date).days <= days
        except:
            return False

    def get_schema(self) -> Dict[str, Any]:
        """Get tool parameter schema."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query for regulatory research",
                },
                "search_type": {
                    "type": "string",
                    "enum": ["regulatory", "legal", "technical", "market"],
                    "default": "regulatory",
                    "description": "Type of search to perform",
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific regulatory areas to focus on (e.g., ANVISA, LGPD)",
                },
                "include_analysis": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include analytical insights in the response",
                },
                "language": {
                    "type": "string",
                    "default": "pt-BR",
                    "description": "Language preference for sources and response",
                },
                "max_citations": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum number of citations to return",
                },
            },
            "required": ["query"],
        }

    async def search_regulatory_updates(
        self,
        regulatory_bodies: List[str],
        days_back: int = 30,
        keywords: Optional[List[str]] = None
    ) -> ToolResult:
        """
        Specialized method to search for recent regulatory updates.
        
        Args:
            regulatory_bodies: List of regulatory bodies to monitor (e.g., ["ANVISA", "ANATEL"])
            days_back: Number of days to look back
            keywords: Optional keywords to filter results
        """
        # Build specialized query for regulatory updates
        query_parts = [
            f"Mudanças regulatórias recentes últimos {days_back} dias",
            f"Órgãos: {', '.join(regulatory_bodies)}",
        ]
        
        if keywords:
            query_parts.append(f"Palavras-chave: {', '.join(keywords)}")
            
        query_parts.extend([
            "Incluir: RDCs, Resoluções, Portarias, Instruções Normativas",
            "Focar em: novas regulamentações, alterações, consultas públicas, prazos de adequação"
        ])
        
        full_query = "\n".join(query_parts)
        
        return await self.execute(
            query=full_query,
            search_type="regulatory",
            focus_areas=regulatory_bodies,
            include_analysis=True,
            max_citations=30
        )

    async def analyze_compliance_requirements(
        self,
        product_or_service: str,
        regulatory_framework: str,
        company_context: Optional[str] = None
    ) -> ToolResult:
        """
        Analyze specific compliance requirements for a product or service.
        
        Args:
            product_or_service: Description of the product or service
            regulatory_framework: The regulatory framework to analyze (e.g., "ANVISA RDC 301/2019")
            company_context: Optional company-specific context
        """
        query_parts = [
            f"Análise detalhada de requisitos de conformidade",
            f"Produto/Serviço: {product_or_service}",
            f"Framework regulatório: {regulatory_framework}",
            "Incluir:",
            "- Requisitos obrigatórios específicos",
            "- Documentação necessária",
            "- Prazos e procedimentos",
            "- Penalidades por não conformidade",
            "- Casos práticos e precedentes",
        ]
        
        if company_context:
            query_parts.append(f"Contexto empresarial: {company_context}")
            
        full_query = "\n".join(query_parts)
        
        return await self.execute(
            query=full_query,
            search_type="regulatory",
            include_analysis=True,
            max_citations=25
        )

    async def research_international_harmonization(
        self,
        brazilian_regulation: str,
        target_markets: List[str]
    ) -> ToolResult:
        """
        Research international regulatory harmonization for export/import.
        
        Args:
            brazilian_regulation: The Brazilian regulation to compare
            target_markets: List of target markets (e.g., ["USA", "EU", "MERCOSUL"])
        """
        query = f"""
        Análise comparativa de harmonização regulatória internacional
        
        Regulamentação brasileira: {brazilian_regulation}
        Mercados-alvo: {', '.join(target_markets)}
        
        Analisar:
        - Equivalências regulatórias
        - Acordos de reconhecimento mútuo
        - Diferenças críticas
        - Requisitos adicionais por mercado
        - Processos de certificação internacional
        - Harmonização MERCOSUL se aplicável
        """
        
        return await self.execute(
            query=query,
            search_type="regulatory",
            focus_areas=["harmonização", "comércio internacional", "equivalência"],
            include_analysis=True,
            max_citations=30
        )