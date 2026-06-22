"""
Data loading and helper utilities — all @st.cache_data functions live here.
Imported by main.py, competitor_view.py.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT       = Path(__file__).parent.parent
DATA_DIR   = ROOT / "data" / "cleaned"
EXCEL_PATH = ROOT / "Anaysis" / "OSH Datenanalyse.xlsx"

COUNTRY_NAME_MAP = {
    "morocco": "Morocco",
    "egypt":   "Egypt",
    "tunisia": "Tunisia",
}


# ---------------------------------------------------------------------------
# OSH facility loaders
# ---------------------------------------------------------------------------
@st.cache_data
def load_country(key: str) -> pd.DataFrame:
    path = DATA_DIR / f"{key}_clean.parquet"
    if not path.exists():
        st.error(f"Cleaned data not found: {path}\nRun: python scripts/clean_data.py")
        st.stop()
    df = pd.read_parquet(path)
    for col in ("sector", "contributor_list", "facility_type_list",
                "processing_type_list", "product_type_list"):
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: list(x) if isinstance(x, (list, np.ndarray)) else []
            )
    return df


@st.cache_data
def load_all() -> pd.DataFrame:
    frames = []
    for key in ("morocco", "egypt", "tunisia"):
        try:
            frames.append(load_country(key))
        except Exception:
            pass
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def get_data(country_key) -> pd.DataFrame:
    return load_all() if country_key is None else load_country(country_key)


# ---------------------------------------------------------------------------
# Competitor loader
# ---------------------------------------------------------------------------
@st.cache_data
def load_competitors() -> pd.DataFrame:
    path = DATA_DIR / "competitors_locations.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


# ---------------------------------------------------------------------------
# Verified brands loader
# ---------------------------------------------------------------------------
_VERIFIED_BRANDS_FALLBACK = [
    "AB Lindex", "ASOS", "About You", "Adidas", "Amfori", "Arcadia Group",
    "Armani", "Armedangels", "Asda", "Bel&Bo", "Benetton Group", "Bestseller",
    "Bluebird", "Boden", "Capri Holdings", "Coonen by design", "Cutter & Buck",
    "Debenhams", "Denim House", "Desigual", "DuPont", "ELK", "El Corte Ingles",
    "Elite Merchandising Corp", "Etam Lingerie", "Fabienne Chapot", "Fairtrade",
    "Fanatics", "Find Sourcing", "Fjällräven", "Fruit of the Loom", "G-Star RAW",
    "GAP Inc.", "H&M Group", "HEMA", "Hugo Boss", "Inditex", "JD", "JOG Group",
    "John Lewis", "Just Brands", "Karl Lagerfeld", "Kiabi Brands", "Kontoor Brands",
    "Lacoste", "Maison123", "Mango", "Marks & Spencer", "Matalan",
    "Millenium Ladieswear", "Mint Velvet", "Missguided", "NA-KD", "Neotex",
    "New Look Retailers", "Next Level Apparel", "Next PLC", "Nike", "Nudie Jeans",
    "One and All", "Otto", "PVH", "Passenger Clothing", "Pimkie", "Primark",
    "R.M. Williams", "Ralph Lauren Corporation", "Reiss", "River Island",
    "Royal Design", "Scotch & Soda", "Sheeba International Garments Co.",
    "Stitch Fix", "Studio Anneloes", "TFG London Brands", "Target Corporation",
    "The Very Group", "The White Company", "Tiger of Sweden", "Underarmour",
    "Undiz", "Victoria Secret", "WE Europe BV", "WM Morisson", "Wikirate",
    "Wolf Lingerie", "Worldly Fashion", "Zalando SE",
]


@st.cache_data
def load_verified_brands() -> list:
    """
    Returns the sorted, deduplicated list of brand names from column J of
    OSH Datenanalyse.xlsx (sheet: OSH Firmensuche V3). Falls back to a
    hardcoded list if the Excel file is not present (e.g. on Streamlit Cloud).
    """
    try:
        if not EXCEL_PATH.exists():
            raise FileNotFoundError
        df = pd.read_excel(
            EXCEL_PATH, sheet_name="OSH Firmensuche V3", usecols="J", header=0
        )
        col = df.iloc[:, 0]
        return sorted({
            str(v).strip()
            for v in col.dropna()
            if str(v).strip() and str(v).strip().lower() not in ("unternehmen", "")
        })
    except Exception:
        return sorted(set(_VERIFIED_BRANDS_FALLBACK))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def all_unique_values(df: pd.DataFrame, col: str) -> list:
    vals = set()
    for cell in df[col]:
        if isinstance(cell, (list, np.ndarray)):
            vals.update(cell)
    return sorted(vals)


def osh_to_csv_bytes(df: pd.DataFrame) -> bytes:
    export = df.copy()
    for col in ("sector", "contributor_list", "facility_type_list",
                "processing_type_list", "product_type_list"):
        if col in export.columns:
            export[col] = export[col].apply(
                lambda x: " | ".join(str(i) for i in x)
                if isinstance(x, (list, np.ndarray)) else x
            )
    return export.to_csv(index=False).encode("utf-8")


def comp_to_csv_bytes(df: pd.DataFrame) -> bytes:
    cols = [
        "company", "country", "city", "facility_name", "facility_type",
        "bonded_warehouse", "indoor_size", "outdoor_size", "services",
        "comments", "address", "lat", "lng", "source_1",
    ]
    export = df[[c for c in cols if c in df.columns]]
    return export.to_csv(index=False).encode("utf-8")
