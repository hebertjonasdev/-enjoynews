"""Nitter (Twitter/X alternative frontend) RSS source for social signals."""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx
import feedparser

from ..models import Category, RawArticle, SourceType


@dataclass
class NitterConfig:
    instances: list[str]
    timeout: int = 30
    max_per_query: int = 20


# Curated accounts to monitor (official orgs, journalists, breaking news)
NITTER_ACCOUNTS = {
    # Brasil - Oficiais
    "planalto": Category.POLITICA,
    "govbr": Category.BRASIL,
    "camaradeputados": Category.POLITICA,
    "senadofederal": Category.POLITICA,
    "stf_oficial": Category.POLITICA,
    "tsejus": Category.POLITICA,
    "tcuniao": Category.POLITICA,
    "cguonline": Category.POLITICA,
    "mpf_pgr": Category.POLITICA,
    "pfdc_oficial": Category.POLITICA,
    "defensoria_uni": Category.POLITICA,
    "agenciabrasil": Category.BRASIL,
    "radioagenciabrasil": Category.BRASIL,
    "ebc_radios": Category.CULTURA,
    "tvbrasil": Category.CULTURA,

    # Brasil - Jornalistas/Veículos
    "g1": Category.BRASIL,
    "folha": Category.BRASIL,
    "uolnoticias": Category.BRASIL,
    "estadao": Category.BRASIL,
    "valoreconomico": Category.ECONOMIA,
    "cnnbrasil": Category.BRASIL,
    "poder360": Category.POLITICA,
    "metropoles": Category.BRASIL,
    "brasildefato": Category.BRASIL,
    "jornalnexio": Category.BRASIL,
    "revistaforum": Category.BRASIL,
    "cartacapital": Category.BRASIL,

    # Economia
    "bcb_oficial": Category.ECONOMIA,
    "cvm_oficial": Category.ECONOMIA,
    "bnDES": Category.ECONOMIA,
    "ibge": Category.ECONOMIA,
    "ipeadata": Category.ECONOMIA,
    "fgv_ibre": Category.ECONOMIA,

    # Mundo - Oficiais
    "un": Category.MUNDO,
    "un_portuguese": Category.MUNDO,
    "who": Category.SAUDE,
    "pahowho": Category.SAUDE,
    "imfnews": Category.ECONOMIA,
    "worldbank": Category.ECONOMIA,
    "wto": Category.ECONOMIA,
    "unesco": Category.CULTURA,
    "ilo": Category.ECONOMIA,
    "unhcr": Category.MUNDO,
    "unicef": Category.MUNDO,
    "faonews": Category.MEIO_AMBIENTE,
    "wfp": Category.MUNDO,

    # Latino-América - Oficiais
    "casarosada": Category.LATINO_AMERICA,
    "presidencial_cl": Category.LATINO_AMERICA,
    "presidencia_uy": Category.LATINO_AMERICA,
    "presidencia_py": Category.LATINO_AMERICA,
    "presidencia_bo": Category.LATINO_AMERICA,
    "presidencia_ec": Category.LATINO_AMERICA,
    "presidencia_pe": Category.LATINO_AMERICA,
    "cancilleria_ar": Category.LATINO_AMERICA,
    "sre_mx": Category.LATINO_AMERICA,
    "minrel_chile": Category.LATINO_AMERICA,
    "minexterior_col": Category.LATINO_AMERICA,

    # Latino-América - Veículos
    "clarincom": Category.LATINO_AMERICA,
    "lanacion": Category.LATINO_AMERICA,
    "pagina12": Category.LATINO_AMERICA,
    "eluniversal_mx": Category.LATINO_AMERICA,
    "lajornada": Category.LATINO_AMERICA,
    "milenio": Category.LATINO_AMERICA,
    "eltiempo": Category.LATINO_AMERICA,
    "elespectador": Category.LATINO_AMERICA,
    "latercera": Category.LATINO_AMERICA,
    "elmercurio": Category.LATINO_AMERICA,
    "elcomercio_peru": Category.LATINO_AMERICA,
    "larepublica_pe": Category.LATINO_AMERICA,
    "eluniverso_ec": Category.LATINO_AMERICA,
    "elobservador_uy": Category.LATINO_AMERICA,
    "larazon_bo": Category.LATINO_AMERICA,
    "abc_color_py": Category.LATINO_AMERICA,
    "elnacionalweb": Category.LATINO_AMERICA,

    # Organizações Esportivas
    "fifa": Category.ESPORTES,
    "fifaworldcup": Category.ESPORTES,
    "olympics": Category.ESPORTES,
    "paralympics": Category.ESPORTES,
    "cbffutebol": Category.ESPORTES,
    "conmebol": Category.ESPORTES,
    "uefa": Category.ESPORTES,
}

