# 🚀 Guia Completo de Deploy - Soluto Regulatory Agents

## 📋 Índice
1. [Pré-requisitos](#pré-requisitos)
2. [Configuração Inicial](#configuração-inicial)
3. [Deploy Local (Desenvolvimento)](#deploy-local-desenvolvimento)
4. [Deploy Produção (Docker)](#deploy-produção-docker)
5. [Testando o Sistema](#testando-o-sistema)
6. [Monitoramento e Observabilidade](#monitoramento-e-observabilidade)
7. [Troubleshooting](#troubleshooting)
8. [Melhores Práticas](#melhores-práticas)

## 🔧 Pré-requisitos

### Software Necessário
- **Docker**: 24.0+ e Docker Compose 2.20+
- **Python**: 3.11+ (para desenvolvimento local)
- **Git**: 2.40+
- **Node.js**: 20+ (opcional, para ferramentas de desenvolvimento)

### Recursos Mínimos
- **CPU**: 4 cores
- **RAM**: 8GB (16GB recomendado)
- **Disco**: 20GB livres
- **Portas**: 2024, 9090, 3000, 6379, 5432

## 🛠️ Configuração Inicial

### 1. Clone o Repositório
```bash
git clone https://github.com/luis1402-02/soluto-regulatory-agents.git
cd soluto-regulatory-agents
```

### 2. Configure as Variáveis de Ambiente
```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite o arquivo .env
nano .env
```

#### Variáveis Obrigatórias:
```env
# APIs Principais (OBRIGATÓRIO)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxx

# LangSmith (ALTAMENTE RECOMENDADO)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__xxxxxxxxxxxxx
LANGCHAIN_PROJECT=soluto-regulatory-agents
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# Configurações do Sistema
APP_ENV=production
LOG_LEVEL=INFO
```

#### Variáveis Opcionais:
```env
# Redis (usar valores padrão se não alterado)
REDIS_URL=redis://redis:6379/0

# PostgreSQL (usar valores padrão se não alterado)
DATABASE_URL=postgresql+asyncpg://soluto:soluto123@postgres:5432/soluto_regulatory

# Segurança
SECRET_KEY=sua-chave-secreta-aqui
API_RATE_LIMIT=100
```

### 3. Crie Diretórios Necessários
```bash
# Já criados, mas verificar
mkdir -p logs data nginx/ssl
```

## 🏃 Deploy Local (Desenvolvimento)

### 1. Ambiente Virtual Python
```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 2. Executar Localmente
```bash
# Modo desenvolvimento
python -m src.cli --help

# Servidor de desenvolvimento
uvicorn src.api.app:create_app --factory --reload --port 2024
```

## 🐳 Deploy Produção (Docker)

### 1. Deploy Rápido (Recomendado)
```bash
# Dar permissão ao script
chmod +x scripts/quick-start.sh

# Executar deploy completo
./scripts/quick-start.sh
```

### 2. Deploy Manual Detalhado
```bash
# Build das imagens
docker-compose -f docker-compose.prod.yml build

# Iniciar todos os serviços
docker-compose -f docker-compose.prod.yml up -d

# Verificar status
docker-compose -f docker-compose.prod.yml ps

# Ver logs em tempo real
docker-compose -f docker-compose.prod.yml logs -f
```

### 3. Validar Deploy
```bash
# Executar script de validação
python scripts/validate.py

# Ou verificar manualmente
curl http://localhost:2024/health
```

## 🧪 Testando o Sistema

### 1. Teste via API REST
```bash
# Análise simples
curl -X POST http://localhost:2024/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Quais são as principais regulamentações do Banco Central para fintechs em 2025?",
    "context": "Análise para startup fintech",
    "priority": "high"
  }'

# Análise com contexto detalhado
curl -X POST http://localhost:2024/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Requisitos ANVISA para registro de dispositivo médico classe II",
    "context": {
      "company": "MedTech Innovations",
      "product_type": "Monitor cardíaco",
      "target_market": "Brasil"
    },
    "priority": "critical"
  }'
```

### 2. Teste via LangServe Playground
1. Acesse: http://localhost:2024/regulatory/playground
2. Interface visual para testar queries
3. Visualize responses em tempo real
4. Teste diferentes cenários regulatórios

### 3. Teste via CLI
```bash
# Análise via CLI
docker exec -it soluto-app python -m src.cli analyze \
  "Compliance para pagamentos instantâneos PIX"

# Chat interativo
docker exec -it soluto-app python -m src.cli chat
```

### 4. Teste de Carga
```bash
# Instalar k6 (se não tiver)
brew install k6  # Mac
# ou
sudo apt-get install k6  # Ubuntu

# Executar teste de carga
k6 run scripts/load-test.js
```

## 📊 Monitoramento e Observabilidade

### 1. Dashboard de Monitoramento
- **URL**: http://localhost:2024/monitoring/dashboard
- **Recursos**:
  - Visualização em tempo real do fluxo de agentes
  - Métricas de performance
  - Status de cada agente
  - Logs de execução

### 2. LangSmith (Recomendado)
1. Acesse: https://smith.langchain.com
2. Faça login com sua conta
3. Navegue até o projeto "soluto-regulatory-agents"
4. Visualize:
   - Traces completos de execução
   - Latência por agente
   - Tokens utilizados
   - Erros e debugging

### 3. Prometheus
- **URL**: http://localhost:9090
- **Queries úteis**:
  ```promql
  # Requisições por minuto
  rate(http_requests_total[1m])
  
  # Latência média
  histogram_quantile(0.95, http_request_duration_seconds_bucket)
  
  # Uso de memória
  process_resident_memory_bytes
  ```

### 4. Grafana
- **URL**: http://localhost:3000
- **Login**: admin/admin (altere na primeira vez)
- **Dashboards pré-configurados**:
  - System Overview
  - Agent Performance
  - API Metrics

### 5. Logs
```bash
# Logs da aplicação
docker-compose -f docker-compose.prod.yml logs -f app

# Logs específicos
tail -f logs/app.log
tail -f logs/errors.log
tail -f logs/langchain.log

# Logs estruturados (JSON)
docker logs soluto-app 2>&1 | jq '.'
```

## 🔧 Troubleshooting

### Problemas Comuns

#### 1. Porta 2024 em Uso
```bash
# Verificar processo
sudo lsof -i :2024

# Matar processo
sudo kill -9 <PID>

# Ou mudar porta no .env
APP_PORT=3024
```

#### 2. Erro de API Key
```bash
# Verificar variáveis
docker exec soluto-app env | grep API_KEY

# Recarregar após mudança
docker-compose -f docker-compose.prod.yml restart app
```

#### 3. Memória Insuficiente
```bash
# Verificar uso
docker stats

# Ajustar limites no docker-compose.prod.yml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 4G
```

#### 4. Erro de Conexão Redis/PostgreSQL
```bash
# Verificar conectividade
docker exec soluto-app ping redis
docker exec soluto-app pg_isready -h postgres

# Reiniciar serviços
docker-compose -f docker-compose.prod.yml restart redis postgres
```

### Debug Avançado

#### 1. Modo Debug
```bash
# Ativar debug no .env
LOG_LEVEL=DEBUG
LANGCHAIN_VERBOSE=true

# Reiniciar
docker-compose -f docker-compose.prod.yml restart app
```

#### 2. Shell Interativo
```bash
# Acessar container
docker exec -it soluto-app bash

# Python shell
docker exec -it soluto-app python
>>> from src.graph import RegulatoryMultiAgentSystem
>>> system = RegulatoryMultiAgentSystem()
```

#### 3. Análise de Performance
```bash
# Profile com py-spy
docker exec soluto-app py-spy top --pid 1

# Análise de memória
docker exec soluto-app python -m memory_profiler src/cli.py
```

## 🚀 Melhores Práticas

### 1. Segurança
- ✅ Sempre use HTTPS em produção
- ✅ Mantenha API keys seguras (use secrets manager)
- ✅ Configure rate limiting
- ✅ Use autenticação para APIs públicas
- ✅ Audite logs regularmente

### 2. Performance
- ✅ Configure cache Redis adequadamente
- ✅ Use connection pooling para DB
- ✅ Monitore uso de tokens OpenAI/Perplexity
- ✅ Configure workers baseado em CPU cores
- ✅ Use CDN para assets estáticos

### 3. Confiabilidade
- ✅ Configure health checks
- ✅ Use restart policies
- ✅ Implemente circuit breakers
- ✅ Configure backups automáticos
- ✅ Teste disaster recovery

### 4. Observabilidade
- ✅ Use structured logging
- ✅ Configure alertas no Grafana
- ✅ Monitore custos de API
- ✅ Track SLIs/SLOs
- ✅ Implemente distributed tracing

## 📚 Recursos Adicionais

### Documentação
- [README Principal](README.md)
- [Arquitetura do Sistema](docs/ARCHITECTURE.md)
- [API Reference](http://localhost:2024/api/docs)

### Suporte
- **Issues**: https://github.com/luis1402-02/soluto-regulatory-agents/issues
- **Discussions**: https://github.com/luis1402-02/soluto-regulatory-agents/discussions

### Comandos Úteis
```bash
# Status completo
./scripts/status.sh

# Backup do sistema
./scripts/backup.sh

# Update do sistema
git pull && ./scripts/deploy.sh

# Limpeza completa
docker-compose -f docker-compose.prod.yml down -v
docker system prune -af
```

## 🎯 Checklist de Deploy

### Pré-Deploy
- [ ] Configurar todas as API keys no .env
- [ ] Verificar portas disponíveis
- [ ] Garantir espaço em disco suficiente
- [ ] Fazer backup de dados existentes

### Deploy
- [ ] Executar quick-start.sh
- [ ] Verificar health check
- [ ] Executar validação
- [ ] Testar uma query básica

### Pós-Deploy
- [ ] Configurar monitoramento
- [ ] Testar LangSmith tracing
- [ ] Configurar alertas
- [ ] Documentar configurações específicas

---

**🎉 Parabéns! Seu sistema Soluto Regulatory Agents está pronto para uso!**

Para qualquer dúvida ou problema, consulte a seção de Troubleshooting ou abra uma issue no GitHub.