#!/bin/bash

set -e

echo "🚀 Запуск развертывания Fetal Monitor System..."

# Проверка архитектуры
ARCH=$(uname -m)
echo "📊 Архитектура системы: $ARCH"

# Определяем какой compose файл использовать
if [[ "$ARCH" == "arm"* ]] || [[ "$ARCH" == "aarch"* ]]; then
    COMPOSE_FILE="docker-compose.arm.yml"
    echo "🎯 Используем ARM-оптимизированную конфигурацию"
else
    COMPOSE_FILE="docker-compose.yml"
    echo "🎯 Используем стандартную конфигурацию"
fi

# Сборка и запуск
echo "🔨 Сборка Docker образов..."
docker-compose -f $COMPOSE_FILE build

echo "🚀 Запуск сервисов..."
docker-compose -f $COMPOSE_FILE up -d

echo "⏳ Ожидание запуска сервисов..."
sleep 30

# Проверка здоровья
echo "🏥 Проверка здоровья сервисов..."
docker-compose -f $COMPOSE_FILE ps

echo "✅ Развертывание завершено!"
echo "📊 Frontend доступен по: http://localhost"
echo "🔧 API доступен по: http://localhost:8001"
echo "📈 Health checks:"
echo "   Frontend: http://localhost/health"
echo "   ML Service: http://localhost:8001/api/ping"