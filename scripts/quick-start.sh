#!/bin/bash

# Kubernetes Resource Monitor - Quick Start Script
# Usage: curl -fsSL https://raw.githubusercontent.com/AllYouZombies/fastapi-k8s-resource-dashboard/master/scripts/quick-start.sh | PROMETHEUS_URL=http://your-prometheus:9090 bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/AllYouZombies/fastapi-k8s-resource-dashboard.git"
PROJECT_DIR="fastapi-k8s-resource-dashboard"

echo -e "${BLUE}🚀 Kubernetes Resource Monitor - Quick Start${NC}"
echo -e "${BLUE}Repository: ${REPO_URL}${NC}"
echo "=================================================="

# Status output functions
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check required environment variables
if [ -z "$PROMETHEUS_URL" ]; then
    print_error "PROMETHEUS_URL environment variable is required!"
    echo -e "\n${YELLOW}Usage:${NC}"
    echo "curl -fsSL https://raw.githubusercontent.com/AllYouZombies/fastapi-k8s-resource-dashboard/master/scripts/quick-start.sh | PROMETHEUS_URL=http://your-prometheus:9090 bash"
    echo -e "\n${YELLOW}Examples:${NC}"
    echo "# Local Prometheus"
    echo "curl -fsSL ... | PROMETHEUS_URL=http://localhost:9090 bash"
    echo ""
    echo "# Kubernetes Prometheus"
    echo "curl -fsSL ... | PROMETHEUS_URL=http://kube-prometheus-stack-prometheus.monitoring.svc:9090 bash"
    echo ""
    echo "# Port-forwarded Prometheus"
    echo "curl -fsSL ... | PROMETHEUS_URL=http://host.docker.internal:9090 bash"
    exit 1
fi

# Check dependencies
echo -e "\n${BLUE}Checking dependencies...${NC}"

if ! command -v git &> /dev/null; then
    print_error "Git is not installed!"
    exit 1
fi
print_status "Git found"

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed!"
    exit 1
fi
print_status "Docker found"

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed!"
    exit 1
fi
print_status "Docker Compose found"

if ! command -v kubectl &> /dev/null; then
    print_warning "kubectl not found - please ensure Kubernetes access is configured"
else
    print_status "kubectl found"
fi

# Clone or update repository
echo -e "\n${BLUE}Setting up project...${NC}"

if [ -d "$PROJECT_DIR" ]; then
    print_status "Project directory exists, updating..."
    cd "$PROJECT_DIR"
    git pull origin master
else
    print_status "Cloning repository..."
    git clone "$REPO_URL"
    cd "$PROJECT_DIR"
fi

# Configure environment
echo -e "\n${BLUE}Configuring environment...${NC}"

if [ ! -f .env ]; then
    cp .env.example .env
    print_status "Created .env from template"
else
    print_status ".env already exists"
fi

# Set Prometheus URL
sed -i "s|^PROMETHEUS_URL=.*|PROMETHEUS_URL=$PROMETHEUS_URL|" .env
print_status "Configured PROMETHEUS_URL: $PROMETHEUS_URL"

# Set host UID/GID
if ! grep -q "HOST_UID=" .env; then
    echo "HOST_UID=$(id -u)" >> .env
    echo "HOST_GID=$(id -g)" >> .env
    print_status "Added HOST_UID and HOST_GID to .env"
else
    sed -i "s/^HOST_UID=.*/HOST_UID=$(id -u)/" .env
    sed -i "s/^HOST_GID=.*/HOST_GID=$(id -g)/" .env
    print_status "Updated HOST_UID and HOST_GID in .env"
fi

# Create directories
mkdir -p data logs
print_status "Created data/ and logs/ directories"

# Start application
echo -e "\n${BLUE}Starting application...${NC}"

# Stop old containers if they exist
if docker ps -q -f name=k8s-resource-monitor &> /dev/null; then
    echo "Stopping old containers..."
    if command -v docker-compose &> /dev/null; then
        docker-compose down
    else
        docker compose down
    fi
fi

# Build and start
echo "Building and starting container..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d --build
else
    docker compose up -d --build
fi

# Wait for application to be ready
echo -e "\n${BLUE}Waiting for application to start...${NC}"
sleep 10

# Check if application is running
for i in {1..30}; do
    if curl -s http://localhost:8000/health/liveness &> /dev/null; then
        print_status "Application is ready!"
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

# Show access information
echo -e "\n${GREEN}🎉 Kubernetes Resource Monitor is running!${NC}"
echo "=================================================="
echo -e "🌐 Web Interface: ${BLUE}http://localhost:8000${NC}"
echo -e "📊 Dashboard: ${BLUE}http://localhost:8000/dashboard${NC}"
echo -e "❤️ Health Check: ${BLUE}http://localhost:8000/health${NC}"

echo -e "\n${BLUE}Configuration:${NC}"
echo "📍 Project directory: $(pwd)"
echo "🎯 Prometheus URL: $PROMETHEUS_URL"
echo "📁 Data directory: $(pwd)/data"
echo "📋 Logs directory: $(pwd)/logs"

echo -e "\n${BLUE}Useful commands:${NC}"
if command -v docker-compose &> /dev/null; then
    echo "  View logs:      docker-compose logs -f"
    echo "  Stop:           docker-compose down"
    echo "  Restart:        docker-compose restart"
    echo "  Status:         docker-compose ps"
else
    echo "  View logs:      docker compose logs -f"
    echo "  Stop:           docker compose down"
    echo "  Restart:        docker compose restart"
    echo "  Status:         docker compose ps"
fi

echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Open http://localhost:8000/dashboard in your browser"
echo "2. Check that data is being collected from your cluster"
echo "3. Explore resource recommendations for optimization"

if ! command -v kubectl &> /dev/null; then
    echo -e "\n${YELLOW}Note:${NC} kubectl not found. Make sure to:"
    echo "1. Install kubectl"
    echo "2. Configure kubeconfig access to your cluster"
    echo "3. Restart the application: docker-compose restart"
fi

echo -e "\n${GREEN}Happy monitoring! 🚀${NC}"