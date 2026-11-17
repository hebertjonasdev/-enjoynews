"""Article enrichment with contextual data from free APIs."""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any, Optional

import httpx
from rich.console import Console

from .models import ProcessedArticle, Category

console = Console()


@dataclass
class EnrichmentConfig:
    """API keys for enrichment services."""
    brasil_api_key: Optional[str] = None
    worldbank_key: Optional[str] = None
    alphavantage_key: Optional[str] = None
    coingecko_key: Optional[str] = None
    openweather_key: Optional[str] = None
    restcountries_key: Optional[str] = None


class EnrichmentClient:
    """Fetch contextual data to enrich articles."""

    def __init__(self, config: EnrichmentConfig, http_client: httpx.AsyncClient):
        self.config = config
        self.client = http_client
        self._country_cache: dict[str, dict] = {}
        self._indicator_cache: dict[str, dict] = {}

    # ============================================================
    # Country / Geography (REST Countries - free, no key)
    # ============================================================
    async def get_country_info(self, country_code: str) -> dict[str, Any]:
        """Get country metadata: flag, capital, currency, languages, region."""
        if country_code in self._country_cache:
            return self._country_cache[country_code]

        try:
            # REST Countries v3.1 - free, no auth
            resp = await self.client.get(
                f"https://restcountries.com/v3.1/alpha/{country_code.lower()}",
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            if data:
                country = data[0]
                result = {
                    "name": country.get("name", {}).get("common", ""),
                    "official_name": country.get("name", {}).get("official", ""),
                    "flag": country.get("flags", {}).get("png", ""),
                    "flag_svg": country.get("flags", {}).get("svg", ""),
                    "capital": country.get("capital", [""])[0] if country.get("capital") else "",
                    "region": country.get("region", ""),
                    "subregion": country.get("subregion", ""),
                    "population": country.get("population", 0),
                    "area_km2": country.get("area", 0),
                    "currencies": list(country.get("currencies", {}).keys()),
                    "languages": list(country.get("languages", {}).values()),
                    "timezones": country.get("timezones", []),
                    "borders": country.get("borders", []),
                    "cca2": country.get("cca2", "").lower(),
                    "cca3": country.get("cca3", "").lower(),
                }
                self._country_cache[country_code] = result
                return result
        except Exception as e:
            console.print(f"[yellow]REST Countries error for {country_code}: {e}[/yellow]")

        return {}

    def extract_countries_from_text(self, text: str) -> list[str]:
        """Extract country codes mentioned in text (simple heuristic)."""
        # Common country names -> ISO codes
        country_map = {
            "brasil": "BR", "brazil": "BR",
            "estados unidos": "US", "eua": "US", "united states": "US",
            "china": "CN",
            "rússia": "RU", "russia": "RU",
            "índia": "IN", "india": "IN",
            "alemanha": "DE", "germany": "DE",
            "frança": "FR", "france": "FR",
            "japão": "JP", "japan": "JP",
            "reino unido": "GB", "uk": "GB",
            "itália": "IT", "italy": "IT",
            "canadá": "CA", "canada": "CA",
            "austrália": "AU", "australia": "AU",
            "coreia do sul": "KR", "south korea": "KR",
            "méxico": "MX", "mexico": "MX",
            "argentina": "AR",
            "colômbia": "CO", "colombia": "CO",
            "chile": "CL",
            "peru": "PE",
            "venezuela": "VE",
            "equador": "EC", "ecuador": "EC",
            "bolívia": "BO", "bolivia": "BO",
            "paraguai": "PY", "paraguay": "PY",
            "uruguai": "UY", "uruguay": "UY",
            "portugal": "PT",
            "espanha": "ES", "spain": "ES",
            "frança": "FR",
            "ítalia": "IT",
        }

        text_lower = text.lower()
        found = []
        for name, code in country_map.items():
            if name in text_lower and code not in found:
                found.append(code)
        return found[:5]  # Limit

    # ============================================================
    # Economic Indicators (World Bank - free, no key for basic)
    # ============================================================
    async def get_worldbank_indicators(self, country_code: str, indicators: list[str]) -> dict[str, Any]:
        """Fetch World Bank indicators for a country.

        Common indicators:
        - NY.GDP.MKTP.CD: GDP (current US$)
        - NY.GDP.MKTP.KD.ZG: GDP growth (annual %)
        - FP.CPI.TOTL.ZG: Inflation, consumer prices (annual %)
        - SL.UEM.TOTL.ZS: Unemployment, total (% of labor force)
        - NE.EXP.GNFS.ZS: Exports of goods and services (% of GDP)
        - NE.IMP.GNFS.ZS: Imports of goods and services (% of GDP)
        """
        cache_key = f"{country_code}:{','.join(sorted(indicators))}"
        if cache_key in self._indicator_cache:
            return self._indicator_cache[cache_key]

        try:
            indicator_str = ";".join(indicators)
            url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator_str}"
            params = {"format": "json", "per_page": 10, "date": "2020:2024"}
            resp = await self.client.get(url, params=params, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()

            result = {}
            if len(data) > 1 and data[1]:
                for entry in data[1]:
                    indicator_id = entry.get("indicator", {}).get("id", "")
                    value = entry.get("value")
                    year = entry.get("date")
                    if value is not None:
                        if indicator_id not in result:
                            result[indicator_id] = []
                        result[indicator_id].append({"year": year, "value": value})

            self._indicator_cache[cache_key] = result
            return result
        except Exception as e:
            console.print(f"[yellow]World Bank error for {country_code}: {e}[/yellow]")
            return {}

    # ============================================================
    # Financial Markets (Alpha Vantage - free 25/day)
    # ============================================================
    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        """Get real-time stock quote (Alpha Vantage)."""
        if not self.config.alphavantage_key:
            return {}

        try:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.config.alphavantage_key,
            }
            resp = await self.client.get("https://www.alphavantage.co/query", params=params, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()

            quote = data.get("Global Quote", {})
            if quote:
                return {
                    "symbol": quote.get("01. symbol"),
                    "price": float(quote.get("05. price", 0)),
                    "change": float(quote.get("09. change", 0)),
                    "change_percent": quote.get("10. change percent", "").replace("%", ""),
                    "volume": int(quote.get("06. volume", 0)),
                    "latest_trading_day": quote.get("07. latest trading day"),
                }
        except Exception as e:
            console.print(f"[yellow]Alpha Vantage error for {symbol}: {e}[/yellow]")
        return {}

    def extract_tickers_from_text(self, text: str) -> list[str]:
        """Extract potential stock tickers from text."""
        # Brazilian tickers: PETR4, VALE3, ITUB4, BBDC4, ABEV3, etc.
        # US tickers: AAPL, MSFT, GOOGL, TSLA, etc.
        # Pattern: 3-5 uppercase letters + optional number (BR style)
        br_pattern = r"\b[A-Z]{4}\d\b"
        us_pattern = r"\b[A-Z]{2,5}\b"

        tickers = set()
        for match in re.finditer(br_pattern, text):
            tickers.add(match.group())
        # Common US tickers (avoid false positives)
        common_us = {"AAPL", "MSFT", "GOOGL", "GOOG", "TSLA", "AMZN", "META", "NVDA", "NFLX", "JPM", "V", "MA", "UNH", "HD", "PG", "DIS", "PYPL", "ADBE", "CRM", "INTC", "CSCO", "VZ", "KO", "PEP", "WMT", "MRK", "PFE", "T", "VZ", "CVX", "XOM", "COP", "BA", "CAT", "GE", "IBM", "ORCL", "CRM", "NOW", "AMD", "QCOM", "AVGO", "TXN", "AMAT", "MU", "LRCX", "KLAC", "SNPS", "CDNS", "MCHP", "ADI", "MRVL", "ON", "FTNT", "PANW", "ZS", "CRWD", "OKTA", "DDOG", "SNOW", "PLTR", "RBLX", "U", "NET", "ESTC", "MDB", "TEAM", "ATLASSIAN", "SHOP", "SQ", "PYPL", "ADYEN", "STRIPE"}
        for match in re.finditer(us_pattern, text):
            ticker = match.group()
            if ticker in common_us:
                tickers.add(ticker)
        return list(tickers)[:5]

    # ============================================================
    # Crypto (CoinGecko - free, generous)
    # ============================================================
    async def get_crypto_price(self, coin_id: str) -> dict[str, Any]:
        """Get crypto price in BRL and USD."""
        try:
            params = {
                "ids": coin_id,
                "vs_currencies": "brl,usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
            }
            resp = await self.client.get("https://api.coingecko.com/api/v3/simple/price", params=params, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()

            if coin_id in data:
                return {
                    "id": coin_id,
                    "brl": data[coin_id].get("brl"),
                    "usd": data[coin_id].get("usd"),
                    "change_24h": data[coin_id].get("brl_24h_change") or data[coin_id].get("usd_24h_change"),
                    "vol_24h": data[coin_id].get("brl_24h_vol") or data[coin_id].get("usd_24h_vol"),
                }
        except Exception as e:
            console.print(f"[yellow]CoinGecko error for {coin_id}: {e}[/yellow]")
        return {}

    def extract_crypto_from_text(self, text: str) -> list[str]:
        """Extract crypto mentions."""
        crypto_map = {
            "bitcoin": "bitcoin", "btc": "bitcoin",
            "ethereum": "ethereum", "eth": "ethereum",
            "solana": "solana", "sol": "solana",
            "ripple": "ripple", "xrp": "ripple",
            "cardano": "cardano", "ada": "cardano",
            "dogecoin": "dogecoin", "doge": "dogecoin",
            "polkadot": "polkadot", "dot": "polkadot",
            "polygon": "matic-network", "matic": "matic-network",
            "avalanche": "avalanche-2", "avax": "avalanche-2",
            "chainlink": "chainlink", "link": "chainlink",
            "uniswap": "uniswap", "uni": "uniswap",
        }
        text_lower = text.lower()
        found = []
        for name, id_ in crypto_map.items():
            if name in text_lower and id_ not in found:
                found.append(id_)
        return found[:3]

    # ============================================================
    # Weather (OpenWeatherMap - free 1000/day)
    # ============================================================
    async def get_weather(self, city: str, country_code: str = "BR") -> dict[str, Any]:
        """Get current weather for context."""
        if not self.config.openweather_key:
            return {}

        try:
            params = {
                "q": f"{city},{country_code}",
                "appid": self.config.openweather_key,
                "units": "metric",
                "lang": "pt_br",
            }
            resp = await self.client.get("https://api.openweathermap.org/data/2.5/weather", params=params, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()

            return {
                "city": data.get("name"),
                "country": data.get("sys", {}).get("country"),
                "temp": data.get("main", {}).get("temp"),
                "feels_like": data.get("main", {}).get("feels_like"),
                "humidity": data.get("main", {}).get("humidity"),
                "description": data.get("weather", [{}])[0].get("description"),
                "icon": data.get("weather", [{}])[0].get("icon"),
                "wind_speed": data.get("wind", {}).get("speed"),
            }
        except Exception as e:
            console.print(f"[yellow]OpenWeather error for {city}: {e}[/yellow]")
        return {}

    # ============================================================
    # Brazil Specific (Brasil API - free, no key)
    # ============================================================
    async def get_brasil_api(self, endpoint: str) -> dict[str, Any]:
        """Generic Brasil API call."""
        try:
            resp = await self.client.get(f"https://brasilapi.com.br/api/{endpoint}", timeout=10.0)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            console.print(f"[yellow]Brasil API error for {endpoint}: {e}[/yellow]")
            return {}

    async def get_feriados(self, ano: int = 2025) -> list[dict]:
        """Feriados nacionais Brasil."""
        return await self.get_brasil_api(f"feriados/v1/{ano}")

    async def get_bancos(self) -> list[dict]:
        """Lista de bancos brasileiros."""
        return await self.get_brasil_api("banks/v1")

    async def get_cep(self, cep: str) -> dict:
        """Consulta CEP."""
        return await self.get_brasil_api(f"cep/v1/{cep}")

    async def get_ddd(self, ddd: str) -> dict:
        """Consulta DDD."""
        return await self.get_brasil_api(f"ddd/v1/{ddd}")

    async def get_cnpj(self, cnpj: str) -> dict:
        """Consulta CNPJ."""
        return await self.get_brasil_api(f"cnpj/v1/{cnpj}")

    async def get_ibge_municipios(self, uf: str) -> list[dict]:
        """Municípios por UF."""
        return await self.get_brasil_api(f"ibge/municipios/v1/{uf}")

    # ============================================================
    # Main enrichment orchestration
    # ============================================================
    async def enrich_article(self, article: ProcessedArticle) -> ProcessedArticle:
        """Enrich article with contextual data based on category and content."""
        full_text = f"{article.summary.headline} {article.summary.full_text}"
        category = article.raw.category_hint

        enrichment = {
            "countries": [],
            "indicators": {},
            "stocks": {},
            "crypto": {},
            "weather": {},
            "brasil_data": {},
        }

        # 1. Countries mentioned
        country_codes = self.extract_countries_from_text(full_text)
        if country_codes:
            # Primary country from category
            primary_country = None
            if category == Category.BRASIL or category == Category.POLITICA or category == Category.ECONOMIA:
                primary_country = "BR"
            elif category == Category.LATINO_AMERICA:
                # Try to guess from text
                latam_codes = {"AR", "MX", "CO", "CL", "PE", "VE", "EC", "BO", "PY", "UY"}
                for c in country_codes:
                    if c in latam_codes:
                        primary_country = c
                        break

            # Fetch country info for all mentioned
            for code in country_codes:
                info = await self.get_country_info(code)
                if info:
                    enrichment["countries"].append(info)

            # Fetch economic indicators for primary country
            if primary_country:
                indicators = [
                    "NY.GDP.MKTP.CD",      # GDP
                    "NY.GDP.MKTP.KD.ZG",   # GDP growth
                    "FP.CPI.TOTL.ZG",      # Inflation
                    "SL.UEM.TOTL.ZS",      # Unemployment
                ]
                enrichment["indicators"] = await self.get_worldbank_indicators(primary_country, indicators)

                # Brazil-specific data
                if primary_country == "BR":
                    feriados = await self.get_feriados()
                    if feriados:
                        enrichment["brasil_data"]["feriados"] = feriados[:10]

        # 2. Stock tickers
        tickers = self.extract_tickers_from_text(full_text)
        for ticker in tickers[:3]:
            quote = await self.get_stock_quote(ticker)
            if quote:
                enrichment["stocks"][ticker] = quote

        # 3. Crypto
        cryptos = self.extract_crypto_from_text(full_text)
        for coin in cryptos[:2]:
            price = await self.get_crypto_price(coin)
            if price:
                enrichment["crypto"][coin] = price

        # 3. Weather (for environment/disaster news)
        if category in [Category.MEIO_AMBIENTE, Category.SAUDE, Category.CIENCIA]:
            # Try to extract city from text
            # Simplified: use capital of primary country
            if country_codes:
                capital_map = {"BR": "Brasília", "AR": "Buenos Aires", "MX": "Cidade do México", "CO": "Bogotá", "CL": "Santiago", "PE": "Lima"}
                city = capital_map.get(country_codes[0])
                if city:
                    enrichment["weather"] = await self.get_weather(city, country_codes[0])

        # Attach enrichment to article metadata
        article.raw.metadata["enrichment"] = enrichment
        return article


async def enrich_articles(articles: list[ProcessedArticle], config: EnrichmentConfig, http_client: httpx.AsyncClient) -> list[ProcessedArticle]:
    """Enrich multiple articles in parallel (with concurrency limit)."""
    client = EnrichmentClient(config, http_client)
    semaphore = asyncio.Semaphore(5)

    async def enrich_one(article: ProcessedArticle) -> ProcessedArticle:
        async with semaphore:
            return await client.enrich_article(article)

    return await asyncio.gather(*[enrich_one(a) for a in articles])