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

release:
	@if [ -z "$(TAG)" ]; then \
		echo "❌ Please provide TAG=vX.Y.Z"; \
		exit 1; \
	fi
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "❌ Uncommitted changes. Commit first."; \
		exit 1; \
	fi
	git tag -a $(TAG) -m "Release $(TAG)"
	git push origin $(TAG)
	@which gh >/dev/null 2>&1 || { echo "❌ Install GitHub CLI: brew install gh"; exit 1; }
	@gh auth status >/dev/null 2>&1 || { echo "❌ Run: gh auth login"; exit 1; }
	@if [ -f scripts/RELEASE_TEMPLATE.md ]; then \
		gh release create $(TAG) --title "$(TAG)" --notes-file scripts/RELEASE_TEMPLATE.md; \
	else \
		gh release create $(TAG) --title "$(TAG)" --notes "Release $(TAG)"; \
	fi
release:
	@if [ -z "$(TAG)" ]; then echo "❌ Please provide TAG=vX.Y.Z"; exit 1; fi
	@if [ -n "$$(git status --porcelain)" ]; then echo "❌ Uncommitted changes. Commit first."; exit 1; fi
	git tag -a $(TAG) -m "Release $(TAG)"
	git push origin $(TAG)
	@which gh >/dev/null 2>&1 || { echo "❌ Install GitHub CLI: brew install gh"; exit 1; }
	@gh auth status >/dev/null 2>&1 || { echo "❌ Run: gh auth login"; exit 1; }
	gh release create $(TAG) --title "$(TAG)" --notes-file scripts/RELEASE_TEMPLATE.md
	@echo "✅ GitHub Release created for $(TAG)"
