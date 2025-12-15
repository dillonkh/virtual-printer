.PHONY: help build up down start stop restart logs logs-socket logs-api clean status ps shell-socket shell-api test

help:
	@echo "Virtual Printer - Docker Management"
	@echo ""
	@echo "Available commands:"
	@echo "  make build         - Build Docker images"
	@echo "  make up            - Start all services (build if needed)"
	@echo "  make down          - Stop and remove all services"
	@echo "  make start         - Start existing services"
	@echo "  make stop          - Stop services without removing"
	@echo "  make restart       - Restart all services"
	@echo "  make logs          - View logs from all services"
	@echo "  make logs-socket   - View logs from socket server"
	@echo "  make logs-api      - View logs from API server"
	@echo "  make status        - Show service status"
	@echo "  make ps            - List running containers"
	@echo "  make shell-socket  - Open shell in socket server container"
	@echo "  make shell-api     - Open shell in API server container"
	@echo "  make clean         - Stop services and remove outputs"
	@echo "  make test          - Test both servers with sample data"
	@echo ""

build:
	docker-compose build

up:
	docker-compose up -d
	@echo ""
	@echo "Virtual Printer services started!"
	@echo "  - Socket Server: localhost:9100"
	@echo "  - API Server:    http://localhost:8000"
	@echo "  - API Docs:      http://localhost:8000/docs"
	@echo ""
	@echo "Run 'make logs' to view logs"

down:
	docker-compose down

start:
	docker-compose start

stop:
	docker-compose stop

restart:
	docker-compose restart

logs:
	docker-compose logs -f

logs-socket:
	docker-compose logs -f socket-server

logs-api:
	docker-compose logs -f api-server

status:
	@docker-compose ps

ps:
	@docker-compose ps

shell-socket:
	docker-compose exec socket-server /bin/bash

shell-api:
	docker-compose exec api-server /bin/bash

clean:
	docker-compose down -v
	rm -rf outputs/*
	@echo "Cleaned up containers and outputs"

test:
	@echo "Testing API Server..."
	@curl -s http://localhost:8000/ | python -m json.tool || echo "API server not responding"
	@echo ""
	@echo "Listing jobs..."
	@curl -s http://localhost:8000/jobs | python -m json.tool || echo "Could not list jobs"
	@echo ""
	@echo "To test socket server, run:"
	@echo "  echo '%PDF-1.4 test' | nc localhost 9100"
