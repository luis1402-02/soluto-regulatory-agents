"""Database service for regulatory information."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from ..config import get_settings
from ..utils import get_logger

logger = get_logger(__name__)

Base = declarative_base()


class Regulation(Base):
    """Regulation model."""

    __tablename__ = "regulations"

    id = Column(Integer, primary_key=True)
    agency = Column(String(50), nullable=False)
    number = Column(String(100), nullable=False, unique=True)
    title = Column(String(500), nullable=False)
    type = Column(String(50))  # RDC, IN, Portaria, etc.
    publication_date = Column(DateTime)
    effective_date = Column(DateTime)
    status = Column(String(50))  # Em vigor, Revogada, Alterada
    summary = Column(Text)
    full_text_url = Column(String(500))
    tags = Column(Text)  # JSON array
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ComplianceTemplate(Base):
    """Compliance template model."""

    __tablename__ = "compliance_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100))
    agency = Column(String(50))
    description = Column(Text)
    template_data = Column(Text)  # JSON
    version = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RegulatoryUpdate(Base):
    """Regulatory update/news model."""

    __tablename__ = "regulatory_updates"

    id = Column(Integer, primary_key=True)
    agency = Column(String(50))
    title = Column(String(500), nullable=False)
    summary = Column(Text)
    url = Column(String(500))
    impact_level = Column(String(20))  # High, Medium, Low
    tags = Column(Text)  # JSON array
    published_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class RegulationDatabase:
    """Database service for regulatory information."""

    def __init__(self):
        """Initialize database service."""
        self.settings = get_settings()
        self.engine = None
        self.async_session = None

    async def initialize(self):
        """Initialize database connection."""
        self.engine = create_async_engine(
            self.settings.database_url,
            echo=False,
            future=True,
        )
        
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("database_initialized")

    async def close(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()

    async def add_regulation(
        self,
        agency: str,
        number: str,
        title: str,
        **kwargs,
    ) -> Regulation:
        """Add a new regulation to database."""
        async with self.async_session() as session:
            regulation = Regulation(
                agency=agency,
                number=number,
                title=title,
                **kwargs,
            )
            session.add(regulation)
            await session.commit()
            await session.refresh(regulation)
            
            logger.info(
                "regulation_added",
                agency=agency,
                number=number,
            )
            
            return regulation

    async def search_regulations(
        self,
        query: Optional[str] = None,
        agency: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Regulation]:
        """Search regulations in database."""
        async with self.async_session() as session:
            stmt = select(Regulation)
            
            if agency:
                stmt = stmt.where(Regulation.agency == agency)
            
            if status:
                stmt = stmt.where(Regulation.status == status)
            
            if query:
                # Simple text search - in production use full-text search
                stmt = stmt.where(
                    Regulation.title.ilike(f"%{query}%") |
                    Regulation.summary.ilike(f"%{query}%")
                )
            
            stmt = stmt.limit(limit)
            
            result = await session.execute(stmt)
            regulations = result.scalars().all()
            
            return regulations

    async def get_regulation(self, number: str) -> Optional[Regulation]:
        """Get regulation by number."""
        async with self.async_session() as session:
            stmt = select(Regulation).where(Regulation.number == number)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def add_template(
        self,
        name: str,
        category: str,
        template_data: Dict[str, Any],
        **kwargs,
    ) -> ComplianceTemplate:
        """Add compliance template."""
        async with self.async_session() as session:
            template = ComplianceTemplate(
                name=name,
                category=category,
                template_data=json.dumps(template_data),
                **kwargs,
            )
            session.add(template)
            await session.commit()
            await session.refresh(template)
            
            return template

    async def get_templates(
        self,
        category: Optional[str] = None,
        agency: Optional[str] = None,
    ) -> List[ComplianceTemplate]:
        """Get compliance templates."""
        async with self.async_session() as session:
            stmt = select(ComplianceTemplate)
            
            if category:
                stmt = stmt.where(ComplianceTemplate.category == category)
            
            if agency:
                stmt = stmt.where(ComplianceTemplate.agency == agency)
            
            result = await session.execute(stmt)
            templates = result.scalars().all()
            
            return templates

    async def add_regulatory_update(
        self,
        title: str,
        agency: str,
        **kwargs,
    ) -> RegulatoryUpdate:
        """Add regulatory update/news."""
        async with self.async_session() as session:
            update = RegulatoryUpdate(
                title=title,
                agency=agency,
                **kwargs,
            )
            session.add(update)
            await session.commit()
            await session.refresh(update)
            
            return update

    async def get_recent_updates(
        self,
        days: int = 30,
        agency: Optional[str] = None,
        impact_level: Optional[str] = None,
    ) -> List[RegulatoryUpdate]:
        """Get recent regulatory updates."""
        async with self.async_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            stmt = select(RegulatoryUpdate).where(
                RegulatoryUpdate.published_date >= cutoff_date
            )
            
            if agency:
                stmt = stmt.where(RegulatoryUpdate.agency == agency)
            
            if impact_level:
                stmt = stmt.where(RegulatoryUpdate.impact_level == impact_level)
            
            stmt = stmt.order_by(RegulatoryUpdate.published_date.desc())
            
            result = await session.execute(stmt)
            updates = result.scalars().all()
            
            return updates

    async def populate_initial_data(self):
        """Populate database with initial regulatory data."""
        # Add sample regulations
        sample_regulations = [
            {
                "agency": "ANVISA",
                "number": "RDC 301/2019",
                "title": "Dispõe sobre as Diretrizes Gerais de Boas Práticas de Fabricação de Medicamentos",
                "type": "RDC",
                "status": "Em vigor",
                "summary": "Estabelece os requisitos mínimos de Boas Práticas de Fabricação de Medicamentos para Uso Humano",
            },
            {
                "agency": "ANVISA",
                "number": "RDC 430/2020",
                "title": "Dispõe sobre o registro e a notificação de produtos de higiene pessoal, cosméticos e perfumes",
                "type": "RDC",
                "status": "Em vigor",
                "summary": "Define critérios para registro e notificação de produtos cosméticos",
            },
            {
                "agency": "ANATEL",
                "number": "Resolução 715/2019",
                "title": "Aprova o Regulamento de Avaliação da Conformidade e de Homologação de Produtos para Telecomunicações",
                "type": "Resolução",
                "status": "Em vigor",
                "summary": "Estabelece os procedimentos para homologação de produtos de telecomunicações",
            },
        ]
        
        for reg_data in sample_regulations:
            try:
                await self.add_regulation(**reg_data)
            except Exception as e:
                logger.debug("regulation_exists", number=reg_data["number"])
        
        # Add sample templates
        sample_templates = [
            {
                "name": "Checklist BPF ANVISA",
                "category": "BPF",
                "agency": "ANVISA",
                "description": "Checklist para auditoria de Boas Práticas de Fabricação",
                "template_data": {
                    "sections": [
                        {
                            "name": "Documentação",
                            "items": [
                                "Manual de Qualidade",
                                "POPs atualizados",
                                "Registros de treinamento",
                            ],
                        },
                        {
                            "name": "Instalações",
                            "items": [
                                "Áreas classificadas",
                                "Sistemas de HVAC",
                                "Controle de contaminação",
                            ],
                        },
                    ],
                },
            },
        ]
        
        for template_data in sample_templates:
            try:
                await self.add_template(**template_data)
            except Exception as e:
                logger.debug("template_exists", name=template_data["name"])
        
        logger.info("initial_data_populated")