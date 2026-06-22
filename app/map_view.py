"""
Map builders: build_hexbin_map (pydeck) and build_heatmap (folium).
"""

import math
from collections import defaultdict

import folium
from folium.plugins import Fullscreen, HeatMap
import numpy as np
import pandas as pd
import pydeck as pdk

COUNTRY_CENTERS = {
    "morocco": [31.5, -7.0],
    "egypt":   [26.8, 30.8],
    "tunisia": [33.9,  9.5],
    None:      [30.0, 10.0],
}
COUNTRY_ZOOM = {
    "morocco": 6,
    "egypt":   6,
    "tunisia": 6,
    None:      4,
}

_COMP_PALETTE = [
    "#e6550d", "#756bb1", "#31a354", "#0571b0", "#ca0020",
    "#4dac26", "#d6604d", "#92c5de", "#f1b6da", "#74c476",
    "#bcbddc", "#f4a582", "#b8e186", "#8dd3c7", "#fb8072",
    "#80b1d3", "#fdb462",
]


def _spiral_jitter(df: pd.DataFrame, step: float = 0.008) -> pd.DataFrame:
    """
    Spread rows that share identical lat/lng onto a golden-angle spiral so
    stacked markers separate visually. Returns a copy with adjusted lat/lng.
    """
    df = df.copy().reset_index(drop=True)
    counts = defaultdict(int)
    jlat, jlng = [], []
    for _, row in df.iterrows():
        key = (round(float(row["lat"]), 5), round(float(row["lng"]), 5))
        n = counts[key]
        counts[key] += 1
        if n == 0:
            jlat.append(float(row["lat"]))
            jlng.append(float(row["lng"]))
        else:
            angle = n * 137.508 * math.pi / 180   # golden angle
            r = step * math.sqrt(n)
            jlat.append(float(row["lat"]) + r * math.cos(angle))
            jlng.append(float(row["lng"]) + r * math.sin(angle))
    df["lat"] = jlat
    df["lng"] = jlng
    return df


# ---------------------------------------------------------------------------
# Hexbin map (pydeck HexagonLayer) — used in Tab 1
# ---------------------------------------------------------------------------
def build_hexbin_map(df: pd.DataFrame, country_key) -> pdk.Deck:
    center = COUNTRY_CENTERS.get(country_key, [30.0, 10.0])
    zoom   = COUNTRY_ZOOM.get(country_key, 4)

    point_data = (
        df[["lat", "lng", "name"]]
        .dropna(subset=["lat", "lng"])
        .rename(columns={"lng": "longitude", "lat": "latitude"})
        .to_dict(orient="records")
    )

    radius_by_zoom = {4: 25000, 5: 18000, 6: 12000, 7: 6000, 8: 3000}
    radius = radius_by_zoom.get(zoom, 12000)

    layer = pdk.Layer(
        "HexagonLayer",
        id="hexlayer",
        data=point_data,
        get_position=["longitude", "latitude"],
        radius=radius,
        elevation_scale=50,
        elevation_range=[0, 1500],
        pickable=True,
        extruded=True,
        coverage=0.9,
        color_range=[
            [29, 145, 192],
            [65, 182, 196],
            [127, 205, 187],
            [199, 233, 180],
            [237, 248, 177],
            [255, 237, 160],
            [254, 178,  76],
            [253, 141,  60],
            [240,  59,  32],
        ],
    )

    view = pdk.ViewState(
        latitude=center[0],
        longitude=center[1],
        zoom=zoom,
        pitch=45,
        bearing=0,
    )

    return pdk.Deck(
        layers=[layer],
        initial_view_state=view,
        tooltip={"text": "Facilities in cell: {elevationValue}"},
        map_style=pdk.map_styles.CARTO_LIGHT,
        map_provider="carto",
    )


# ---------------------------------------------------------------------------
# Heatmap (folium) — used in Tab 2, optionally with competitor overlay
# ---------------------------------------------------------------------------
def build_heatmap(
    df: pd.DataFrame,
    country_key,
    competitors_df: pd.DataFrame = None,
) -> folium.Map:
    center = COUNTRY_CENTERS.get(country_key, [30.0, 10.0])
    zoom   = COUNTRY_ZOOM.get(country_key, 4)
    m = folium.Map(location=center, zoom_start=zoom, tiles="CartoDB positron")

    Fullscreen(
        position="topleft",
        title="Fullscreen",
        title_cancel="Exit fullscreen",
        force_separate_button=True,
    ).add_to(m)

    # OSH production density layer
    osh_group = folium.FeatureGroup(name="OSH production facilities", show=True)
    heat_data = df[["lat", "lng"]].dropna().values.tolist()
    if heat_data:
        HeatMap(
            heat_data,
            radius=18,
            blur=12,
            max_zoom=12,
            gradient={0.2: "blue", 0.5: "lime", 0.8: "orange", 1.0: "red"},
        ).add_to(osh_group)
    osh_group.add_to(m)

    # Competitor circle markers
    if competitors_df is not None and not competitors_df.empty:
        companies = sorted(competitors_df["company"].unique())
        company_colour = {
            c: _COMP_PALETTE[i % len(_COMP_PALETTE)]
            for i, c in enumerate(companies)
        }

        comp_group = folium.FeatureGroup(name="Competitor facilities", show=True)
        jittered = _spiral_jitter(competitors_df)

        for _, row in jittered.iterrows():
            colour = company_colour.get(row["company"], "#e6550d")
            source = str(row.get("source_1", "") or "").strip()
            source_html = (
                f"<b>Source:</b> <a href='{source}' target='_blank' "
                f"style='color:#0571b0'>link</a><br>"
                if source else ""
            )

            popup_html = (
                "<div style='min-width:260px;font-family:sans-serif;font-size:13px'>"
                f"<b style='color:#c0392b'>{row.get('company','')}</b><br>"
                f"<span style='color:#555'>{row.get('facility_name','')}</span><br>"
                "<hr style='margin:4px 0'>"
                f"<b>City:</b> {row.get('city','')} · {row.get('country','')}<br>"
                f"<b>Address:</b> {row.get('address','—') or '—'}<br>"
                f"<b>Facility type:</b> {row.get('facility_type','')}<br>"
                f"<b>Bonded WH:</b> {row.get('bonded_warehouse','Not stated')}<br>"
                f"<b>Indoor size:</b> {row.get('indoor_size','') or '—'}<br>"
                f"<b>Outdoor size:</b> {row.get('outdoor_size','') or '—'}<br>"
                f"<b>Services:</b> {row.get('services','') or '—'}<br>"
                f"{source_html}"
                f"<i style='color:#777;font-size:11px'>{row.get('comments','')}</i>"
                "</div>"
            )

            folium.CircleMarker(
                location=[row["lat"], row["lng"]],
                radius=8,
                color="white",
                weight=2,
                fill=True,
                fill_color=colour,
                fill_opacity=0.85,
                popup=folium.Popup(popup_html, max_width=340),
                tooltip=(
                    f"{row.get('company','')} — "
                    f"{row.get('city','')} — "
                    f"{row.get('facility_type','')}"
                ),
            ).add_to(comp_group)

        comp_group.add_to(m)

    folium.LayerControl(position="topright", collapsed=False).add_to(m)
    return m
