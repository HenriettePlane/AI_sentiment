-- =============================================================
-- AI Sentiment Heatmap — Supabase schema
-- Run this once in the Supabase SQL Editor
-- =============================================================

-- 1. Articles table
CREATE TABLE IF NOT EXISTS articles (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    url             TEXT        NOT NULL,
    title           TEXT,
    source_name     TEXT,
    avg_tone        DOUBLE PRECISION,
    published_date  DATE        NOT NULL,
    themes          TEXT[],
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Most specific location (highest granularity from V2Locations)
    specific_location_type  SMALLINT,
    specific_location_name  TEXT,
    specific_country_code   CHAR(2),
    specific_adm1_code      TEXT,
    specific_latitude       DOUBLE PRECISION,
    specific_longitude      DOUBLE PRECISION,

    -- Most mentioned location (most frequently appearing in V2Locations)
    mentioned_location_type SMALLINT,
    mentioned_location_name TEXT,
    mentioned_country_code  CHAR(2),
    mentioned_adm1_code     TEXT,
    mentioned_latitude      DOUBLE PRECISION,
    mentioned_longitude     DOUBLE PRECISION,

    UNIQUE (url, published_date)
);

-- 2. Indexes
CREATE INDEX IF NOT EXISTS idx_articles_published_date
    ON articles (published_date);

CREATE INDEX IF NOT EXISTS idx_articles_specific_country_date
    ON articles (specific_country_code, published_date);

CREATE INDEX IF NOT EXISTS idx_articles_mentioned_country_date
    ON articles (mentioned_country_code, published_date);

-- 3. Row-Level Security
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;

-- Public read access (anon key)
CREATE POLICY "Public read access"
    ON articles FOR SELECT
    USING (true);

-- Service-role write access
CREATE POLICY "Service role insert"
    ON articles FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Service role update"
    ON articles FOR UPDATE
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role delete"
    ON articles FOR DELETE
    USING (true);

-- 4. RPC function: aggregate sentiment by country
CREATE OR REPLACE FUNCTION get_sentiment_by_country(
    start_date DATE,
    end_date   DATE
)
RETURNS TABLE (
    country_code  CHAR(2),
    avg_tone      DOUBLE PRECISION,
    article_count BIGINT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        mentioned_country_code AS country_code,
        AVG(articles.avg_tone) AS avg_tone,
        COUNT(*)               AS article_count
    FROM articles
    WHERE published_date BETWEEN start_date AND end_date
      AND mentioned_country_code IS NOT NULL
    GROUP BY mentioned_country_code;
$$;
