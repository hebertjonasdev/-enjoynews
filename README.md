# EnjoyNews 📰

Portal de notícias automatizado — coleta, resume, publica no blog e gera vídeos diários para YouTube Shorts e TikTok.

**Stack:** Python (coleta/LLM/vídeo) + Astro (blog) + GitHub Actions (cron) + Vercel (deploy) + Ollama/HF (LLM grátis)

---

## 🎯 Funcionalidades

- **Coleta 2x/dia (07h/18h BRT):** RSS (G1, BBC, NYT, Folha, UOL, Estadão, Reuters, AP, El País, Le Monde, DW, + LatAm), NewsAPI/GNews free, Nitter (X/Twitter)
- **Resumo jornalístico:** Estilo G1/BBC/NYT via LLM local/remoto (llama3.1:8b, qwen2.5:7b)
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
```

### 3. Deploy automático
- **Blog:** Push na `main` → GitHub Actions → Build Astro → Deploy Vercel
- **Coleta:** Cron 07h/18h BRT → Gera MDX → Commit → Deploy
- **Vídeo:** Cron 08h BRT → Gera MP4 → Upload YouTube Shorts + TikTok

### 4. Domínio próprio (opcional)
- Compre `enjoynews.com.br` no Registro.br (R$ 40/ano)
- No Vercel: Project → Settings → Domains → Add `enjoynews.com.br`
- No Registro.br: CNAME `cname.vercel-dns.com`

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

| Serviço | Free Tier | Link |
|---------|-----------|------|
| **Pexels** | 200 req/hora, 20k/mês | https://www.pexels.com/api/ |
| **Pixabay** | 500 req/hora | https://pixabay.com/api/docs/ |
| **NewsAPI** | 100 req/dia | https://newsapi.org/ |
| **GNews** | 100 req/dia | https://gnews.io/ |
| **YouTube Data API** | 10k unidades/dia | https://console.cloud.google.com/ |
| **TikTok for Developers** | Video upload | https://developers.tiktok.com/ |
| **Hugging Face Inference** | 30k req/mês | https://huggingface.co/settings/tokens |
| **Ollama remoto** | Vários hosts grátis | https://github.com/ollama/ollama |

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