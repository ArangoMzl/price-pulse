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

        # 3) Hacer request a Amazon
        url = f"https://{domain}/s"
        params = {
            "k": query.strip(),
            "ref": "nb_sb_noss",
            "s": "relevanceblender",
        }

        try:
            response = self.session.get(
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

        # 4) Detectar CAPTCHA
        html_lower = response.text.lower()
        if any(s in html_lower for s in [
            "enter the characters you see below",
            "sorry, we just need to make sure you're not a robot",
            "/errors/validatecaptcha",
        ]):
            raise CaptchaError(
                f"⚠️ Amazon pidió CAPTCHA para {domain}.\n\n"
                "💡 Soluciones:\n"
                "1. Espera 10-15 minutos y vuelve a intentar\n"
                "2. Usa una VPN\n"
                "3. Configura ScraperAPI en .env (gratis 1000/mes)\n"
                "4. Usa Rainforest API (más confiable, de pago)"
            )

        # 5) Sin resultados
        if any(s in html_lower for s in [
            "no results for your search query",
            "did not match any products",
            "0 件の結果",  # "0 results" en japonés
        ]):
            # Guardar caché vacío para no repetir
            self._save_cache(query, domain, [])
            return []

        # 6) Parsear HTML
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
                    # Detectar moneda específica del texto (puede diferir entre items)
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
        Amazon muestra precios en la moneda local según la IP/ubicación del usuario.
        Ejemplo: amazon.com desde Colombia → COP.

        Para amazon.co.jp, prioriza la moneda de los productos (no del header).
        """
        # Para amazon.co.jp: revisar los precios de productos directamente
        if default == "JPY":
            product_prices = soup.select('[data-component-type="s-search-result"] .a-price .a-offscreen')[:5]
            for price_el in product_prices:
                text = price_el.get_text(strip=True)
                if "$" in text and "¥" not in text:
                    return "USD"
                if "¥" in text or "￥" in text:
                    return "JPY"
            # También revisar símbolos dentro de resultados de búsqueda
            product_symbols = soup.select('[data-component-type="s-search-result"] .a-price-symbol')[:5]
            for sym in product_symbols:
                text = sym.get_text(strip=True).upper()
                if "$" in text:
                    return "USD"
                if "¥" in text or "￥" in text:
                    return "JPY"

        # Detección general: revisar los primeros símbolos de precio
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
# SCRAPER PARA ALIEXPRESS (vía ScraperAPI con render=true)
# ============================================================================
class AliExpressScraper:
    """
    Scraper para AliExpress usando ScraperAPI con renderizado JavaScript.
    AliExpress bloquea requests directos, por lo que necesita ScraperAPI.
    Plan gratuito: 1000 requests/mes.
    """

    BASE_URL = "https://www.aliexpress.com/wholesale"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SCRAPER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "❌ SCRAPER_API_KEY no configurada.\n"
                "AliExpress requiere ScraperAPI para funcionar.\n"
                "Regístrate gratis en https://www.scraperapi.com/ (1000 requests/mes)"
            )
        self.scraper = AmazonScraper(min_delay=0.5, max_delay=1.0)

    def search(self, query: str, max_results: int = 10) -> list[Product]:
        """Busca productos en AliExpress."""
        if not query or not query.strip():
            return []

        cache_key = f"aliexpress:{query}"
        cached = self.scraper._get_cache(cache_key, "aliexpress.com")
        if cached is not None:
            return cached[:max_results]

        target_url = (
            f"{self.BASE_URL}?SearchText={query.strip().replace(' ', '+')}"
            f"&catId=0&SortType=total_tranpro_desc"
        )

        try:
            response = requests.get(
                "https://api.scraperapi.com/",
                params={
                    "api_key": self.api_key,
                    "url": target_url,
                    "render": "true",
                    "country_code": "us",
                },
                timeout=90,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error ScraperAPI (AliExpress): {e}")

        if "captcha" in response.text.lower() or "punish" in response.text.lower():
            raise CaptchaError(
                "⚠️ AliExpress pidió CAPTCHA.\n"
                "💡 Espera 10-15 minutos e intenta de nuevo."
            )

        products = self._parse(response.text)
        if products:
            self.scraper._save_cache(cache_key, "aliexpress.com", products)
        return products[:max_results]

    def _parse(self, html: str) -> list[Product]:
        """Extrae productos del HTML de AliExpress."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        products = []

        # AliExpress guarda datos en JSON embebido en script tags
        products = self._parse_from_json(soup)
        if products:
            return products

        # Fallback: parsear desde HTML
        return self._parse_from_html(soup)

    def _parse_from_json(self, soup) -> list[Product]:
        """Intenta extraer productos del JSON embebido en la página."""
        import json as json_mod

        products = []

        # Buscar scripts con datos de productos
        for script in soup.find_all("script"):
            text = script.string or ""
            if not text:
                continue

            # Buscar patrones de JSON con datos de productos
            # AliExpress guarda datos en window.runParams o window._dida_config_
            for pattern in [
                r'window\.runParams\s*=\s*(\{.*?\});',
                r'"itemList"\s*:\s*(\[.*?\])',
                r'"items"\s*:\s*(\[.*?\])',
                r'"products"\s*:\s*(\[.*?\])',
            ]:
                matches = re.findall(pattern, text, re.DOTALL)
                for match in matches:
                    try:
                        data = json_mod.loads(match) if isinstance(match, str) else match
                        if isinstance(data, list):
                            for item in data:
                                product = self._extract_product_from_dict(item)
                                if product:
                                    products.append(product)
                        elif isinstance(data, dict):
                            # Buscar listas anidadas
                            for key in ["itemList", "items", "products", "data"]:
                                if key in data and isinstance(data[key], list):
                                    for item in data[key]:
                                        product = self._extract_product_from_dict(item)
                                        if product:
                                            products.append(product)
                    except (ValueError, TypeError, KeyError):
                        continue

        return products

    def _extract_product_from_dict(self, item: dict) -> Optional[Product]:
        """Extrae un Product de un diccionario JSON."""
        try:
            if not isinstance(item, dict):
                return None

            # Título
            title = (
                item.get("title")
                or item.get("productTitle")
                or item.get("name")
                or ""
            )
            if isinstance(title, dict):
                title = title.get("displayTitle", "") or title.get("text", "")
            title = str(title).strip()
            if not title or len(title) < 3:
                return None

            # Precio
            price = None
            price_raw = (
                item.get("price")
                or item.get("salePrice")
                or item.get("minPrice")
            )
            if isinstance(price_raw, dict):
                price_raw = price_raw.get("price") or price_raw.get("text", "")
            if isinstance(price_raw, str):
                price_clean = re.sub(r"[^\d.]", "", price_raw)
                try:
                    price = float(price_clean)
                except ValueError:
                    pass
            elif isinstance(price_raw, (int, float)):
                price = float(price_raw)

            # URL
            url = item.get("productDetailUrl") or item.get("url") or item.get("link") or ""
            if not url and item.get("productId"):
                url = f"https://www.aliexpress.com/item/{item['productId']}.html"
            if url and not url.startswith("http"):
                url = f"https:{url}" if url.startswith("//") else f"https://www.aliexpress.com{url}"

            # Imagen
            image = item.get("image") or item.get("imageUrl") or item.get("imgUrl") or ""
            if isinstance(image, dict):
                image = image.get("url", "")
            if image and not image.startswith("http"):
                image = f"https:{image}" if image.startswith("//") else image

            # Rating
            rating = None
            rating_raw = item.get("rating") or item.get("averageStar") or item.get("starRating")
            if isinstance(rating_raw, dict):
                rating_raw = rating_raw.get("averageStar") or rating_raw.get("rating")
            if rating_raw is not None:
                try:
                    rating = float(str(rating_raw).replace(",", "."))
                except (ValueError, TypeError):
                    pass

            # Ventas/reseñas
            reviews_count = None
            orders_raw = item.get("tradeDesc") or item.get("orders") or item.get("soldCount") or ""
            if isinstance(orders_raw, str):
                orders_clean = re.sub(r"[^\d]", "", orders_raw.split("+")[0] if "+" in orders_raw else orders_raw.split(" ")[0])
                try:
                    reviews_count = int(orders_clean) if orders_clean else None
                except ValueError:
                    pass

            return Product(
                title=title,
                price=price,
                currency="USD",
                rating=rating,
                reviews_count=reviews_count,
                url=url,
                image=image if image else None,
                shipping="Envío internacional",
                is_prime=False,
                asin="",
                country="AliExpress 🌍",
            )
        except Exception:
            return None

    def _parse_from_html(self, soup) -> list[Product]:
        """Fallback: parsea productos desde el HTML de AliExpress."""
        products = []

        # Selectores para tarjetas de producto en AliExpress
        cards = soup.select(
            '[class*="multi--container"],'
            '[class*="product-snippet"],'
            '.search-item,'
            '[data-widget="search#productCard"]'
        )

        for card in cards:
            try:
                # Título
                title_el = card.select_one(
                    '[class*="multi--title"],'
                    '[class*="product-title"],'
                    'h3,'
                    '[class*="title"]'
                )
                title = title_el.get_text(strip=True) if title_el else ""
                if not title or len(title) < 3:
                    continue

                # Precio
                price = None
                price_el = card.select_one(
                    '[class*="multi--price-sale"],'
                    '[class*="price--current"],'
                    '[class*="price"],'
                    '.price'
                )
                if price_el:
                    price_text = price_el.get_text(strip=True)
                    price_clean = re.sub(r"[^\d.]", "", price_text)
                    try:
                        price = float(price_clean)
                    except ValueError:
                        pass

                # URL
                url = ""
                link_el = card.select_one("a[href]")
                if link_el:
                    href = link_el.get("href", "")
                    if href.startswith("//"):
                        url = f"https:{href}"
                    elif href.startswith("/"):
                        url = f"https://www.aliexpress.com{href}"
                    elif href.startswith("http"):
                        url = href

                # Imagen
                image = None
                img_el = card.select_one("img[src]")
                if img_el:
                    image = img_el.get("src") or img_el.get("data-src")
                    if image and image.startswith("//"):
                        image = f"https:{image}"

                # Rating
                rating = None
                rating_el = card.select_one('[class*="rating"], [class*="star"]')
                if rating_el:
                    rating_text = rating_el.get_text(strip=True)
                    m = re.search(r"(\d+\.?\d*)", rating_text)
                    if m:
                        try:
                            rating = float(m.group(1))
                        except ValueError:
                            pass

                # Ventas
                reviews_count = None
                sold_el = card.select_one('[class*="sold"], [class*="trade"]')
                if sold_el:
                    sold_text = sold_el.get_text(strip=True)
                    sold_clean = re.sub(r"[^\d]", "", sold_text.split("+")[0] if "+" in sold_text else sold_text.split(" ")[0])
                    try:
                        reviews_count = int(sold_clean) if sold_clean else None
                    except ValueError:
                        pass

                if price is not None or url:
                    products.append(Product(
                        title=title,
                        price=price,
                        currency="USD",
                        rating=rating,
                        reviews_count=reviews_count,
                        url=url,
                        image=image,
                        shipping="Envío internacional",
                        is_prime=False,
                        asin="",
                        country="AliExpress 🌍",
                    ))
            except Exception:
                continue

        return products


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
