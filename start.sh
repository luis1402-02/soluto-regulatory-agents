#!/bin/bash

# Quick start script for Soluto Regulatory Agents
# For immediate testing and development

echo "🚀 Starting Soluto Regulatory Agents (Quick Mode)..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your API keys:"
    echo "   - OPENAI_API_KEY"
    echo "   - PERPLEXITY_API_KEY"
    echo ""
    read -p "Press Enter after editing .env..."
fi

# Create logs directory
mkdir -p logs data

# Start with docker-compose
echo "🔄 Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services
echo "⏳ Waiting for services to start..."
sleep 10

# Quick health check
if curl -f -s http://localhost:2024/health > /dev/null; then
    echo "✅ System is running!"
    echo ""
    echo "🎯 Access Points:"
    echo "   Main App:      http://localhost:2024"
    echo "   Monitoring:    http://localhost:2024/monitoring/dashboard"
    echo "   API Docs:      http://localhost:2024/api/docs"
    echo ""
    echo "🧪 Test the system:"
    echo "   python scripts/validate.py"
    echo ""
else
    echo "❌ System not responding. Check logs:"
    echo "   docker-compose -f docker-compose.prod.yml logs"
fi