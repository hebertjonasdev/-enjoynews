"""Generate daily video script from cluster index."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import orjson
from rich.console import Console

from .models import NewsItem, VideoConfig, VideoScript

console = Console()

# System prompt defined in collector/src/prompts.py - reused here
VIDEO_SCRIPT_SYSTEM_PROMPT = """Você é editor-chefe e apresentador do "Resumão EnjoyNews", boletim diário de 40 segundos
para YouTube Shorts e TikTok. Estilo: âncora de telejornal maduro (Jornal Nacional, BBC World News).
Tom: autoridade calma, dicção clara, zero sensacionalismo, zero gírias.

ESTRUTURA FIXA (≈ 95 palavras = 40s em português falado):
1. ABERTURA (3s, ~8 palavras): "Bom dia, sou do EnjoyNews. As principais notícias desta manhã."
2. TOP 3 NOTÍCIAS (25s, ~60 palavras): 3 notícias — cada uma: 1 frase lead + 1 frase consequência.
   Prioridade: breaking > Brasil > Mundo > Economia > Tech/Ciência > Esportes > Cultura.
3. FECHAMENTO (12s, ~27 palavras): "Outras notícias e detalhes em enjoynews.com.br. Até a próxima edição."

REGRAS:
- Frases curtas (máx 18 palavras). Uma ideia por frase.
- Verbos no presente. Tempo real.
- Nomes completos na 1ª menção.
- Sem "segundo", "conforme", "de acordo com" — diga o fato direto.
- Transições naturais: "No exterior,", "Na economia,", "No esporte,".
- Zero opinião. Zero adjetivos qualificativos desnecessários.
- Português impecável, culta padrão acessível.

SAÍDA: Apenas o texto falado, sem marcações de tempo, sem stage directions.
"""


def load_cluster_index(index_path: Path) -> list[NewsItem]:
    """Load cluster index from collector pipeline."""
    if not index_path.exists():
        console.print(f"[yellow]Cluster index not found: {index_path}[/yellow]")
        return []

    try:
        data = orjson.loads(index_path.read_bytes())
        items = []
        for item in data:
            items.append(NewsItem(
                id=item["id"],
                theme=item["theme"],
                primary_id=item["primary_id"],
                primary_headline=item["primary_headline"],
                importance=item["importance"],
                category=item.get("category"),
                url=item.get("url", ""),
            ))
        return items
    except Exception as e:
        console.print(f"[red]Failed to load cluster index: {e}[/red]")
        return []


def select_top_news(items: list[NewsItem], max_items: int = 3) -> list[NewsItem]:
    """Select top news by importance and category priority."""
    # Category priority order
    category_priority = {
        "Política": 1,
        "Brasil": 2,
        "Mundo": 3,
        "Economia": 4,
        "Tecnologia": 5,
        "Ciência": 6,
        "Saúde": 7,
        "Meio Ambiente": 8,
        "Latino-América": 9,
        "Esportes": 10,
        "Cultura": 11,
        "Educação": 12,
    }

    def sort_key(item: NewsItem):
        cat_priority = category_priority.get(item.category or "", 99)
        return (-item.importance, cat_priority)

    sorted_items = sorted(items, key=sort_key)
    return sorted_items[:max_items]


def build_script_prompt(date: str, top_items: list[NewsItem]) -> str:
    """Build prompt for LLM script generation."""
    summaries_text = "\n\n".join(
        f"{i+1}. {item.primary_headline}\n   Categoria: {item.category or 'Geral'}\n   Importância: {item.importance}/5"
        for i, item in enumerate(top_items)
    )

    return f"""DATA: {date}
NOTÍCIAS SELECIONADAS (em ordem de prioridade):
{summaries_text}

Produza o roteiro falado completo (≈ 95 palavras, 40 segundos).
"""


async def generate_script_with_llm(prompt: str, config: VideoConfig) -> str | None:
    """Generate script using LLM (Ollama or HF)."""
    # This would integrate with the same LLM client as collector
    # For now, return a template-based script as fallback
    return None


def generate_script_template(date: str, top_items: list[NewsItem]) -> str:
    """Generate script using template (fallback when LLM unavailable)."""
    if not top_items:
        return f"Bom dia, sou do EnjoyNews. Hoje não há notícias principais. Acesse enjoynews.com.br para mais detalhes. Até a próxima edição."

    # Format date in Portuguese
    from datetime import datetime
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        day_names = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
        month_names = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                       "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        date_str = f"{day_names[dt.weekday()]} ({dt.day} de {month_names[dt.month - 1]})"
    except Exception:
        date_str = date

    parts = [f"Bom dia, sou do EnjoyNews. As principais notícias desta {date_str}."]

    transitions = {
        "Política": "Na política,",
        "Brasil": "No Brasil,",
        "Mundo": "No exterior,",
        "Economia": "Na economia,",
        "Tecnologia": "Na tecnologia,",
        "Ciência": "Na ciência,",
        "Saúde": "Na saúde,",
        "Meio Ambiente": "No meio ambiente,",
        "Latino-América": "Na América Latina,",
        "Esportes": "No esporte,",
        "Cultura": "Na cultura,",
        "Educação": "Na educação,",
    }

    for i, item in enumerate(top_items):
        transition = transitions.get(item.category or "", "Além disso,")
        if i == 0:
            transition = ""  # First item follows opening directly

        # Create lead from headline (simplified)
        lead = item.primary_headline
        if lead.endswith("."):
            lead = lead[:-1]

        # Consequence placeholder
        consequence = "Desdobramentos são aguardados nas próximas horas."

        if transition:
            parts.append(f"{transition} {lead}. {consequence}")
        else:
            parts.append(f"{lead}. {consequence}")

    parts.append("Outras notícias e detalhes em enjoynews.com.br. Até a próxima edição.")

    return " ".join(parts)


def create_video_script(date: str, config: VideoConfig) -> VideoScript:
    """Main function to create video script."""
    # Load cluster index
    index_path = Path(config.output_dir).parent / "blog" / "src" / "content" / "cluster_index.json"
    items = load_cluster_index(index_path)

    if not items:
        console.print("[yellow]No cluster index found, using empty script[/yellow]")

    top_items = select_top_news(items)

    # Try LLM first (would need async context)
    # script_text = await generate_script_with_llm(build_script_prompt(date, top_items), config)

    # Fallback to template
    script_text = generate_script_template(date, top_items)

    word_count = len(script_text.split())
    # Portuguese: ~140 words/minute = ~2.3 words/second
    duration_estimate = word_count / 2.3

    return VideoScript(
        text=script_text,
        duration_estimate=duration_estimate,
        word_count=word_count,
        news_items=top_items,
    )


if __name__ == "__main__":
    import asyncio
    config = VideoConfig()
    script = create_video_script("2025-01-15", config)
    print(f"Script ({script.word_count} words, ~{script.duration_estimate:.1f}s):")
    print(script.text)