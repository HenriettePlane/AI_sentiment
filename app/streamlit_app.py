"""AI Sentiment Heatmap — Streamlit Dashboard."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import date, timedelta
from supabase import create_client

from config.settings import SUPABASE_URL, SUPABASE_ANON_KEY

st.set_page_config(page_title="AI Sentiment Heatmap", layout="wide")


@st.cache_resource
def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


@st.cache_data(ttl=3600)
def fetch_sentiment(start_date: str, end_date: str) -> pd.DataFrame:
    client = get_supabase_client()
    response = client.rpc(
        "get_sentiment_by_country",
        {"start_date": start_date, "end_date": end_date},
    ).execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame(columns=["country_code", "avg_tone", "article_count"])


# --- Sidebar ---
st.sidebar.title("Filters")
today = date.today()
default_start = today - timedelta(days=30)
min_date = today - timedelta(days=365)

start_date = st.sidebar.date_input("Start date", value=default_start, min_value=min_date, max_value=today)
end_date = st.sidebar.date_input("End date", value=today, min_value=min_date, max_value=today)

if start_date > end_date:
    st.sidebar.error("Start date must be before end date.")
    st.stop()

# --- Data ---
df = fetch_sentiment(start_date.isoformat(), end_date.isoformat())

# --- Header ---
st.title("AI Sentiment Heatmap")
st.caption(f"Showing data from {start_date} to {end_date}")

# --- Metrics ---
if not df.empty:
    col1, col2, col3 = st.columns(3)
    col1.metric("Countries", len(df))
    col2.metric("Total Articles", int(df["article_count"].sum()))
    col3.metric("Global Avg Tone", f"{df['avg_tone'].mean():.2f}")
else:
    st.info("No data available for the selected date range.")
    st.stop()

# --- Choropleth ---
# GDELT uses FIPS 10-4 country codes; Plotly needs ISO-3166-1 alpha-3
FIPS_TO_ISO3 = {
    "AF": "AFG", "AL": "ALB", "AG": "DZA", "AO": "AGO", "AC": "ATG",
    "AR": "ARG", "AM": "ARM", "AS": "AUS", "AU": "AUT", "AJ": "AZE",
    "BF": "BHS", "BA": "BHR", "BG": "BGD", "BB": "BRB", "BO": "BLR",
    "BE": "BEL", "BH": "BLZ", "BN": "BEN", "BT": "BTN", "BL": "BOL",
    "BK": "BIH", "BC": "BWA", "BR": "BRA", "BX": "BRN", "BU": "BGR",
    "UV": "BFA", "BY": "BDI", "CB": "KHM", "CM": "CMR", "CA": "CAN",
    "CV": "CPV", "CT": "CAF", "CD": "TCD", "CI": "CHL", "CH": "CHN",
    "CO": "COL", "CN": "COM", "CF": "COG", "CG": "COD", "CS": "CRI",
    "IV": "CIV", "HR": "HRV", "CU": "CUB", "CY": "CYP", "EZ": "CZE",
    "DA": "DNK", "DJ": "DJI", "DO": "DMA", "DR": "DOM", "EC": "ECU",
    "EG": "EGY", "ES": "SLV", "EK": "GNQ", "ER": "ERI", "EN": "EST",
    "ET": "ETH", "FJ": "FJI", "FI": "FIN", "FR": "FRA", "GB": "GAB",
    "GA": "GMB", "GG": "GEO", "GM": "DEU", "GH": "GHA", "GR": "GRC",
    "GJ": "GRD", "GT": "GTM", "GV": "GIN", "PU": "GNB", "GY": "GUY",
    "HA": "HTI", "HO": "HND", "HU": "HUN", "IC": "ISL", "IN": "IND",
    "ID": "IDN", "IR": "IRN", "IZ": "IRQ", "EI": "IRL", "IS": "ISR",
    "IT": "ITA", "JM": "JAM", "JA": "JPN", "JO": "JOR", "KZ": "KAZ",
    "KE": "KEN", "KR": "KIR", "KN": "PRK", "KS": "KOR", "KU": "KWT",
    "KG": "KGZ", "LA": "LAO", "LG": "LVA", "LE": "LBN", "LT": "LSO",
    "LI": "LBR", "LY": "LBY", "LS": "LIE", "LH": "LTU", "LU": "LUX",
    "MK": "MKD", "MA": "MDG", "MI": "MWI", "MY": "MYS", "MV": "MDV",
    "ML": "MLI", "MT": "MLT", "RM": "MHL", "MR": "MRT", "MP": "MUS",
    "MX": "MEX", "FM": "FSM", "MD": "MDA", "MN": "MCO", "MG": "MNG",
    "MJ": "MNE", "MO": "MAR", "MZ": "MOZ", "BM": "MMR", "WA": "NAM",
    "NR": "NRU", "NP": "NPL", "NL": "NLD", "NZ": "NZL", "NU": "NIC",
    "NG": "NER", "NI": "NGA", "NO": "NOR", "MU": "OMN", "PK": "PAK",
    "PS": "PLW", "PM": "PAN", "PP": "PNG", "PA": "PRY", "PE": "PER",
    "RP": "PHL", "PL": "POL", "PO": "PRT", "QA": "QAT", "RO": "ROU",
    "RS": "RUS", "RW": "RWA", "SC": "KNA", "ST": "LCA", "VC": "VCT",
    "WS": "WSM", "SM": "SMR", "TP": "STP", "SA": "SAU", "SG": "SEN",
    "RI": "SRB", "SE": "SYC", "SL": "SLE", "SN": "SGP", "LO": "SVK",
    "SI": "SVN", "BP": "SLB", "SO": "SOM", "SF": "ZAF", "SP": "ESP",
    "CE": "LKA", "SU": "SDN", "NS": "SUR", "WZ": "SWZ", "SW": "SWE",
    "SZ": "CHE", "SY": "SYR", "TW": "TWN", "TI": "TJK", "TZ": "TZA",
    "TH": "THA", "TT": "TLS", "TO": "TGO", "TN": "TON", "TD": "TTO",
    "TS": "TUN", "TU": "TUR", "TX": "TKM", "TV": "TUV", "UG": "UGA",
    "UP": "UKR", "AE": "ARE", "UK": "GBR", "US": "USA", "UY": "URY",
    "UZ": "UZB", "NH": "VUT", "VE": "VEN", "VM": "VNM", "YM": "YEM",
    "ZA": "ZMB", "ZI": "ZWE",
}

df["iso3"] = df["country_code"].map(FIPS_TO_ISO3)
df_mapped = df.dropna(subset=["iso3"])

fig = px.choropleth(
    df_mapped,
    locations="iso3",
    locationmode="ISO-3",
    color="avg_tone",
    hover_name="country_code",
    hover_data={"article_count": True, "avg_tone": ":.2f", "iso3": False},
    color_continuous_scale=[
        [0.0, "#d73027"],    # -5  strong red
        [0.15, "#f46d43"],   # -3.5
        [0.25, "#fdae61"],   # -2.5
        [0.35, "#fee08b"],   # -1.5
        [0.45, "#ffffbf"],   # -0.5
        [0.55, "#d9ef8b"],   #  0.5
        [0.65, "#a6d96a"],   #  1.5
        [0.75, "#66bd63"],   #  2.5
        [0.85, "#1a9850"],   #  3.5
        [1.0, "#006837"],    #  5   strong green
    ],
    range_color=[-5, 5],
    title="Average Sentiment by Country",
)
fig.update_layout(
    geo=dict(showframe=False, showcoastlines=True, projection_type="natural earth"),
    margin=dict(l=0, r=0, t=40, b=0),
)
st.plotly_chart(fig, use_container_width=True)

# --- Raw data ---
with st.expander("Raw data"):
    st.dataframe(df.sort_values("article_count", ascending=False), use_container_width=True)
