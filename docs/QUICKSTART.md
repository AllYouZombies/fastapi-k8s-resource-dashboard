# 🚀 Быстрый старт

Простая пошаговая инструкция для запуска Kubernetes Resource Monitor.

## Перед началом

Убедитесь, что у вас есть:
- ✅ Docker и Docker Compose
- ✅ Доступ к Kubernetes кластеру (kubeconfig в `~/.kube/config`)
- ✅ URL вашего Prometheus сервера

## Шаг 1: Клонирование

```bash
git clone <repository-url>
cd k8s-resource-monitor
```

## Шаг 2: Настройка

```bash
# Создание файла конфигурации
cp .env.example .env

# Редактирование конфигурации
nano .env
```

**Обязательно измените:**
```bash
PROMETHEUS_URL=http://your-prometheus-server:9090
```

Замените `your-prometheus-server:9090` на ваш реальный адрес Prometheus.

## Шаг 3: Запуск

### Автоматический запуск (рекомендуется)
```bash
./start.sh
```

### Или ручной запуск
```bash
mkdir -p data logs
docker-compose up -d
```

## Шаг 4: Проверка

Откройте в браузере: **http://localhost:8000**

Если видите дашборд с таблицами ресурсов - всё работает! 🎉

## Полезные команды

```bash
# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Статус контейнера
docker-compose ps
```

## Устранение проблем

### Prometheus недоступен
```bash
# Проверьте URL в .env
cat .env | grep PROMETHEUS_URL

# Проверьте доступность
curl -I http://your-prometheus:9090
```

### Kubernetes недоступен
```bash
# Проверьте kubeconfig
kubectl get nodes

# Проверьте права доступа
kubectl auth can-i get pods
```

### Контейнер не запускается
```bash
# Проверьте логи
docker-compose logs k8s-resource-monitor

# Проверьте порт
netstat -tulpn | grep 8000
```

## Что дальше?

- 📊 Изучите dashboard по адресу http://localhost:8000
- 🔧 Посмотрите API документацию: http://localhost:8000/docs
- ❤️ Проверьте health: http://localhost:8000/health
- 📚 Читайте полную документацию в папке `docs/`

---

**Нужна помощь?** Читайте подробные руководства:
- [README.md](README.md) - Полное описание
- [docs/configuration.md](docs/configuration.md) - Детальная настройка
- [docs/operations.md](docs/operations.md) - Администрирование