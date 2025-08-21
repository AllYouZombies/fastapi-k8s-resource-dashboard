#!/bin/bash

# Kubernetes Resource Monitor - Startup Script
# Automated setup and application launch

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Kubernetes Resource Monitor - Startup Script${NC}"
echo -e "${BLUE}Repository: https://github.com/AllYouZombies/fastapi-k8s-resource-dashboard${NC}"
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

# Dependency checks
echo -e "\n${BLUE}Checking dependencies...${NC}"

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
    print_warning "kubectl not found - please check Kubernetes access"
else
    print_status "kubectl found"
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "\n${BLUE}Creating configuration file...${NC}"
    cp .env.example .env
    print_status "Created .env file from template"
    print_warning "IMPORTANT: Configure PROMETHEUS_URL in the .env file!"
    echo -e "   Edit the file: ${YELLOW}nano .env${NC}"
    echo -e "   Set your Prometheus: ${YELLOW}PROMETHEUS_URL=http://your-prometheus:9090${NC}"
else
    print_status ".env file already exists"
fi

# Configure UID/GID for kubeconfig access
echo -e "\n${BLUE}Setting up access permissions...${NC}"
if ! grep -q "HOST_UID=" .env; then
    echo "HOST_UID=$(id -u)" >> .env
    echo "HOST_GID=$(id -g)" >> .env
    print_status "Added HOST_UID and HOST_GID to .env"
else
    # Update existing values
    sed -i "s/^HOST_UID=.*/HOST_UID=$(id -u)/" .env
    sed -i "s/^HOST_GID=.*/HOST_GID=$(id -g)/" .env
    print_status "Updated HOST_UID and HOST_GID in .env"
fi

# Create necessary directories
echo -e "\n${BLUE}Creating directories...${NC}"
mkdir -p data logs
print_status "Created data/ and logs/ directories"

# Check kubeconfig
echo -e "\n${BLUE}Checking Kubernetes access...${NC}"
if [ -f ~/.kube/config ]; then
    print_status "kubeconfig found in ~/.kube/config"
    if kubectl get nodes &> /dev/null; then
        print_status "Kubernetes connection working"
    else
        print_warning "kubeconfig found, but cluster connection failed"
    fi
else
    print_warning "kubeconfig not found in ~/.kube/config"
    echo "   Configure Kubernetes access or change KUBECONFIG_PATH in .env"
fi

# Check Prometheus settings
echo -e "\n${BLUE}Checking Prometheus settings...${NC}"
if [ -f .env ]; then
    PROMETHEUS_URL=$(grep "^PROMETHEUS_URL=" .env | cut -d'=' -f2)
    if [[ "$PROMETHEUS_URL" == "http://your-prometheus-server:9090" ]]; then
        print_error "PROMETHEUS_URL not configured! Edit the .env file"
        echo -e "   Current value: ${RED}$PROMETHEUS_URL${NC}"
        echo -e "   Change to your Prometheus server"
        exit 1
    else
        print_status "PROMETHEUS_URL configured: $PROMETHEUS_URL"
    fi
fi

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
echo "Building Docker image..."
if command -v docker-compose &> /dev/null; then
    docker-compose build
    echo "Starting container..."
    docker-compose up -d
else
    docker compose build
    echo "Starting container..."
    docker compose up -d
fi

# Check startup
echo -e "\n${BLUE}Checking status...${NC}"
sleep 5

if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

if $COMPOSE_CMD ps | grep -q "Up"; then
    print_status "Container started successfully"
    
    # Wait for application readiness
    echo "Waiting for application to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health/liveness &> /dev/null; then
            print_status "Application is ready!"
            break
        fi
        echo -n "."
        sleep 2
    done
    echo ""
    
    # Access information
    echo -e "\n${GREEN}🎉 Application started successfully!${NC}"
    echo "=================================================="
    echo -e "🌐 Web Interface: ${BLUE}http://localhost:8000${NC}"
    echo -e "📊 Dashboard: ${BLUE}http://localhost:8000/dashboard${NC}"
    echo -e "❤️ Health Check: ${BLUE}http://localhost:8000/health${NC}"
    
    echo -e "\n${BLUE}Useful commands:${NC}"
    if command -v docker-compose &> /dev/null; then
        echo "  Logs:           docker-compose logs -f"
        echo "  Stop:           docker-compose down"
        echo "  Restart:        docker-compose restart"
        echo "  Status:         docker-compose ps"
    else
        echo "  Logs:           docker compose logs -f"
        echo "  Stop:           docker compose down"
        echo "  Restart:        docker compose restart"
        echo "  Status:         docker compose ps"
    fi
    
else
    print_error "Container startup failed!"
    echo -e "\n${BLUE}Logs for diagnosis:${NC}"
    $COMPOSE_CMD logs --tail 20
    exit 1
fi