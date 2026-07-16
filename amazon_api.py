"""
Cliente para Rainforest API - Búsqueda de productos en Amazon.
Documentación: https://www.rainforestapi.com/docs
"""
import os
import requests
from dataclasses import dataclass, field, asdict
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Product:
    """Representa un producto de Amazon."""
    title: str
    price: Optional[float] = None
    currency: str = "USD"
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    url: str = ""
    image: Optional[str] = None
    shipping: Optional[str] = None
    is_prime: bool = False
    asin: str = ""
    country: str = ""  # USA o Japón

    def to_dict(self):
        return asdict(self)


class AmazonSearch:
    """Cliente para buscar productos en Amazon via Rainforest API."""

    BASE_URL = "https://api.rainforestapi.com/request"

    # Mapeo de dominio a moneda esperada
    DOMAIN_CURRENCY = {
        "amazon.com": "USD",
        "amazon.co.jp": "JPY",
        "amazon.co.uk": "GBP",
        "amazon.de": "EUR",
        "amazon.es": "EUR",
        "amazon.com.mx": "MXN",
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("RAINFOREST_API_KEY")
        if not self.api_key:
            raise ValueError(
                "❌ No se encontró RAINFOREST_API_KEY.\n"
                "Obtén una gratis en: https://www.rainforestapi.com/\n"
                "Luego configúrala en el archivo .env"
            )

    def search(
        self,
        query: str,
        domain: str = "amazon.com",
        max_results: int = 10,
    ) -> list[Product]:
        """
        Busca productos en Amazon.

        Args:
            query: Término de búsqueda (ej: "wireless headphones")
            domain: 'amazon.com' (USA), 'amazon.co.jp' (Japón), etc.
            max_results: Número máximo de resultados (1-50)

        Returns:
            Lista de objetos Product
        """
        if not query or not query.strip():
            return []

        params = {
            "api_key": self.api_key,
            "type": "search",
            "amazon_domain": domain,
            "search_term": query.strip(),
            "max_results": max(1, min(50, max_results)),
            "sort_by": "relevance",
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise ConnectionError(f"⏱️ Timeout al consultar {domain}")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise PermissionError("🔑 API key inválida o expirada")
            elif response.status_code == 429:
                raise PermissionError("🚫 Límite de requests alcanzado")
            else:
                raise ConnectionError(f"Error HTTP {response.status_code}: {e}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error de red: {e}")

        data = response.json()
        products = []

        for item in data.get("search_results", []):
            product = self._parse_product(item, domain)
            if product:
                products.append(product)

        return products

    def _parse_product(self, item: dict, domain: str) -> Optional[Product]:
        """Convierte un resultado de la API en un Product."""
        try:
            # Precio: puede venir como dict {value, currency} o número
            price = None
            currency = self.DOMAIN_CURRENCY.get(domain, "USD")

            price_data = item.get("price")
            if isinstance(price_data, dict):
                value = price_data.get("value")
                if value is not None:
                    try:
                        price = float(value)
                    except (ValueError, TypeError):
                        price = None
                if "currency" in price_data:
                    currency = price_data["currency"]
            elif isinstance(price_data, (int, float)):
                price = float(price_data)

            # Rating
            rating = None
            if item.get("rating") is not None:
                try:
                    rating = float(item["rating"])
                except (ValueError, TypeError):
                    pass

            # Reseñas
            reviews_count = item.get("ratings_total") or item.get("reviews_total")
            if reviews_count is not None:
                try:
                    reviews_count = int(reviews_count)
                except (ValueError, TypeError):
                    reviews_count = None

            # Shipping / entrega
            shipping = None
            delivery = item.get("delivery")
            if isinstance(delivery, dict):
                shipping = delivery.get("text") or delivery.get("fastest_delivery")
            elif isinstance(delivery, str):
                shipping = delivery

            return Product(
                title=(item.get("title") or "Sin título").strip(),
                price=price,
                currency=currency,
                rating=rating,
                reviews_count=reviews_count,
                url=item.get("link", ""),
                image=item.get("image"),
                shipping=shipping,
                is_prime=bool(item.get("is_prime", False)),
                asin=item.get("asin", ""),
                country="Japón 🇯🇵" if domain == "amazon.co.jp" else "USA 🇺🇸",
            )
        except Exception:
            # Si un producto individual falla, lo ignoramos
            return None


def convert_currency(amount: float, from_currency: str, to_currency: str = "USD") -> Optional[float]:
    """
    Convierte entre monedas usando exchangerate-api.com (gratis, sin key).
    Usa caché interna para evitar llamadas repetidas (TTL 1h).
    Soporta USD, COP, JPY, EUR, GBP, MXN y muchas más.
    """
    if from_currency == to_currency:
        return amount
    if amount is None:
        return None
    rate = get_exchange_rate(from_currency, to_currency)
    if rate is not None:
        return amount * rate
    return None


# Caché simple de tasas de cambio (válido por 1 hora)
_EXCHANGE_CACHE = {"timestamp": None, "rates": {}}
_EXCHANGE_TTL_SECONDS = 3600


def get_exchange_rate(from_currency: str, to_currency: str) -> Optional[float]:
    """
    Obtiene la tasa de cambio con caché de 1 hora.
    """
    if from_currency == to_currency:
        return 1.0

    import time
    now = time.time()

    # Caché válida?
    if (
        _EXCHANGE_CACHE["timestamp"] is not None
        and now - _EXCHANGE_CACHE["timestamp"] < _EXCHANGE_TTL_SECONDS
        and from_currency in _EXCHANGE_CACHE["rates"]
        and to_currency in _EXCHANGE_CACHE["rates"].get(from_currency, {})
    ):
        return _EXCHANGE_CACHE["rates"][from_currency].get(to_currency)

    try:
        r = requests.get(f"https://open.er-api.com/v6/latest/{from_currency}", timeout=10)
        r.raise_for_status()
        rates = r.json().get("rates", {})
        _EXCHANGE_CACHE["rates"][from_currency] = rates
        _EXCHANGE_CACHE["timestamp"] = now
        return rates.get(to_currency)
    except Exception:
        return None
