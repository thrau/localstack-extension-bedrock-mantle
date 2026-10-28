VENV_BIN = python3 -m venv
VENV_DIR ?= .venv
VENV_ACTIVATE = $(VENV_DIR)/bin/activate
VENV_RUN = . $(VENV_ACTIVATE)

venv: $(VENV_ACTIVATE)

$(VENV_ACTIVATE): pyproject.toml
	test -d .venv || $(VENV_BIN) .venv
	$(VENV_RUN); pip install --upgrade pip
	$(VENV_RUN); pip install -e .[dev]
	touch $(VENV_DIR)/bin/activate

clean:
	rm -rf .venv/ build/ dist/ .eggs/ *.egg-info/

install: venv

dist: venv
	$(VENV_RUN); python -m build

lint: venv
	$(VENV_RUN); ruff check .
	$(VENV_RUN); ruff format --check .

format: venv
	$(VENV_RUN); ruff check --fix .
	$(VENV_RUN); ruff format .

.PHONY: clean dist install venv lint format
