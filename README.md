<div align="center">

```
    ⚡ PRICE PULSE ⚡
    ════════════════════════════
        🇺🇸  vs  🇯🇵
       💰 Best Deal Finder
```

# ⚡ Price Pulse

### Real-time Amazon price comparison across **USA 🇺🇸** and **Japan 🇯🇵**

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Streamlit](https://img.shields.io/badge/streamlit-1.32+-FF4B4B.svg?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/status-active-success.svg?style=for-the-badge)]()
[![Maintenance](https://img.shields.io/badge/maintained-yes-brightgreen.svg?style=for-the-badge)]()

**Stop checking Amazon in two tabs.** Price Pulse searches both stores simultaneously,
highlights the best deal globally, and converts everything to your favorite currency.

[✨ Features](#-features) •
[🚀 Quick Start](#-quick-start) •
[📖 Usage](#-usage) •
[🛠️ Tech Stack](#️-tech-stack) •
[🤝 Contributing](#-contributing)

</div>

---

## 🎯 What is Price Pulse?

**Price Pulse** is a free, open-source web app built with **Python + Streamlit** that lets you
compare product prices between **Amazon USA** 🇺🇸 and **Amazon Japan** 🇯🇵 in real time.

It's designed for **cross-border shoppers**, deal hunters, and anyone who wants to know if
buying from Japan or the USA gives them a better price — including shipping, ratings, and currency conversion.

> 💡 **Why "Price Pulse"?** Because prices change like a heartbeat. Price Pulse keeps you in sync.

---

## ✨ Features

### 🔍 Smart Search
- 🔎 **Dual-country search** — USA and Japan simultaneously
- 🎯 **5 sort criteria** — Price (asc/desc), rating, most reviews, best value
- 🎛️ **Advanced filters** — Prime only, in-stock only, min rating
- 📦 **Smart caching** — 24h local cache means instant results for repeated searches

### 💰 Multi-Currency
- 💵 **USD** (US Dollar)
- 🇨🇴 **COP** (Colombian Peso)
- 💴 **JPY** (Japanese Yen)
- 🔄 **Auto-conversion** with cached exchange rates (1h TTL)

### 🛡️ Three Search Methods

| Method | Cost | Limit | Best For |
|--------|------|-------|----------|
| 🆓 **Direct Scraping** | Free | Unlimited* | Daily personal use |
| 🆓 **ScraperAPI** | Free | ~33/day | Anti-bot bypass |
| 💎 **Rainforest API** | From $49/mo | 10K+/mo | Production |

### 🏆 Best Deal Detection
- 🌟 **Global winner** highlighted at the top
- 📊 **Per-country stats** — min, average, total results
- 💱 **Side-by-side comparison** with smart currency conversion

### 🎨 Polished UI
- 📱 **Responsive layout** — works on desktop and mobile
- 🌗 **Custom theme** — Amazon-inspired orange + dark cards
- ⚡ **Toast notifications** — see when results come from cache
- 🔄 **Auto-refresh** with smart caching

---

## 🖼️ Demo

```
┌─────────────────────────────────────────────┐
│  🛒 Price Pulse                              │
│  ════════════════════════════════════════    │
│                                              │
│  ⚙️ Sidebar              📊 Results          │
│  ┌──────────┐          ┌──────────────┐     │
│  │ Search:  │          │ 🇺🇸 USA        │     │
│  │ [laptop] │   ───▶   │ ┌──────────┐ │     │
│  │          │          │ │ 🏆 Best  │ │     │
│  │ ☑ USA    │          │ │ $999 USD │ │     │
│  │ ☑ Japan  │          │ │ ⭐ 4.5   │ │     │
│  │          │          │ └──────────┘ │     │
│  │ 💵 USD   │          └──────────────┘     │
│  └──────────┘                                │
└─────────────────────────────────────────────┘
```

> 📸 Add a real screenshot by running the app and saving the page!

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** — [Download here](https://www.python.org/downloads/)
  - ⚠️ During installation, check **"Add Python to PATH"**

### Installation

```bash
# 1️⃣ Clone the repo
git clone https://github.com/ArangoMzl/price-pulse.git
cd price-pulse

# 2️⃣ Create virtual environment
python -m venv venv

# 3️⃣ Activate it
# Windows (CMD):
venv\Scripts\activate
# Windows (PowerShell):
venv\Scripts\Activate.ps1
# Mac/Linux:
source venv/bin/activate

# 4️⃣ Install dependencies
pip install -r requirements.txt

# 5️⃣ Run the app
streamlit run app.py
```

🎉 The app will open automatically at **http://localhost:8501**

---

## 📖 Usage

### Basic workflow

1. **Open the app** in your browser
2. **Type** what you want to search (e.g. "wireless headphones", "laptop", "mechanical keyboard")
3. **Select countries** — USA 🇺🇸, Japan 🇯🇵, or both
4. **Choose currency** for conversions (USD / COP / None)
5. **Click 🔍 Buscar**
6. **Compare** results — the best global deal is highlighted at the top

### Example searches

| Query | Best country to search |
|-------|------------------------|
| `mechanical keyboard` | USA usually wins |
| `anime figure` | Japan wins easily |
| `laptop stand` | Mixed — depends on brand |
| `gaming mouse` | USA usually wins |
| `Japanese snacks` | Japan only |

---

## ⚙️ Configuration

Price Pulse works **out of the box** with the free scraping method. No API keys required!

But you can unlock more reliable search methods by editing `.env`:

```bash
# Copy the example file
cp .env.example .env

# Edit .env and uncomment the keys you want to use
```

### Get free API keys

| Service | Free Tier | Sign up |
|---------|-----------|---------|
| **ScraperAPI** | 1,000 requests/month | [scraperapi.com](https://www.scraperapi.com/) |
| **Rainforest API** | 100 requests (trial) | [rainforestapi.com](https://www.rainforestapi.com/) |

---

## 🛠️ Tech Stack

<div align="center">

| Layer | Technology |
|-------|-----------|
| 🎨 **Frontend** | [Streamlit](https://streamlit.io/) |
| 🐍 **Backend** | Python 3.9+ |
| 🌐 **HTTP** | [Requests](https://requests.readthedocs.io/) |
| 🍜 **Parsing** | [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) + [lxml](https://lxml.de/) |
| 🔐 **Config** | [python-dotenv](https://pypi.org/project/python-dotenv/) |
| 💱 **Currency** | [exchangerate-api.com](https://www.exchangerate-api.com/) (free, no key) |

</div>

---

## 📂 Project Structure

```
price-pulse/
├── ⚡ app.py              # Main Streamlit UI
├── 🔍 amazon_api.py       # Rainforest API client
├── 🕷️ scraper.py           # Direct Amazon scraper + ScraperAPI wrapper
├── 📋 requirements.txt    # Python dependencies
├── 🔐 .env.example        # Environment template
├── 🚫 .gitignore          # Git exclusions
├── ⚖️ LICENSE              # MIT License
├── 📖 README.md           # This file
├── 🎨 .streamlit/
│   └── config.toml        # Theme configuration
└── 💾 .cache/             # Auto-generated search cache (24h TTL)
```

---

## 🧠 How It Works

```
┌──────────────┐
│ User types   │
│ "laptop"     │
└──────┬───────┘
       │
       ▼
┌──────────────────┐     ┌─────────────────┐
│ Check cache?     │────▶│ Cache HIT:      │
└──────┬───────────┘     │ Return instantly│
       │ NO              └─────────────────┘
       ▼
┌──────────────────┐
│ Scrape Amazon    │
│ USA 🇺🇸 + Japan 🇯🇵│
│ with delays      │
│ + User-Agent     │
│ rotation         │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Parse HTML       │
│ Detect currency  │
│ (USD/COP/JPY)    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Convert prices   │
│ to target        │
│ currency (USD/   │
│ COP)             │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Display: best    │
│ deal highlighted │
│ + per-country    │
│ results          │
└──────────────────┘
```

---

## 🗺️ Roadmap

- [ ] 📊 Search history with SQLite
- [ ] 📈 Historical price tracking (Keepa API)
- [ ] 📧 Email alerts when prices drop
- [ ] 🌐 More countries (UK, Germany, Mexico)
- [ ] 🔍 Image-based search (upload photo → find product)
- [ ] 📦 Wishlist with target price alerts
- [ ] 🐳 Docker support
- [ ] ☁️ Deploy to Streamlit Cloud (free hosting)
- [ ] 📱 PWA support (install as mobile app)

---

## 🤝 Contributing

Contributions are **welcome and appreciated**! 💜

1. 🍴 Fork the repo
2. 🌿 Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. 💾 Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. 📤 Push to the branch (`git push origin feature/AmazingFeature`)
5. 🎉 Open a Pull Request

### Ideas for contributions

- 🌍 Add support for more Amazon regions
- 🎨 Improve UI/UX
- 🐛 Fix bugs or edge cases
- 📝 Improve documentation
- 🧪 Add tests
- 🌐 Translate the UI to other languages

---

## 🐛 Troubleshooting

<details>
<summary><b>❌ "No module named 'streamlit'"</b></summary>

You didn't activate the virtual environment or install dependencies:
```bash
venv\Scripts\activate
pip install -r requirements.txt
```
</details>

<details>
<summary><b>❌ Amazon asks for CAPTCHA</b></summary>

Amazon is rate-limiting your IP. Try:
1. ⏰ Wait 10-15 minutes
2. 🔌 Use a VPN
3. 🔑 Switch to ScraperAPI (free tier) in the sidebar
4. 💎 Or use Rainforest API (paid)
</details>

<details>
<summary><b>❌ Prices look wrong (e.g. "USD 2,024,751")</b></summary>

Amazon detected your location and is showing prices in your local currency (e.g. COP).
The app now auto-detects and labels them correctly. Clear the cache:
```bash
# Sidebar → "🗑️ Limpiar caché"
# Or manually:
rm -rf .cache
```
</details>

<details>
<summary><b>❌ Port 8501 already in use</b></summary>

Streamlit will offer to use another port. Accept with `Y`.
Or specify manually: `streamlit run app.py --server.port 8502`
</details>

---

## ⚖️ License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for the full text.

> ⚠️ **Disclaimer**: The direct scraping method queries Amazon without explicit authorization.
> It's intended for **personal and moderate use**. Respect Amazon's Terms of Service.
> For commercial use, please use the official APIs.

---

## 🙏 Acknowledgments

- 🛒 [Amazon](https://amazon.com) — for being the marketplace we all use
- 🌐 [Rainforest API](https://www.rainforestapi.com/) — for the clean data API
- 🔧 [ScraperAPI](https://www.scraperapi.com/) — for handling anti-bot
- 💱 [exchangerate-api.com](https://www.exchangerate-api.com/) — for free currency conversion
- 🎨 [Streamlit](https://streamlit.io/) — for making Python web apps a joy
- 💜 All open-source contributors

---

## 👤 Author

Built with ❤️ by **[Your Name]**

- 🌐 Website: [your-site.com](https://your-site.com)
- 💼 LinkedIn: [Your Name](https://linkedin.com/in/yourname)
- 🐦 Twitter: [@yourhandle](https://twitter.com/yourhandle)
- 📧 Email: your.email@example.com

---

## ⭐ Show your support

If **Price Pulse** helped you save money on a purchase, give it a ⭐ on GitHub!
It helps others discover the project.

<div align="center">

```
╔═══════════════════════════════════════╗
║                                       ║
║   ⚡ Made with ❤️ for deal hunters    ║
║                                       ║
╚═══════════════════════════════════════╝
```

**[⬆ back to top](#-price-pulse)**

</div>
