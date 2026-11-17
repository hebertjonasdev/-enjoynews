# EnjoyNews 📰

Portal de notícias automatizado — coleta, resume, publica no blog e gera vídeos diários para YouTube Shorts e TikTok.

**Stack:** Python (coleta/LLM/vídeo) + Astro (blog) + GitHub Actions (cron) + Vercel (deploy) + Ollama/HF (LLM grátis)

---

## 🎯 Funcionalidades

- **Coleta 2x/dia (07h/18h BRT):** RSS (G1, BBC, NYT, Folha, UOL, Estadão, Reuters, AP, El País, Le Monde, DW, + 20+ LatAm), NewsAPI/GNews/Currents/WorldNews/Guardian free, Nitter (X/Twitter), Sitemaps
- **Resumo jornalístico:** Estilo G1/BBC/NYT via LLM (Groq Llama 3.1 70B primário → Together AI → HF → Ollama fallback)
- **Enriquecimento automático:** Brasil API (CNPJ/CEP/IBGE), World Bank (macro), Alpha Vantage (ações), CoinGecko (crypto), OpenWeather (clima), REST Countries (metadados)
- **Blog estático:** Astro + Tailwind + MDX — design editorial (laranja/bege/marrom), SEO, RSS, sitemap
- **Vídeo diário (08h BRT):** Roteiro 40s → TTS (edge-tts) + Stock footage (Pexels/Pixabay) → ffmpeg → YouTube Shorts + TikTok
- **Zero custo marginal:** APIs gratuitas, LLM self-hosted/grátis, hospedagem Vercel/GitHub Actions free tier

---

## 🚀 Quick Start (Local)

```bash
# 1. Clone e entre
cd enjoynews

# 2. Configure variáveis (copie .env.example → .env e preencha)
cp .env.example .env
# Edite .env com suas chaves (PEXELS_KEY, etc.)

# 3. Suba tudo (blog + collector + video)
make dev

# 4. Acesse
# Blog: http://localhost:4321
# Collector: roda uma vez e sai
# Video: gera em output/video/
```

### Com local Ollama (precisa 8GB+ RAM)
```bash
make dev-local
# Primeira vez baixa ~5GB (llama3.1:8b)
```

---

## ☁️ Deploy Produção (GitHub Actions + Vercel)

### 1. Push para GitHub
```bash
git remote add origin https://github.com/SEU_USUARIO/enjoynews.git
git push -u origin main
```

### 2. Configure GitHub Secrets
```bash
make install-secrets
# Segue o guia impresso no terminal
# OBRIGATÓRIOS: GROQ_API_KEY, PEXELS_KEY, VERCEL_TOKEN, VERCEL_ORG_ID, VERCEL_PROJECT_ID
# OBRIGATÓRIOS (vídeo): YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN, TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_ACCESS_TOKEN
# OPCIONAIS (recomendados): NEWSAPI_KEY, GNEWS_KEY, CURRENTS_KEY, WORLDNEWS_KEY, GUARDIAN_KEY, TOGETHER_API_KEY, ALPHAVANTAGE_KEY, OPENWEATHER_KEY, HF_API_TOKEN, OLLAMA_HOST
```

### 3. Deploy automático
- **Blog:** Push na `main` → GitHub Actions → Build Astro → Deploy Vercel
- **Coleta:** Cron 07h/18h BRT → Gera MDX → Commit → Deploy
- **Vídeo:** Cron 08h BRT → Gera MP4 → Upload YouTube Shorts + TikTok

### 4. Verificar funcionamento
```bash
# Após push, vá em: https://github.com/SEU_USUARIO/enjoynews/actions
# Verifique se "Collect & Publish" e "Generate & Upload Video" rodam sem erro
# Blog: https://enjoynews.vercel.app (ou seu domínio)
```

### 5. Domínio próprio (opcional)
- Compre `enjoynews.com.br` no Registro.br (R$ 40/ano)
- No Vercel: Project → Settings → Domains → Add `enjoynews.com.br`
- No Registro.br: CNAME `cname.vercel-dns.com`

### 6. Teste local da coleta (opcional)
```bash
# Rode uma vez localmente para testar
make collector
# Verifique blog/src/content/posts/ para MDX gerados
```

---

## 📁 Estrutura

