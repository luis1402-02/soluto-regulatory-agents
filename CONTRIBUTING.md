# Contributing to Soluto Regulatory Agents

Obrigado por seu interesse em contribuir para o Soluto Regulatory Agents! 🎉

## Como Contribuir

### 1. Fork e Clone

```bash
# Fork o repositório no GitHub
# Clone seu fork
git clone https://github.com/YOUR_USERNAME/soluto-regulatory-agents.git
cd soluto-regulatory-agents
```

### 2. Setup de Desenvolvimento

```bash
# Crie um ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale dependências de desenvolvimento
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configure pre-commit hooks
pre-commit install
```

### 3. Crie uma Branch

```bash
# Crie uma branch para sua feature/fix
git checkout -b feature/minha-nova-feature
# ou
git checkout -b fix/correcao-de-bug
```

### 4. Faça suas Alterações

- Siga o estilo de código existente
- Adicione testes para novas funcionalidades
- Atualize a documentação se necessário
- Mantenha commits atômicos e bem descritos

### 5. Teste suas Alterações

```bash
# Execute os testes
pytest tests/

# Verifique o código
ruff check src/
mypy src/

# Formate o código
black src/
isort src/
```

### 6. Commit e Push

```bash
# Commit com mensagem descritiva
git commit -m "feat: adiciona suporte para nova API ANVISA"

# Push para seu fork
git push origin feature/minha-nova-feature
```

### 7. Abra um Pull Request

- Vá para o repositório original no GitHub
- Clique em "New Pull Request"
- Descreva suas alterações detalhadamente
- Aguarde revisão

## Padrões de Código

### Python
- Use type hints sempre que possível
- Docstrings em formato Google
- Máximo 88 caracteres por linha
- Imports organizados com isort

### Commits
Seguimos Conventional Commits:
- `feat:` nova funcionalidade
- `fix:` correção de bug
- `docs:` documentação
- `style:` formatação
- `refactor:` refatoração
- `test:` testes
- `chore:` tarefas gerais

### Testes
- Mínimo 80% de cobertura
- Use pytest fixtures
- Mock APIs externas
- Teste casos de erro

## Reportando Issues

Use os templates de issue:
- **Bug Report**: Para reportar problemas
- **Feature Request**: Para sugerir melhorias
- **Question**: Para dúvidas

## Code of Conduct

Seja respeitoso e profissional. Contribuições de todos são bem-vindas!

## Dúvidas?

Abra uma [Discussion](https://github.com/YOUR_USERNAME/soluto-regulatory-agents/discussions) no GitHub.

Obrigado por contribuir! 🚀