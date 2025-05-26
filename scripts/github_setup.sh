#!/bin/bash

# Script to setup and push the repository to GitHub
# This script helps create the repository and push the code

echo "🚀 Setting up Soluto Regulatory Agents on GitHub"
echo "=============================================="

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install Git first."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "src" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Initialize git if needed
if [ ! -d ".git" ]; then
    echo "📂 Initializing Git repository..."
    git init
    git branch -M main
fi

# Add all files
echo "📄 Adding files to Git..."
git add .

# Create initial commit
echo "💾 Creating initial commit..."
git commit -m "🎉 Initial commit: Soluto Regulatory Agents v1.0

- Multi-agent regulatory compliance system
- LangGraph v0.2.38 with Command patterns
- Perplexity AI Sonar Pro integration
- Real-time monitoring dashboard
- Complete LangChain/LangSmith integration
- Production-ready deployment with Docker
- Brazilian regulatory focus (ANVISA, ANATEL, LGPD)"

echo ""
echo "📝 Now you need to:"
echo ""
echo "1. Create a new repository on GitHub:"
echo "   - Go to: https://github.com/new"
echo "   - Repository name: soluto-regulatory-agents"
echo "   - Description: Sistema multiagente regulatório com IA para o Grupo Soluto"
echo "   - Make it Public or Private as desired"
echo "   - DON'T initialize with README, .gitignore or License"
echo ""
echo "2. After creating the repository, run these commands:"
echo ""
echo "   git remote add origin https://github.com/YOUR_USERNAME/soluto-regulatory-agents.git"
echo "   git push -u origin main"
echo ""
echo "3. (Optional) If you want to use SSH instead of HTTPS:"
echo "   git remote set-url origin git@github.com:YOUR_USERNAME/soluto-regulatory-agents.git"
echo ""
echo "4. Enable GitHub Pages (optional) for documentation:"
echo "   - Go to Settings > Pages"
echo "   - Source: Deploy from a branch"
echo "   - Branch: main, folder: /docs"
echo ""
echo "5. Setup GitHub Actions (optional) for CI/CD:"
echo "   - The .github/workflows directory can be added later"
echo ""
echo "✅ Git repository is ready! Follow the steps above to push to GitHub."