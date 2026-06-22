"""
Tab 2: Competitor Analysis — filters, heatmap overlay, competitor table.
Rendered entirely inside st.tabs()[1] context; shared OSH df passed in.
"""

import hashlib

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from data_loader import load_competitors, comp_to_csv_bytes, COUNTRY_NAME_MAP
from map_view import build_heatmap

# Canonical service tags — keep in sync with _SERVICE_CANON in clean_competitors.py
CANONICAL_SERVICES = [
    "Air freight",
    "Automotive logistics",
    "Bonded warehousing",
    "Contract logistics",
    "Control tower / reporting",
    "Cross-docking / JIT",
    "Customs",
    "Fashion logistics",
    "Food logistics",
    "Freight forwarding",
    "Road freight",
    "Sea freight",
    "Value-added services (VAS)",
    "Warehousing",
]


# ---------------------------------------------------------------------------
# Sidebar competitor filters — always visible, note they affect Tab 2 only
# ---------------------------------------------------------------------------
def render_competitor_sidebar() -> dict:
    st.divider()
    st.subheader("Competitor Filters")
    st.caption("These filters apply to the **Competitor Analysis** tab only.")

    all_comp = load_competitors()

    if all_comp.empty:
        st.info("No competitor data loaded.")
        return {}

    # Company multiselect
    company_options = sorted(all_comp["company"].dropna().unique())
    sel_companies = st.multiselect(
        "Competitor",
        company_options,
        default=[],
        key="comp_companies",
    )

    # Facility type multiselect
    ft_options = sorted(all_comp["facility_type"].dropna().unique())
    sel_facility_types = st.multiselect(
        "Facility type",
        ft_options,
        default=[],
        key="comp_facility_type",
    )

    # Bonded warehouse radio
    bonded_choice = st.radio(
        "Bonded warehouse",
        ["All", "Yes", "No", "Not stated"],
        index=0,
        horizontal=True,
        key="comp_bonded",
    )

    # Services multiselect (canonical tags)
    sel_services = st.multiselect(
        "Services",
        CANONICAL_SERVICES,
        default=[],
        key="comp_services",
    )

    return {
        "companies":       sel_companies,
        "facility_types":  sel_facility_types,
        "bonded":          bonded_choice,
        "services":        sel_services,
    }


# ---------------------------------------------------------------------------
# Apply competitor filters
# ---------------------------------------------------------------------------
def filter_competitors(country_key, filters: dict) -> pd.DataFrame:
    all_comp = load_competitors()
    if all_comp.empty:
        return all_comp

    df = all_comp.copy()

    # Country filter
    if country_key is not None:
        country_name = COUNTRY_NAME_MAP.get(country_key, "")
        df = df[df["country"] == country_name]

    if filters.get("companies"):
        df = df[df["company"].isin(filters["companies"])]

    if filters.get("facility_types"):
        df = df[df["facility_type"].isin(filters["facility_types"])]

    if filters.get("bonded") and filters["bonded"] != "All":
        df = df[df["bonded_warehouse"] == filters["bonded"]]

    if filters.get("services"):
        # Keep row if it has ANY of the selected service tags
        def _has_service(cell):
            tags = {t.strip() for t in str(cell).split(";")} if cell else set()
            return bool(tags & set(filters["services"]))
        df = df[df["services"].apply(_has_service)]

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Tab 2 body
# ---------------------------------------------------------------------------
def render_competitor_tab(df_osh: pd.DataFrame, country_key, filters: dict):
    """
    df_osh      — OSH data already filtered by the shared sidebar
    country_key — None | "morocco" | "egypt" | "tunisia"
    filters     — dict from render_competitor_sidebar()
    """
    comp_df = filter_competitors(country_key, filters)

    st.subheader("Competitor Analysis — Heatmap + Facility Overlay")

    # Refresh counter — incrementing it changes the map key, forcing a fresh iframe mount
    if "heatmap_refresh" not in st.session_state:
        st.session_state["heatmap_refresh"] = 0

    if st.button("↺ Refresh heatmap", key="reload_comp"):
        st.session_state["heatmap_refresh"] += 1
        st.rerun()

    if df_osh.empty:
        st.warning("No OSH facilities match the current filters.")
    else:
        try:
            m = build_heatmap(df_osh, country_key, competitors_df=comp_df)
            map_state = (
                f"{country_key}|{len(df_osh)}|{len(comp_df)}"
                f"|{','.join(sorted(comp_df['company'].unique())) if not comp_df.empty else ''}"
                f"|{'|'.join(sorted(filters.get('services', [])))}"
                f"|{st.session_state['heatmap_refresh']}"
            )
            map_key = "cmap_" + hashlib.md5(map_state.encode()).hexdigest()[:10]
            st_folium(m, width="100%", height=580, returned_objects=[], key=map_key)
        except Exception as e:
            st.warning(f"Map could not be rendered: {e}")

    # Metrics
    all_comp_country = filter_competitors(country_key, {})
    c1, c2 = st.columns(2)
    c1.metric("Competitors shown", len(comp_df))
    c2.metric("Total in region", len(all_comp_country))

    # Competitor data table
    st.subheader("Competitor facility data")

    if comp_df.empty:
        st.info("No competitor facilities match the current filters.")
        return

    table_cols = [
        "company", "country", "city", "facility_name", "facility_type",
        "bonded_warehouse", "indoor_size", "outdoor_size", "services",
        "comments", "source_1",
    ]
    existing = [c for c in table_cols if c in comp_df.columns]
    col_rename = {
        "company":          "Company",
        "country":          "Country",
        "city":             "City",
        "facility_name":    "Facility name",
        "facility_type":    "Facility type",
        "bonded_warehouse": "Bonded WH",
        "indoor_size":      "Indoor size",
        "outdoor_size":     "Outdoor size",
        "services":         "Services",
        "comments":         "Comments",
        "source_1":         "Source",
    }
    display_df = comp_df[existing].rename(columns=col_rename)

    st.dataframe(
        display_df,
        use_container_width=True,
        height=400,
        column_config={
            "Source": st.column_config.LinkColumn("Source", display_text="link"),
        },
    )

    st.download_button(
        label="Download competitor data (CSV)",
        data=comp_to_csv_bytes(comp_df),
        file_name="competitors_filtered.csv",
        mime="text/csv",
    )
