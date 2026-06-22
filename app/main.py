"""
OSH Supply Chain Analysis — Streamlit App
Run: streamlit run app/main.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# Ensure sibling modules in app/ are importable when run via `streamlit run app/main.py`
sys.path.insert(0, str(Path(__file__).parent))

from data_loader import (
    get_data,
    load_verified_brands,
    all_unique_values,
    osh_to_csv_bytes,
)
from map_view import build_hexbin_map, build_heatmap
from competitor_view import render_competitor_sidebar, render_competitor_tab

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="OSH Supply Chain Analysis",
    page_icon="🗺️",
    layout="wide",
)

st.title("OSH Supply Chain Analysis — Morocco · Egypt · Tunisia")
st.caption(
    "Open Supply Hub production facility data. Visualisation for bachelor thesis "
    "on logistics market entry. Data: Open Supply Hub 2026."
)

# Make tabs larger and visually prominent
st.markdown("""
<style>
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    margin-top: 8px;
}
.stTabs [data-baseweb="tab"] {
    font-size: 1.1rem;
    font-weight: 600;
    padding: 10px 28px;
    border-radius: 6px 6px 0 0;
    background-color: #f0f2f6;
    color: #444;
}
.stTabs [aria-selected="true"] {
    background-color: #ffffff;
    color: #0f1117;
    border-bottom: 3px solid #e63946;
}
</style>
""", unsafe_allow_html=True)

COUNTRIES = {
    "All Countries": None,
    "Morocco":       "morocco",
    "Egypt":         "egypt",
    "Tunisia":       "tunisia",
}

DEFAULT_SECTORS = ["Apparel"]

# ---------------------------------------------------------------------------
# Sidebar — shared controls (rendered outside st.tabs so they affect both tabs)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Controls")

    country_label = st.selectbox("Country", list(COUNTRIES.keys()))
    country_key = COUNTRIES[country_label]

    st.divider()
    st.subheader("OSH Filters")
    st.caption("Apply to both tabs.")

    df_full = get_data(country_key)

    # Sector filter — default to Apparel
    all_sectors = all_unique_values(df_full, "sector")
    initial_sectors = [s for s in DEFAULT_SECTORS if s in all_sectors]
    sel_sectors = st.multiselect("Sector", all_sectors, default=initial_sectors)

    # Brand multiselect — verified brands shown with ★ prefix
    verified_brands = load_verified_brands()
    verified_set = set(verified_brands)
    all_brands = all_unique_values(df_full, "contributor_list")
    brand_options = (
        ["★ " + b for b in all_brands if b in verified_set]
        + [b for b in all_brands if b not in verified_set]
    )

    sel_brands_raw = st.multiselect("Brand / Contributor", brand_options, default=[])
    sel_brands = [b.lstrip("★ ") for b in sel_brands_raw]

    # Competitor sidebar filters (always visible, affect Tab 2 only)
    comp_filters = render_competitor_sidebar()

# ---------------------------------------------------------------------------
# Apply OSH filters
# ---------------------------------------------------------------------------
df = df_full.copy()

if sel_sectors:
    df = df[df["sector"].apply(lambda s: any(sec in s for sec in sel_sectors))]

if sel_brands:
    df = df[df["contributor_list"].apply(lambda c: any(b in c for b in sel_brands))
]

# ---------------------------------------------------------------------------
# Summary metrics bar
# ---------------------------------------------------------------------------
col_m, col_e, col_t = st.columns(3)
counts = df.groupby("country_key").size()
col_m.metric("Morocco", counts.get("morocco", 0))
col_e.metric("Egypt",   counts.get("egypt",   0))
col_t.metric("Tunisia", counts.get("tunisia", 0))

# ---------------------------------------------------------------------------
# Three-tab layout
# ---------------------------------------------------------------------------
tab1, tab2, tab_about = st.tabs(["Supply Chain Map", "Competitor Analysis", "About"])

# ── About ─────────────────────────────────────────────────────────────────
with tab_about:
    st.markdown("""
## About this analysis

This dashboard was built as part of a bachelor thesis assessing logistics market entry
opportunities in Morocco, Egypt, and Tunisia, with a focus on the apparel and textile
supply chain.

---

### Production facility data — Open Supply Hub

