"""Sitemap-based source for sites without RSS (official orgs, etc.)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import httpx
from lxml import etree

from ..models import Category, RawArticle, SourceType


@dataclass
class SitemapSourceConfig:
    name: str
    sitemap_url: str
    category: Category
    subcategory: str | None = None
    url_pattern: str | None = None  # Regex to filter article URLs
    exclude_pattern: str | None = None
    max_urls: int = 50
    language: str = "pt"


# Curated sitemaps for official orgs and sites without good RSS
SITEMAP_SOURCES = [
    # Brasil - Governo
    SitemapSourceConfig(
        name="Gov.br",
        sitemap_url="https://www.gov.br/sitemap.xml",
        category=Category.BRASIL,
        subcategory="Oficial",
        url_pattern=r"/noticias/|/ultimas-noticias/|/assuntos/",
        max_urls=30,
    ),
    SitemapSourceConfig(
        name="Planalto",
        sitemap_url="https://www.planalto.gov.br/sitemap.xml",
        category=Category.POLITICA,
        subcategory="Presidência",
        url_pattern=r"/noticias/|/discursos/|/decretos/",
        max_urls=20,
    ),
    SitemapSourceConfig(
        name="Câmara dos Deputados",
        sitemap_url="https://www.camara.leg.br/sitemap.xml",
        category=Category.POLITICA,
        subcategory="Legislativo",
        url_pattern=r"/noticias/|/ultimas-noticias/",
        max_urls=20,
    ),
    SitemapSourceConfig(
        name="Senado Federal",
        sitemap_url="https://www.senado.leg.br/sitemap.xml",
        category=Category.POLITICA,
        subcategory="Legislativo",
        url_pattern=r"/noticias/|/agencia-senado/",
        max_urls=20,
    ),
    SitemapSourceConfig(
        name="STF",
        sitemap_url="https://www.stf.jus.br/sitemap.xml",
        category=Category.POLITICA,
        subcategory="Judiciário",
        url_pattern=r"/noticias/|/informativos/",
        max_urls=20,
    ),
    SitemapSourceConfig(
        name="TSE",
        sitemap_url="https://www.tse.jus.br/sitemap.xml",
        category=Category.POLITICA,
        subcategory="Eleitoral",
        url_pattern=r"/noticias/|/imprensa/",
        max_urls=15,
    ),
    SitemapSourceConfig(
        name="TCU",
        sitemap_url="https://www.tcu.gov.br/sitemap.xml",
        category=Category.POLITICA,
        subcategory="Contas",
        url_pattern=r"/noticias/|/imprensa/",
        max_urls=15,
    ),
    SitemapSourceConfig(
        name="Banco Central",
        sitemap_url="https://www.bcb.gov.br/sitemap.xml",
        category=Category.ECONOMIA,
        subcategory="Banco Central",
        url_pattern=r"/noticias/|/comunicados/|/atas/",
        max_urls=20,
    ),
    SitemapSourceConfig(
        name="IBGE",
        sitemap_url="https://www.ibge.gov.br/sitemap.xml",
        category=Category.ECONOMIA,
        subcategory="Estatísticas",
        url_pattern=r"/noticias/|/releases/",
        max_urls=15,
    ),
    SitemapSourceConfig(
        name="Fiocruz",
        sitemap_url="https://portal.fiocruz.br/sitemap.xml",
        category=Category.SAUDE,
        subcategory="Pesquisa",
        url_pattern=r"/noticia/|/ultimas-noticias/",
        max_urls=15,
    ),
    SitemapSourceConfig(
        name="INPE",
        sitemap_url="https://www.inpe.br/sitemap.xml",
        category=Category.CIENCIA,
        subcategory="Espaço",
        url_pattern=r"/noticias/|/ultimas/",
        max_urls=10,
    ),
    SitemapSourceConfig(
        name="Embrapa",
        sitemap_url="https://www.embrapa.br/sitemap.xml",
        category=Category.CIENCIA,
        subcategory="Agro",
        url_pattern=r"/noticias/|/imprensa/",
        max_urls=10,
    ),

    # Internacional - Organismos
    SitemapSourceConfig(
        name="ONU Brasil",
        sitemap_url="https://brasil.un.org/sitemap.xml",
        category=Category.MUNDO,
        subcategory="ONU",
        url_pattern=r"/noticias/|/press-releases/",
        max_urls=20,
        language="pt",
    ),
    SitemapSourceConfig(
        name="OPAS",
        sitemap_url="https://www.paho.org/sitemap.xml",
        category=Category.SAUDE,
        subcategory="OPAS",
        url_pattern=r"/news/|/noticias/",
        max_urls=20,
        language="pt",
    ),
    SitemapSourceConfig(
        name="UNESCO",
        sitemap_url="https://www.unesco.org/sitemap.xml",
        category=Category.CULTURA,
        subcategory="UNESCO",
        url_pattern=r"/news/|/articles/",
        max_urls=15,
        language="pt",
    ),

    # Latino-América - Governos
    SitemapSourceConfig(
        name="Casa Rosada (AR)",
        sitemap_url="https://www.argentina.gob.ar/sitemap.xml",
        category=Category.LATINO_AMERICA,
        subcategory="Argentina",
        url_pattern=r"/noticias/|/novedades/",
        max_urls=20,
        language="es",
    ),
    SitemapSourceConfig(
        name="Gob.cl (CL)",
        sitemap_url="https://www.gob.cl/sitemap.xml",
        category=Category.LATINO_AMERICA,
        subcategory="Chile",
        url_pattern=r"/noticias/|/prensa/",
        max_urls=15,
        language="es",
    ),
    SitemapSourceConfig(
        name="Gobierno.uy (UY)",
        sitemap_url="https://www.gub.uy/sitemap.xml",
        category=Category.LATINO_AMERICA,
        subcategory="Uruguai",
        url_pattern=r"/noticias/|/comunicados/",
        max_urls=15,
        language="es",
    ),
    SitemapSourceConfig(
        name="Gobierno México",
        sitemap_url="https://www.gob.mx/sitemap.xml",
        category=Category.LATINO_AMERICA,
        subcategory="México",
        url_pattern=r"/articulos/|/prensa/",
        max_urls=20,
        language="es",
    ),

    # Esportes - Oficiais
    SitemapSourceConfig(
        name="FIFA",
        sitemap_url="https://www.fifa.com/sitemap.xml",
        category=Category.ESPORTES,
        subcategory="FIFA",
        url_pattern=r"/news/|/tournaments/",
        max_urls=20,
    ),
    SitemapSourceConfig(
        name="COI",
        sitemap_url="https://olympics.com/sitemap.xml",
        category=Category.ESPORTES,
        subcategory="Olimpíadas",
        url_pattern=r"/news/|/pt/news/",
        max_urls=20,
    ),
    SitemapSourceConfig(
        name="CBF",
        sitemap_url="https://www.cbf.com.br/sitemap.xml",
        category=Category.ESPORTES,
        subcategory="Futebol BR",
        url_pattern=r"/noticias/|/imprensa/",
        max_urls=15,
    ),
    SitemapSourceConfig(
        name="CONMEBOL",
        sitemap_url="https://www.conmebol.com/sitemap.xml",
        category=Category.ESPORTES,
        subcategory="América do Sul",
        url_pattern=r"/noticias/|/news/",
        max_urls=15,
    ),
]


class SitemapSource:
    """Fetch article URLs from sitemaps and extract content."""

    def __init__(self, config: SitemapSourceConfig, http_client: httpx.AsyncClient):
        self.config = config
        self.client = http_client

    async def fetch_sitemap_urls(self) -> list[str]:
        """Parse sitemap and return article URLs."""
        try:
            resp = await self.client.get(self.config.sitemap_url)
            resp.raise_for_status()
        except Exception as e:
            print(f"Sitemap fetch error for {self.config.name}: {e}")
            return []

        urls = []
        try:
            root = etree.fromstring(resp.content)
            # Handle both sitemap index and urlset
            for elem in root.iter():
                tag = elem.tag.split("}")[-1]  # Remove namespace
                if tag == "loc":
                    url = elem.text.strip()
                    if self._is_article_url(url):
                        urls.append(url)
                        if len(urls) >= self.config.max_urls:
                            break
        except Exception as e:
            print(f"Sitemap parse error for {self.config.name}: {e}")

        return urls

    def _is_article_url(self, url: str) -> bool:
        """Check if URL matches article pattern."""
        if self.config.exclude_pattern and re.search(self.config.exclude_pattern, url):
            return False
        if self.config.url_pattern:
            return bool(re.search(self.config.url_pattern, url))
        # Default: look for common article patterns
        return bool(re.search(r"/(noticia|news|article|post|matéria|reportagem|release)s?/", url))

    async def fetch_articles(self) -> list[RawArticle]:
        """Fetch and extract articles from sitemap."""
        urls = await self.fetch_sitemap_urls()
        articles = []

        for url in urls:
            try:
                article = await self._extract_article(url)
                if article:
                    articles.append(article)
            except Exception as e:
                print(f"Extract error for {url}: {e}")

        return articles

    async def _extract_article(self, url: str) -> RawArticle | None:
        """Extract article content using newsplease/readability."""
        from newsplease import NewsPlease
        from readability import Document

        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            html = resp.text

            # Try NewsPlease first
            article = NewsPlease.from_html(html, url=url)
            title = article.title or ""
            text = article.maintext or ""
            authors = article.authors or []
            date_publish = article.date_publish

            # Fallback to readability
            if not text or len(text) < 200:
                doc = Document(html)
                title = title or doc.title()
                text = text or doc.summary()

            if not title or not text or len(text) < 200:
                return None

            # Clean text
            from html2text import html2text
            clean_text = html2text(text)[:5000]

            published_at = date_publish or datetime.now(timezone.utc)
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)

            return RawArticle(
                url=url,
                title=title[:500],
                source_name=self.config.name,
                source_type=SourceType.SITEMAP,
                source_url=url,
                published_at=published_at,
                raw_text=clean_text,
                author=", ".join(authors) if authors else None,
                language=self.config.language,
                category_hint=self.config.category,
                tags=[self.config.subcategory] if self.config.subcategory else [],
                metadata={"sitemap_source": self.config.name},
            )

        except Exception as e:
            print(f"Article extraction failed for {url}: {e}")
            return None


async def fetch_sitemap_articles(
    sources: list[SitemapSourceConfig],
    http_client: httpx.AsyncClient,
) -> list[RawArticle]:
    """Convenience function for pipeline."""
    all_articles = []
    for config in sources:
        source = SitemapSource(config, http_client)
        articles = await source.fetch_articles()
        all_articles.extend(articles)
    return all_articles