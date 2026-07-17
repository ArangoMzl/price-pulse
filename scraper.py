"""
scraper.py - Scraper directo a Amazon con caché en disco.
⚠️ Este método consulta Amazon directamente. Úsalo responsablemente:
- El caché evita consultas repetidas (mismo producto = misma respuesta).
- Se aplica un delay aleatorio entre requests para no sobrecargar.
- Si Amazon pide CAPTCHA, la app te avisará para que esperes unos minutos.

Alternativas 100% gratuitas con más robustez si te bloquean:
- ScraperAPI (1000 requests/mes gratis): https://www.scraperapi.com/
- ZenRows (1000 requests/mes gratis): https://www.zenrows.com/
"""
import os
import re
import json
import time
import random
import hashlib
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import asdict
from typing import Optional

from amazon_api import Product


# ============================================================================
# CONFIGURACIÓN
# ============================================================================
CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_HOURS = 24  # Cache de 24 horas

# Pool de User-Agents realistas (desktop + mobile)
USER_AGENTS = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    # Safari Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Mobile (más difícil de detectar como bot)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
]


class CaptchaError(Exception):
    """Amazon pidió un CAPTCHA."""
    pass


# ============================================================================
# SCRAPER PRINCIPAL
# ============================================================================
class AmazonScraper:
    """Scraper directo a Amazon con caché, rotación de user agents y rate limiting."""

    def __init__(self, min_delay: float = 2.5, max_delay: float = 4.5):
        self.session = requests.Session()
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request = 0.0
        self.request_count = 0

    # ---------- Rate limiting ----------
    def _wait(self):
        """Espera aleatoria para no sobrecargar Amazon."""
        elapsed = time.time() - self.last_request
        delay = random.uniform(self.min_delay, self.max_delay)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self.last_request = time.time()
        self.request_count += 1

    # ---------- Headers ----------
    def _headers(self, domain: str) -> dict:
        ua = random.choice(USER_AGENTS)
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8" if domain == "amazon.co.jp" else "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    # ---------- Caché en disco ----------
    @staticmethod
    def _cache_key(query: str, domain: str) -> str:
        s = f"{domain}:{query.lower().strip()}"
        return hashlib.md5(s.encode()).hexdigest()

    @staticmethod
    def _get_cache(query: str, domain: str) -> Optional[list[Product]]:
        cache_file = CACHE_DIR / f"{AmazonScraper._cache_key(query, domain)}.json"
        if not cache_file.exists():
            return None
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(data["cached_at"])
            if datetime.now() - cached_at > timedelta(hours=CACHE_TTL_HOURS):
                return None
            return [Product(**p) for p in data["products"]]
        except Exception:
            return None

    @staticmethod
    def _save_cache(query: str, domain: str, products: list[Product]):
        cache_file = CACHE_DIR / f"{AmazonScraper._cache_key(query, domain)}.json"
        try:
            data = {
                "cached_at": datetime.now().isoformat(),
                "query": query,
                "domain": domain,
                "products": [asdict(p) for p in products],
            }
            cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    # ---------- Búsqueda ----------
    def search(self, query: str, domain: str = "amazon.com", max_results: int = 10) -> list[Product]:
        """Busca productos en Amazon. Devuelve lista de Product."""
        if not query or not query.strip():
            return []

        # 1) Revisar caché primero (instantáneo, sin request a Amazon)
        cached = self._get_cache(query, domain)
        if cached is not None:
            return cached[:max_results]

        # 2) Rate limiting
        self._wait()

        # 3) Crear sesión fresca para cada búsqueda (evita conflictos entre dominios)
        session = requests.Session()

        # 4) Hacer request a Amazon
        url = f"https://{domain}/s"
        params = {
            "k": query.strip(),
            "ref": "nb_sb_noss",
            "s": "relevanceblender",
        }

        try:
            response = session.get(
                url,
                params=params,
                headers=self._headers(domain),
                timeout=30,
                allow_redirects=True,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise ConnectionError(f"⏱️ Timeout al conectar con {domain}")
        except requests.exceptions.HTTPError as e:
            raise ConnectionError(f"Error HTTP {response.status_code} en {domain}: {e}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error de red al conectar con {domain}: {e}")
        finally:
            session.close()

        # 5) Detectar CAPTCHA
        html_lower = response.text.lower()
        if any(s in html_lower for s in [
            "enter the characters you see below",
            "sorry, we just need to make sure you're not a robot",
            "/errors/validatecaptcha",
            "automated access requests",
        ]):
            raise CaptchaError(
                f"⚠️ Amazon pidió CAPTCHA para {domain}.\n\n"
                "💡 Soluciones:\n"
                "1. Espera 10-15 minutos y vuelve a intentar\n"
                "2. Usa una VPN\n"
                "3. Configura ScraperAPI en .env (gratis 1000/mes)"
            )

        # 6) Parsear HTML (siempre intentar parsear)
        products = self._parse(response.text, domain)

        # 7) Guardar en caché
        if products:
            self._save_cache(query, domain, products)

        return products[:max_results]

    # ---------- Parsing ----------
    def _parse(self, html: str, domain: str) -> list[Product]:
        """Extrae productos del HTML de búsqueda de Amazon."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError(
                "Falta beautifulsoup4. Ejecuta: pip install beautifulsoup4 lxml"
            )

        soup = BeautifulSoup(html, "html.parser")
        default_currency = "JPY" if domain == "amazon.co.jp" else "USD"
        country = "Japón 🇯🇵" if domain == "amazon.co.jp" else "USA 🇺🇸"

        # Detectar la moneda REAL que Amazon está mostrando en la página.
        # Cuando visitas amazon.com desde Colombia, Amazon te muestra precios en COP.
        # Cuando visitas amazon.co.jp desde fuera de Japón, puede mostrar USD.
        detected_currency = self._detect_page_currency(soup, default_currency)

        products = []
        items = soup.select('[data-component-type="s-search-result"]')

        for item in items:
            try:
                asin = item.get("data-asin", "").strip()
                if not asin:
                    continue

                # Título
                title_el = (
                    item.select_one("h2 span")
                    or item.select_one("h2 .a-link-normal span")
                    or item.select_one(".s-title-instructions-style span")
                )
                title = title_el.get_text(strip=True) if title_el else ""
                if not title or len(title) < 3:
                    continue

                # URL
                url = ""
                url_el = item.select_one("h2 a[href]") or item.select_one("a[href*='/dp/']")
                if url_el:
                    href = url_el.get("href", "")
                    if href.startswith("/"):
                        url = f"https://{domain}{href.split('?')[0]}"
                    elif href.startswith("http"):
                        url = href.split("?")[0]

                if not url:
                    continue

                # Precio - detectar moneda específica de este item
                price = None
                item_currency = detected_currency  # usar la detectada de la página

                price_el = item.select_one(".a-price .a-offscreen")
                if not price_el:
                    price_el = item.select_one(".a-price span")
                if price_el:
                    price_text = price_el.get_text(strip=True)
                    # Para amazon.co.jp: siempre usar detected_currency (USD)
                    # No detectar por texto porque Amazon.co.jp muestra "¥" en el header
                    if domain != "amazon.co.jp":
                        item_currency = self._detect_currency_from_text(price_text, detected_currency)
                    price = self._parse_price(price_text, item_currency)

                # Para amazon.co.jp: si el item_currency es USD, la moneda real es USD
                # El país sigue siendo Japón (el producto viene de ahí)
                item_country = country

                # Rating
                rating = None
                rating_el = item.select_one(".a-icon-alt")
                if rating_el:
                    rating_text = rating_el.get_text(strip=True)
                    m = re.search(r"(\d+\.?\d*)", rating_text)
                    if m:
                        try:
                            rating = float(m.group(1))
                        except ValueError:
                            pass

                # Reseñas (count)
                reviews_count = None
                rev_candidates = item.select("span.a-size-base.s-underline-text")
                for rev_el in rev_candidates:
                    txt = rev_el.get_text(strip=True).replace(",", "").replace(".", "")
                    if txt.isdigit():
                        reviews_count = int(txt)
                        break

                # Imagen (varios selectores para cubrir lazy-loading)
                image = None
                img_el = (
                    item.select_one("img.s-image")
                    or item.select_one("img[data-src]")
                    or item.select_one("img.a-dynamic-image")
                )
                if img_el:
                    image = img_el.get("src") or img_el.get("data-src")
                    if image:
                        if image.startswith("//"):
                            image = f"https:{image}"
                        elif image.startswith("/"):
                            image = f"https://{domain}{image}"

                # Prime
                is_prime = bool(
                    item.select_one(".a-icon-prime")
                    or item.select_one("[aria-label*='Prime']")
                    or item.select_one("i.a-icon-prime")
                )

                products.append(Product(
                    title=title,
                    price=price,
                    currency=item_currency,
                    rating=rating,
                    reviews_count=reviews_count,
                    url=url,
                    image=image,
                    shipping=None,
                    is_prime=is_prime,
                    asin=asin,
                    country=item_country,
                ))
            except Exception:
                continue

        return products

    def _detect_page_currency(self, soup, default: str) -> str:
        """
        Detecta la moneda que Amazon está mostrando en TODA la página.
        Para amazon.co.jp desde Colombia: siempre USD (Amazon muestra precios internacionales).
        """
        # Para amazon.co.jp: siempre USD (desde Colombia, Amazon muestra precios en USD)
        if default == "JPY":
            return "USD"

        # Detección general para amazon.com y otros
        symbols = soup.select(".a-price-symbol")[:5]
        for sym in symbols:
            text = sym.get_text(strip=True).upper()
            if "COP" in text or "COL$" in text:
                return "COP"
            if "MXN" in text or "MEX$" in text:
                return "MXN"
            if "EUR" in text or "€" in text:
                return "EUR"
            if "JPY" in text or "￥" in text:
                return "JPY"
            if "¥" in text:
                return "JPY"
            if "GBP" in text or "£" in text:
                return "GBP"
            if "BRL" in text or "R$" in text:
                return "BRL"
            if "ARS" in text:
                return "ARS"
            if "CLP" in text:
                return "CLP"
            if "$" in text:
                return "USD"
        return default

    def _detect_currency_from_text(self, text: str, default: str) -> str:
        """Detecta la moneda a partir del texto del precio."""
        if not text:
            return default
        text_upper = text.upper()
        if "COP" in text_upper or "COL$" in text:
            return "COP"
        if "MXN" in text_upper or "MEX$" in text:
            return "MXN"
        if "EUR" in text_upper or "€" in text:
            return "EUR"
        if "JPY" in text_upper or "￥" in text:
            return "JPY"
        if "¥" in text:
            return "JPY"
        if "GBP" in text_upper or "£" in text:
            return "GBP"
        if "BRL" in text_upper or "R$" in text:
            return "BRL"
        if "ARS" in text_upper:
            return "ARS"
        if "$" in text:
            return "USD"
        return default

    @staticmethod
    def _parse_price(text: str, currency_hint: str = "USD") -> Optional[float]:
        """
        Convierte texto de precio a float, manejando formatos de varios países.

        Formatos soportados:
        - USD: '$1,234.56'   (coma=thousands, dot=decimal)
        - COP: 'COP$ 2.024.751,00' (dot=thousands, comma=decimal)
        - JPY: '¥1,234'      (sin decimales, coma=thousands)
        - EUR: '€1.234,56'   (dot=thousands, comma=decimal)
        """
        if not text:
            return None
        cleaned = re.sub(r"[^\d.,]", "", text)
        if not cleaned:
            return None

        has_comma = "," in cleaned
        has_dot = "." in cleaned

        # Monedas que usan coma como decimal: COP, EUR, MXN, BRL, ARS, CLP, etc.
        decimal_is_comma = currency_hint in (
            "COP", "EUR", "MXN", "BRL", "ARS", "CLP", "PEN", "VES",
        )

        if has_comma and has_dot:
            # Ambos separadores: decidir cuál es decimal según la moneda
            if decimal_is_comma:
                # Formato europeo/colombiano: coma=decimal, punto=miles
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                # Formato US: punto=decimal, coma=miles
                cleaned = cleaned.replace(",", "")
        elif has_comma and not has_dot:
            # Solo comas: depende de la moneda
            if decimal_is_comma:
                # Coma es decimal (formato europeo sin parte de miles)
                cleaned = cleaned.replace(",", ".")
            else:
                # Coma es separador de miles
                cleaned = cleaned.replace(",", "")
        # Si solo tiene punto, está OK para ambos formatos

        try:
            return float(cleaned)
        except ValueError:
            return None


# ============================================================================
# SCRAPER CON SERVICIO EXTERNO (ScraperAPI) - 1000 requests gratis/mes
# ============================================================================
class ScraperAPIWrapper:
    """
    Wrapper para ScraperAPI (https://www.scraperapi.com/).
    Plan gratuito: 1000 requests/mes. Maneja anti-bot por ti.
    Para usarlo:
    1. Regístrate en https://www.scraperapi.com/
    2. Copia tu API key
    3. Agrégala al .env: SCRAPER_API_KEY=tu_key
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SCRAPER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "❌ SCRAPER_API_KEY no configurada.\n"
                "Regístrate gratis en https://www.scraperapi.com/ (1000 requests/mes)"
            )
        self.scraper = AmazonScraper(min_delay=0.5, max_delay=1.0)

    def search(self, query: str, domain: str = "amazon.com", max_results: int = 10) -> list[Product]:
        # Revisar caché primero
        cached = self.scraper._get_cache(query, domain)
        if cached is not None:
            return cached[:max_results]

        target_url = f"https://{domain}/s?k={query.strip().replace(' ', '+')}"

        try:
            response = requests.get(
                "https://api.scraperapi.com/",
                params={
                    "api_key": self.api_key,
                    "url": target_url,
                    "render": "false",
                    "country_code": "us" if domain == "amazon.com" else "jp",
                },
                timeout=60,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error ScraperAPI: {e}")

        if "captcha" in response.text.lower():
            raise CaptchaError("ScraperAPI devolvió CAPTCHA. Reduce la frecuencia de búsquedas.")

        products = self.scraper._parse(response.text, domain)
        if products:
            self.scraper._save_cache(query, domain, products)
        return products[:max_results]


# ============================================================================
# UTILIDADES DE CACHÉ
# ============================================================================
def clear_cache():
    """Limpia toda la caché de búsquedas."""
    count = 0
    for f in CACHE_DIR.glob("*.json"):
        try:
            f.unlink()
            count += 1
        except Exception:
            pass
    return count


def cache_stats() -> dict:
    """Estadísticas de la caché."""
    files = list(CACHE_DIR.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files)
    return {
        "entries": len(files),
        "size_mb": total_size / (1024 * 1024),
        "ttl_hours": CACHE_TTL_HOURS,
    }