```
enjoynews/
├── .github/workflows/     # GitHub Actions (cron + deploy)
├── collector/             # Python: fetch → extract → summarize → MDX
├── video/                 # Python: script → TTS → ffmpeg → upload
├── blog/                  # Astro: site estático + design system
├── shared/                # Schemas JSON compartilhados
├── docker-compose.yml     # Dev stack completa
├── Makefile               # Comandos úteis
└── README.md
```

---

## 🔑 APIs Gratuitas Necessárias

| Serviço | Free Tier | Link | Prioridade |
|---------|-----------|------|------------|
| **Groq Cloud** | 14k req/dia, Llama 3.1 70B | https://console.groq.com/ | 🔴 **Obrigatório (LLM primário)** |
| **Pexels** | 200 req/hora, 20k/mês | https://www.pexels.com/api/ | 🔴 **Obrigatório (vídeo)** |
| **Together AI** | $1 crédito grátis | https://api.together.xyz/ | 🟡 Fallback LLM |
| **NewsAPI** | 100 req/dia | https://newsapi.org/ | 🟡 Mais fontes |
| **GNews** | 100 req/dia | https://gnews.io/ | 🟡 Mais fontes |
| **Currents API** | 100 req/dia | https://currentsapi.services/ | 🟡 Mais fontes |
| **World News API** | 100 req/dia | https://worldnewsapi.com/ | 🟡 Mais fontes |
| **The Guardian API** | 500 req/dia | https://open-platform.theguardian.com/ | 🟡 UK/Global |
| **YouTube Data API** | 10k unidades/dia | https://console.cloud.google.com/ | 🔴 **Obrigatório (Shorts)** |
| **TikTok for Developers** | Video upload | https://developers.tiktok.com/ | 🔴 **Obrigatório (TikTok)** |
| **Alpha Vantage** | 25 req/dia | https://www.alphavantage.co/ | 🟢 Enriquecimento (ações) |
| **OpenWeatherMap** | 1000 req/dia | https://openweathermap.org/api | 🟢 Enriquecimento (clima) |
| **CoinGecko** | Generoso | https://www.coingecko.com/en/api | 🟢 Enriquecimento (crypto) |
| **Hugging Face Inference** | 30k req/mês | https://huggingface.co/settings/tokens | 🟢 Fallback LLM |
| **Ollama remoto** | Vários hosts grátis | https://github.com/ollama/ollama | 🟢 Último fallback |

---

## 🎨 Design System (Tailwind)

```js
// Cores EnjoyNews
enjoy: {
  orange:  '#E86C00',   // Primário
  beige:   '#F5F0E8',   // Background
  brown:   '#C4A484',   // Secundário
  ink:     '#1A1A1A',   // Texto
  paper:   '#FFFFFF',   // Cards
}

// Fontes
sans:  'Inter'          // UI, corpo
serif: 'Playfair Display'  // Headlines
display: 'Fraunces'     // Hero/Breaking
```

---

## 📅 Cron Schedule (UTC)

| Evento | BRT | UTC (GitHub Actions) |
|--------|-----|----------------------|
| Coleta manhã | 07:00 | 10:00 |
| Coleta tarde | 18:00 | 21:00 |
| Vídeo diário | 08:00 | 11:00 |

*Workflows usam UTC. Ajuste no `.github/workflows/*.yml` se necessário.*

---

## 🛠 Desenvolvimento

### Collector
```bash
cd collector
pip install -e . --constraint=constraints.txt
python -m src.pipeline --output ../blog/src/content/posts --once
```

### Video
```bash
cd video
pip install -e . --constraint=constraints.txt
python -m src.main --date 2025-01-15 --output ../output/video/daily.mp4
```

### Blog
```bash
cd blog
npm install
npm run dev
```

---

## 📝 Licença

MIT — Use livremente. Créditos aos projetos open source que tornam isso possível.

---

## 🙏 Créditos / Forks inspiradores

- `rssbridge/rss-bridge` — RSS bridges para X/Reddit/Instagram
- `nitter/nitter` — Frontend alternativo Twitter (RSS)
- `c0fec0de/newsplease` — Extração de artigos
- `travisvn/edge-tts` — TTS Microsoft Edge grátis
- `pexels/pexels-api` — Stock footage free
- `withastro/astro` — Static site generator
- `ollama/ollama` — LLM local simples