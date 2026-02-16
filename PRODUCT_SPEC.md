# Product Specification: AI Sentiment Heatmap

## 1. Problem & Audience

Investors, analysts, and researchers with a stake in the AI industry lack a clear, real-time view of how global media sentiment toward AI is shifting. Existing tools don't make it easy to spot geographic or temporal patterns that could signal inflection points — like the "AI bubble" deflating.

This product targets anyone who wants to track the state of AI hype: investors with AI exposure, market analysts, and journalists covering the AI narrative.

## 2. Product Overview

An open-source web dashboard that visualizes global news sentiment about AI using data from the GDELT Project. The dashboard combines GDELT's built-in tone scores with custom NLP analysis of headlines to give users a multi-layered view of sentiment.

## 3. Features

### MVP (Phase 1)

- Country-level geographic heatmap of AI sentiment, filterable by date range
- Streamlit dashboard with date range controls

### Phase 2

- Animated temporal heatmap showing sentiment changing over time
- Custom NLP sentiment analysis on headlines (model TBD)
- Drill-down: click a region to see underlying articles, headlines, and sources

## 4. Data

### Source

- **GDELT Project** via Google BigQuery
- **Filter**: GDELT theme code `TAX_FNCACT_ARTIFICIAL_INTELLIGENCE` (Phase 2 may add keyword-based search to supplement)

### Fields Extracted (per article)

| Field | Description |
|-------|-------------|
| url | Article URL |
| title | Article headline |
| source_name | Publishing source |
| country_code | Country of publication/focus |
| lat/lon | Geographic coordinates |
| avg_tone | GDELT's built-in sentiment score |
| date | Publication date |
| themes | GDELT theme codes |

### Volume & Retention

- ~1,000–2,500 rows/day (~450 bytes/row, ~20–35 MB/month)
- 12-month rolling window (estimated 240–400 MB, within Supabase free tier)
- Automated cleanup of records older than 12 months

## 5. Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   GDELT      │     │   Python     │     │  Supabase    │     │  Streamlit   │
│   BigQuery   │────>│   Pipeline   │────>│  PostgreSQL  │────>│  Dashboard   │
│              │     │              │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                           │
                     GitHub Actions
                     (daily cron)
```

| Layer | Tool |
|-------|------|
| Extraction | Python + google-cloud-bigquery |
| Storage | Supabase (PostgreSQL) |
| Processing | Python (pandas + NLP model TBD in Phase 2) |
| Visualization | Streamlit + Plotly |
| Hosting | Streamlit Community Cloud (apps sleep after inactivity) |
| Scheduling | GitHub Actions (daily cron) |

## 6. Technical Constraints

- **Cost**: All tools and hosting must use free tiers or open-source software
- **Security**: API keys and secrets managed via environment variables and GitHub Secrets — never committed to the repo. Repository includes `.env.example` and `.gitignore`.
- **Collaboration**: Public GitHub repository with README and contribution guidelines
- **BigQuery quota**: Free tier provides 1 TB/month — daily queries should stay well within this

## 7. Phased Delivery

| Phase | Key Deliverable |
|-------|-----------------|
| **MVP** | Daily pipeline + country-level sentiment heatmap + Streamlit app |
| **Phase 2** | Temporal heatmap + custom NLP + drill-down |
