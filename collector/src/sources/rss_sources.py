"""RSS/Atom feed sources for EnjoyNews - curated free sources."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..models import Category, SourceType


@dataclass(frozen=True)
class RssSource:
    """RSS feed configuration."""
    name: str
    url: str
    category: Category
    subcategory: str | None = None
    language: str = "pt"
    selector: str | None = None  # CSS selector for full content if needed
    enabled: bool = True


# ============================================================
# BRASIL - Principais portais
# ============================================================
BRASIL_SOURCES = [
    # G1 / Globo
    RssSource("G1 - Últimas", "https://g1.globo.com/rss/g1/", Category.BRASIL, "Geral"),
    RssSource("G1 - Política", "https://g1.globo.com/rss/g1/politica/", Category.POLITICA, "Brasil"),
    RssSource("G1 - Economia", "https://g1.globo.com/rss/g1/economia/", Category.ECONOMIA, "Brasil"),
    RssSource("G1 - Mundo", "https://g1.globo.com/rss/g1/mundo/", Category.MUNDO, "Brasil"),
    RssSource("G1 - Tecnologia", "https://g1.globo.com/rss/g1/tecnologia/", Category.TECNOLOGIA, "Brasil"),
    RssSource("G1 - Ciência", "https://g1.globo.com/rss/g1/ciencia/", Category.CIENCIA, "Brasil"),
    RssSource("G1 - Saúde", "https://g1.globo.com/rss/g1/saude/", Category.SAUDE, "Brasil"),
    RssSource("G1 - Meio Ambiente", "https://g1.globo.com/rss/g1/meio-ambiente/", Category.MEIO_AMBIENTE, "Brasil"),
    RssSource("G1 - Educação", "https://g1.globo.com/rss/g1/educacao/", Category.EDUCACAO, "Brasil"),
    RssSource("G1 - Esportes", "https://ge.globo.com/rss/", Category.ESPORTES, "Brasil"),

    # Folha de S.Paulo
    RssSource("Folha - Em Foco", "https://feeds.folha.uol.com.br/emfoco/rss091.xml", Category.BRASIL, "Geral"),
    RssSource("Folha - Política", "https://feeds.folha.uol.com.br/politica/rss091.xml", Category.POLITICA, "Brasil"),
    RssSource("Folha - Mercado", "https://feeds.folha.uol.com.br/mercado/rss091.xml", Category.ECONOMIA, "Brasil"),
    RssSource("Folha - Mundo", "https://feeds.folha.uol.com.br/mundo/rss091.xml", Category.MUNDO, "Brasil"),
    RssSource("Folha - Ciência", "https://feeds.folha.uol.com.br/ciencia/rss091.xml", Category.CIENCIA, "Brasil"),
    RssSource("Folha - Tec", "https://feeds.folha.uol.com.br/tec/rss091.xml", Category.TECNOLOGIA, "Brasil"),
    RssSource("Folha - Esporte", "https://feeds.folha.uol.com.br/esporte/rss091.xml", Category.ESPORTES, "Brasil"),
    RssSource("Folha - Ilustrada", "https://feeds.folha.uol.com.br/ilustrada/rss091.xml", Category.CULTURA, "Brasil"),

    # UOL
    RssSource("UOL - Notícias", "https://rss.uol.com.br/feed/noticias.xml", Category.BRASIL, "Geral"),
    RssSource("UOL - Política", "https://rss.uol.com.br/feed/politica.xml", Category.POLITICA, "Brasil"),
    RssSource("UOL - Economia", "https://rss.uol.com.br/feed/economia.xml", Category.ECONOMIA, "Brasil"),
    RssSource("UOL - Mundo", "https://rss.uol.com.br/feed/mundo.xml", Category.MUNDO, "Brasil"),
    RssSource("UOL - Tecnologia", "https://rss.uol.com.br/feed/tecnologia.xml", Category.TECNOLOGIA, "Brasil"),
    RssSource("UOL - Ciência", "https://rss.uol.com.br/feed/cienciaesaude.xml", Category.CIENCIA, "Brasil"),
    RssSource("UOL - Esportes", "https://rss.uol.com.br/feed/esporte.xml", Category.ESPORTES, "Brasil"),

    # Estadão
    RssSource("Estadão - Geral", "https://www.estadao.com.br/feed/", Category.BRASIL, "Geral"),
    RssSource("Estadão - Política", "https://politica.estadao.com.br/feed/", Category.POLITICA, "Brasil"),
    RssSource("Estadão - Economia", "https://economia.estadao.com.br/feed/", Category.ECONOMIA, "Brasil"),
    RssSource("Estadão - Internacional", "https://internacional.estadao.com.br/feed/", Category.MUNDO, "Brasil"),
    RssSource("Estadão - Tecnologia", "https://tecnologia.estadao.com.br/feed/", Category.TECNOLOGIA, "Brasil"),
    RssSource("Estadão - Esportes", "https://esportes.estadao.com.br/feed/", Category.ESPORTES, "Brasil"),

    # Valor Econômico
    RssSource("Valor - Brasil", "https://valor.globo.com/rss/valor/brasil/", Category.ECONOMIA, "Brasil"),
    RssSource("Valor - Internacional", "https://valor.globo.com/rss/valor/internacional/", Category.MUNDO, "Brasil"),
    RssSource("Valor - Empresas", "https://valor.globo.com/rss/valor/empresas/", Category.ECONOMIA, "Brasil"),
    RssSource("Valor - Finanças", "https://valor.globo.com/rss/valor/financas/", Category.ECONOMIA, "Brasil"),

    # CNN Brasil
    RssSource("CNN Brasil", "https://www.cnnbrasil.com.br/feed/", Category.BRASIL, "Geral"),

    # Poder360
    RssSource("Poder360", "https://www.poder360.com.br/feed/", Category.POLITICA, "Brasil"),

    # Metrópoles
    RssSource("Metrópoles", "https://www.metropoles.com/feed/", Category.BRASIL, "Geral"),

    # Brasil de Fato
    RssSource("Brasil de Fato", "https://www.brasildefato.com.br/feed", Category.BRASIL, "Geral"),

    # Agência Brasil (oficial)
    RssSource("Agência Brasil", "https://agenciabrasil.ebc.com.br/rss.xml", Category.BRASIL, "Oficial"),
]

# ============================================================
# MUNDO - Portais internacionais (PT/EN/ES)
# ============================================================
MUNDO_SOURCES = [
    # BBC
    RssSource("BBC Brasil", "https://feeds.bbci.co.uk/portuguese/rss.xml", Category.MUNDO, "BBC"),
    RssSource("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", Category.MUNDO, "BBC"),
    RssSource("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml", Category.ECONOMIA, "BBC"),
    RssSource("BBC Tech", "https://feeds.bbci.co.uk/news/technology/rss.xml", Category.TECNOLOGIA, "BBC"),
    RssSource("BBC Science", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", Category.CIENCIA, "BBC"),

    # The New York Times (PT)
    RssSource("NYT Brasil", "https://www.nytimes.com/pt/feed/", Category.MUNDO, "NYT"),
    RssSource("NYT World", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", Category.MUNDO, "NYT"),
    RssSource("NYT Business", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", Category.ECONOMIA, "NYT"),
    RssSource("NYT Tech", "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml", Category.TECNOLOGIA, "NYT"),
    RssSource("NYT Science", "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml", Category.CIENCIA, "NYT"),

    # Reuters (PT)
    RssSource("Reuters Brasil", "https://feeds.reuters.com/reuters/brazilNews", Category.MUNDO, "Reuters"),
    RssSource("Reuters World", "https://feeds.reuters.com/reuters/worldNews", Category.MUNDO, "Reuters"),
    RssSource("Reuters Business", "https://feeds.reuters.com/reuters/businessNews", Category.ECONOMIA, "Reuters"),
    RssSource("Reuters Tech", "https://feeds.reuters.com/reuters/technologyNews", Category.TECNOLOGIA, "Reuters"),

    # AP News
    RssSource("AP News World", "https://feeds.apnews.com/rss/apf-worldnews", Category.MUNDO, "AP"),
    RssSource("AP News Business", "https://feeds.apnews.com/rss/apf-business", Category.ECONOMIA, "AP"),

    # El País (Brasil/América Latina)
    RssSource("El País Brasil", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/brasil", Category.LATINO_AMERICA, "El País"),
    RssSource("El País Internacional", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/internacional", Category.MUNDO, "El País"),
    RssSource("El País Economía", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/economia", Category.ECONOMIA, "El País"),
    RssSource("El País Ciencia", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/ciencia", Category.CIENCIA, "El País"),

    # DW (Deutsche Welle) - Português
    RssSource("DW Brasil", "https://rss.dw.com/rdf/rss-pt-br", Category.MUNDO, "DW"),
    RssSource("DW América Latina", "https://rss.dw.com/rdf/rss-pt-latam", Category.LATINO_AMERICA, "DW"),

    # France 24 (PT)
    RssSource("France 24 Brasil", "https://www.france24.com/pt/rss", Category.MUNDO, "France24"),

    # Euronews (PT)
    RssSource("Euronews PT", "https://pt.euronews.com/rss", Category.MUNDO, "Euronews"),
]

# ============================================================
# LATINO-AMÉRICA - Fontes regionais
# ============================================================
LATAM_SOURCES = [
    # Argentina
    RssSource("Clarín", "https://www.clarin.com/rss/", Category.LATINO_AMERICA, "Argentina"),
    RssSource("La Nación", "https://www.lanacion.com.ar/rss/", Category.LATINO_AMERICA, "Argentina"),
    RssSource("Página/12", "https://www.pagina12.com.ar/rss", Category.LATINO_AMERICA, "Argentina"),

    # México
    RssSource("El Universal", "https://www.eluniversal.com.mx/rss", Category.LATINO_AMERICA, "México"),
    RssSource("La Jornada", "https://www.lajornada.com.mx/rss", Category.LATINO_AMERICA, "México"),
    RssSource("Milenio", "https://www.milenio.com/rss", Category.LATINO_AMERICA, "México"),

    # Colômbia
    RssSource("El Tiempo", "https://www.eltiempo.com/rss", Category.LATINO_AMERICA, "Colômbia"),
    RssSource("El Espectador", "https://www.elespectador.com/rss/", Category.LATINO_AMERICA, "Colômbia"),

    # Chile
    RssSource("La Tercera", "https://www.latercera.com/rss/", Category.LATINO_AMERICA, "Chile"),
    RssSource("El Mercurio", "https://www.elmercurio.com/rss/", Category.LATINO_AMERICA, "Chile"),

    # Peru
    RssSource("El Comercio", "https://elcomercio.pe/rss/", Category.LATINO_AMERICA, "Peru"),
    RssSource("La República", "https://larepublica.pe/rss/", Category.LATINO_AMERICA, "Peru"),

    # Equador
    RssSource("El Universo", "https://www.eluniverso.com/rss/", Category.LATINO_AMERICA, "Equador"),

    # Uruguai
    RssSource("El Observador", "https://www.elobservador.com.uy/rss/", Category.LATINO_AMERICA, "Uruguai"),

    # Bolívia
    RssSource("La Razón", "https://www.la-razon.com/rss/", Category.LATINO_AMERICA, "Bolívia"),

    # Paraguay
    RssSource("ABC Color", "https://www.abc.com.py/rss/", Category.LATINO_AMERICA, "Paraguay"),

    # Venezuela
    RssSource("El Nacional", "https://www.elnacional.com/feed/", Category.LATINO_AMERICA, "Venezuela"),

    # Organismos regionais
    RssSource("Mercosul", "https://www.mercosur.int/feed/", Category.LATINO_AMERICA, "Mercosul"),
    RssSource("OEA", "https://www.oas.org/es/rss.xml", Category.LATINO_AMERICA, "OEA"),
    RssSource("CEPAL", "https://www.cepal.org/es/rss.xml", Category.LATINO_AMERICA, "CEPAL"),
]

# ============================================================
# ORGANISMOS OFICIAIS MUNDIAIS
# ============================================================
OFFICIAL_SOURCES = [
    # ONU
    RssSource("ONU News", "https://news.un.org/feed/subscribe/pt/rss/all", Category.MUNDO, "ONU"),
    RssSource("ONU Brasil", "https://news.un.org/feed/subscribe/pt/rss/region/americas", Category.LATINO_AMERICA, "ONU"),

    # OMS
    RssSource("OMS", "https://www.who.int/rss-feeds/news-feed.xml", Category.SAUDE, "OMS"),
    RssSource("OPAS", "https://www.paho.org/rss.xml", Category.SAUDE, "OPAS"),

    # FMI / Banco Mundial
    RssSource("FMI", "https://www.imf.org/en/News/RSS", Category.ECONOMIA, "FMI"),
    RssSource("Banco Mundial", "https://www.worldbank.org/en/news/rss", Category.ECONOMIA, "Banco Mundial"),

    # OMC
    RssSource("OMC", "https://www.wto.org/english/news_e/news_e_rss.xml", Category.ECONOMIA, "OMC"),

    # UNESCO
    RssSource("UNESCO", "https://www.unesco.org/feed/rss", Category.CULTURA, "UNESCO"),

    # COI (Olimpíadas)
    RssSource("COI", "https://olympics.com/rss/", Category.ESPORTES, "COI"),

    # FIFA
    RssSource("FIFA", "https://www.fifa.com/rss/", Category.ESPORTES, "FIFA"),

    # Corte Internacional de Justiça
    RssSource("CIJ", "https://www.icj-cij.org/rss", Category.MUNDO, "CIJ"),
]

# ============================================================
# TECNOLOGIA & CIÊNCIA - Fontes especializadas
# ============================================================
TECH_SCIENCE_SOURCES = [
    # BR
    RssSource("TecMundo", "https://www.tecmundo.com.br/rss", Category.TECNOLOGIA, "Brasil"),
    RssSource("Canaltech", "https://canaltech.com.br/rss/", Category.TECNOLOGIA, "Brasil"),
    RssSource("Olhar Digital", "https://olhardigital.com.br/feed/", Category.TECNOLOGIA, "Brasil"),
    RssSource("Manual do Usuário", "https://manualdousuario.net/feed/", Category.TECNOLOGIA, "Brasil"),

    # INT
    RssSource("TechCrunch", "https://techcrunch.com/feed/", Category.TECNOLOGIA, "Global"),
    RssSource("The Verge", "https://www.theverge.com/rss/index.xml", Category.TECNOLOGIA, "Global"),
    RssSource("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", Category.TECNOLOGIA, "Global"),
    RssSource("Wired", "https://www.wired.com/feed/rss", Category.TECNOLOGIA, "Global"),
    RssSource("MIT Tech Review", "https://www.technologyreview.com/feed/", Category.TECNOLOGIA, "Global"),

    # Ciência
    RssSource("Nature", "https://www.nature.com/nature.rss", Category.CIENCIA, "Nature"),
    RssSource("Science", "https://www.science.org/rss/news_current.xml", Category.CIENCIA, "Science"),
    RssSource("Scientific American", "https://www.scientificamerican.com/feed/", Category.CIENCIA, "SciAm"),
    RssSource("New Scientist", "https://www.newscientist.com/feed/", Category.CIENCIA, "NewSci"),
]

# ============================================================
# CULTURA & ENTRETENIMENTO
# ============================================================
CULTURE_SOURCES = [
    RssSource("Estadão Cultura", "https://cultura.estadao.com.br/feed/", Category.CULTURA, "Brasil"),
    RssSource("Folha Ilustrada", "https://feeds.folha.uol.com.br/ilustrada/rss091.xml", Category.CULTURA, "Brasil"),
    RssSource("NYT Culture", "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml", Category.CULTURA, "NYT"),
    RssSource("BBC Culture", "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml", Category.CULTURA, "BBC"),
]

# ============================================================
# ALL SOURCES - Combined
# ============================================================
ALL_RSS_SOURCES = (
    BRASIL_SOURCES
    + MUNDO_SOURCES
    + LATAM_SOURCES
    + OFFICIAL_SOURCES
    + TECH_SCIENCE_SOURCES
    + CULTURE_SOURCES
)

# Helper to get enabled sources
def get_enabled_sources() -> list[RssSource]:
    return [s for s in ALL_RSS_SOURCES if s.enabled]

# Source count by category
def count_by_category() -> dict[Category, int]:
    from collections import Counter
    return dict(Counter(s.category for s in get_enabled_sources()))