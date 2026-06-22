# OSH Supply Chain Analysis

Interactive visualisation of Open Supply Hub (OSH) production facility data for
**Morocco**, **Egypt**, and **Tunisia**, with an overlay of logistics competitor locations.
Built as a supporting tool for a bachelor thesis on logistics market entry into North
African apparel supply chains.

---

## What it does

- **Supply Chain Map** — Kepler-style hexbin density map of OSH production facilities.
  Click a hex cell to filter the facility table to that cluster.
- **Competitor Analysis** — Heatmap of OSH facility density overlaid with circle markers
  for 16 logistics companies (41 facility locations). Filter by company, facility type,
  bonded-warehouse status, and services.
- **Sidebar filters** — country, sector, and brand filters shared across both views.

---

## Deployment (Streamlit Cloud)

Upload only these folders/files — no raw data or source Excel files are required at runtime:

```
app/
data/cleaned/
requirements.txt
README.md
```

---

## Local setup

**Requirements:** Python 3.10+

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell
# source .venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the app
streamlit run app/main.py
```

Open **http://localhost:8501** in your browser.

---

## Regenerating the cleaned data (optional)

The pre-built Parquet files in `data/cleaned/` are included and ready to use.
To rebuild from source (requires raw files not included in this repo):

```bash
python scripts/clean_data.py          # OSH facility data → data/cleaned/
python scripts/clean_competitors.py   # Competitor locations → data/cleaned/
```

---

## Data sources

| Dataset | Source |
|---|---|
| Production facilities | [Open Supply Hub](https://opensupplyhub.org/) — downloaded 2026 |
| Competitor locations | Public company websites, press releases, industry directories — researched 2026 |