The facility data shown in the **Supply Chain Map** tab comes from
[Open Supply Hub (OS Hub)](https://opensupplyhub.org/), a non-profit, collaborative
supply chain mapping platform. OS Hub functions as a free, public database where brands,
factories, civil society organisations, and the public can share, search, and visualise
global production locations and their connections.

For this analysis, all publicly available facility records for Morocco, Egypt, and Tunisia
were downloaded and cleaned:

- Raw data: **3,553 facilities** across the three countries
- Pipe-delimited contributor and sector fields were split and mapped to canonical brand
  and sector names
- Facilities without valid coordinates were dropped
- The resulting cleaned dataset covers **711 facilities in Morocco**, **429 in Egypt**,
  and **2,413 in Tunisia**

The hexbin map aggregates these locations into density cells — elevation and colour
indicate the number of facilities per cell, making production clusters immediately visible.

---

### Competitor data — logistics providers in the apparel industry

The **Competitor Analysis** tab shows the physical presence of logistics service providers
active in Morocco, Egypt, and Tunisia with relevance to the fashion supply chain.

The competitor set was derived from a structured market review of European logistics
providers. Starting from a longlist of providers with potential relevance to the fashion
industry, companies were filtered by confirmed operational presence in at least one of
the three target markets. A second filter applied fashion-supply-chain specialisation —
only providers with recognisable fashion-sector positioning or dedicated fashion solutions
were retained.

For each provider, facility locations were researched from public sources (company
websites, press releases, industry directories). Key attributes collected per location:
facility type, bonded-warehouse status, storage capacity, services offered, and source
URL. All locations were geocoded and standardised before import.

The resulting dataset covers **16 logistics companies** and **41 facility locations**
across the three countries, with the largest concentration in Morocco.

 """)

# ── Tab 1: Supply Chain Map (Hexbin) ─────────────────────────────────────
with tab1:
    st.subheader(f"Supply Chain Map — {country_label}")

    if "hexbin_refresh" not in st.session_state:
        st.session_state["hexbin_refresh"] = 0

    if st.button("↺ Refresh map", key="reload_hexbin"):
        st.session_state["hexbin_refresh"] += 1
        st.rerun()

    # pydeck click → filter table rows to clicked hex cell
    clicked_points = None

    if df.empty:
        st.warning("No facilities match the current filters.")
    else:
        deck = build_hexbin_map(df, country_key)
        hexbin_key = f"hexbin_{country_key}_{len(df)}_{st.session_state['hexbin_refresh']}"
        event = st.pydeck_chart(
            deck,
            use_container_width=True,
            height=580,
            on_select="rerun",
            selection_mode="single-object",
            key=hexbin_key,
        )
        try:
            picked = event.selection.objects.get("hexlayer", [])
            if picked:
                clicked_points = picked[0].get("points", [])
        except Exception:
            clicked_points = None

    # Export
    st.subheader("Export")
    st.download_button(
        label="Download filtered data (CSV)",
        data=osh_to_csv_bytes(df),
        file_name=f"osh_{country_label.lower().replace(' ', '_')}_filtered.csv",
        mime="text/csv",
    )

    # Facility data table — narrow to clicked hex cell when one is selected
    display_cols = [
        "os_id", "name", "address", "country_name",
        "lat", "lng", "sector_display", "contributor_display",
        "number_of_workers", "parent_company",
        "facility_type_list", "processing_type", "product_type",
        "contribution_date",
    ]

    df_table = df.copy()

    if clicked_points:
        # Each point has "position": [lng, lat] and "index" keys
        try:
            indices = [p["index"] for p in clicked_points if "index" in p]
            if indices:
                df_table = df.iloc[indices]
                st.caption(f"Showing {len(df_table)} facilities in selected hex cell. Click elsewhere to reset.")
            else:
                # fallback: match by lat/lng proximity
                coords = [(p["position"][1], p["position"][0]) for p in clicked_points if "position" in p]
                if coords:
                    mask = df.apply(
                        lambda r: any(
                            abs(r["lat"] - la) < 0.001 and abs(r["lng"] - lo) < 0.001
                            for la, lo in coords
                        ),
                        axis=1,
                    )
                    df_table = df[mask]
                    if not df_table.empty:
                        st.caption(f"Showing {len(df_table)} facilities in selected hex cell. Click elsewhere to reset.")
        except Exception:
            pass

    st.subheader(
        "Facility data table"
        + (f" — {len(df_table)} of {len(df)} facilities" if len(df_table) != len(df) else "")
    )
    display_cols_existing = [c for c in display_cols if c in df_table.columns]
    _tbl = df_table[display_cols_existing].copy()
    # Flatten list columns to readable strings for table display
    for lc in ("facility_type_list", "processing_type_list", "product_type_list"):
        if lc in _tbl.columns:
            _tbl[lc] = _tbl[lc].apply(
                lambda x: " | ".join(x) if isinstance(x, (list, np.ndarray)) else (x or "")
            )
    st.dataframe(
        _tbl.rename(columns={
            "sector_display":      "sector",
            "contributor_display": "contributors",
            "facility_type_list":  "facility type",
        }),
        use_container_width=True,
        height=400,
    )

    # Structural overview expander
    with st.expander("Structural overview of the production landscape", expanded=False):
        if not df.empty:
            st.markdown("#### Facilities by country")
            country_counts = (
                df.groupby("country_name")
                .agg(
                    facilities=("os_id", "count"),
                    avg_workers=("number_of_workers", "mean"),
                    facilities_with_brands=(
                        "contributor_display",
                        lambda x: (x != "—").sum(),
                    ),
                )
                .round(0)
                .astype({"facilities": int, "facilities_with_brands": int})
            )
            st.dataframe(country_counts, use_container_width=True)

            st.markdown("#### Top brands by facility count")
            brand_rows = [
                {"brand": brand, "country": row["country_name"]}
                for _, row in df.iterrows()
                for brand in row.get("contributor_list", [])
            ]
            if brand_rows:
                brand_df = pd.DataFrame(brand_rows)
                top_brands = (
                    brand_df.groupby("brand")
                    .agg(
                        facilities=("country", "count"),
                        countries=("country", lambda x: ", ".join(sorted(set(x)))),
                    )
                    .sort_values("facilities", ascending=False)
                    .head(20)
                )
                st.dataframe(top_brands, use_container_width=True)

            st.markdown("#### Sector distribution")
            sector_rows = [
                {"sector": sec, "country": row["country_name"]}
                for _, row in df.iterrows()
                for sec in row.get("sector", [])
            ]
            if sector_rows:
                sec_df = pd.DataFrame(sector_rows)
                sec_counts = (
                    sec_df.groupby(["sector", "country"])
                    .size()
                    .unstack(fill_value=0)
                )
                # Sort by total across all displayed columns (descending)
                sec_counts["_total"] = sec_counts.sum(axis=1)
                sec_counts = sec_counts.sort_values("_total", ascending=False).drop(columns="_total")
                st.dataframe(sec_counts, use_container_width=True)

# ── Tab 2: Competitor Analysis ────────────────────────────────────────────
with tab2:
    render_competitor_tab(df, country_key, comp_filters)
