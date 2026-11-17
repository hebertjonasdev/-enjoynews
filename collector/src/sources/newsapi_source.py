"""NewsAPI.org and GNews.io source adapters."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from ..models import Category, RawArticle, SourceType


@dataclass
class NewsAPIConfig:
    api_key: str
    base_url: str = "https://newsapi.org/v2"
    language: str = "pt"
    page_size: int = 50


@dataclass
class GNewsConfig:
    api_key: str
    base_url: str = "https://gnews.io/api/v4"
    language: str = "pt"
    max_results: int = 50


CATEGORY_MAPPING_NEWS_API = {
    "general": Category.BRASIL,
    "business": Category.ECONOMIA,
    "technology": Category.TECNOLOGIA,
    "science": Category.CIENCIA,
    "health": Category.SAUDE,
    "sports": Category.ESPORTES,
    "entertainment": Category.CULTURA,
}

CATEGORY_MAPPING_GNEWS = {
    "general": Category.BRASIL,
    "business": Category.ECONOMIA,
    "technology": Category.TECNOLOGIA,
    "science": Category.CIENCIA,
    "health": Category.SAUDE,
    "sports": Category.ESPORTES,
    "entertainment": Category.CULTURA,
}


class NewsAPISource:
    """NewsAPI.org free tier adapter (100 req/day)."""

    def __init__(self, config: NewsAPIConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_top_headlines(
        self,
        category: str = "general",
        country: str = "br",
        page: int = 1,
    ) -> list[RawArticle]:
        """Fetch top headlines for a category."""
        params = {
            "apiKey": self.config.api_key,
            "category": category,
            "country": country,
            "language": self.config.language,
            "pageSize": self.config.page_size,
            "page": page,
        }
        url = f"{self.config.base_url}/top-headlines"
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("articles", []):
            if not item.get("url") or not item.get("title"):
                continue
            published = item.get("publishedAt")
            if published:
                published_at = datetime.fromisoformat(published.replace("Z", "+00:00"))
            else:
                published_at = datetime.now(timezone.utc)

            articles.append(RawArticle(
                url=item["url"],
                title=item["title"],
                source_name=f"NewsAPI - {item.get('source', {}).get('name', 'Unknown')}",
                source_type=SourceType.NEWSAPI,
                source_url=item.get("url"),
                published_at=published_at,
                raw_text=item.get("description") or item.get("content"),
                author=item.get("author"),
                language=item.get("language", "pt"),
                category_hint=CATEGORY_MAPPING_NEWS_API.get(category),
                tags=[category],
                metadata={"newsapi_category": category, "newsapi_source": item.get("source")},
            ))
        return articles

    async def fetch_everything(
        self,
        query: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        page: int = 1,
    ) -> list[RawArticle]:
        """Search articles (limited in free tier)."""
        params = {
            "apiKey": self.config.api_key,
            "q": query,
            "language": self.config.language,
            "pageSize": self.config.page_size,
            "page": page,
            "sortBy": "publishedAt",
        }
        if from_date:
            params["from"] = from_date.isoformat()
        if to_date:
            params["to"] = to_date.isoformat()

        url = f"{self.config.base_url}/everything"
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("articles", []):
            if not item.get("url") or not item.get("title"):
                continue
            published = item.get("publishedAt")
            published_at = datetime.fromisoformat(published.replace("Z", "+00:00")) if published else datetime.now(timezone.utc)

            articles.append(RawArticle(
                url=item["url"],
                title=item["title"],
                source_name=f"NewsAPI - {item.get('source', {}).get('name', 'Unknown')}",
                source_type=SourceType.NEWSAPI,
                source_url=item.get("url"),
                published_at=published_at,
                raw_text=item.get("description") or item.get("content"),
                author=item.get("author"),
                language=item.get("language", "pt"),
                category_hint=Category.BRASIL,  # default, will be reclassified
                tags=[query],
                metadata={"newsapi_query": query, "newsapi_source": item.get("source")},
            ))
        return articles

    async def close(self):
        await self.client.aclose()


class GNewsSource:
    """GNews.io free tier adapter (100 req/day)."""

    def __init__(self, config: GNewsConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_top_headlines(
        self,
        category: str = "general",
        country: str = "br",
        page: int = 1,
    ) -> list[RawArticle]:
        params = {
            "token": self.config.api_key,
            "category": category,
            "lang": self.config.language,
            "country": country,
            "max": self.config.max_results,
            "page": page,
        }
        url = f"{self.config.base_url}/top-headlines"
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("articles", []):
            if not item.get("url") or not item.get("title"):
                continue
            published = item.get("publishedAt")
            published_at = datetime.fromisoformat(published.replace("Z", "+00:00")) if published else datetime.now(timezone.utc)

            articles.append(RawArticle(
                url=item["url"],
                title=item["title"],
                source_name=f"GNews - {item.get('source', {}).get('name', 'Unknown')}",
                source_type=SourceType.GNEWS,
                source_url=item.get("url"),
                published_at=published_at,
                raw_text=item.get("description") or item.get("content"),
                author=item.get("source", {}).get("name"),
                language=self.config.language,
                category_hint=CATEGORY_MAPPING_GNEWS.get(category),
                tags=[category],
                metadata={"gnews_category": category, "gnews_source": item.get("source")},
            ))
        return articles

    async def fetch_search(
        self,
        query: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        page: int = 1,
    ) -> list[RawArticle]:
        params = {
            "token": self.config.api_key,
            "q": query,
            "lang": self.config.language,
            "max": self.config.max_results,
            "page": page,
        }
        if from_date:
            params["from"] = from_date.isoformat()
        if to_date:
            params["to"] = to_date.isoformat()

        url = f"{self.config.base_url}/search"
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("articles", []):
            if not item.get("url") or not item.get("title"):
                continue
            published = item.get("publishedAt")
            published_at = datetime.fromisoformat(published.replace("Z", "+00:00")) if published else datetime.now(timezone.utc)

            articles.append(RawArticle(
                url=item["url"],
                title=item["title"],
                source_name=f"GNews - {item.get('source', {}).get('name', 'Unknown')}",
                source_type=SourceType.GNEWS,
                source_url=item.get("url"),
                published_at=published_at,
                raw_text=item.get("description") or item.get("content"),
                author=item.get("source", {}).get("name"),
                language=self.config.language,
                category_hint=Category.BRASIL,
                tags=[query],
                metadata={"gnews_query": query, "gnews_source": item.get("source")},
            ))
        return articles

    async def close(self):
        await self.client.aclose()


# Convenience functions for pipeline
async def fetch_newsapi_articles(api_key: str, categories: list[str] | None = None) -> list[RawArticle]:
    """Fetch from NewsAPI for multiple categories."""
    if not api_key:
        return []
    config = NewsAPIConfig(api_key=api_key)
    source = NewsAPISource(config)
    cats = categories or list(CATEGORY_MAPPING_NEWS_API.keys())
    all_articles = []
    for cat in cats:
        try:
            articles = await source.fetch_top_headlines(category=cat)
            all_articles.extend(articles)
        except Exception as e:
            print(f"NewsAPI error for {cat}: {e}")
    await source.close()
    return all_articles


async def fetch_gnews_articles(api_key: str, categories: list[str] | None = None) -> list[RawArticle]:
    """Fetch from GNews for multiple categories."""
    if not api_key:
        return []
    config = GNewsConfig(api_key=api_key)
    source = GNewsSource(config)
    cats = categories or list(CATEGORY_MAPPING_GNEWS.keys())
    all_articles = []
    for cat in cats:
        try:
            articles = await source.fetch_top_headlines(category=cat)
            all_articles.extend(articles)
        except Exception as e:
            print(f"GNews error for {cat}: {e}")
    await source.close()
    return all_articles