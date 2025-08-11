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

DATE := $(shell date +%F)

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
	@if [ -z "$(TAG)" ]; then echo "❌ Please provide TAG=vX.Y.Z"; exit 1; fi
	@if [ -n "$$(git status --porcelain)" ]; then echo "❌ Uncommitted changes. Commit first."; exit 1; fi
	git tag -a $(TAG) -m "Release $(TAG)"
	git push origin $(TAG)
	@which gh >/dev/null 2>&1 || { echo "❌ Install GitHub CLI: brew install gh"; exit 1; }
	@gh auth status >/dev/null 2>&1 || { echo "❌ Run: gh auth login"; exit 1; }
	sed -e 's/{{TAG}}/$(TAG)/g' -e 's/{{DATE}}/$(DATE)/g' scripts/RELEASE_TEMPLATE.md > /tmp/release_$(TAG).md
	gh release create $(TAG) --title "$(TAG)" --notes-file /tmp/release_$(TAG).md
	@echo "✅ GitHub Release created for $(TAG)"

.PHONY: commit-release

# Usage:
#   make commit-release MSG="my changes" TAG=v0.2.1
commit-release:
	@if [ -z "$(MSG)" ] || [ -z "$(TAG)" ]; then \
		echo "❌ Usage: make commit-release MSG=\"commit message\" TAG=vX.Y.Z"; \
		exit 1; \
	fi
	# 1) Stage & commit
	git add -A
	@git commit -m "$(MSG)" || echo "ℹ️ No changes to commit."
	# 2) Push current branch
	BRANCH=$$(git rev-parse --abbrev-ref HEAD); \
	git push origin $$BRANCH
	# 3) Tag + GitHub Release (reuses your existing 'release' rule)
	$(MAKE) release TAG=$(TAG)

assemble:
	@slug=$$(basename $$(ls -1t src/data/output/*-post.md | head -n1) | sed 's/-post\.md$$//'); \
	post=src/data/output/$$slug-post.md; \
	seo=src/data/output/$$slug-seo-json.json; \
	out=src/data/output/$$slug.md; \
	$(PYTHON) -m src.utils.assemble $$post $$seo $$out && echo "📄 Final blog: $$out"

site-sync:
	@echo "→ Syncing final posts to Astro content collection"
	@mkdir -p apps/site/src/content/posts
	# copy only final assembled posts (exclude notes and drafts)
	@find src/data/output -maxdepth 1 -type f -name "*.md" ! -name "*-post.md" ! -name "*-notes.md" \
		-exec cp {} apps/site/src/content/posts/ \;
	@echo "✓ Synced"

dev:
	make run PDF=$(PDF) QUIET=0 && make assemble && make site-sync && (cd apps/site && npm run dev)
content-normalize:
	@$(PYTHON) scripts/clean_markdown.py apps/site/src/content/posts/*.md || true

# Normalize all Markdown in the Astro content dir
content-normalize:
	@$(PYTHON) scripts/clean_markdown.py apps/site/src/content/posts/*.md || true

# Copy final assembled posts into Astro and normalize them
site-sync:
	@echo "→ Syncing final posts to Astro content collection"
	@mkdir -p apps/site/src/content/posts
	@find src/data/output -maxdepth 1 -type f -name "*.md" ! -name "*-post.md" ! -name "*-notes.md" \
		-exec cp {} apps/site/src/content/posts/ \;
	@$(MAKE) content-normalize
	@echo "✓ Synced"

# Quick guard you can also use in CI later
content-check:
	@if grep -En '^\s*```' apps/site/src/content/posts/*.md; then \
	  echo "❌ Found triple backticks in posts"; exit 1; \
	else echo "✅ No fenced posts found"; fi

