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
	@echo "🔴 OBRIGATÓRIOS (LLM + Deploy + Vídeo):"
	@echo "  GROQ_API_KEY           - Groq Cloud (console.groq.com) - LLM PRIMÁRIO GRÁTIS"
	@echo "  VERCEL_TOKEN           - Vercel access token (vercel.com/account/tokens)"
	@echo "  VERCEL_ORG_ID          - Vercel org ID (vercel inspect <deploy>)"
	@echo "  VERCEL_PROJECT_ID      - Vercel project ID"
	@echo "  PEXELS_KEY             - Pexels API key (https://www.pexels.com/api/)"
	@echo "  YOUTUBE_CLIENT_ID      - Google Cloud OAuth client ID"
	@echo "  YOUTUBE_CLIENT_SECRET  - Google Cloud OAuth client secret"
	@echo "  YOUTUBE_REFRESH_TOKEN  - Offline refresh token (run: python -m video.src.upload youtube-auth)"
	@echo "  TIKTOK_CLIENT_KEY      - TikTok Developers app client key"
	@echo "  TIKTOK_CLIENT_SECRET   - TikTok Developers app client secret"
	@echo "  TIKTOK_ACCESS_TOKEN    - TikTok access token with video.upload scope"
	@echo ""
	@echo "🟡 RECOMENDADOS (mais fontes + fallback LLM):"
	@echo "  TOGETHER_API_KEY       - Together AI (api.together.xyz) - Fallback LLM"
	@echo "  NEWSAPI_KEY            - NewsAPI.org (100 req/day free)"
	@echo "  GNEWS_KEY              - GNews.io (100 req/day free)"
	@echo "  CURRENTS_KEY           - Currents API (100 req/day free)"
	@echo "  WORLDNEWS_KEY          - World News API (100 req/day free)"
	@echo "  GUARDIAN_KEY           - The Guardian API (500 req/day free)"
	@echo "  HF_API_TOKEN           - Hugging Face token (hf.co/settings/tokens)"
	@echo "  OLLAMA_HOST            - Remote Ollama endpoint (e.g., https://ollama.xxx)"
	@echo ""
	@echo "🟢 OPCIONAIS (enriquecimento automático):"
	@echo "  ALPHAVANTAGE_KEY       - Alpha Vantage (25 req/day free) - ações"
	@echo "  OPENWEATHER_KEY        - OpenWeatherMap (1000 req/day free) - clima"
	@echo "  PIXABAY_KEY            - Pixabay API key (free) - footage backup"
	@echo "  MEDIASTACK_KEY         - MediaStack (100 req/month free) - backup only"
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