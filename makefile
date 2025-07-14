# Dieta - Gestione Menu - Makefile

.PHONY: install test run deploy clean help

# Variables
PYTHON = python3
PIP = pip
VENV = venv
PROJECT_NAME = dieta

# Colors for output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
NC = \033[0m # No Color

help: ## Show this help message
	@echo "$(GREEN)Dieta - Gestione Menu$(NC)"
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies and setup project
	@echo "$(GREEN)Installing dependencies...$(NC)"
	$(PYTHON) -m venv $(VENV)
	./$(VENV)/bin/$(PIP) install --upgrade pip
	./$(VENV)/bin/$(PIP) install -r requirements.txt
	@echo "$(GREEN)Setup complete!$(NC)"

test: ## Run tests
	@echo "$(GREEN)Running tests...$(NC)"
	./$(VENV)/bin/$(PYTHON) -m pytest tests/ -v

deploy: ## Deploy to production
	@echo "$(GREEN)Deploying to production...$(NC)"
	sudo systemctl stop financeapi || true
	sudo cp deploy/systemd/financeapi.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable financeapi
	sudo systemctl start financeapi
	@echo "$(GREEN)Deployment complete!$(NC)"

logs: ## Show logs
	@echo "$(GREEN)Showing logs...$(NC)"
	sudo journalctl -u financeapi -f

status: ## Check service status
	@echo "$(GREEN)Service status:$(NC)"
	sudo systemctl status financeapi

clean: ## Clean build artifacts
	@echo "$(GREEN)Cleaning...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache

lint: ## Run code linting
	@echo "$(GREEN)Running linter...$(NC)"
	./$(VENV)/bin/flake8 --max-line-length=100 --ignore=E501 .

format: ## Format code
	@echo "$(GREEN)Formatting code...$(NC)"
	./$(VENV)/bin/black --line-length=100 .

backup: ## Backup configuration
	@echo "$(GREEN)Creating backup...$(NC)"
	tar -czf backup-$(shell date +%Y%m%d-%H%M%S).tar.gz \
		--exclude=venv \
		--exclude=__pycache__ \
		--exclude=*.pyc \
		.

requirements: ## Update requirements.txt
	@echo "$(GREEN)Updating requirements.txt...$(NC)"
	./$(VENV)/bin/$(PIP) freeze > requirements.txt