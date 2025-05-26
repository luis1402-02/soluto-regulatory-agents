#!/bin/bash

# Status Script - Verifica o status completo do sistema

set -e

echo "🔍 Verificando Status do Sistema Soluto Regulatory Agents"
echo "========================================================"
echo ""

# Função para verificar serviço
check_service() {
    local service=$1
    local port=$2
    local url=$3
    
    echo -n "Verificando $service... "
    
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo "✅ OK"
        return 0
    else
        echo "❌ FALHOU"
        return 1
    fi
}

# Verificar se Docker está rodando
echo "🐳 Docker Status:"
if docker info > /dev/null 2>&1; then
    echo "✅ Docker está rodando"
else
    echo "❌ Docker não está rodando"
    exit 1
fi

echo ""

# Verificar containers
echo "📦 Containers Status:"
docker-compose -f docker-compose.prod.yml ps

echo ""

# Verificar serviços
echo "🌐 Serviços:"
check_service "API Principal" "2024" "http://localhost:2024/health"
check_service "Prometheus" "9090" "http://localhost:9090/-/healthy"
check_service "Grafana" "3000" "http://localhost:3000/api/health"
check_service "Redis" "6379" "http://localhost:2024/health" # Via app
check_service "PostgreSQL" "5432" "http://localhost:2024/health" # Via app

echo ""

# Verificar uso de recursos
echo "💻 Uso de Recursos:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep -E "(soluto|CONTAINER)"

echo ""

# Verificar logs recentes
echo "📝 Logs Recentes (últimas 10 linhas):"
docker-compose -f docker-compose.prod.yml logs --tail=10 app | grep -E "(ERROR|WARNING|INFO)" || echo "Sem logs recentes"

echo ""

# Verificar API keys
echo "🔑 Configuração de API Keys:"
if docker exec soluto-app env | grep -q "OPENAI_API_KEY="; then
    echo "✅ OPENAI_API_KEY configurada"
else
    echo "❌ OPENAI_API_KEY não configurada"
fi

if docker exec soluto-app env | grep -q "PERPLEXITY_API_KEY="; then
    echo "✅ PERPLEXITY_API_KEY configurada"
else
    echo "❌ PERPLEXITY_API_KEY não configurada"
fi

if docker exec soluto-app env | grep -q "LANGCHAIN_API_KEY="; then
    echo "✅ LANGCHAIN_API_KEY configurada"
else
    echo "⚠️  LANGCHAIN_API_KEY não configurada (opcional)"
fi

echo ""

# Verificar espaço em disco
echo "💾 Espaço em Disco:"
df -h | grep -E "(/|/var/lib/docker)" | awk '{print $6 " - " $5 " usado de " $2}'

echo ""

# URLs de acesso
echo "🔗 URLs de Acesso:"
echo "   - API Principal: http://localhost:2024"
echo "   - API Docs: http://localhost:2024/api/docs"
echo "   - Dashboard: http://localhost:2024/monitoring/dashboard"
echo "   - LangServe: http://localhost:2024/regulatory/playground"
echo "   - Prometheus: http://localhost:9090"
echo "   - Grafana: http://localhost:3000"

echo ""
echo "========================================================"
echo "✅ Verificação completa!"