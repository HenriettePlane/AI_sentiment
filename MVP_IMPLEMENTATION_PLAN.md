# MVP Implementation Plan: AI Sentiment Heatmap

## Context

We need to build the MVP defined in `PRODUCT_SPEC.md`: a daily data pipeline that extracts AI-related articles from GDELT via BigQuery, stores them in Supabase, and displays a country-level sentiment heatmap in a Streamlit web app.

## Project Structure

```
capstone_project/
├── .github/workflows/daily_pipeline.yml
├── pipeline/
│   ├── __init__.py
│   ├── extract.py          # BigQuery extraction
│   ├── transform.py        # Data cleaning & parsing
│   ├── load.py             # Supabase upsert
│   ├── cleanup.py          # 12-month rolling window deletion
│   └── run.py              # Orchestrator
├── app/
│   └── streamlit_app.py    # Dashboard
├── config/
│   └── settings.py         # Env var config
├── tests/
│   ├── __init__.py
│   └── test_transform.py
├── setup_supabase.sql       # DDL + RLS + RPC function (run once in Supabase SQL Editor)
├── .env.example
├── .gitignore
├── requirements.txt
└── PRODUCT_SPEC.md          # Already exists
```

## Implementation Steps

### Step 1: Repository scaffolding
- Init git repo, create all directories and boilerplate files
- `.gitignore` (env files, __pycache__, .venv, .DS_Store, JSON keys)
- `.env.example` with all required env vars documented
- `requirements.txt`: google-cloud-bigquery, db-dtypes, pandas, supabase, streamlit, plotly, python-dotenv, pytest
- `config/settings.py`: load env vars via python-dotenv

### Step 2: Supabase schema (`setup_supabase.sql`)

**`articles` table** (single table, two location perspectives per article):
- id, url, title, source_name, avg_tone, published_date, themes (TEXT[]), ingested_at
- **Most specific location** (highest granularity from V2Locations — type 5 > 4 > 3 > 2 > 1): specific_location_type, specific_location_name, specific_country_code (CHAR 2), specific_adm1_code, specific_latitude, specific_longitude
- **Most mentioned location** (most frequently appearing location in V2Locations): mentioned_location_type, mentioned_location_name, mentioned_country_code (CHAR 2), mentioned_adm1_code, mentioned_latitude, mentioned_longitude
- UNIQUE constraint on (url, published_date) for upsert dedup
- Indexes on published_date, (specific_country_code, published_date), (mentioned_country_code, published_date)

**MVP heatmap** aggregates by mentioned_country_code (most representative of what the article is about). Phase 2 can use specific_* columns for sub-country drill-down.

**Sentiment aggregation**: simple unweighted average of avg_tone per country for MVP. Normalization and weighted averaging (by source diversity, recency, etc.) deferred to Phase 2.

**RLS policies**: public read, service_role write
**RPC function** `get_sentiment_by_country(start_date, end_date)` — groups by mentioned_country_code, returns avg_tone and article_count.

### Step 3: `pipeline/extract.py`
- Query `gdelt-bq.gdeltv2.gkg_partitioned` filtered by `_PARTITIONTIME` (critical for free tier) and theme `TAX_FNCACT_ARTIFICIAL_INTELLIGENCE`
- Return raw columns: url, source_name, raw_locations, raw_tone, raw_date, raw_themes, extras
- Default date range: yesterday to today

### Step 4: `pipeline/transform.py`
- Parse functions:
  - `parse_tone` — first CSV value from V2Tone
  - `parse_locations` — parses ALL semicolon-separated entries from V2Locations into a list of dicts (type, name, country_code, adm1, lat, lon)
  - `select_most_specific` — from parsed locations, pick the one with the highest type value (most granular)
  - `select_most_mentioned` — from parsed locations, pick the one whose (country_code, name) appears most frequently
  - `parse_date` — YYYYMMDD... to YYYY-MM-DD
  - `parse_themes` — split on ; and strip offsets
- `transform(df)` → single cleaned DataFrame with article fields + specific_* and mentioned_* location columns
- Drop rows missing both country codes and avg_tone/published_date; dedup by url+date
- Title: use GKG Extras field when available, fall back to URL. Proper title extraction deferred to Phase 2.
- Unit tests in `tests/test_transform.py` with hardcoded GDELT format strings, including multi-location V2Locations entries

### Step 5: `pipeline/load.py`
- Upsert to `articles` table in batches of 500 using `on_conflict="url,published_date"`
- Single table, no FK resolution needed
- Uses service_role key

### Step 6: `pipeline/cleanup.py`
- Delete articles where published_date < (today - 365 days)

### Step 7: `pipeline/run.py`
- Orchestrate: extract → transform → load → cleanup with logging
- Accept optional CLI args for backfill: `python -m pipeline.run 2025-01-01 2025-06-01`

### Step 8: `app/streamlit_app.py`
- Sidebar: date range picker (default last 30 days, max 365 days back)
- Metrics row: countries covered, total articles, global avg tone
- Plotly choropleth: country_code locations, RdYlGn color scale, range -10 to 10
- Collapsible raw data table
- Uses Supabase anon key (read-only) and the `get_sentiment_by_country` RPC function
- `st.cache_data(ttl=3600)` for query caching

### Step 9: GitHub Actions (`daily_pipeline.yml`)
- Cron: 06:00 UTC daily
- workflow_dispatch for manual runs
- Steps: checkout, setup Python 3.12, pip install, GCP auth via `google-github-actions/auth@v2`, run pipeline
- Secrets: GCP_SERVICE_ACCOUNT_JSON, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

## Verification

1. **Extract**: Run locally, confirm 1,000–2,500 rows returned for one day, check BigQuery bytes scanned < 5 GB
2. **Transform**: `pytest tests/test_transform.py` — all parse functions covered
3. **Load**: Load test rows, check Supabase Table Editor, run twice to confirm upsert dedup
4. **Cleanup**: Temporarily set RETENTION_DAYS=0, verify deletion
5. **Full pipeline**: `python -m pipeline.run` — data appears in Supabase
6. **Streamlit**: `streamlit run app/streamlit_app.py` — map renders, date picker works, metrics correct
7. **GitHub Actions**: Manual trigger via workflow_dispatch, monitor logs

## Key Design Decisions

- **Raw extraction + separate transform**: keeps extract pure (network I/O only), transform independently testable
- **Supabase RPC for aggregation**: returns ~200 rows instead of 75k, avoids hitting 50k row read limit
- **Partitioned BigQuery table**: ~2-5 GB/day scanned vs 3.6 TB+ for unpartitioned — essential for free tier
- **GKG Extras field for title**: GKG doesn't have a title column; Extras sometimes contains it, URL is fallback. Proper extraction deferred to Phase 2.
- **Two location perspectives per article**: V2Locations contains multiple locations. Rather than storing all of them, we extract the most specific (highest granularity) and most mentioned (most frequent). MVP aggregates by mentioned_country_code; Phase 2 can use specific_* columns for sub-country drill-down. No separate table, no JSON blobs.
- **Simple unweighted average for MVP**: each article counts equally toward a country's sentiment score. Weighted/normalized scoring deferred to Phase 2.
