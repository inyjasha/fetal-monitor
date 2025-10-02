#!/bin/bash

echo "🛑 Остановка Fetal Monitor System..."

ARCH=$(uname -m)
if [[ "$ARCH" == "arm"* ]] || [[ "$ARCH" == "aarch"* ]]; then
    COMPOSE_FILE="docker-compose.arm.yml"
else
    COMPOSE_FILE="docker-compose.yml"
fi

docker-compose -f $COMPOSE_FILE down

echo "✅ Система остановлена"