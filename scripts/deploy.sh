#!/bin/bash

# Soluto Regulatory Agents - Production Deployment Script
# Maio 2025 - LangGraph v0.2.38 Best Practices

set -e

echo "🚀 Deploying Soluto Regulatory Agents to Production..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons"
   exit 1
fi

# Check prerequisites
print_status "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from template..."
    cp .env.example .env
    print_warning "Please edit .env file with your API keys before continuing."
    print_warning "Required: OPENAI_API_KEY, PERPLEXITY_API_KEY"
    read -p "Press enter after editing .env file..."
fi

# Validate critical environment variables
print_status "Validating environment configuration..."

# Source .env file
set -a
source .env
set +a

if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
    print_error "OPENAI_API_KEY is not set in .env file"
    exit 1
fi

if [ -z "$PERPLEXITY_API_KEY" ] || [ "$PERPLEXITY_API_KEY" = "your_perplexity_api_key_here" ]; then
    print_error "PERPLEXITY_API_KEY is not set in .env file"
    exit 1
fi

print_success "Environment validation passed"

# Create necessary directories
print_status "Creating directories..."
mkdir -p logs data monitoring/grafana/dashboards monitoring/grafana/datasources nginx/ssl

# Build the application
print_status "Building application containers..."
docker-compose -f docker-compose.prod.yml build --no-cache

# Start the services
print_status "Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 15

# Health check
print_status "Performing health checks..."

# Check main application
if curl -f -s http://localhost:2024/health > /dev/null; then
    print_success "✅ Main application is healthy (port 2024)"
else
    print_error "❌ Main application health check failed"
    docker-compose -f docker-compose.prod.yml logs app
    exit 1
fi

# Check Redis
if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping | grep -q PONG; then
    print_success "✅ Redis is healthy"
else
    print_error "❌ Redis health check failed"
    exit 1
fi

# Check PostgreSQL
if docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U soluto | grep -q "accepting connections"; then
    print_success "✅ PostgreSQL is healthy"
else
    print_error "❌ PostgreSQL health check failed"
    exit 1
fi

# Display service status
print_status "Service Status:"
docker-compose -f docker-compose.prod.yml ps

# Display access information
echo ""
echo "🎉 ${GREEN}Deployment completed successfully!${NC}"
echo ""
echo "📊 ${PURPLE}Access URLs:${NC}"
echo "   🤖 Main Application:    http://localhost:2024"
echo "   📈 Monitoring Dashboard: http://localhost:2024/monitoring/dashboard"
echo "   📊 Grafana:             http://localhost:3000 (admin/admin)"
echo "   🔧 LangGraph Studio:    http://localhost:8123"
echo "   📋 API Documentation:   http://localhost:2024/api/docs"
echo ""
echo "🔑 ${YELLOW}API Authentication:${NC}"
echo "   Use header: X-API-Key: $API_KEY"
echo ""
echo "📝 ${BLUE}Quick Test:${NC}"
echo "   curl -X POST http://localhost:2024/api/tasks \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -H \"X-API-Key: $API_KEY\" \\"
echo "     -d '{\"task\": \"Análise de conformidade ANVISA para dispositivos médicos\"}'"
echo ""
echo "🔍 ${BLUE}Monitor Logs:${NC}"
echo "   docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "🛑 ${RED}Stop Services:${NC}"
echo "   docker-compose -f docker-compose.prod.yml down"
echo ""
print_success "Sistema Multiagente Regulatório do Grupo Soluto está PRONTO PARA PRODUÇÃO! 🚀"