# Makefile for myproject

# Default environment name
ENV_NAME = template_repo

.PHONY: setup update lint format test clean

setup:
	@echo "🔧 Creating or updating environment..."
	conda env create -f environment.yml || conda env update -f environment.yml
	@echo "✅ Environment ready. Activate with: conda activate $(ENV_NAME)"

update:
	@echo "⬆️  Updating dependencies..."
	conda env update -f environment.yml --prune

lint:
	@echo "🧹 Running Ruff lint..."
	ruff check src tests

format:
	@echo "🎨 Formatting code with Ruff..."
	ruff format src tests

test:
	@echo "🧪 Running tests..."
	pytest -v

clean:
	@echo "🗑️  Cleaning build artifacts..."
	rm -rf build dist .pytest_cache *.egg-info
