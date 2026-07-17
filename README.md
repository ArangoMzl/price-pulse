<div align="center">

# 🛒 Price Comparator

### Compara precios en **Amazon USA** 🇺🇸 y **Amazon Japón** 🇯🇵 en tiempo real

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![Streamlit](https://img.shields.io/badge/streamlit-1.32+-FF4B4B.svg?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg?style=flat)](LICENSE)

</div>

---

## ¿Qué hace?

Busca productos en Amazon USA y Japón al mismo tiempo, compara precios en USD y muestra la equivalencia en COP (Peso colombiano). El mejor precio se destaca automáticamente.

## Características

- 🔎 **Búsqueda dual** — USA y Japón simultáneamente
- 💰 **Siempre USD** — Todos los precios se muestran en dólares
- 🇨🇴 **Conversión a COP** — Equivalente en pesos colombianos
- 🏆 **Mejor oferta** — Se destaca el producto más barato
- 🎯 **5 criterios de orden** — Precio, rating, reseñas, mejor valor
- 🎛️ **Filtros** — Solo Prime, solo con precio visible
- 📦 **Caché local** — Resultados guardados 24h (sin requests repetidos)

## Métodos de búsqueda

| Método | Costo | Confiabilidad |
|--------|-------|---------------|
| 🆓 **Scraping directo** | Gratis | Puede ser bloqueado por Amazon |
| 🆓 **ScraperAPI** | Gratis (1000/mes) | Maneja anti-bot automáticamente |

## Inicio rápido

```bash
# 1. Clonar el repo
git clone https://github.com/ArangoMzl/price-pulse.git
cd price-pulse

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. (Opcional) Configurar ScraperAPI para mayor confiabilidad
# Copiar .env.example a .env y agregar tu key de scraperapi.com

# 5. Ejecutar
streamlit run app.py
```

## Tech Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | [Streamlit](https://streamlit.io/) |
| Backend | Python 3.9+ |
| HTTP | [Requests](https://requests.readthedocs.io/) |
| Parsing | [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) + lxml |
| Config | [python-dotenv](https://pypi.org/project/python-dotenv/) |
| Monedas | [exchangerate-api.com](https://www.exchangerate-api.com/) (gratis) |

## Estructura

```
price-pulse/
├── app.py              # Interfaz principal Streamlit
├── amazon_api.py       # Cliente Rainforest API + conversión de monedas
├── scraper.py          # Scraper directo + ScraperAPI wrapper
├── requirements.txt    # Dependencias
├── .env                # API keys (no se sube al repo)
├── .gitignore          # Archivos excluidos de git
├── LICENSE             # Licencia MIT
└── .streamlit/
    └── config.toml     # Tema de la app
```

## Licencia

Distribuido bajo la **[Licencia MIT](LICENSE)**. Eres libre de usar, modificar y distribuir este software.

> **Nota**: Este software consulta Amazon.com y Amazon.co.jp para obtener información de productos. El método de scraping directo está destinado para uso personal y moderado. Los usuarios son responsables de cumplir con los Términos de Servicio de Amazon. Para uso comercial, utiliza la API oficial de Amazon Product Advertising.

## Autor

Desarrollado por **ArangoMzl**
