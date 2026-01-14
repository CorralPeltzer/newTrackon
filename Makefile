SHELL := /bin/bash
.ONESHELL:
.DEFAULT_GOAL := check

VENV_DIR := .venv
UV := uv
ACTIVATE := source $(VENV_DIR)/bin/activate

# Ensure the project virtual environment exists
venv:
	@if [ ! -f "$(VENV_DIR)/bin/activate" ]; then \
		$(UV) sync; \
	fi

# Run all quality checks in order
check: venv
	$(ACTIVATE)
	$(UV) run ruff check && \
	$(UV) run ruff format && \
	$(UV) run basedpyright && \
	$(UV) run ty check
