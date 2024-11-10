VENV_DIR = venv
PYTHON = $(VENV_DIR)/bin/python
PIP = $(VENV_DIR)/bin/pip

.PHONY: install format clean


venv:
	python3 -m venv $(VENV_DIR)
	$(PIP) install .[dev]

dev: venv
	@cat $(VENV_DIR)/bin/activate > dev
	@echo export PYTHONPATH=$(PWD)/ >> dev
	@echo "Dev environment ready, type '. dev' to activate"

format:
	black .
	isort .

clean:
	rm -rf venv/
	rm dev

