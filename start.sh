#!/bin/bash

# Kubernetes Resource Monitor - Startup Script
# Автоматическая подготовка и запуск приложения

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Kubernetes Resource Monitor - Startup Script${NC}"
echo -e "${BLUE}Repository: https://github.com/AllYouZombies/fastapi-k8s-resource-dashboard${NC}"
echo "=================================================="

# Функция для вывода статуса
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Проверка зависимостей
echo -e "\n${BLUE}Проверка зависимостей...${NC}"

if ! command -v docker &> /dev/null; then
    print_error "Docker не установлен!"
    exit 1
fi
print_status "Docker найден"

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose не установлен!"
    exit 1
fi
print_status "Docker Compose найден"

if ! command -v kubectl &> /dev/null; then
    print_warning "kubectl не найден - проверьте доступ к Kubernetes"
else
    print_status "kubectl найден"
fi

# Создание .env файла если не существует
if [ ! -f .env ]; then
    echo -e "\n${BLUE}Создание файла конфигурации...${NC}"
    cp .env.example .env
    print_status "Создан .env файл из шаблона"
    print_warning "ОБЯЗАТЕЛЬНО настройте PROMETHEUS_URL в файле .env!"
    echo -e "   Отредактируйте файл: ${YELLOW}nano .env${NC}"
    echo -e "   Укажите ваш Prometheus: ${YELLOW}PROMETHEUS_URL=http://your-prometheus:9090${NC}"
else
    print_status "Файл .env уже существует"
fi

# Настройка UID/GID для доступа к kubeconfig
echo -e "\n${BLUE}Настройка прав доступа...${NC}"
if ! grep -q "HOST_UID=" .env; then
    echo "HOST_UID=$(id -u)" >> .env
    echo "HOST_GID=$(id -g)" >> .env
    print_status "Добавлены HOST_UID и HOST_GID в .env"
else
    # Обновляем существующие значения
    sed -i "s/^HOST_UID=.*/HOST_UID=$(id -u)/" .env
    sed -i "s/^HOST_GID=.*/HOST_GID=$(id -g)/" .env
    print_status "Обновлены HOST_UID и HOST_GID в .env"
fi

# Создание необходимых директорий
echo -e "\n${BLUE}Создание директорий...${NC}"
mkdir -p data logs
print_status "Созданы директории data/ и logs/"

# Проверка kubeconfig
echo -e "\n${BLUE}Проверка доступа к Kubernetes...${NC}"
if [ -f ~/.kube/config ]; then
    print_status "kubeconfig найден в ~/.kube/config"
    if kubectl get nodes &> /dev/null; then
        print_status "Подключение к Kubernetes работает"
    else
        print_warning "kubeconfig найден, но подключение к кластеру не работает"
    fi
else
    print_warning "kubeconfig не найден в ~/.kube/config"
    echo "   Настройте доступ к Kubernetes или измените KUBECONFIG_PATH в .env"
fi

# Проверка настроек Prometheus
echo -e "\n${BLUE}Проверка настроек Prometheus...${NC}"
if [ -f .env ]; then
    PROMETHEUS_URL=$(grep "^PROMETHEUS_URL=" .env | cut -d'=' -f2)
    if [[ "$PROMETHEUS_URL" == "http://your-prometheus-server:9090" ]]; then
        print_error "PROMETHEUS_URL не настроен! Отредактируйте .env файл"
        echo -e "   Текущее значение: ${RED}$PROMETHEUS_URL${NC}"
        echo -e "   Измените на ваш Prometheus сервер"
        exit 1
    else
        print_status "PROMETHEUS_URL настроен: $PROMETHEUS_URL"
    fi
fi

# Запуск приложения
echo -e "\n${BLUE}Запуск приложения...${NC}"

# Остановка старых контейнеров если есть
if docker ps -q -f name=k8s-resource-monitor &> /dev/null; then
    echo "Остановка старых контейнеров..."
    if command -v docker-compose &> /dev/null; then
        docker-compose down
    else
        docker compose down
    fi
fi

# Сборка и запуск
echo "Сборка Docker образа..."
if command -v docker-compose &> /dev/null; then
    docker-compose build
    echo "Запуск контейнера..."
    docker-compose up -d
else
    docker compose build
    echo "Запуск контейнера..."
    docker compose up -d
fi

# Проверка запуска
echo -e "\n${BLUE}Проверка состояния...${NC}"
sleep 5

if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

if $COMPOSE_CMD ps | grep -q "Up"; then
    print_status "Контейнер запущен успешно"
    
    # Ожидание готовности приложения
    echo "Ожидание готовности приложения..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health/liveness &> /dev/null; then
            print_status "Приложение готово к работе!"
            break
        fi
        echo -n "."
        sleep 2
    done
    echo ""
    
    # Информация о доступе
    echo -e "\n${GREEN}🎉 Приложение успешно запущено!${NC}"
    echo "=================================================="
    echo -e "🌐 Веб-интерфейс: ${BLUE}http://localhost:8000${NC}"
    echo -e "📊 Dashboard: ${BLUE}http://localhost:8000/dashboard${NC}"
    echo -e "🔧 API документация: ${BLUE}http://localhost:8000/docs${NC}"
    echo -e "❤️ Health Check: ${BLUE}http://localhost:8000/health${NC}"
    
    echo -e "\n${BLUE}Полезные команды:${NC}"
    if command -v docker-compose &> /dev/null; then
        echo "  Логи:           docker-compose logs -f"
        echo "  Остановка:      docker-compose down"
        echo "  Перезапуск:     docker-compose restart"
        echo "  Статус:         docker-compose ps"
    else
        echo "  Логи:           docker compose logs -f"
        echo "  Остановка:      docker compose down"
        echo "  Перезапуск:     docker compose restart"
        echo "  Статус:         docker compose ps"
    fi
    
else
    print_error "Ошибка запуска контейнера!"
    echo -e "\n${BLUE}Логи для диагностики:${NC}"
    $COMPOSE_CMD logs --tail 20
    exit 1
fi