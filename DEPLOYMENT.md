# 🚀 Guia de Deploy - Sistema Soluto Regulatory Agents

## 1. Configuração Inicial

### 1.1 Clone o Repositório
```bash
git clone https://github.com/luis1402-02/soluto-regulatory-agents.git
cd soluto-regulatory-agents
```

### 1.2 Configure as Variáveis de Ambiente
```bash
cp .env.example .env
```

Edite o arquivo `.env` e adicione suas chaves:
```env
# APIs Principais
OPENAI_API_KEY=sua-chave-openai
PERPLEXITY_API_KEY=sua-chave-perplexity

# LangSmith (Opcional mas Recomendado)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=sua-chave-langsmith
LANGCHAIN_PROJECT=soluto-regulatory-agents
```

## 2. Deploy com Docker

### 2.1 Deploy Completo (Recomendado)
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### 2.2 Ou Deploy Manual
```bash
# Build e start dos containers
docker-compose -f docker-compose.prod.yml up -d --build

# Verificar logs
docker-compose -f docker-compose.prod.yml logs -f app
```

## 3. Validação do Sistema

### 3.1 Executar Script de Validação
```bash
python scripts/validate.py
```

### 3.2 Verificações Manuais
- **API Principal**: http://localhost:2024/health
- **Dashboard de Monitoramento**: http://localhost:2024/monitoring/dashboard
- **Documentação API**: http://localhost:2024/api/docs
- **LangServe Playground**: http://localhost:2024/regulatory/playground

## 4. Testando o Sistema

### 4.1 Via API (curl)
```bash
curl -X POST http://localhost:2024/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Quais são as principais regulamentações do Banco Central para fintechs em 2025?",
    "context": "Análise para empresa fintech",
    "priority": "high"
  }'
```

### 4.2 Via LangServe Playground
1. Acesse: http://localhost:2024/regulatory/playground
2. Teste com queries regulatórias
3. Observe o fluxo dos agentes no dashboard

### 4.3 Via Interface Web (se implementada)
Acesse: http://localhost:2024

## 5. Monitoramento

### 5.1 Dashboard em Tempo Real
- **URL**: http://localhost:2024/monitoring/dashboard
- **Recursos**:
  - Visualização do fluxo de agentes (Mermaid.js)
  - Métricas de performance
  - Logs em tempo real
  - Status dos agentes

### 5.2 Prometheus & Grafana
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### 5.3 LangSmith
- Acesse: https://smith.langchain.com
- Verifique traces do projeto "soluto-regulatory-agents"

## 6. Comandos Úteis

### Ver Logs
```bash
# Todos os serviços
docker-compose -f docker-compose.prod.yml logs -f

# Apenas aplicação
docker-compose -f docker-compose.prod.yml logs -f app

# Apenas Redis
docker-compose -f docker-compose.prod.yml logs -f redis
```

### Reiniciar Serviços
```bash
# Reiniciar tudo
docker-compose -f docker-compose.prod.yml restart

# Reiniciar apenas app
docker-compose -f docker-compose.prod.yml restart app
```

### Parar Sistema
```bash
docker-compose -f docker-compose.prod.yml down
```

### Limpar e Reconstruir
```bash
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d --build
```

## 7. Troubleshooting

### Porta 2024 em Uso
```bash
# Verificar processo usando a porta
sudo lsof -i :2024

# Matar processo
sudo kill -9 <PID>
```

### Erro de Permissão Docker
```bash
# Adicionar usuário ao grupo docker
sudo usermod -aG docker $USER
# Fazer logout e login novamente
```

### API Keys Inválidas
- Verifique o arquivo `.env`
- Confirme que as chaves estão corretas
- Reinicie os containers após mudanças

## 8. Próximos Passos

1. **Testar Fluxos Principais**:
   - Análise de compliance bancário
   - Pesquisa de regulamentações
   - Geração de relatórios

2. **Configurar Alertas**:
   - Configure alertas no Grafana
   - Configure webhooks para notificações

3. **Otimizar Performance**:
   - Ajuste limites de memória no docker-compose
   - Configure cache Redis adequadamente

## 9. Suporte

- **Repositório**: https://github.com/luis1402-02/soluto-regulatory-agents
- **Issues**: https://github.com/luis1402-02/soluto-regulatory-agents/issues
- **Documentação**: Ver README.md para mais detalhes