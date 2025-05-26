#!/bin/bash

echo "🔧 Resolvendo autenticação do GitHub"
echo "===================================="
echo ""

echo "⚠️  Parece que há um problema de autenticação."
echo "   Username no repositório: luis1402-02"
echo "   Username tentando push: luis1402-2002"
echo ""
echo "Vamos resolver isso!"
echo ""

# Opções para resolver
echo "Escolha uma opção:"
echo ""
echo "1️⃣  Opção 1: Usar Personal Access Token (RECOMENDADO)"
echo "   - Mais seguro e simples"
echo "   - Funciona sempre"
echo ""
echo "2️⃣  Opção 2: Usar SSH ao invés de HTTPS"
echo "   - Requer configurar chave SSH"
echo ""
echo "3️⃣  Opção 3: Corrigir o username"
echo "   - Se o repositório foi criado com outro usuário"
echo ""

read -p "Digite sua escolha (1, 2 ou 3): " choice

case $choice in
    1)
        echo ""
        echo "📝 Configurando com Personal Access Token"
        echo ""
        echo "1. Vá para: https://github.com/settings/tokens/new"
        echo "2. Crie um token com permissões:"
        echo "   ✅ repo (todas as opções)"
        echo "   ✅ workflow (opcional)"
        echo "3. Copie o token gerado"
        echo ""
        read -p "Cole seu Personal Access Token aqui: " token
        
        # Configurar remote com token
        echo ""
        echo "🔄 Atualizando remote com autenticação..."
        read -p "Confirme seu username do GitHub: " username
        
        git remote set-url origin https://${username}:${token}@github.com/${username}/soluto-regulatory-agents.git
        
        echo "✅ Remote configurado com token!"
        echo ""
        echo "Agora tente novamente:"
        echo "git push -u origin main"
        ;;
        
    2)
        echo ""
        echo "🔑 Configurando SSH"
        echo ""
        
        # Verificar se já existe chave SSH
        if [ -f ~/.ssh/id_ed25519.pub ]; then
            echo "✅ Você já tem uma chave SSH!"
            cat ~/.ssh/id_ed25519.pub
        else
            echo "Gerando nova chave SSH..."
            ssh-keygen -t ed25519 -C "your_email@example.com"
            echo ""
            echo "📋 Sua chave SSH pública:"
            cat ~/.ssh/id_ed25519.pub
        fi
        
        echo ""
        echo "1. Copie a chave acima"
        echo "2. Vá para: https://github.com/settings/keys"
        echo "3. Clique em 'New SSH key'"
        echo "4. Cole a chave e salve"
        echo ""
        read -p "Pressione Enter após adicionar a chave no GitHub..."
        
        # Mudar para SSH
        read -p "Confirme seu username do GitHub: " username
        git remote set-url origin git@github.com:${username}/soluto-regulatory-agents.git
        
        echo "✅ Remote configurado com SSH!"
        echo ""
        echo "Agora tente:"
        echo "git push -u origin main"
        ;;
        
    3)
        echo ""
        echo "👤 Corrigindo username"
        echo ""
        read -p "Digite o username CORRETO do GitHub: " correct_username
        
        # Atualizar remote
        git remote set-url origin https://github.com/${correct_username}/soluto-regulatory-agents.git
        
        echo "✅ Remote atualizado!"
        echo ""
        echo "Se ainda der erro 403, você precisará usar uma das opções 1 ou 2 para autenticação."
        echo ""
        echo "Tente novamente:"
        echo "git push -u origin main"
        ;;
        
    *)
        echo "❌ Opção inválida!"
        exit 1
        ;;
esac

echo ""
echo "💡 Dicas adicionais:"
echo "   - GitHub não aceita mais senha para push via HTTPS"
echo "   - Use sempre Personal Access Token ou SSH"
echo "   - Verifique se o repositório foi criado com o usuário correto"
echo ""
echo "📚 Documentação:"
echo "   - Personal Access Tokens: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token"
echo "   - SSH Keys: https://docs.github.com/en/authentication/connecting-to-github-with-ssh"