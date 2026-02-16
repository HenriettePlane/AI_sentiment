"""AI Sentiment Heatmap — Streamlit Dashboard."""

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
fig = px.choropleth(
    df,
    locations="country_code",
    locationmode="ISO-3166-1 alpha-2",
    color="avg_tone",
    hover_name="country_code",
    hover_data={"article_count": True, "avg_tone": ":.2f"},
    color_continuous_scale="RdYlGn",
    range_color=[-10, 10],
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
