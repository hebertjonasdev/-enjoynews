"""Main collector pipeline: fetch → extract → summarize → dedup → cluster → publish MDX."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import orjson
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
import numpy as np

from .models import (
    PipelineConfig,
    RawArticle,
    ProcessedArticle,
    Cluster,
    Category,
    Importance,
)
from .sources import (
    get_enabled_sources,
    fetch_newsapi_articles,
    fetch_gnews_articles,
    fetch_currents_articles,
    fetch_mediastack_articles,
    fetch_worldnews_articles,
    fetch_guardian_articles,
    fetch_nitter_articles,
    fetch_sitemap_articles,
    SITEMAP_SOURCES,
)
from .llm_client import create_llm_client
from .prompts import validate_summary_json
from .enrichment import enrich_articles, EnrichmentConfig

console = Console()


class CollectorPipeline:
    """Orchestrates the full collection and publishing pipeline."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.http_client = httpx.AsyncClient(
            timeout=config.request_timeout,
            headers={"User-Agent": config.user_agent},
        )
        self.llm = create_llm_client(config)
        self.embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Enrichment config
        self.enrichment_config = EnrichmentConfig(
            brasil_api_key=config.brasil_api_key,
            worldbank_key=config.worldbank_key,
            alphavantage_key=config.alphavantage_key,
            coingecko_key=config.coingecko_key,
            openweather_key=config.openweather_key,
            restcountries_key=config.restcountries_key,
        )

        # Load existing articles for dedup
        self.existing_hashes: set[str] = set()
        self.existing_embeddings: list[np.ndarray] = []
        self._load_existing_articles()

    def _load_existing_articles(self):
        """Load existing MDX files for deduplication."""
        if not self.output_dir.exists():
            return
        for mdx_file in self.output_dir.glob("*.mdx"):
            try:
                content = mdx_file.read_text(encoding="utf-8")
                # Extract URL from frontmatter
                import re
                match = re.search(r'sourceUrl:\s*["\'](.+?)["\']', content)
                if match:
                    url_hash = hashlib.md5(match.group(1).encode()).hexdigest()[:12]
                    self.existing_hashes.add(url_hash)
            except Exception:
                pass

    def _article_hash(self, article: RawArticle) -> str:
        """Generate content hash for deduplication."""
        content = f"{article.url}{article.title}{article.published_at.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    async def fetch_all_sources(self) -> list[RawArticle]:
        """Fetch articles from all configured sources in parallel."""
        console.print("[bold cyan]Fetching from all sources...[/bold cyan]")

        tasks = []

        # RSS feeds
        rss_sources = get_enabled_sources()
        console.print(f"  [dim]RSS sources: {len(rss_sources)}[/dim]")
        tasks.append(self._fetch_rss_feeds(rss_sources))

        # NewsAPI
        if self.config.newsapi_key:
            console.print("  [dim]NewsAPI: enabled[/dim]")
            tasks.append(fetch_newsapi_articles(self.config.newsapi_key))
        else:
            tasks.append(asyncio.sleep(0, result=[]))

        # GNews
        if self.config.gnews_key:
            console.print("  [dim]GNews: enabled[/dim]")
            tasks.append(fetch_gnews_articles(self.config.gnews_key))
        else:
            tasks.append(asyncio.sleep(0, result=[]))

        # Currents API
        if self.config.currents_key:
            console.print("  [dim]Currents API: enabled[/dim]")
            tasks.append(fetch_currents_articles(self.config.currents_key))
        else:
            tasks.append(asyncio.sleep(0, result=[]))

        # MediaStack
        if self.config.mediastack_key:
            console.print("  [dim]MediaStack: enabled[/dim]")
            tasks.append(fetch_mediastack_articles(self.config.mediastack_key))
        else:
            tasks.append(asyncio.sleep(0, result=[]))

        # World News API
        if self.config.worldnews_key:
            console.print("  [dim]World News API: enabled[/dim]")
            tasks.append(fetch_worldnews_articles(self.config.worldnews_key))
        else:
            tasks.append(asyncio.sleep(0, result=[]))

        # The Guardian
        if self.config.guardian_key:
            console.print("  [dim]The Guardian API: enabled[/dim]")
            tasks.append(fetch_guardian_articles(self.config.guardian_key))
        else:
            tasks.append(asyncio.sleep(0, result=[]))

        # Nitter
        if self.config.nitter_instances:
            console.print(f"  [dim]Nitter instances: {len(self.config.nitter_instances)}[/dim]")
            tasks.append(fetch_nitter_articles(self.config.nitter_instances))
        else:
            tasks.append(asyncio.sleep(0, result=[]))

        # Sitemaps
        console.print(f"  [dim]Sitemap sources: {len(SITEMAP_SOURCES)}[/dim]")
        tasks.append(fetch_sitemap_articles(SITEMAP_SOURCES, self.http_client))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                console.print(f"[red]Source {i} failed: {result}[/red]")
            elif isinstance(result, list):
                all_articles.extend(result)

        console.print(f"[green]Total fetched: {len(all_articles)}[/green]")
        return all_articles

    async def _fetch_rss_feeds(self, sources: list) -> list[RawArticle]:
        """Fetch and parse RSS feeds."""
        import feedparser
        from html2text import html2text

        articles = []
        semaphore = asyncio.Semaphore(10)

        async def fetch_one(source):
            async with semaphore:
                try:
                    resp = await self.http_client.get(source.url)
                    resp.raise_for_status()
                    feed = feedparser.parse(resp.text)

                    for entry in feed.entries[:20]:  # Limit per feed
                        link = entry.get("link", "")
                        title = entry.get("title", "").strip()
                        summary = entry.get("summary", "").strip()
                        published = entry.get("published_parsed")

                        if not link or not title:
                            continue

                        if published:
                            published_at = datetime(*published[:6], tzinfo=timezone.utc)
                        else:
                            published_at = datetime.now(timezone.utc)

                        # Clean text
                        clean_text = html2text(summary)[:5000] if summary else ""

                        articles.append(RawArticle(
                            url=link,
                            title=title[:500],
                            source_name=source.name,
                            source_type=source.source_type if hasattr(source, 'source_type') else "rss",
                            source_url=source.url,
                            published_at=published_at,
                            raw_text=clean_text,
                            author=entry.get("author"),
                            language=source.language,
                            category_hint=source.category,
                            tags=[source.subcategory] if source.subcategory else [],
                            metadata={"rss_source": source.name},
                        ))
                except Exception as e:
                    console.print(f"[yellow]RSS error {source.name}: {e}[/yellow]")

        await asyncio.gather(*[fetch_one(s) for s in sources])
        return articles

    def deduplicate(self, articles: list[RawArticle]) -> list[RawArticle]:
        """Remove duplicates based on URL hash and semantic similarity."""
        console.print("[bold cyan]Deduplicating...[/bold cyan]")

        unique = []
        seen_hashes = set()

        for article in articles:
            h = self._article_hash(article)
            if h in self.existing_hashes or h in seen_hashes:
                continue
            seen_hashes.add(h)
            unique.append(article)

        console.print(f"  After URL dedup: {len(unique)}")
        return unique

    def filter_recent(self, articles: list[RawArticle]) -> list[RawArticle]:
        """Keep only articles within dedup window."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.config.dedup_window_minutes)
        recent = [a for a in articles if a.published_at >= cutoff]
        console.print(f"  After time filter: {len(recent)}")
        return recent

    async def summarize_articles(self, articles: list[RawArticle]) -> list[ProcessedArticle]:
        """Generate journalistic summaries via LLM."""
        console.print("[bold cyan]Summarizing with LLM...[/bold cyan]")

        processed = []
        semaphore = asyncio.Semaphore(3)  # Limit concurrent LLM calls

        async def process_one(article: RawArticle) -> ProcessedArticle | None:
            async with semaphore:
                if not article.raw_text or len(article.raw_text) < 200:
                    return None

                summary = await self.llm.summarize_article(article, self.config)
                if not summary or summary.confidence < self.config.min_confidence:
                    return None

                # Generate hero image placeholder (will be filled by video pipeline or manual)
                hero_url = None
                # TODO: integrate with Pexels/Unsplash API

                processed_article = ProcessedArticle(
                    id=str(uuid.uuid4())[:12],
                    raw=article,
                    summary=summary,
                    hero_image_url=hero_url,
                )
                return processed_article

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Summarizing", total=len(articles))
            for article in articles:
                result = await process_one(article)
                if result:
                    processed.append(result)
                progress.advance(task)

        console.print(f"[green]Successfully summarized: {len(processed)}[/green]")
        return processed

    def cluster_articles(self, articles: list[ProcessedArticle]) -> list[Cluster]:
        """Cluster articles by semantic similarity (same story)."""
        if len(articles) < 2:
            return [Cluster(id=str(uuid.uuid4())[:8], primary=a, theme=a.summary.headline) for a in articles]

        console.print("[bold cyan]Clustering related stories...[/bold cyan]")

        # Generate embeddings
        texts = [a.summary.full_text for a in articles]
        embeddings = self.embedder.encode(texts, show_progress_bar=False)

        # DBSCAN clustering
        clustering = DBSCAN(eps=0.35, min_samples=2, metric="cosine").fit(embeddings)
        labels = clustering.labels_

        clusters = []
        for label in set(labels):
            if label == -1:
                # Noise points - each becomes own cluster
                for i, l in enumerate(labels):
                    if l == -1:
                        a = articles[i]
                        clusters.append(Cluster(
                            id=str(uuid.uuid4())[:8],
                            primary=a,
                            theme=a.summary.headline,
                        ))
            else:
                cluster_articles = [articles[i] for i, l in enumerate(labels) if l == label]
                # Sort by importance, then date
                cluster_articles.sort(key=lambda x: (-x.summary.importance.value, x.raw.published_at))
                primary = cluster_articles[0]
                for a in cluster_articles[1:]:
                    a.clustered_with.append(primary.id)
                    a.is_primary_in_cluster = False
                clusters.append(Cluster(
                    id=str(uuid.uuid4())[:8],
                    primary=primary,
                    related=cluster_articles[1:],
                    theme=primary.summary.headline,
                ))

        console.print(f"[green]Formed {len(clusters)} clusters[/green]")
        return clusters

    def select_for_publishing(self, clusters: list[Cluster]) -> list[ProcessedArticle]:
        """Select top articles for publishing (primary from each cluster)."""
        # Sort clusters by primary importance
        clusters.sort(key=lambda c: (-c.primary.summary.importance.value, c.primary.raw.published_at))

        selected = []
        for cluster in clusters[:self.config.max_clusters]:
            selected.append(cluster.primary)
            selected.extend(cluster.related)

        return selected

    def write_mdx_files(self, articles: list[ProcessedArticle]) -> int:
        """Write articles as MDX files for Astro blog."""
        console.print("[bold cyan]Writing MDX files...[/bold cyan]")

        count = 0
        for article in articles:
            if not article.is_primary_in_cluster:
                continue  # Only publish primary articles (related are linked in UI)

            frontmatter = article.to_mdx_frontmatter()
            content = article.to_mdx_content()

            # Build MDX
            fm_lines = ["---"]
            for key, value in frontmatter.items():
                if value is None:
                    continue
                if isinstance(value, list):
                    fm_lines.append(f"{key}: {orjson.dumps(value).decode()}")
                elif isinstance(value, str):
                    # Escape quotes
                    escaped = value.replace('"', '\\"')
                    fm_lines.append(f'{key}: "{escaped}"')
                else:
                    fm_lines.append(f"{key}: {value}")
            fm_lines.append("---")
            fm_lines.append("")

            mdx_content = "\n".join(fm_lines) + content

            # Filename: YYYY-MM-DD-slug.mdx
            date_str = article.raw.published_at.strftime("%Y-%m-%d")
            slug = article.summary.headline.lower()
            slug = "".join(c if c.isalnum() or c == "-" else "-" for c in slug)
            slug = "-".join(slug.split("-")[:8])  # Max 8 words
            filename = f"{date_str}-{slug}-{article.id}.mdx"

            filepath = self.output_dir / filename
            filepath.write_text(mdx_content, encoding="utf-8")
            count += 1

        console.print(f"[green]Written {count} MDX files to {self.output_dir}[/green]")
        return count

    async def run(self, once: bool = False) -> int:
        """Run the full pipeline."""
        console.rule("[bold]EnjoyNews Collector Pipeline[/bold]")

        # Health check LLM
        if not await self.llm.health_check():
            console.print("[red]LLM health check failed![/red]")
            return 0

        # Fetch
        articles = await self.fetch_all_sources()
        if not articles:
            console.print("[yellow]No articles fetched[/yellow]")
            return 0

        # Filter
        articles = self.filter_recent(articles)
        articles = self.deduplicate(articles)

        if not articles:
            console.print("[yellow]No new articles after filtering[/yellow]")
            return 0

        # Limit
        articles = articles[:self.config.max_articles_per_run]

        # Summarize
        processed = await self.summarize_articles(articles)
        if not processed:
            console.print("[yellow]No articles passed summarization[/yellow]")
            return 0

        # Enrich with contextual data
        console.print("[bold cyan]Enriching articles with contextual data...[/bold cyan]")
        processed = await enrich_articles(processed, self.enrichment_config, self.http_client)

        # Cluster
        clusters = self.cluster_articles(processed)

        # Select
        selected = self.select_for_publishing(clusters)

        # Write
        count = self.write_mdx_files(selected)

        # Save cluster index for video pipeline
        cluster_index = self.output_dir.parent / "cluster_index.json"
        cluster_data = []
        for c in clusters:
            cluster_data.append({
                "id": c.id,
                "theme": c.theme,
                "primary_id": c.primary.id,
                "primary_headline": c.primary.summary.headline,
                "importance": c.primary.summary.importance.value,
                "category": c.primary.raw.category_hint.value if c.primary.raw.category_hint else None,
                "url": str(c.primary.raw.url),
            })
        cluster_index.write_text(orjson.dumps(cluster_data).decode(), encoding="utf-8")

        console.rule(f"[bold green]Pipeline complete: {count} articles published[/bold green]")
        return count

    async def close(self):
        await self.http_client.aclose()
        if hasattr(self.llm, 'close'):
            await self.llm.close()


def load_config_from_env() -> PipelineConfig:
    """Load configuration from environment variables."""
    return PipelineConfig(
        max_articles_per_run=int(os.getenv("MAX_ARTICLES_PER_RUN", "50")),
        dedup_window_minutes=int(os.getenv("DEDUP_WINDOW_MINUTES", "1440")),
        min_confidence=float(os.getenv("MIN_CONFIDENCE", "0.6")),
        max_clusters=int(os.getenv("MAX_CLUSTERS", "20")),
        output_dir=os.getenv("OUTPUT_DIR", "output/posts"),
        # LLM Providers
        groq_api_key=os.getenv("GROQ_API_KEY"),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"),
        together_api_key=os.getenv("TOGETHER_API_KEY"),
        together_model=os.getenv("TOGETHER_MODEL", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
        hf_api_token=os.getenv("HF_API_TOKEN"),
        hf_model=os.getenv("HF_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct"),
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        # News APIs
        newsapi_key=os.getenv("NEWSAPI_KEY"),
        gnews_key=os.getenv("GNEWS_KEY"),
        currents_key=os.getenv("CURRENTS_KEY"),
        mediastack_key=os.getenv("MEDIASTACK_KEY"),
        worldnews_key=os.getenv("WORLDNEWS_KEY"),
        guardian_key=os.getenv("GUARDIAN_KEY"),
        # Enrichment APIs
        brasil_api_key=os.getenv("BRASIL_API_KEY"),
        worldbank_key=os.getenv("WORLDBANK_KEY"),
        alphavantage_key=os.getenv("ALPHAVANTAGE_KEY"),
        coingecko_key=os.getenv("COINGECKO_KEY"),
        openweather_key=os.getenv("OPENWEATHER_KEY"),
        restcountries_key=os.getenv("RESTCOUNTRIES_KEY"),
        # Social
        nitter_instances=os.getenv("NITTER_INSTANCES", "").split(",") if os.getenv("NITTER_INSTANCES") else [],
        # General
        request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
    )


async def main():
    parser = argparse.ArgumentParser(description="EnjoyNews Collector Pipeline")
    parser.add_argument("--output", default="output/posts", help="Output directory for MDX files")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--max-articles", type=int, default=50, help="Max articles per run")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    args = parser.parse_args()

    config = load_config_from_env()
    config.output_dir = args.output
    config.max_articles_per_run = args.max_articles

    pipeline = CollectorPipeline(config)
    try:
        count = await pipeline.run(once=args.once)
        return 0 if count > 0 else 1
    finally:
        await pipeline.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)