# Hashtags to monitor for breaking/trending
NITTER_HASHTAGS = [
    "#Brasil",
    "#PoliticaBR",
    "#EconomiaBR",
    "#TecnologiaBR",
    "#CienciaBR",
    "#SaudeBR",
    "#MeioAmbiente",
    "#LatinoAmerica",
    "#AmericaLatina",
    "#Mercosul",
    "#OEABrasil",
    "#ONU",
    "#OMS",
    "#FIFA",
    "#COI",
]


class NitterSource:
    """Fetch tweets via Nitter RSS feeds."""

    def __init__(self, config: NitterConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            timeout=config.timeout,
            headers={"User-Agent": "EnjoyNewsBot/0.1"},
        )
        self._instance_cycle = iter(config.instances)

    def _get_instance(self) -> str:
        """Get next instance (round-robin with fallback)."""
        try:
            return next(self._instance_cycle)
        except StopIteration:
            self._instance_cycle = iter(self.config.instances)
            return next(self._instance_cycle)

    async def _fetch_rss(self, url: str) -> list[RawArticle]:
        """Fetch and parse RSS from Nitter instance."""
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
        except Exception:
            # Try next instance
            instance = self._get_instance()
            new_url = url.replace(self.config.instances[0], instance) if self.config.instances else url
            try:
                resp = await self.client.get(new_url)
                resp.raise_for_status()
            except Exception:
                return []

        feed = feedparser.parse(resp.text)
        articles = []

        for entry in feed.entries[:self.config.max_per_query]:
            # Nitter RSS entry structure
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

            # Extract username from link: https://nitter.net/user/status/123
            username = "unknown"
            try:
                parts = link.split("/")
                if len(parts) >= 4:
                    username = parts[3]
            except Exception:
                pass

            category = NITTER_ACCOUNTS.get(username.lower(), Category.BRASIL)

            articles.append(RawArticle(
                url=link,
                title=title[:500],
                source_name=f"X/@{username}",
                source_type=SourceType.NITTER,
                source_url=link,
                published_at=published_at,
                raw_text=summary,
                author=username,
                language="pt",
                category_hint=category,
                tags=["x", "twitter", "social", username],
                metadata={"nitter_username": username, "nitter_instance": self._get_instance()},
            ))

        return articles

    async def fetch_account_timeline(self, username: str, instance: str | None = None) -> list[RawArticle]:
        """Fetch RSS for a specific account."""
        instance = instance or self._get_instance()
        url = f"{instance}/{quote(username)}/rss"
        return await self._fetch_rss(url)

    async def fetch_hashtag(self, hashtag: str, instance: str | None = None) -> list[RawArticle]:
        """Fetch RSS for a hashtag search."""
        instance = instance or self._get_instance()
        url = f"{instance}/search/rss?q={quote(hashtag)}&f=tweets"
        return await self._fetch_rss(url)

    async def fetch_all_accounts(self, limit_per_account: int = 5) -> list[RawArticle]:
        """Fetch from all curated accounts (sample)."""
        all_articles = []
        accounts = list(NITTER_ACCOUNTS.keys())
        random.shuffle(accounts)

        for username in accounts[:30]:  # Limit to 30 accounts per run
            try:
                articles = await self.fetch_account_timeline(username)
                all_articles.extend(articles[:limit_per_account])
            except Exception as e:
                print(f"Nitter error for @{username}: {e}")

        return all_articles

    async def fetch_hashtags(self, limit_per_tag: int = 3) -> list[RawArticle]:
        """Fetch from trending hashtags."""
        all_articles = []
        for tag in NITTER_HASHTAGS[:10]:
            try:
                articles = await self.fetch_hashtag(tag)
                all_articles.extend(articles[:limit_per_tag])
            except Exception as e:
                print(f"Nitter hashtag error for {tag}: {e}")
        return all_articles

    async def close(self):
        await self.client.aclose()


async def fetch_nitter_articles(instances: list[str]) -> list[RawArticle]:
    """Convenience function for pipeline."""
    if not instances:
        return []
    config = NitterConfig(instances=instances)
    source = NitterSource(config)
    articles = []
    try:
        articles.extend(await source.fetch_all_accounts())
        articles.extend(await source.fetch_hashtags())
    finally:
        await source.close()
    return articles