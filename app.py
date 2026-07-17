"""
Price Comparator - Amazon USA y Japon
"""
import os
import streamlit as st

from amazon_api import AmazonSearch, Product, convert_currency
from scraper import (
    AmazonScraper,
    ScraperAPIWrapper,
    CaptchaError,
    cache_stats,
    clear_cache,
)


st.set_page_config(
    page_title="Price Comparator",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .best-deal {
        background: linear-gradient(90deg, #ffd700 0%, #ffec8b 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #ffa500;
        margin-bottom: 1rem;
    }
    .price-tag {
        font-size: 1.5rem;
        font-weight: bold;
        color: #B12704;
    }
    .meta-info {
        color: #565959;
        font-size: 0.85rem;
    }
    .cache-info {
        background-color: #e8f5e9;
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        font-size: 0.85rem;
        color: #2e7d32;
    }
</style>
""", unsafe_allow_html=True)

MAX_RESULTS = 5


def render_product_card(product: Product):
    cols = st.columns([1, 4, 1.2])

    with cols[0]:
        if product.image:
            st.markdown(
                f'<img src="{product.image}" width="130" style="border-radius:8px;">',
                unsafe_allow_html=True,
            )
        else:
            st.markdown("📦")

    with cols[1]:
        st.markdown(f"**{product.title[:120]}{'...' if len(product.title) > 120 else ''}**")

        meta_parts = []
        if product.rating is not None:
            stars = "⭐" * int(round(product.rating))
            meta_parts.append(f"{stars} {product.rating}/5")
        if product.reviews_count is not None:
            meta_parts.append(f"({product.reviews_count:,} reseñas)")
        if product.is_prime:
            meta_parts.append("⚡ Prime")
        if product.asin:
            meta_parts.append(f"ASIN: {product.asin}")

        if meta_parts:
            st.markdown(
                f"<p class='meta-info'>{' • '.join(meta_parts)}</p>",
                unsafe_allow_html=True,
            )

        if product.shipping:
            st.caption(f"📦 {product.shipping}")

        st.caption(f"🌍 {product.country}")

    with cols[2]:
        if product.price is not None:
            st.markdown(
                f"<p class='price-tag'>{product.currency} {product.price:,.2f}</p>",
                unsafe_allow_html=True,
            )
            if product.currency != "COP":
                converted = convert_currency(product.price, product.currency, "COP")
                if converted:
                    st.caption(f"🇨🇴 ≈ COP {converted:,.0f}")
        else:
            st.caption("Precio no disponible")

        if product.url:
            st.link_button(
                "Ver en Amazon ↗",
                product.url,
                use_container_width=True,
            )

    st.divider()


def filter_and_sort(products: list[Product], sort_by: str, only_prime: bool, only_with_price: bool):
    filtered = products

    if only_prime:
        filtered = [p for p in filtered if p.is_prime]

    if only_with_price:
        filtered = [p for p in filtered if p.price is not None]

    if sort_by == "💰 Precio (menor a mayor)":
        filtered.sort(key=lambda p: p.price if p.price is not None else float("inf"))
    elif sort_by == "💰 Precio (mayor a menor)":
        filtered.sort(key=lambda p: p.price if p.price is not None else 0, reverse=True)
    elif sort_by == "⭐ Rating (mejor)":
        filtered.sort(key=lambda p: p.rating if p.rating is not None else 0, reverse=True)
    elif sort_by == "📝 Más reseñas":
        filtered.sort(key=lambda p: p.reviews_count or 0, reverse=True)
    elif sort_by == "🎯 Mejor valor (rating/precio)":
        def value_score(p):
            if p.price and p.rating and p.reviews_count:
                return (p.rating * (p.reviews_count ** 0.3)) / p.price
            return 0
        filtered.sort(key=value_score, reverse=True)

    return filtered


def get_client(method: str):
    if method == "🆓 Scraping directo (gratis)":
        return AmazonScraper()
    elif method == "🆓 ScraperAPI (1000 gratis/mes)":
        return ScraperAPIWrapper()
    else:
        return AmazonScraper()


st.title("🛒 Comparador de Precios")
st.markdown("Busca productos en **Amazon USA** 🇺🇸 y **Amazon Japón** 🇯🇵 y compara opciones.")

with st.sidebar:
    st.header("⚙️ Configuración de búsqueda")

    method = st.radio(
        "🔧 Método de búsqueda",
        options=[
            "🆓 Scraping directo (gratis)",
            "🆓 ScraperAPI (1000 gratis/mes)",
        ],
        index=0,
        help="Scraping directo es gratis pero puede ser bloqueado. ScraperAPI es más confiable.",
    )

    st.divider()

    search_query = st.text_input(
        "¿Qué producto buscas?",
        placeholder="Ej: laptop, headphones, ssd...",
    )

    st.subheader("🌍 Países a buscar")
    col_usa, col_jpn = st.columns(2)
    with col_usa:
        search_usa = st.checkbox("🇺🇸 USA", value=True)
    with col_jpn:
        search_japan = st.checkbox("🇯🇵 Japón", value=True)

    st.subheader("🔀 Ordenar por")
    sort_by = st.selectbox(
        "Criterio de orden",
        [
            "💰 Precio (menor a mayor)",
            "💰 Precio (mayor a menor)",
            "⭐ Rating (mejor)",
            "📝 Más reseñas",
            "🎯 Mejor valor (rating/precio)",
        ],
        label_visibility="collapsed",
    )

    st.subheader("🎛️ Filtros")
    only_prime = st.checkbox("Solo productos Prime", value=False)
    only_with_price = st.checkbox("Solo con precio visible", value=True)

    st.divider()

    if "Scraping directo" in method:
        stats = cache_stats()
        st.markdown(
            f"<div class='cache-info'>📦 Caché: {stats['entries']} búsquedas guardadas "
            f"({stats['size_mb']:.2f} MB, {stats['ttl_hours']}h TTL)</div>",
            unsafe_allow_html=True,
        )
        if st.button("🗑️ Limpiar caché", use_container_width=True):
            n = clear_cache()
            st.success(f"✅ {n} entradas eliminadas")
            st.rerun()
    elif "ScraperAPI" in method:
        has_key = bool(os.getenv("SCRAPER_API_KEY"))
        if has_key:
            st.success("✅ ScraperAPI Key configurada")
        else:
            st.error("❌ SCRAPER_API_KEY no encontrada")
            st.markdown("[Obtener gratis →](https://www.scraperapi.com/)")

    search_btn = st.button("🔍 Buscar", type="primary", use_container_width=True)


if not search_btn:
    st.info(
        "👈 Configura tu búsqueda en el panel lateral y presiona **Buscar**."
    )
    st.stop()

if not search_query or not search_query.strip():
    st.warning("⚠️ Por favor escribe un producto para buscar.")
    st.stop()

if not search_usa and not search_japan:
    st.warning("⚠️ Selecciona al menos un país.")
    st.stop()


client = get_client(method)


def do_search(domain: str, country_label: str):
    label = f"🔍 Buscando '{search_query}' en {country_label}..."
    with st.spinner(label):
        cached = client._get_cache(search_query, domain) if hasattr(client, "_get_cache") else None
        if cached is not None:
            st.toast(f"⚡ Resultado de caché para {country_label}", icon="⚡")
        return client.search(search_query, domain=domain, max_results=MAX_RESULTS)


results: dict[str, list[Product]] = {}
errors: dict[str, str] = {}

if search_usa:
    try:
        results["🇺🇸 Amazon USA"] = do_search("amazon.com", "Amazon USA")
    except CaptchaError as e:
        errors["🇺🇸 Amazon USA"] = str(e)
    except Exception as e:
        errors["🇺🇸 Amazon USA"] = f"Error: {e}"

if search_japan:
    try:
        results["🇯🇵 Amazon Japón"] = do_search("amazon.co.jp", "Amazon Japón")
    except CaptchaError as e:
        errors["🇯🇵 Amazon Japón"] = str(e)
    except Exception as e:
        errors["🇯🇵 Amazon Japón"] = f"Error: {e}"


for country, err in errors.items():
    if "CAPTCHA" in err:
        st.error(err)
    else:
        st.error(f"❌ {country}: {err}")

if not results:
    st.stop()


all_priced = [p for products in results.values() for p in products if p.price is not None]
if all_priced and len(results) > 1:
    st.markdown("---")
    st.subheader("🏆 Mejor oferta global")

    def price_in_cop(p: Product):
        if p.currency == "COP":
            return p.price
        converted = convert_currency(p.price, p.currency, "COP")
        return converted if converted is not None else float("inf")

    best = min(all_priced, key=price_in_cop)
    price_cop = price_in_cop(best)

    st.markdown('<div class="best-deal">', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 4])
    with col1:
        if best.image:
            st.markdown(
                f'<img src="{best.image}" width="150" style="border-radius:8px;">',
                unsafe_allow_html=True,
            )
    with col2:
        st.markdown(f"### {best.title[:150]}")
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Precio original", f"{best.currency} {best.price:,.2f}")
        col_b.metric("En COP", f"🇨🇴 COP {price_cop:,.0f}" if price_cop != float("inf") else "—")
        col_c.metric("Rating", f"{best.rating}⭐" if best.rating else "N/A")
        col_d.metric("Tienda", best.country)
        st.link_button("🛒 Ir al producto", best.url, type="primary")
    st.markdown("</div>", unsafe_allow_html=True)


st.markdown("---")
st.subheader("📋 Resultados por país")

tabs = st.tabs(list(results.keys()))
for tab, (country, products) in zip(tabs, results.items()):
    with tab:
        if not products:
            st.warning(f"Sin resultados en {country}. Intenta con otro término.")
            continue

        filtered = filter_and_sort(products, sort_by, only_prime, only_with_price)

        if not filtered:
            st.warning("Ningún producto pasa los filtros. Ajusta los criterios.")
            continue

        priced = [p for p in filtered if p.price is not None]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total encontrados", len(products))
        col2.metric("Después de filtros", len(filtered))
        if priced:
            min_price = min(p.price for p in priced)
            avg_price = sum(p.price for p in priced) / len(priced)
            col3.metric("Precio mínimo", f"{priced[0].currency} {min_price:,.2f}")
            col4.metric("Precio promedio", f"{priced[0].currency} {avg_price:,.2f}")

        st.markdown("")

        for product in filtered:
            render_product_card(product)


st.markdown("---")
stats = cache_stats()
st.caption(
    f"💡 Caché: {stats['entries']} entradas · "
    f"Los precios son en tiempo real de Amazon."
)
