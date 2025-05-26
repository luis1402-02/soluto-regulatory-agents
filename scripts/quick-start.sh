#!/bin/bash

# Quick Start Script - Soluto Regulatory Agents
# Este script automatiza o processo de deploy inicial

set -e

echo "🚀 Iniciando Deploy do Sistema Soluto Regulatory Agents..."
echo "=================================================="

# Verificar se .env existe
if [ ! -f .env ]; then
    echo "📝 Criando arquivo .env..."
    cp .env.example .env
    echo "⚠️  IMPORTANTE: Edite o arquivo .env e adicione suas API keys!"
    echo "   - OPENAI_API_KEY"
    echo "   - PERPLEXITY_API_KEY"
    echo "   - LANGCHAIN_API_KEY (opcional)"
    echo ""
    echo "Pressione ENTER após configurar o .env..."
    read
fi

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não encontrado. Por favor, instale o Docker primeiro."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não encontrado. Por favor, instale o Docker Compose primeiro."
    exit 1
fi

# Dar permissão aos scripts
echo "🔧 Configurando permissões..."
chmod +x scripts/*.sh

# Parar containers existentes
echo "🛑 Parando containers existentes..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

# Build e deploy
echo "🏗️  Construindo imagens Docker..."
docker-compose -f docker-compose.prod.yml build

echo "🚀 Iniciando containers..."
docker-compose -f docker-compose.prod.yml up -d

# Aguardar serviços iniciarem
echo "⏳ Aguardando serviços iniciarem..."
sleep 10

# Verificar saúde do sistema
echo "🏥 Verificando saúde do sistema..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -f http://localhost:2024/health &>/dev/null; then
        echo "✅ Sistema está saudável!"
        break
    else
        echo "⏳ Aguardando sistema iniciar... (tentativa $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    fi
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ Sistema não respondeu no tempo esperado."
    echo "Verifique os logs com: docker-compose -f docker-compose.prod.yml logs"
    exit 1
fi

# Executar validação
echo "🔍 Executando validação do sistema..."
python scripts/validate.py || echo "⚠️  Validação falhou - verifique os logs"

echo ""
echo "=================================================="
echo "✅ Deploy Concluído!"
echo "=================================================="
echo ""
echo "🌐 Acesse o sistema em:"
echo "   - API Principal: http://localhost:2024"
echo "   - Dashboard de Monitoramento: http://localhost:2024/monitoring/dashboard"
echo "   - Documentação API: http://localhost:2024/api/docs"
echo "   - LangServe Playground: http://localhost:2024/regulatory/playground"
echo ""
echo "📊 Serviços de Monitoramento:"
echo "   - Prometheus: http://localhost:9090"
echo "   - Grafana: http://localhost:3000 (admin/admin)"
echo ""
echo "🔍 Comandos úteis:"
echo "   - Ver logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "   - Parar sistema: docker-compose -f docker-compose.prod.yml down"
echo "   - Reiniciar: docker-compose -f docker-compose.prod.yml restart"
echo ""
echo "🧪 Teste o sistema com:"
echo "   curl -X POST http://localhost:2024/api/analyze \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"query\": \"Regulamentações do Banco Central para fintechs\"}'"
echo ""