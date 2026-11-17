.PHONY: help dev collector video blog logs clean install-secrets

# Default target
help:
	@echo "EnjoyNews - News Automation Platform"
	@echo ""
	@echo "Usage:"
	@echo "  make dev           Start all services (blog + collector + video + ollama)"
	@echo "  make dev-local     Start with local Ollama (requires 8GB+ RAM)"
	@echo "  make collector     Run collector pipeline once"
	@echo "  make video         Generate daily video for today"
	@echo "  make blog          Start Astro dev server only"
	@echo "  make logs          Show logs from all services"
	@echo "  make clean         Stop and remove containers, volumes"
	@echo "  make install-secrets  Guide to configure GitHub secrets"
	@echo ""

# Development with remote LLM (default - no local Ollama)
dev:
	docker compose --profile blog --profile collector --profile video up --build

# Development with local Ollama (pulls llama3.1:8b - needs ~8GB RAM)
dev-local:
	docker compose --profile blog --profile collector --profile video --profile local-llm up --build

# Run collector once (outputs MDX to blog/src/content/posts)
collector:
	docker compose --profile collector run --rm collector

# Generate daily video (outputs to output/video/)
video:
	docker compose --profile video run --rm video

# Start blog dev server only
blog:
	docker compose --profile blog up --build blog

# View logs
logs:
	docker compose logs -f

# Clean everything
clean:
	docker compose down -v --remove-orphans
	docker system prune -f

# Install Python deps locally (for IDE support)
install-collector-deps:
	cd collector && pip install -e . --constraint=constraints.txt

install-video-deps:
	cd video && pip install -e . --constraint=constraints.txt

# Guide for GitHub Secrets
install-secrets:
	@echo "=== GitHub Secrets Configuration ==="
	@echo "Go to: https://github.com/<SEU_USUARIO>/enjoynews/settings/secrets/actions"
	@echo ""
	@echo "Required:"
	@echo "  VERCEL_TOKEN           - Vercel access token (vercel.com/account/tokens)"
	@echo "  VERCEL_ORG_ID          - Vercel org ID (vercel inspect <deploy>)"
	@echo "  VERCEL_PROJECT_ID      - Vercel project ID"
	@echo "  PEXELS_KEY             - Pexels API key (https://www.pexels.com/api/)"
	@echo "  YOUTUBE_CLIENT_ID      - Google Cloud OAuth client ID"
	@echo "  YOUTUBE_CLIENT_SECRET  - Google Cloud OAuth client secret"
	@echo "  YOUTUBE_REFRESH_TOKEN  - Offline refresh token (run: python -m video.src.auth.youtube)"
	@echo "  TIKTOK_CLIENT_KEY      - TikTok Developers app client key"
	@echo "  TIKTOK_CLIENT_SECRET   - TikTok Developers app client secret"
	@echo "  TIKTOK_ACCESS_TOKEN    - TikTok access token with video.upload scope"
	@echo ""
	@echo "Optional (free tiers):"
	@echo "  NEWSAPI_KEY            - NewsAPI.org key (100 req/day free)"
	@echo "  GNEWS_KEY              - GNews.io key (100 req/day free)"
	@echo "  PIXABAY_KEY            - Pixabay API key (free)"
	@echo "  HF_API_TOKEN           - Hugging Face token (for remote inference API)"
	@echo "  OLLAMA_HOST            - Remote Ollama endpoint (e.g., https://ollama.xxx)"
	@echo ""
	@echo "After adding secrets, push to main to trigger first workflow run."

# Git helpers
git-status:
	git status

git-push:
	git add -A && git commit -m "chore: updates $$(date -u +'%Y-%m-%d %H:%M')" && git push

# Deploy manually
deploy-blog:
	cd blog && npm run build && npx vercel --prod --token=$$VERCEL_TOKEN