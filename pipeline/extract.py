"""BigQuery extraction for GDELT GKG AI-related articles."""

import logging
from datetime import date, timedelta

import pandas as pd
from google.cloud import bigquery

logger = logging.getLogger(__name__)

QUERY = """
SELECT
    DocumentIdentifier AS url,
    SourceCollectionIdentifier,
    Extras AS extras,
    V2Locations AS raw_locations,
    V2Tone AS raw_tone,
    DATE AS raw_date,
    V2Themes AS raw_themes,
    SharingImage
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME BETWEEN TIMESTAMP(@start_date) AND TIMESTAMP(@end_date)
  AND V2Themes LIKE '%TAX_FNCACT_ARTIFICIAL_INTELLIGENCE%'
"""


def extract(start_date: date | None = None, end_date: date | None = None) -> pd.DataFrame:
    """Extract AI-related articles from GDELT BigQuery.

    Args:
        start_date: Inclusive start date. Defaults to yesterday.
        end_date: Inclusive end date. Defaults to today.

    Returns:
        Raw DataFrame with GDELT GKG columns.
    """
    if start_date is None:
        start_date = date.today() - timedelta(days=3)
    if end_date is None:
        end_date = date.today() - timedelta(days=1)

    client = bigquery.Client()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
    )

    logger.info("Querying GDELT GKG for %s to %s", start_date, end_date)
    df = client.query(QUERY, job_config=job_config).to_dataframe()
    logger.info("Extracted %d rows", len(df))
    return df
