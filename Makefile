# Makefile for crewai-biolit-blog (portable)

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
OUTDIR := src/data/output

# user overrides
TOPK ?= 8
QUIET ?= 0
QUIET_FLAG := $(if $(filter 1,$(QUIET)),--quiet,)

# Use .env if present; otherwise fall back to exported env vars
ifeq ($(wildcard .env),.env)
ENV_ARGS := --env-file .env
else
ENV_ARGS := -e OPENAI_API_KEY=$(OPENAI_API_KEY) -e OPENAI_MODEL=$(OPENAI_MODEL)
endif

.PHONY: setup run clean docker-build docker-run

setup:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	@if [ -z "$(PDF)" ]; then echo "❌ Please provide PDF=path/to/file.pdf"; exit 1; fi
	mkdir -p $(OUTDIR)
	$(PYTHON) -m src.main --pdf "$(PDF)" --top-k $(TOPK) $(QUIET_FLAG)
	@echo "📄 Latest file:" && ls -1t $(OUTDIR) | head -n1 | sed 's/^/ - /'

clean:
	rm -rf src/data/vectorstore ~/.cache/chroma

docker-build:
	docker build -t crewai-biolit-blog .

docker-run:
	@if [ -z "$(PDF)" ]; then echo "❌ Please provide PDF=path/to/file.pdf"; exit 1; fi
	mkdir -p $(OUTDIR)
	docker run --rm $(ENV_ARGS) \
		-v "$$(pwd)/src/data/input:/app/src/data/input" \
		-v "$$(pwd)/$(OUTDIR):/app/$(OUTDIR)" \
		crewai-biolit-blog \
		python -m src.main --pdf "src/data/input/$$(basename "$(PDF)")" --top-k $(TOPK) $(QUIET_FLAG)
	@echo "📄 Latest file:" && ls -1t $(OUTDIR) | head -n1 | sed 's/^/ - /'

