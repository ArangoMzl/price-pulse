"""
scraper.py - Scraper directo a Amazon con caché en disco.
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


CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_HOURS = 24

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

IMAGE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.amazon.com/",
}


class CaptchaError(Exception):
    pass


class AmazonScraper:
    """Scraper directo a Amazon con caché, rotación de user agents y rate limiting."""

    def __init__(self, min_delay: float = 5.0, max_delay: float = 8.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request = 0.0
        self.request_count = 0

    def _wait(self):
        elapsed = time.time() - self.last_request
        delay = random.uniform(self.min_delay, self.max_delay)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self.last_request = time.time()
        self.request_count += 1

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
            "DNT": "1",
        }

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

    def _do_request(self, url: str, params: dict, domain: str) -> requests.Response:
        """Hace un request con reintento automático."""
        last_error = None
        for attempt in range(3):
            if attempt > 0:
                wait_time = (attempt + 1) * 3 + random.uniform(0, 2)
                time.sleep(wait_time)

            session = requests.Session()
            try:
                response = session.get(
                    url,
                    params=params,
                    headers=self._headers(domain),
                    timeout=30,
                    allow_redirects=True,
                )
                response.raise_for_status()

                html_lower = response.text.lower()
                if any(s in html_lower for s in [
                    "enter the characters you see below",
                    "sorry, we just need to make sure you're not a robot",
                    "/errors/validatecaptcha",
                    "automated access requests",
                    "pet type the characters",
                ]):
                    last_error = "CAPTCHA"
                    continue

                return response
            except requests.exceptions.RequestException:
                last_error = "REQUEST_ERROR"
                continue
            finally:
                session.close()

        if last_error == "CAPTCHA":
            raise CaptchaError(
                f"⚠️ Amazon pidió CAPTCHA para {domain}.\n"
                "💡 Espera 10-15 minutos e intenta de nuevo."
            )
        return None

    def search(self, query: str, domain: str = "amazon.com", max_results: int = 5) -> list[Product]:
        if not query or not query.strip():
            return []

        cached = self._get_cache(query, domain)
        if cached is not None:
            return cached[:max_results]

        self._wait()

        url = f"https://{domain}/s"
        params = {
            "k": query.strip(),
            "ref": "nb_sb_noss",
            "s": "relevanceblender",
        }

        response = self._do_request(url, params, domain)
        if response is None:
            return []

        products = self._parse(response.text, domain)

        if products:
            self._save_cache(query, domain, products)

        return products[:max_results]

    def _parse(self, html: str, domain: str) -> list[Product]:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return []

        soup = BeautifulSoup(html, "html.parser")
        default_currency = "JPY" if domain == "amazon.co.jp" else "USD"
        country = "Japón 🇯🇵" if domain == "amazon.co.jp" else "USA 🇺🇸"

        detected_currency = self._detect_page_currency(soup, default_currency)

        products = []
        items = soup.select('[data-component-type="s-search-result"]')

        for item in items:
            try:
                asin = item.get("data-asin", "").strip()
                if not asin:
                    continue

                title_el = (
                    item.select_one("h2 span")
                    or item.select_one("h2 .a-link-normal span")
                    or item.select_one(".s-title-instructions-style span")
                )
                title = title_el.get_text(strip=True) if title_el else ""
                if not title or len(title) < 3:
                    continue

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

                price = None
                item_currency = detected_currency

                price_el = item.select_one(".a-price .a-offscreen")
                if not price_el:
                    price_el = item.select_one(".a-price span")
                if price_el:
                    price_text = price_el.get_text(strip=True)
                    if domain == "amazon.co.jp":
                        item_currency = "USD"
                    else:
                        item_currency = self._detect_currency_from_text(price_text, detected_currency)
                    price = self._parse_price(price_text, item_currency)

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

                reviews_count = None
                rev_candidates = item.select("span.a-size-base.s-underline-text")
                for rev_el in rev_candidates:
                    txt = rev_el.get_text(strip=True).replace(",", "").replace(".", "")
                    if txt.isdigit():
                        reviews_count = int(txt)
                        break

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
                    country=country,
                ))
            except Exception:
                continue

        return products

    def _detect_page_currency(self, soup, default: str) -> str:
        """Detecta la moneda que Amazon muestra en la página."""
        # amazon.co.jp desde Colombia siempre muestra USD
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
            if "$" in text:
                return "USD"
        return default

    def _detect_currency_from_text(self, text: str, default: str) -> str:
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
        if "$" in text:
            return "USD"
        return default

    @staticmethod
    def _parse_price(text: str, currency_hint: str = "USD") -> Optional[float]:
        if not text:
            return None
        cleaned = re.sub(r"[^\d.,]", "", text)
        if not cleaned:
            return None

        has_comma = "," in cleaned
        has_dot = "." in cleaned

        decimal_is_comma = currency_hint in (
            "COP", "EUR", "MXN", "BRL", "ARS", "CLP", "PEN", "VES",
        )

        if has_comma and has_dot:
            if decimal_is_comma:
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif has_comma and not has_dot:
            if decimal_is_comma:
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")

        try:
            return float(cleaned)
        except ValueError:
            return None


# ============================================================================
# SCRAPER CON SERVICIO EXTERNO (ScraperAPI)
# ============================================================================
class ScraperAPIWrapper:
    """Wrapper para ScraperAPI."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SCRAPER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "❌ SCRAPER_API_KEY no configurada.\n"
                "Regístrate gratis en https://www.scraperapi.com/ (1000 requests/mes)"
            )
        self.scraper = AmazonScraper(min_delay=3.0, max_delay=5.0)

    def search(self, query: str, domain: str = "amazon.com", max_results: int = 5) -> list[Product]:
        cached = self.scraper._get_cache(query, domain)
        if cached is not None:
            return cached[:max_results]

        target_url = f"https://{domain}/s?k={query.strip().replace(' ', '+')}&ref=nb_sb_noss"

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

    def _get_cache(self, query, domain):
        return self.scraper._get_cache(query, domain)


# ============================================================================
# UTILIDADES
# ============================================================================
def clear_cache():
    count = 0
    for f in CACHE_DIR.glob("*.json"):
        try:
            f.unlink()
            count += 1
        except Exception:
            pass
    return count


def cache_stats() -> dict:
    files = list(CACHE_DIR.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files)
    return {
        "entries": len(files),
        "size_mb": total_size / (1024 * 1024),
        "ttl_hours": CACHE_TTL_HOURS,
    }
